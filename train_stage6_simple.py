#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段6-游戏导向训练脚本（简化版）
基于现有代码，使用阶段6的改进功能
"""

import sys
import os
import random
import torch
import numpy as np
from datetime import datetime

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
print("阶段6-游戏导向训练（简化版）")
print("="*80)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"随机种子: {seed}")
print(f"使用设备: CPU")
print("="*80)
print()

print("[阶段6核心改进]")
print("1. ✅ 策略原因学习 - 学习'为什么这样选择'")
print("2. ✅ 胜率导向损失 - 学习'什么有效'")
print("3. ✅ 策略一致性损失 - 动作和策略同时正确")
print("4. ✅ 改进的策略理解率 - 基于90%匹配率")
print()

print("[训练配置]")
print("1. 动作预测权重: 1.0")
print("2. 策略分类权重: 0.3")
print("3. 策略任务权重: 0.5 (包含策略原因学习)")
print("4. 策略一致性损失权重: 0.3")
print("5. 数据量: 15000样本")
print("6. 训练轮数: 80 epochs")
print("7. 批次大小: 64")
print("8. 学习率: 0.0002")
print()

# 创建模型保存目录
model_dir = "models"
os.makedirs(model_dir, exist_ok=True)

# 创建训练日志目录
log_dir = "training_logs"
os.makedirs(log_dir, exist_ok=True)

print("开始阶段6训练...")
print("-" * 40)

# 开始训练
try:
    train_bc(
        data_dir="game_records",
        epochs=80,                     # 训练轮数
        batch_size=64,                 # 批次大小
        lr=0.0002,                     # 学习率
        dropout_rate=0.1,              # Dropout比率
        model_path="models/bc_model_stage6_simple.pth",  # 模型保存路径
        max_samples=15000,             # 使用15000个样本
        enable_strategy_head=True,      # 启用策略分类头
        action_loss_weight=1.0,        # 动作预测权重
        strategy_loss_weight=0.3,       # 策略分类权重
        use_improved_model=True,       # 使用改进的模型
        attention_heads=8,             # 注意力头数
        # 阶段5任务（阶段6中保留但降低权重）
        enable_strategy_pattern=True,
        strategy_pattern_weight=0.1,
        enable_opponent_modeling=True,
        opponent_model_weight=0.1,
        enable_dynamic_strategy=True,
        dynamic_strategy_weight=0.1
    )

    print()
    print("="*80)
    print("阶段6训练完成")
    print("="*80)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"模型保存路径: models/bc_model_stage6_simple.pth")
    print("="*80)

except KeyboardInterrupt:
    print()
    print("="*80)
    print("训练被用户中断")
    print("="*80)
    print("提示：训练进度已保存，可以继续训练")

except Exception as e:
    print()
    print("="*80)
    print(f"训练过程中发生错误: {e}")
    print("="*80)
    import traceback
    traceback.print_exc()
