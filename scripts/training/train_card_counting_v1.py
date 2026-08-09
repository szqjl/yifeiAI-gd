# -*- coding: utf-8 -*-
"""
GUA-223 / CardCountingNetwork-训练方案 §8 Phase 1
CardCountingNetwork 训练入口

> 真源：docs/guandan-brain/CardCountingNetwork-训练方案.md §八 Phase 1
> 关联：GUA-223 / GUA-057 / docs/analysis/param_data_ratio.md

训练配置（Phase 1 修订 · 数据 577 样本 · 不期望收敛）：
  - 优化器：Adam(lr=3e-4, weight_decay=1e-4)
  - 损失：masked CrossEntropyLoss（3 类）
  - 批大小：32（577 样本 / 32 ≈ 18 步/epoch）
  - 最大 epoch：30
  - 早停 patience：5（val_loss 不降）
  - dropout：0.3
  - 模型保存：models/card_counting/card_counting_v1.pt
  - 训练日志：logs/training_card_counting_v1_<timestamp>.log

用法：
    python scripts/training/train_card_counting_v1.py
    python scripts/training/train_card_counting_v1.py --epochs 10 --lr 1e-4
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.etl.botzone_to_counting_dataset import iter_clean_samples
from src.v.nn.features.card_counting_network import (
    CardCountingNet,
    build_sample_input,
    count_parameters,
    save_checkpoint,
)


def train_val_split(
    samples: List[dict], val_ratio: float = 0.2, seed: int = 42
) -> Tuple[List[dict], List[dict]]:
    """按 match_id 分组切分（防同 match 泄露）。"""
    import random
    rng = random.Random(seed)
    match_to_samples: Dict[str, List[dict]] = {}
    for s in samples:
        match_to_samples.setdefault(s["match_id"], []).append(s)
    match_ids = sorted(match_to_samples.keys())
    rng.shuffle(match_ids)
    n_val = max(1, int(len(match_ids) * val_ratio))
    val_match_ids = set(match_ids[:n_val])
    train_samples = []
    val_samples = []
    for s in samples:
        if s["match_id"] in val_match_ids:
            val_samples.append(s)
        else:
            train_samples.append(s)
    return train_samples, val_samples


def prepare_batch(samples: List[dict]) -> Tuple[torch.Tensor, torch.Tensor]:
    """samples list → (history_seq batch, hand_context batch, gt batch) tensors."""
    history_list, hand_list, gt_list = [], [], []
    for s in samples:
        h, hc = build_sample_input(s)
        history_list.append(h)
        hand_list.append(hc)
        gt_list.append(s["ground_truth"])
    return (
        torch.from_numpy(np.stack(history_list)).float(),
        torch.from_numpy(np.stack(hand_list)).float(),
        torch.from_numpy(np.stack(gt_list)).long(),
    )


def masked_cross_entropy(
    logits: torch.Tensor,  # (B, 108, 3)
    target: torch.Tensor,  # (B, 108, 3) one-hot
) -> torch.Tensor:
    """3 类 softmax + CE（masked：仅对有效 slot 计算）。"""
    B = logits.shape[0]
    logits_flat = logits.view(B * 108, 3)
    target_cls = target.argmax(dim=-1).view(B * 108)  # (B*108,)
    return nn.functional.cross_entropy(logits_flat, target_cls)


def evaluate(model: CardCountingNet, val_samples: List[dict], device: str) -> Dict[str, float]:
    """返回 val_loss + 槽位准确率。"""
    model.eval()
    if not val_samples:
        return {"val_loss": 0.0, "val_acc": 0.0, "val_acc_my": 0.0, "val_acc_played": 0.0, "val_acc_rest": 0.0}
    history, hand, gt = prepare_batch(val_samples)
    history, hand, gt = history.to(device), hand.to(device), gt.to(device)
    with torch.no_grad():
        out = model(history, hand)
        loss = masked_cross_entropy(out, gt)
        pred = out.argmax(dim=-1)  # (B, 108)
        target = gt.argmax(dim=-1)
        # 整体准确率
        acc = (pred == target).float().mean().item()
        # 分项准确率
        for cls in range(3):
            pass
        gt_cls = target.cpu().numpy()
        pred_np = pred.cpu().numpy()
        n_my = (gt_cls == 0).sum()
        n_played = (gt_cls == 1).sum()
        n_rest = (gt_cls == 2).sum()
        acc_my = ((pred_np == 0) & (gt_cls == 0)).sum() / max(n_my, 1)
        acc_played = ((pred_np == 1) & (gt_cls == 1)).sum() / max(n_played, 1)
        acc_rest = ((pred_np == 2) & (gt_cls == 2)).sum() / max(n_rest, 1)
    return {
        "val_loss": loss.item(),
        "val_acc": acc,
        "val_acc_my": float(acc_my),
        "val_acc_played": float(acc_played),
        "val_acc_rest": float(acc_rest),
    }


def train(args):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("train_card_counting_v1")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("设备: %s", device)

    # 1) 加载数据
    samples = iter_clean_samples(args.data_dir, drop_warnings=True)
    if len(samples) < 50:
        logger.error("❌ 样本不足（%d < 50）", len(samples))
        sys.exit(1)
    logger.info("加载样本: %d（drop_warnings=True）", len(samples))

    train_samples, val_samples = train_val_split(samples, val_ratio=args.val_ratio)
    logger.info("训练集: %d  验证集: %d（match_id 分组防泄露）", len(train_samples), len(val_samples))

    # 2) 模型
    model = CardCountingNet(hidden_dim=args.hidden_dim, dropout=args.dropout)
    model.to(device)
    n_params = count_parameters(model)
    logger.info("模型参数量: %d（hidden_dim=%d）", n_params, args.hidden_dim)

    optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    # 3) 训练循环
    best_val_loss = float("inf")
    best_epoch = -1
    no_improve = 0
    history_log = []
    t_start = time.time()
    for epoch in range(1, args.epochs + 1):
        model.train()
        # mini-batch
        rng = np.random.default_rng(epoch)
        order = rng.permutation(len(train_samples))
        epoch_losses = []
        for i in range(0, len(order), args.batch_size):
            batch_idx = order[i: i + args.batch_size]
            batch = [train_samples[j] for j in batch_idx]
            history, hand, gt = prepare_batch(batch)
            history, hand, gt = history.to(device), hand.to(device), gt.to(device)
            optimizer.zero_grad()
            out = model(history, hand)
            loss = masked_cross_entropy(out, gt)
            loss.backward()
            optimizer.step()
            epoch_losses.append(loss.item())
        train_loss = float(np.mean(epoch_losses))
        # val
        val = evaluate(model, val_samples, device)
        elapsed = time.time() - t_start
        logger.info(
            "epoch %2d/%d  train_loss=%.4f  val_loss=%.4f  val_acc=%.4f  "
            "(my=%.3f played=%.3f rest=%.3f)  %.1fs",
            epoch, args.epochs, train_loss, val["val_loss"], val["val_acc"],
            val["val_acc_my"], val["val_acc_played"], val["val_acc_rest"], elapsed,
        )
        history_log.append({
            "epoch": epoch,
            "train_loss": train_loss,
            **val,
        })
        # 早停
        if val["val_loss"] < best_val_loss:
            best_val_loss = val["val_loss"]
            best_epoch = epoch
            no_improve = 0
            save_checkpoint(model, Path(args.output_dir) / "card_counting_v1_best.pt")
        else:
            no_improve += 1
            if no_improve >= args.patience:
                logger.info("早停：连续 %d epoch val_loss 未下降", args.patience)
                break

    # 4) 收尾
    save_checkpoint(model, Path(args.output_dir) / "card_counting_v1_final.pt")
    logger.info("=" * 60)
    logger.info("训练完成：best_epoch=%d  best_val_loss=%.4f  best_val_acc=%.4f",
                best_epoch, best_val_loss,
                history_log[best_epoch - 1]["val_acc"] if best_epoch > 0 else 0.0)
    # 摘要
    summary_path = Path(args.output_dir) / "training_summary.txt"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as f:
        f.write(f"train_samples={len(train_samples)}  val_samples={len(val_samples)}\n")
        f.write(f"model=CardCountingNet  hidden_dim={args.hidden_dim}  params={n_params}\n")
        f.write(f"best_epoch={best_epoch}  best_val_loss={best_val_loss:.4f}\n")
        for h in history_log:
            f.write(f"epoch={h['epoch']:2d}  train={h['train_loss']:.4f}  "
                    f"val={h['val_loss']:.4f}  acc={h['val_acc']:.4f}\n")
    logger.info("摘要已写入 %s", summary_path)


def main():
    parser = argparse.ArgumentParser(description="CardCountingNetwork Phase 1 训练")
    parser.add_argument("--data-dir", type=Path, default=Path("data/training/card_counting_v1"))
    parser.add_argument("--output-dir", type=Path, default=Path("models/card_counting"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()