# -*- coding: utf-8 -*-
"""
GUA-038 BC 训练器 — 行为克隆（Behavior Cloning）训练循环。

训练配置：
  - loss: CrossEntropyLoss (masked, 仅对有效 actionList 计算)
  - dropout: 0.2
  - weight_decay: 1e-4
  - max_epochs: 50
  - early_stop patience: 5

验收标准：
  - 验证集准确率 > 60%（非队胜率关单，评审 §6 验收）
  - 训练/验证双看曲线无明显过拟合
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from src.v.nn.training.bc_dataset import BCSample, create_batches, train_val_split

logger = logging.getLogger("bc_trainer")

# ── 设备 & 随机种子 ──────────────────────────────────

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def set_seed(seed: int = 42) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ── 模型加载 ──────────────────────────────────────────


def load_model(model_path: Optional[str] = None,
               device: torch.device = DEVICE) -> nn.Module:
    """加载 UltimateWinRateNet 模型用于 BC 训练或推理。

    优先从检查点加载，否则创建新模型。

    Args:
        model_path: 检查点路径，None 则创建新模型
        device: 设备

    Returns:
        nn.Module（UltimateWinRateNet 实例）
    """
    from src.train.ultimate_win_rate_training import UltimateWinRateNet
    model = UltimateWinRateNet().to(device)
    if model_path and Path(model_path).exists():
        checkpoint = torch.load(model_path, map_location=device)
        state_dict = (checkpoint.get("model_state_dict")
                      if "model_state_dict" in checkpoint
                      else checkpoint)
        model.load_state_dict(state_dict)
        logger.info("✓ BC 模型加载: %s", model_path)
    else:
        logger.info("新建 BC 模型（随机初始化）")
    model.train()
    return model


# ── 损失函数（Masked CrossEntropy）───────────────────


def masked_cross_entropy(
    logits: torch.Tensor,          # (batch, 512)
    targets: torch.Tensor,         # (batch,)  int64
    action_list_sizes: torch.Tensor,  # (batch,)  int64
    label_smoothing: float = 0.1,  # B-α 调参（2026-06-17）：防 collapse 到 top1
) -> torch.Tensor:
    """仅对有效 actionList 范围计算交叉熵（含 label_smoothing）。

    对于每个样本，创建一个 mask 使得 logits 中前 action_list_size 个位置有效，
    其余位置被屏蔽（-inf）。label_smoothing 仅在有效类上分布，
    不会泄漏到 masked 的 -1e9 类（修复 GUA-061 95M loss bug）。

    Args:
        label_smoothing: B-α 调参加入，0.1 防 top1 collapse
    """
    batch_size = logits.size(0)
    max_size = logits.size(1)

    # 创建 mask: (batch, max_size)
    arange = torch.arange(max_size, device=logits.device).unsqueeze(0)  # (1, max_size)
    sizes = action_list_sizes.unsqueeze(1)  # (batch, 1)
    mask = (arange < sizes).float()  # (batch, max_size)

    # 屏蔽无效位置
    masked_logits = logits * mask + (1 - mask) * (-1e9)

    # log_softmax
    log_probs = torch.log_softmax(masked_logits, dim=-1)  # (batch, max_size)

    # NLL of target
    nll = -log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)  # (batch,)

    # label_smoothing: 仅在有效类上分布
    valid_counts = sizes.squeeze(1).float().clamp(min=2)  # (batch,)
    # 所有有效类的平均 log_prob（含 target）
    sum_valid_log_probs = (log_probs * mask).sum(dim=1)  # (batch,)
    # 排除 target 后平均
    target_log_probs = log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)
    other_mean_log_prob = (sum_valid_log_probs - target_log_probs) / (valid_counts - 1)

    # Smoothed loss: (1-α) * NLL(target) + α * mean(NLL(others))
    smoothed_loss = (1 - label_smoothing) * nll + label_smoothing * (-other_mean_log_prob)

    return smoothed_loss.mean()


# ── 训练循环 ──────────────────────────────────────────


def train_epoch(
    model: nn.Module,
    optimizer: optim.Optimizer,
    batch_generator,
    num_batches: int,
    device: torch.device = DEVICE,
) -> float:
    """训练一个 epoch。返回平均 loss。"""
    model.train()
    total_loss = 0.0
    count = 0

    for batch_idx in range(num_batches):
        try:
            batch = next(batch_generator)
        except StopIteration:
            break

        features = torch.FloatTensor(batch["features"]).to(device)
        targets = torch.LongTensor(batch["action_indices"]).to(device)
        sizes = torch.LongTensor(batch["action_list_sizes"]).to(device)

        optimizer.zero_grad()
        outputs = model(features)
        logits = outputs["action_logits"]
        loss = masked_cross_entropy(logits, targets, sizes)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        count += 1

    return total_loss / max(1, count)


@torch.no_grad()
def evaluate(
    model: nn.Module,
    val_samples: List[BCSample],
    batch_size: int = 256,
    device: torch.device = DEVICE,
) -> Tuple[float, float]:
    """评估模型在验证集上的 loss 和准确率。

    Returns:
        (avg_loss, accuracy) — accuracy 为 top-1 匹配率
    """
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0

    batch_gen = create_batches(val_samples, batch_size=batch_size,
                               shuffle=False)
    num_batches = (len(val_samples) + batch_size - 1) // batch_size

    for _ in range(num_batches):
        try:
            batch = next(batch_gen)
        except StopIteration:
            break

        features = torch.FloatTensor(batch["features"]).to(device)
        targets = torch.LongTensor(batch["action_indices"]).to(device)
        sizes = torch.LongTensor(batch["action_list_sizes"]).to(device)

        outputs = model(features)
        logits = outputs["action_logits"]
        loss = masked_cross_entropy(logits, targets, sizes)
        total_loss += loss.item()

        # 准确率：只比较有效动作范围内
        preds = logits.argmax(dim=1)
        batch_size_actual = targets.size(0)
        for i in range(batch_size_actual):
            if sizes[i].item() <= 0:
                continue
            # 只看前 action_list_size 个 logits 中的 argmax
            valid_logits = logits[i, :sizes[i].item()].unsqueeze(0)  # (1, valid_size)
            valid_pred = valid_logits.argmax(dim=1).item()
            if valid_pred == targets[i].item():
                correct += 1
            total += 1

    avg_loss = total_loss / max(1, num_batches)
    accuracy = correct / max(1, total)
    return avg_loss, accuracy


def train(
    train_samples: List[BCSample],
    val_samples: List[BCSample],
    *,
    model: Optional[nn.Module] = None,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    batch_size: int = 64,
    max_epochs: int = 50,
    patience: int = 5,
    output_dir: str = "models/v-nn",
    model_name: str = "bc_model",
    device: torch.device = DEVICE,
    seed: int = 42,
) -> Dict[str, Any]:
    """BC 训练主循环。

    Args:
        train_samples: 训练样本列表
        val_samples: 验证样本列表
        model: 已有模型（可选），None 则创建新模型
        lr: 学习率
        weight_decay: 权重衰减
        batch_size: 批大小
        max_epochs: 最大训练轮数
        patience: 早停 patience
        output_dir: 模型保存目录
        model_name: 模型文件名（不含扩展名）
        device: 训练设备
        seed: 随机种子

    Returns:
        {
            "best_epoch": int,
            "best_val_acc": float,
            "best_val_loss": float,
            "train_losses": List[float],
            "val_losses": List[float],
            "val_accs": List[float],
            "model_path": str,
            "stopped_early": bool,
        }
    """
    set_seed(seed)

    if model is None:
        model = load_model(device=device)
    model = model.to(device)

    optimizer = optim.AdamW(
        model.parameters(),
        lr=lr,
        weight_decay=weight_decay,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    train_batches_per_epoch = max(1, len(train_samples) // batch_size)

    best_val_acc = 0.0
    best_val_loss = float("inf")
    best_epoch = 0
    epochs_no_improve = 0
    stopped_early = False

    train_losses: List[float] = []
    val_losses: List[float] = []
    val_accs: List[float] = []

    logger.info(
        "=" * 60
    )
    logger.info("BC 训练开始: lr=%.0e wd=%.0e bs=%d max_epochs=%d",
                lr, weight_decay, batch_size, max_epochs)
    logger.info("  训练样本: %d | 验证样本: %d | 设备: %s",
                len(train_samples), len(val_samples), device)
    logger.info("=" * 60)

    for epoch in range(1, max_epochs + 1):
        epoch_start = time.time()

        batch_gen = create_batches(train_samples, batch_size=batch_size,
                                   shuffle=True, seed=seed + epoch)
        train_loss = train_epoch(
            model, optimizer, batch_gen,
            num_batches=train_batches_per_epoch,
            device=device,
        )
        val_loss, val_acc = evaluate(model, val_samples,
                                     batch_size=min(batch_size * 2, 512),
                                     device=device)

        train_losses.append(train_loss)
        val_losses.append(val_loss)
        val_accs.append(val_acc)

        epoch_time = time.time() - epoch_start

        logger.info(
            "Epoch %3d/%d | train_loss=%.4f | val_loss=%.4f | val_acc=%.2f%% | %.1fs",
            epoch, max_epochs, train_loss, val_loss, val_acc * 100, epoch_time,
        )

        # 早停检查
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_val_loss = val_loss
            best_epoch = epoch
            epochs_no_improve = 0
            # 保存最佳模型
            model_path = output_path / f"{model_name}.pth"
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "train_loss": train_loss,
                "val_loss": val_loss,
                "val_acc": val_acc,
                "config": {
                    "lr": lr,
                    "weight_decay": weight_decay,
                    "batch_size": batch_size,
                    "max_epochs": max_epochs,
                },
            }, model_path)
            logger.info("  ✓ 新最佳模型保存: val_acc=%.2f%%", val_acc * 100)
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                logger.info(
                    "  早停: %d epoch 无改善 (patience=%d)",
                    epochs_no_improve, patience,
                )
                stopped_early = True
                break

    # 加载最佳模型
    best_model_path = output_path / f"{model_name}.pth"
    if best_model_path.exists():
        checkpoint = torch.load(best_model_path, map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        logger.info("✓ 加载最佳模型 (epoch %d, val_acc=%.2f%%)",
                    best_epoch, best_val_acc * 100)

    # 保存训练记录
    record = {
        "best_epoch": best_epoch,
        "best_val_acc": best_val_acc,
        "best_val_loss": best_val_loss,
        "train_losses": train_losses,
        "val_losses": val_losses,
        "val_accs": val_accs,
        "model_path": str(best_model_path),
        "stopped_early": stopped_early,
        "total_epochs": epoch,
        "total_train_samples": len(train_samples),
        "total_val_samples": len(val_samples),
        "config": {
            "lr": lr,
            "weight_decay": weight_decay,
            "batch_size": batch_size,
            "max_epochs": max_epochs,
            "patience": patience,
            "seed": seed,
        },
    }

    # 保存训练记录
    record_path = output_path / f"{model_name}_training_record.json"
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    logger.info("✓ 训练记录保存: %s", record_path)

    logger.info("=" * 60)
    logger.info("BC 训练完成: best_epoch=%d val_acc=%.2f%%",
                best_epoch, best_val_acc * 100)
    logger.info("=" * 60)

    return record