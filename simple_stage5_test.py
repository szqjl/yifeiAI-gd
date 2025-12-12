#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的阶段5测试
"""

import sys
import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.rl_agent.model import ImprovedGuandanPolicyNet
from src.rl_agent.strategy_pattern_recognizer import StrategyPatternRecognizer
from src.rl_agent.opponent_model import OpponentModel
from src.rl_agent.dynamic_strategy_adjuster import DynamicStrategyAdjuster
from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset


def test_stage5_simple():
    """简化的阶段5测试"""

    print("阶段5高级策略学习测试")
    print("=" * 50)

    # 初始化组件
    main_model = ImprovedGuandanPolicyNet(
        input_dim=512, hidden_dim=256, output_dim=512,
        dropout_rate=0.1, enable_strategy_head=True, attention_heads=8
    )

    pattern_recognizer = StrategyPatternRecognizer(
        input_dim=512, pattern_types=8, hidden_dim=256
    )

    opponent_model = OpponentModel()

    strategy_adjuster = DynamicStrategyAdjuster()

    print("所有组件初始化完成")

    # 加载数据
    parser = ReplayParser("game_records")
    raw_data = parser.load_replays()
    training_data = parser.extract_training_data(raw_data[:2])

    if not training_data:
        print("没有测试数据")
        return

    dataset = GuandanDataset(training_data)
    dataloader = DataLoader(dataset, batch_size=4, shuffle=False)

    print(f"加载数据: {len(dataset)} 个样本")

    # 测试前向传播
    device = torch.device("cpu")
    main_model.to(device)
    pattern_recognizer.to(device)
    opponent_model.to(device)
    strategy_adjuster.to(device)

    main_model.eval()
    pattern_recognizer.eval()
    opponent_model.eval()
    strategy_adjuster.eval()

    total_samples = 0

    print("开始测试前向传播...")

    with torch.no_grad():
        for batch in dataloader:
            states, actions, strategy_labels, pattern_types, strategy_pattern_labels = batch
            batch_size = len(states)
            total_samples += batch_size

            # 主模型
            action_logits, strategy_logits = main_model(states, return_strategy=True)

            # 策略模式识别
            pattern_logits, pattern_confidence = pattern_recognizer(states)

            # 对手建模
            opponent_actions = actions.unsqueeze(1)
            opponent_results = opponent_model(states, opponent_actions)

            # 动态策略调整
            strategy_results = strategy_adjuster(states)

            print(f"批次大小: {batch_size}, 所有组件前向传播成功")

    print(f"总样本数: {total_samples}")
    print("所有组件测试通过")
    print("阶段5集成测试完成")


if __name__ == "__main__":
    test_stage5_simple()
