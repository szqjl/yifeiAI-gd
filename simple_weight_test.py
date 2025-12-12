#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的损失权重测试
"""

import sys
import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.rl_agent.model import GuandanPolicyNet
from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset


def quick_weight_test():
    """快速测试权重组合"""

    print("多任务学习权重优化测试")
    print("=" * 50)

    # 测试权重组合
    combinations = [
        (2.0, 0.1),  # 重视动作预测
        (1.0, 0.5),  # 平衡
        (0.5, 1.0),  # 重视策略分类
    ]

    # 加载模型和数据
    model = GuandanPolicyNet(
        input_dim=512, hidden_dim=256, output_dim=512,
        dropout_rate=0.2, enable_strategy_head=True,
        use_separated_features=False
    )

    # 加载预训练模型
    try:
        checkpoint = torch.load('models/bc_model_stage2_multitask_epoch_30.pth', map_location='cpu')
        model.load_state_dict(checkpoint['model_state_dict'] if 'model_state_dict' in checkpoint else checkpoint)
        print("加载预训练模型成功")
    except:
        print("使用随机初始化模型")
        pass

    # 加载小数据集
    parser = ReplayParser("game_records")
    raw_data = parser.load_replays()
    training_data = parser.extract_training_data(raw_data[:2])
    dataset = GuandanDataset(training_data)
    dataloader = DataLoader(dataset, batch_size=8, shuffle=False)

    results = []

    for action_w, strategy_w in combinations:
        print(f"\n测试权重: 动作={action_w}, 策略={strategy_w}")

        # 克隆模型
        model_copy = GuandanPolicyNet(
            input_dim=512, hidden_dim=256, output_dim=512,
            dropout_rate=0.2, enable_strategy_head=True,
            use_separated_features=False
        )
        model_copy.load_state_dict(model.state_dict())

        # 快速训练
        result = train_quick(model_copy, dataloader, action_w, strategy_w, epochs=2)
        results.append(result)

        print(".2f"
    # 分析结果
    print("\n结果分析:")
    best_action = max(results, key=lambda x: x['exact'])
    best_strategy = max(results, key=lambda x: x['strategy'])

    print(".2f"    print(".2f"
    # 推荐权重
    if best_action['exact'] > 1.0:
        print("推荐: 重视动作预测的权重 (2.0, 0.1)")
    else:
        print("推荐: 平衡权重 (1.0, 0.5)")

    return results


def train_quick(model, dataloader, action_weight, strategy_weight, epochs=2):
    """快速训练"""

    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    action_criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(2.0))
    strategy_criterion = nn.CrossEntropyLoss(ignore_index=7)

    for epoch in range(epochs):
        for batch in dataloader:
            states, actions, strategy_labels, _ = batch

            action_logits = model(states)
            strategy_logits = model.get_strategy_probs(states)

            action_loss = action_criterion(action_logits, actions)
            strategy_loss = strategy_criterion(strategy_logits, strategy_labels)

            total_loss = action_weight * action_loss + strategy_weight * strategy_loss

            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()

    return evaluate_quick(model, dataloader)


def evaluate_quick(model, dataloader):
    """快速评估"""

    model.eval()
    total = 0
    exact_matches = 0
    strategy_correct = 0
    strategy_total = 0

    with torch.no_grad():
        for batch in dataloader:
            states, actions, strategy_labels, _ = batch
            batch_size = len(states)
            total += batch_size

            action_logits = model(states)
            action_probs = torch.sigmoid(action_logits)
            predictions = (action_probs > 0.3).float()

            for i in range(batch_size):
                if torch.equal(predictions[i], actions[i]):
                    exact_matches += 1

            strategy_logits = model.get_strategy_probs(states)
            predicted_strategy = torch.max(strategy_logits, 1)[1]

            for i in range(batch_size):
                true_strategy = strategy_labels[i].item()
                if true_strategy < 7:
                    strategy_total += 1
                    if predicted_strategy[i].item() == true_strategy:
                        strategy_correct += 1

    return {
        'exact': exact_matches / total * 100,
        'strategy': strategy_correct / strategy_total * 100 if strategy_total > 0 else 0
    }


if __name__ == "__main__":
    quick_weight_test()
