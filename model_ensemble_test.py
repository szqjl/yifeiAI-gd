#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模型集成方法：结合多个epoch的模型预测
"""

import sys
import os
import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import DataLoader

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.rl_agent.model import GuandanPolicyNet
from src.train.pretrain import GuandanDataset, ReplayParser


def load_model(model_path):
    """加载模型"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = GuandanPolicyNet(
        input_dim=512,
        hidden_dim=256,
        output_dim=512,
        dropout_rate=0.2,
        enable_strategy_head=False,
        use_separated_features=True
    ).to(device)

    checkpoint = torch.load(model_path, map_location=device)
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)

    model.eval()
    return model, device


def ensemble_predict(models, states, threshold=0.3):
    """集成预测：平均多个模型的概率输出"""
    all_probs = []

    for model, device in models:
        states_device = states.to(device)
        with torch.no_grad():
            logits = model(states_device)
            probs = torch.sigmoid(logits)
            all_probs.append(probs.cpu())

    # 平均概率
    avg_probs = torch.stack(all_probs).mean(dim=0)

    # 应用阈值
    predictions = (avg_probs > threshold).float()

    return predictions, avg_probs


def test_model_ensemble():
    """测试模型集成"""

    print("="*80)
    print("测试模型集成方法")
    print("="*80)

    # 1. 加载测试数据
    print("加载测试数据...")
    parser = ReplayParser("game_records")
    raw_data = parser.load_replays()
    training_data = parser.extract_training_data(raw_data)

    test_data = training_data[:500]  # 使用500个样本测试
    dataset = GuandanDataset(test_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)

    print(f"测试数据集: {len(dataset)} 个样本")

    # 2. 加载多个模型进行集成
    model_paths = [
        "models/bc_model_v1_epoch_80.pth",   # 较早的epoch
        "models/bc_model_v1_epoch_90.pth",   # 较早的epoch
        "models/bc_model_v1_epoch_100.pth",  # 最佳epoch
        "models/bc_model_v1_epoch_110.pth",  # 稍后的epoch
        "models/bc_model_v1_epoch_120.pth",  # 稍后的epoch
    ]

    print(f"\n加载 {len(model_paths)} 个模型进行集成...")
    models = []
    for path in model_paths:
        if os.path.exists(path):
            model, device = load_model(path)
            models.append((model, device))
            print(f"✓ 加载: {path}")
        else:
            print(f"✗ 跳过: {path} (文件不存在)")

    if len(models) < 2:
        print("错误：需要至少2个模型进行集成")
        return

    print(f"\n成功加载 {len(models)} 个模型")

    # 3. 测试集成效果
    print("\n开始集成预测测试...")

    ensemble_exact_matches = 0
    ensemble_card_correct = 0
    ensemble_predicted_cards = []

    single_model_results = {path: {'exact': 0, 'card_acc': 0, 'pred_count': []}
                           for path in model_paths if os.path.exists(path)}

    total_samples = 0

    for batch in dataloader:
        states, actions, _, _ = batch
        batch_size = len(states)
        total_samples += batch_size

        # 集成预测
        ensemble_predictions, ensemble_probs = ensemble_predict(models, states)

        # 计算集成结果
        for i in range(batch_size):
            # 完全匹配准确率
            if torch.equal(ensemble_predictions[i], actions[i]):
                ensemble_exact_matches += 1

            # 卡牌级别准确率
            pred_cards = torch.where(ensemble_predictions[i] > 0)[0]
            true_cards = torch.where(actions[i] > 0)[0]

            if len(true_cards) > 0:
                correct_cards = len(set(pred_cards.tolist()) & set(true_cards.tolist()))
                ensemble_card_correct += correct_cards / len(true_cards)

        # 预测卡牌数
        ensemble_predicted_cards.extend((ensemble_predictions > 0).sum(dim=1).tolist())

        # 单个模型评估（用于对比）
        for j, (model, device) in enumerate(models):
            model_path = model_paths[j]
            if not os.path.exists(model_path):
                continue

            states_device = states.to(device)
            with torch.no_grad():
                logits = model(states_device)
                probs = torch.sigmoid(logits)
                predictions = (probs > 0.3).float()

            for i in range(batch_size):
                # 完全匹配
                if torch.equal(predictions[i].cpu(), actions[i]):
                    single_model_results[model_path]['exact'] += 1

                # 卡牌级别准确率
                pred_cards = torch.where(predictions[i] > 0)[0]
                true_cards = torch.where(actions[i] > 0)[0]

                if len(true_cards) > 0:
                    correct_cards = len(set(pred_cards.tolist()) & set(true_cards.tolist()))
                    single_model_results[model_path]['card_acc'] += correct_cards / len(true_cards)

            # 预测卡牌数
            single_model_results[model_path]['pred_count'].extend(
                (predictions > 0).sum(dim=1).cpu().tolist()
            )

    # 4. 计算结果
    ensemble_exact_acc = ensemble_exact_matches / total_samples * 100
    ensemble_card_acc = ensemble_card_correct / total_samples * 100
    ensemble_avg_pred = np.mean(ensemble_predicted_cards)

    print("\n集成模型结果:")    print(".2f")
    print(".2f")
    print(".1f")

    # 5. 对比单个模型
    print("\n各模型对比:")    print("<25")
    print("-" * 80)

    for path, results in single_model_results.items():
        if results['pred_count']:
            exact_acc = results['exact'] / total_samples * 100
            card_acc = results['card_acc'] / total_samples * 100
            avg_pred = np.mean(results['pred_count'])

            model_name = os.path.basename(path)
            print(">5")

    # 6. 分析集成优势
    best_single = max(single_model_results.values(),
                     key=lambda x: x['exact']/total_samples if x['pred_count'] else 0)
    best_single_acc = best_single['exact'] / total_samples * 100

    print("\n集成效果分析:")    print(".2f")
    print(".2f")
    print(".2f")

    if ensemble_exact_acc > best_single_acc:
        print("✅ 集成成功！集成结果优于最佳单个模型")
    elif ensemble_exact_acc >= best_single_acc * 0.95:
        print("⚠️ 集成效果一般，与最佳单个模型相当")
    else:
        print("❌ 集成效果不佳，低于最佳单个模型")

    print("\n" + "="*80)


if __name__ == "__main__":
    test_model_ensemble()
