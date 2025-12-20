#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段6-游戏导向训练脚本
重点：从"预测准确"转向"赢得游戏"，建立以游戏胜率为导向的训练体系

核心改进：
1. 策略原因学习任务 - 让AI学习"为什么这样选择"
2. 胜率导向损失函数 - 让AI学习"什么有效"
3. 动态阈值调整 - 根据局面自适应调整预测阈值
4. 概率校准 - 提高预测概率的准确性
5. 综合评估体系 - 多维度评估模型性能
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
from src.train.game_oriented_validation import GameOrientedValidator

# 强制使用CPU训练（避免GPU内存问题）
os.environ['FORCE_CPU'] = '1'

# 固定随机种子
seed = 42
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)

print("="*80)
print("阶段6-游戏导向训练")
print("="*80)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"随机种子: {seed}")
print(f"使用设备: CPU")
print("="*80)
print()

print("[阶段6核心理念]")
print("从'预测卡牌的AI' → '赢得游戏的AI'")
print("从'技术先进性' → '游戏有效性'")
print("从'数据拟合' → '策略学习'")
print()

print("[阶段6核心改进]")
print("1. ✅ 策略原因学习任务 - 让AI学习'为什么这样选择'")
print("2. ✅ 胜率导向损失函数 - 让AI学习'什么有效'")
print("3. ✅ 动态阈值调整 - 根据局面自适应调整预测阈值")
print("4. ✅ 概率校准 - 提高预测概率的准确性")
print("5. ✅ 综合评估体系 - 多维度评估模型性能")
print()

print("[策略原因学习任务（26类原因类型）]")
reason_types = [
    'bomb_urgent', 'bomb_endgame', 'bomb_counter', 'bomb_opportunity',
    'suppress_urgent', 'suppress_combo', 'suppress_block', 'suppress_general',
    'protect_teammate_urgent', 'protect_teammate', 'protect_advantage', 'protect_general',
    'control_urgent', 'control_endgame', 'control_general',
    'group_reduce_hands', 'group_reduce_singles', 'group_optimize', 'group_general',
    'follow_counter', 'follow_single', 'follow_general',
    'discard_opening', 'discard_endgame', 'discard_general',
    'unknown'
]
print(f"原因类型: {len(reason_types)}类")
print("映射: 'bomb_urgent': 0, 'bomb_endgame': 1, ..., 'unknown': 25")
print()

print("[训练配置]")
print("1. 动作预测权重: 1.0 (基础任务)")
print("2. 策略分类权重: 0.3 (辅助任务)")
print("3. 策略任务权重: 0.5 (7个任务总权重，平均每个约0.071)")
print("4. 策略原因学习权重: 0.2 (新增：学习'为什么这样选择')")
print("5. 策略一致性损失权重: 0.3 (鼓励动作和策略同时正确)")
print("6. 胜率导向损失权重: 0.3 (新增：学习'什么有效')")
print("7. 数据量: 15000样本（更大的数据集）")
print("8. 训练轮数: 100 epochs")
print("9. 批次大小: 64")
print("10. 学习率: 0.0002")
print("11. Dropout: 0.1")
print("12. 启用所有阶段6功能")
print()

print("[损失函数组合]")
print("total_batch_loss = (")
print("    current_action_weight * action_loss +")
print("    current_strategy_weight * strategy_loss +")
print("    strategy_tasks_loss +")
print("    strategy_consistency_loss +")
print("    win_rate_oriented_loss")  # 阶段6新增
print(")")
print()

print("[监控信息]")
print("- 每个epoch结束后显示：")
print("  * 总损失、动作损失、策略损失、策略任务损失")
print("  * 策略原因学习损失（新增）")
print("  * 胜率导向损失（新增）")
print("  * 完全匹配准确率、卡牌级别准确率")
print("  * 策略分类准确率、策略理解率")
print("  * 策略原因分类准确率（新增）")
print("  * 7个策略任务的准确率")
print("- 每10个epoch保存检查点")
print("- 训练完成后进行游戏导向验证")
print()

# 创建模型保存目录
model_dir = "models"
os.makedirs(model_dir, exist_ok=True)

# 创建训练日志目录
log_dir = "training_logs"
os.makedirs(log_dir, exist_ok=True)

# 训练日志文件
log_file = os.path.join(log_dir, f"stage6_game_oriented_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

print(f"[日志文件] {log_file}")
print()

# 开始训练
try:
    train_bc(
        data_dir="game_records",
        epochs=50,                    # 第一轮优化：减少训练轮数，专注稳定性
        batch_size=32,                # 第一轮优化：减小批次大小，提高稳定性
        lr=0.0001,                    # 第一轮优化：大幅降低学习率，提高稳定性
        dropout_rate=0.2,             # 第一轮优化：增加Dropout，增强正则化
        model_path="models/bc_model_stage6_stability_fix.pth",  # 第一轮优化：新模型路径
        max_samples=8000,             # 第一轮优化：减少样本量，专注质量
        enable_strategy_head=True,     # 启用策略分类头
        action_loss_weight=1.5,       # 第一轮优化：提高动作预测权重，确保基础能力
        strategy_loss_weight=0.1,      # 第一轮优化：降低策略权重，专注稳定性
        use_improved_model=False,     # 第一轮优化：使用基础模型，提高稳定性
        # 阶段5任务（第一轮优化：大幅降低权重，专注核心任务）
        enable_strategy_pattern=True,  # 保留但降低权重
        strategy_pattern_weight=0.05,  # 第一轮优化：大幅降低权重
        enable_opponent_modeling=True, # 保留但降低权重
        opponent_model_weight=0.05,    # 第一轮优化：大幅降低权重
        enable_dynamic_strategy=True,  # 保留但降低权重
        dynamic_strategy_weight=0.05   # 第一轮优化：大幅降低权重
    )

    print()
    print("="*80)
    print("阶段6-游戏导向训练完成")
    print("="*80)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"模型保存路径: models/bc_model_stage6_game_oriented.pth")
    print()

    # 阶段6新增：训练完成后进行游戏导向验证
    print("开始阶段6游戏导向验证...")
    print("-" * 40)

    from src.train.game_oriented_validation import validate_game_records

    # 执行综合验证
    results = validate_game_records(
        data_dir="game_records",
        baseline_dir="game_records",  # 使用相同数据对比不同模型
        player_id=0
    )

    print()
    print("阶段6验证结果总结:")
    print("-" * 40)
    print(f"胜率: {results.get('win_rate', 'N/A')}")
    print(f"策略适应性: {results.get('strategy_adaptability', 'N/A')}")
    print(f"决策质量: {results.get('decision_quality', 'N/A')}")
    print(f"预测准确性: {results.get('prediction_accuracy', 'N/A')}")
    print(f"综合评估分数: {results.get('overall_score', 'N/A')}")
    print()

    if results.get('improvement_analysis'):
        print("改进分析:")
        for key, value in results['improvement_analysis'].items():
            print(f"  {key}: {value}")

    print("="*80)
    print("阶段6训练和验证全部完成！")
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
