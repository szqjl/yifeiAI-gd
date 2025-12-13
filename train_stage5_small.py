#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段5模型训练脚本（小数据量测试版）
使用少量样本进行快速测试，验证训练流程
"""

import sys
import os
import random
import torch
import numpy as np

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.train.pretrain import train_bc

# 强制使用CPU训练（避免GPU内存问题）
os.environ['FORCE_CPU'] = '1'

# 固定随机种子
seed = 42
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)

print("="*80)
print("阶段5模型训练 - 小数据量测试版")
print("="*80)
print(f"随机种子: {seed}")
print(f"使用设备: CPU（避免GPU内存问题）")
print("="*80)
print()

# 小数据量测试配置
print("[测试配置] 使用1000个样本和5个epoch进行快速测试")
print()

train_bc(
    data_dir="game_records",
    epochs=5,                     # 快速测试用5轮
    batch_size=64,                # CPU训练可以使用更大的batch_size
    lr=0.0003,
    dropout_rate=0.1,
    model_path="models/bc_model_stage5_test.pth",
    max_samples=1000,             # 限制1000个样本用于测试
    enable_strategy_head=True,
    action_loss_weight=1.5,
    strategy_loss_weight=0.3,
    use_improved_model=True,
    attention_heads=8,
    enable_strategy_pattern=True,
    strategy_pattern_weight=0.2,
    enable_opponent_modeling=True,
    opponent_model_weight=0.15,
    enable_dynamic_strategy=True,
    dynamic_strategy_weight=0.1
)

print()
print("="*80)
print("阶段5模型训练测试完成")
print("="*80)

