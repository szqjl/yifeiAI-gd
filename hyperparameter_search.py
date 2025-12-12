#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超参数搜索：系统性寻找最优参数组合
"""

import sys
import os
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torch.utils.data import DataLoader
from itertools import product

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.rl_agent.model import GuandanPolicyNet
from src.train.pretrain import GuandanDataset, ReplayParser


def grid_search_hyperparams():
    """网格搜索超参数"""

    print("="*100)
    print("超参数网格搜索")
    print("="*100)

    # 1. 加载数据
    print("加载测试数据...")
    parser = ReplayParser("game_records")
    raw_data = parser.load_replays()
    training_data = parser.extract_training_data(raw_data)

    # 使用较小的数据集进行快速搜索
    test_data = training_data[:1000]  # 1000个样本用于搜索
    dataset = GuandanDataset(test_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

    print(f"搜索数据集: {len(dataset)} 个样本")

    # 2. 定义搜索空间（极小规模测试）
    search_space = {
        'lr': [0.0005],  # 学习率
        'dropout_rate': [0.2],  # Dropout率
        'top_k_weight': [0.3],  # Top-K权重
        'count_penalty_weight': [0.1],  # 数量惩罚权重
        'k_multiplier': [2.0]  # K值倍数
    }

    # 生成所有参数组合
    param_names = list(search_space.keys())
    param_values = list(search_space.values())
    param_combinations = list(product(*param_values))

    print(f"\n搜索空间大小: {len(param_combinations)} 种组合")
    print("搜索参数:")
    for name, values in search_space.items():
        print(f"  {name}: {values}")

    # 3. 搜索最优参数
    results = []

    for i, params in enumerate(param_combinations):
        lr, dropout_rate, top_k_weight, count_penalty_weight, k_multiplier = params

        print(f"\n[{i+1}/{len(param_combinations)}] 测试参数组合:")
        print(f"  lr={lr}, dropout={dropout_rate}, top_k_w={top_k_weight}, count_w={count_penalty_weight}, k_mult={k_multiplier}")

        # 快速训练测试
        accuracy = quick_train_test(dataloader, lr, dropout_rate, top_k_weight, count_penalty_weight, k_multiplier)

        results.append({
            'lr': lr,
            'dropout_rate': dropout_rate,
            'top_k_weight': top_k_weight,
            'count_penalty_weight': count_penalty_weight,
            'k_multiplier': k_multiplier,
            'accuracy': accuracy
        })

        print(".2f")

    # 4. 分析结果
    print("\n" + "="*100)
    print("搜索结果分析")
    print("="*100)

    # 按准确率排序
    results.sort(key=lambda x: x['accuracy'], reverse=True)

    print("\nTop 10 参数组合:")
    print("<5")
    print("-" * 80)

    for i, result in enumerate(results[:10], 1):
        print(">5")

    # 分析最优参数的影响
    print("\n最优参数统计:")
    analyze_param_influence(results, search_space)

    # 返回最优参数
    best_params = results[0]
    print("\n🎯 最优参数组合:")
    print(f"  学习率: {best_params['lr']}")
    print(f"  Dropout: {best_params['dropout_rate']}")
    print(f"  Top-K权重: {best_params['top_k_weight']}")
    print(f"  数量惩罚权重: {best_params['count_penalty_weight']}")
    print(".1f")
    print(".2f")

    return best_params


def quick_train_test(dataloader, lr, dropout_rate, top_k_weight, count_penalty_weight, k_multiplier, epochs=20):
    """快速训练测试"""

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 创建模型
    model = GuandanPolicyNet(
        input_dim=512,
        hidden_dim=256,
        output_dim=512,
        dropout_rate=dropout_rate,
        enable_strategy_head=False,
        use_separated_features=True
    ).to(device)

    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    # 快速训练
    for epoch in range(epochs):
        model.train()
        for batch in dataloader:
            states, actions, _, _ = batch
            states = states.to(device)
            actions = actions.to(device)

            action_logits = model(states)

            # BCE损失
            bce_loss = nn.functional.binary_cross_entropy_with_logits(action_logits, actions, reduction='mean')

            # 预测数量惩罚
            action_probs = torch.sigmoid(action_logits)
            predicted_counts = (action_probs > 0.3).sum(dim=1).float()
            true_counts = actions.sum(dim=1).float()
            count_loss = nn.functional.l1_loss(predicted_counts, true_counts) * count_penalty_weight

            # Top-K约束
            true_card_counts = actions.sum(dim=1).long()
            k_values = torch.max(true_card_counts + 2, torch.ceil(true_card_counts * k_multiplier).long())
            top_k_loss = compute_simple_top_k(action_logits, actions, k_values) * top_k_weight

            # 组合损失
            loss = bce_loss + count_loss + top_k_loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        scheduler.step()

    # 评估
    model.eval()
    exact_matches = 0
    total_eval = 0

    with torch.no_grad():
        for batch in dataloader:
            states, actions, _, _ = batch
            states = states.to(device)
            actions = actions.to(device)

            action_logits = model(states)
            action_probs = torch.sigmoid(action_logits)

            predictions = (action_probs > 0.3).float()

            for i in range(len(states)):
                if torch.equal(predictions[i], actions[i]):
                    exact_matches += 1
                total_eval += 1

    return exact_matches / total_eval * 100


def compute_simple_top_k(logits, targets, k_values):
    """简化的Top-K损失计算"""
    batch_size = logits.shape[0]
    total_loss = 0.0

    for i in range(batch_size):
        k = k_values[i].item()
        if k <= 0:
            continue

        sample_probs = torch.sigmoid(logits[i])
        sample_targets = targets[i]

        # Top-K
        topk_vals, topk_idx = torch.topk(sample_probs, min(k, sample_probs.shape[0]))

        # 创建Top-K掩码
        topk_mask = torch.zeros_like(sample_targets)
        topk_mask[topk_idx] = 1.0

        # 计算Top-K之外的惩罚
        non_topk_mask = 1.0 - topk_mask
        non_topk_penalty = torch.mean((sample_probs * non_topk_mask) ** 2)

        # Top-K BCE
        topk_logits = logits[i] * topk_mask
        topk_targets = sample_targets * topk_mask
        topk_bce = nn.functional.binary_cross_entropy_with_logits(topk_logits, topk_targets)

        total_loss += topk_bce + 0.1 * non_topk_penalty

    return total_loss / batch_size


def analyze_param_influence(results, search_space):
    """分析参数影响"""
    param_stats = {}

    for param_name in search_space.keys():
        values = search_space[param_name]
        value_scores = {}

        for value in values:
            scores = [r['accuracy'] for r in results if r[param_name] == value]
            if scores:
                value_scores[value] = np.mean(scores)

        param_stats[param_name] = value_scores

    # 打印分析结果
    for param_name, value_scores in param_stats.items():
        best_value = max(value_scores.items(), key=lambda x: x[1])
        print(f"  {param_name}: 最优 {best_value[0]} (平均准确率 {best_value[1]:.2f}%)")


if __name__ == "__main__":
    print("开始超参数网格搜索...")
    print("注意：这是一个计算密集型任务，可能需要较长时间")

    best_params = grid_search_hyperparams()

    print("\n搜索完成！")
    # 可以在这里保存最优参数到配置文件
    # save_best_params(best_params)
