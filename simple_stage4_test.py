#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的阶段4训练测试
"""

import sys
import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.rl_agent.model import ImprovedGuandanPolicyNet
from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset


def test_stage4():
    """测试阶段4改进模型"""

    print("阶段4改进模型训练测试")
    print("=" * 50)

    # 创建改进模型
    model = ImprovedGuandanPolicyNet(
        input_dim=512, hidden_dim=256, output_dim=512,
        dropout_rate=0.1, enable_strategy_head=True, attention_heads=8
    )

    print(f"模型参数数量: {sum(p.numel() for p in model.parameters()):,}")

    # 加载数据
    parser = ReplayParser("game_records")
    raw_data = parser.load_replays()
    training_data = parser.extract_training_data(raw_data[:3])

    if not training_data:
        print("没有训练数据")
        return

    dataset = GuandanDataset(training_data)
    dataloader = DataLoader(dataset, batch_size=8, shuffle=True)

    print(f"加载数据: {len(dataset)} 个样本")

    # 训练设置
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)
    action_criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(2.0))
    strategy_criterion = nn.CrossEntropyLoss(ignore_index=7)

    device = torch.device("cpu")
    model.to(device)
    model.train()

    print("开始训练...")

    for epoch in range(3):
        total_action_loss = 0
        total_strategy_loss = 0
        total_samples = 0

        for batch in dataloader:
            states, actions, strategy_labels, _ = batch
            batch_size = len(states)
            total_samples += batch_size

            # 确保数据类型正确
            states = states.float()
            actions = actions.float()
            strategy_labels = strategy_labels.long()

            # 前向传播
            action_logits = model(states)
            strategy_logits = model.get_strategy_probs(states)

            # 计算损失
            action_loss = action_criterion(action_logits, actions)
            strategy_loss = strategy_criterion(strategy_logits, strategy_labels)

            # 多任务损失
            total_loss = 2.0 * action_loss + 0.1 * strategy_loss

            # 反向传播
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()

            total_action_loss += action_loss.item() * batch_size
            total_strategy_loss += strategy_loss.item() * batch_size

        # 输出结果
        avg_action_loss = total_action_loss / total_samples
        avg_strategy_loss = total_strategy_loss / total_samples
        print(f"Epoch {epoch+1}: Action Loss={avg_action_loss:.4f}, Strategy Loss={avg_strategy_loss:.4f}")

    # 评估
    print("评估训练效果...")
    model.eval()

    exact_matches = 0
    total_samples = 0
    predicted_cards = []

    with torch.no_grad():
        for batch in dataloader:
            states, actions, strategy_labels, _ = batch
            batch_size = len(states)
            total_samples += batch_size

            action_logits = model(states)
            action_probs = torch.sigmoid(action_logits)
            predictions = (action_probs > 0.3).float()

            for i in range(batch_size):
                if torch.equal(predictions[i], actions[i]):
                    exact_matches += 1
                predicted_cards.append((predictions[i] > 0).sum().item())

    exact_accuracy = exact_matches / total_samples * 100
    avg_predicted = sum(predicted_cards) / len(predicted_cards)

    print("训练结果:")
    print(".2f")
    print(".1f")

    # 保存模型
    torch.save({
        'model_state_dict': model.state_dict(),
        'epoch': 3,
        'exact_accuracy': exact_accuracy,
        'avg_predicted': avg_predicted
    }, 'models/bc_model_stage4_test.pth')

    print("阶段4测试完成，模型已保存")


if __name__ == "__main__":
    test_stage4()
