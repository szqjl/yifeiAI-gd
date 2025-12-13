#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段5模型训练脚本（优化版）
重点提升动作预测准确率，平衡多任务学习
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
print("阶段5模型训练 - 优化版（重点提升动作预测准确率）")
print("="*80)
print(f"随机种子: {seed}")
print(f"使用设备: CPU")
print("="*80)
print()

# **优化策略**：
# 1. 大幅增加动作预测权重（从1.5增加到3.0）
# 2. 降低辅助任务权重，避免干扰主任务
# 3. 使用更多数据和训练轮数
print("[优化配置]")
print("1. 动作预测权重: 3.0 (主任务，大幅提升)")
print("2. 策略分类权重: 0.3 (辅助任务，保持)")
print("3. 阶段5任务: 暂时禁用，专注于主任务")
print("4. 数据量: 5000样本 (平衡效果和时间)")
print("5. 训练轮数: 30 epochs (充分训练)")
print()
print("[关键改进]")
print("- 暂时禁用阶段5新增任务，避免干扰动作预测学习")
print("- 大幅提升动作预测权重，确保主任务优先")
print("- 增加数据量和训练轮数，提供充分学习机会")
print()

train_bc(
    data_dir="game_records",
    epochs=30,                    # 增加训练轮数
    batch_size=64,                # CPU训练可以使用更大的batch_size
    lr=0.0003,
    dropout_rate=0.1,
    model_path="models/bc_model_stage5_optimized.pth",
    max_samples=5000,             # 使用5000个样本（平衡效果和时间）
    enable_strategy_head=True,
    action_loss_weight=3.0,       # **优化**: 大幅增加动作预测权重（从1.5增加到3.0）
    strategy_loss_weight=0.3,     # 保持策略分类权重
    use_improved_model=True,
    attention_heads=8,
    # **优化**: 暂时禁用阶段5新增任务，专注于主任务（动作预测）
    # 等动作预测准确率提升后再逐步启用
    enable_strategy_pattern=False,  # 暂时禁用
    strategy_pattern_weight=0.0,
    enable_opponent_modeling=False,  # 暂时禁用
    opponent_model_weight=0.0,
    enable_dynamic_strategy=False,  # 暂时禁用
    dynamic_strategy_weight=0.0
)

print()
print("="*80)
print("阶段5模型训练（优化版）完成")
print("="*80)
print("[预期效果]")
print("- 动作预测准确率应显著提升（目标: >20%）")
print("- 策略分类准确率保持较高水平（目标: >80%）")
print("- 策略理解率应有所提升（目标: >10%）")
print("="*80)

