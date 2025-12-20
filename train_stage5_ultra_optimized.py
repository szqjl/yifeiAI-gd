#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段5模型训练脚本（超优化版）
进一步优化预测过多问题，提升完全匹配准确率
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
print("阶段5模型训练 - 超优化版（进一步解决预测过多问题）")
print("="*80)
print(f"随机种子: {seed}")
print(f"使用设备: CPU")
print("="*80)
print()

# **超优化策略**（基于最终优化版结果）：
# 最终优化版结果：
# - 训练时评估: 2.39%完全匹配准确率
# - 测试分析: 41.20%完全匹配准确率（500样本）
# - 预测过多: 58.80%（从96.60%大幅降低）
# 
# 进一步优化措施：
# 1. 进一步增加预测数量惩罚权重（从2.0增加到3.0）
# 2. 增加L1损失权重（从0.3增加到0.5）
# 3. 增加数据量（从10000增加到15000）
# 4. 增加训练轮数（从50增加到60）
print("[超优化配置]")
print("1. 动作预测权重: 3.0 (主任务)")
print("2. 策略分类权重: 0.3 (辅助任务)")
print("3. 预测数量惩罚权重: 3.0 (从2.0进一步增加)")
print("4. L1损失权重: 0.5 (从0.3进一步增加)")
print("5. 阶段5任务: 禁用，专注于主任务")
print("6. 数据量: 15000样本 (从10000增加)")
print("7. 训练轮数: 60 epochs (从50增加)")
print()
print("[关键改进]")
print("- 预测数量惩罚权重从2.0增加到3.0，更严格约束预测过多")
print("- L1损失权重从0.3增加到0.5，更有效约束预测数量偏差")
print("- 增加数据量到15000样本，提供更多学习样本")
print("- 增加训练轮数到60 epochs，充分学习")
print()

# 注意：预测数量惩罚权重和L1损失权重已在pretrain.py中修改
print("[已修改pretrain.py参数]")
print("  ✓ over_predict_penalty权重: 2.0 → 3.0")
print("  ✓ prediction_count_loss权重: 0.3 → 0.5")
print()

train_bc(
    data_dir="game_records",
    epochs=60,                    # 增加训练轮数
    batch_size=64,                # CPU训练可以使用更大的batch_size
    lr=0.0003,
    dropout_rate=0.1,
    model_path="models/bc_model_stage5_ultra_optimized.pth",
    max_samples=15000,            # 使用15000个样本（更多数据）
    enable_strategy_head=True,
    action_loss_weight=3.0,       # 保持动作预测权重
    strategy_loss_weight=0.3,     # 保持策略分类权重
    use_improved_model=True,
    attention_heads=8,
    # 暂时禁用阶段5新增任务
    enable_strategy_pattern=False,
    strategy_pattern_weight=0.0,
    enable_opponent_modeling=False,
    opponent_model_weight=0.0,
    enable_dynamic_strategy=False,
    dynamic_strategy_weight=0.0
)

print()
print("="*80)
print("阶段5模型训练（超优化版）完成")
print("="*80)
print("[预期效果]")
print("- 完全匹配准确率应进一步提升（目标: >5%训练时，>50%测试时）")
print("- 卡牌级别准确率保持高水平（目标: >98%）")
print("- 预测过多问题应进一步改善（目标: <40%样本预测过多）")
print("="*80)

