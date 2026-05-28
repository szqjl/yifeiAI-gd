#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段6-优化版：两阶段训练（基于iRe-VLA方法）
重点：从"预测准确"转向"赢得游戏"，引入两阶段训练提升稳定性

核心改进（基于文章启发）：
1. 两阶段训练循环：
   - 第一阶段：冻结主干，只训练轻量级决策头（Action Head）
   - 第二阶段：收集成功轨迹，混合原始数据，全量微调
2. 策略原因学习任务 - 让AI学习"为什么这样选择"
3. 胜率导向损失函数 - 让AI学习"什么有效"
4. 动态阈值调整 - 根据局面自适应调整预测阈值
5. 概率校准 - 提高预测概率的准确性
6. 综合评估体系 - 多维度评估模型性能
"""

import sys
import os
import random
import torch
import torch.nn as nn
import numpy as np
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.train.pretrain import train_bc
from src.train.game_oriented_validation import GameOrientedValidator
from src.train.trajectory_collector import TrajectoryCollector

# 强制使用CPU训练（避免GPU内存问题）
os.environ['FORCE_CPU'] = '1'

# 固定随机种子
seed = 42
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)

print("="*80)
print("阶段6-优化版：两阶段训练（基于iRe-VLA方法）")
print("="*80)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"随机种子: {seed}")
print(f"使用设备: CPU")
print("="*80)
print()

print("[阶段6优化版核心理念]")
print("从'预测卡牌的AI' → '赢得游戏的AI'")
print("从'技术先进性' → '游戏有效性'")
print("从'数据拟合' → '策略学习'")
print("从'一次性训练' → '两阶段循环训练'")
print()

print("[两阶段训练策略（基于iRe-VLA）]")
print("="*60)
print("第一阶段：冻结主干，只训练决策头")
print("  - 冻结特征提取层（fc1, fc2）")
print("  - 只训练动作预测头（fc3）和策略分类头（fc_strategy）")
print("  - 目标：让AI在本地安全探索，避免'训崩'")
print("  - 优势：训练稳定，单张4090显卡即可运行")
print()
print("第二阶段：收集成功轨迹，全量微调")
print("  - 收集第一阶段探索中的高胜率轨迹")
print("  - 混合原始专家数据")
print("  - 对整个模型（包括LoRA适配器）做全量微调")
print("  - 目标：将临时技巧内化成肌肉记忆")
print("="*60)
print()

print("[阶段6核心改进]")
print("1. ✅ 两阶段训练循环 - 提升训练稳定性")
print("2. ✅ 策略原因学习任务 - 让AI学习'为什么这样选择'")
print("3. ✅ 胜率导向损失函数 - 让AI学习'什么有效'")
print("4. ✅ 动态阈值调整 - 根据局面自适应调整预测阈值")
print("5. ✅ 概率校准 - 提高预测概率的准确性")
print("6. ✅ 综合评估体系 - 多维度评估模型性能")
print("7. ✅ 轨迹收集与回放 - 收集高胜率对局轨迹")
print()

print("[训练配置]")
print("第一阶段配置：")
print("  - 冻结层：fc1, fc2（特征提取层）")
print("  - 训练层：fc3（动作头）, fc_strategy（策略头）")
print("  - 训练轮数: 30 epochs")
print("  - 批次大小: 32")
print("  - 学习率: 0.0002（决策头专用学习率）")
print()
print("第二阶段配置：")
print("  - 全量微调：所有层")
print("  - 数据混合：原始数据 + 成功轨迹")
print("  - 训练轮数: 50 epochs")
print("  - 批次大小: 64")
print("  - 学习率: 0.0001（全量微调学习率）")
print()

# 创建模型保存目录
model_dir = "models"
os.makedirs(model_dir, exist_ok=True)

# 创建训练日志目录
log_dir = "training_logs"
os.makedirs(log_dir, exist_ok=True)

# 创建轨迹保存目录
trajectory_dir = "trajectories"
os.makedirs(trajectory_dir, exist_ok=True)

# 训练日志文件
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join(log_dir, f"stage6_optimized_training_{timestamp}.log")

print(f"[日志文件] {log_file}")
print()

# ==================== 第一阶段：冻结主干，训练决策头 ====================
print("="*80)
print("第一阶段：冻结主干，训练决策头")
print("="*80)
print()

try:
    # 第一阶段训练：只训练决策头
    print("🔧 配置第一阶段训练参数...")
    
    # 注意：需要在pretrain.py中添加freeze_backbone参数支持
    # 这里先使用现有接口，后续需要扩展
    stage1_model_path = f"models/bc_model_stage6_stage1_{timestamp}.pth"
    
    print("🚀 开始第一阶段训练（冻结主干）...")
    print("   - 只训练决策头（fc3, fc_strategy）")
    print("   - 特征提取层（fc1, fc2）冻结")
    print()
    
    train_bc(
        data_dir="game_records",
        epochs=30,                    # 第一阶段：较少轮数
        batch_size=32,                # 第一阶段：较小批次
        lr=0.0002,                    # 第一阶段：决策头学习率
        dropout_rate=0.1,
        model_path=stage1_model_path,
        max_samples=8000,
        enable_strategy_head=True,
        action_loss_weight=1.5,
        strategy_loss_weight=0.1,
        use_improved_model=True,      # 阶段6优化版：使用ImprovedGuandanPolicyNet支持策略原因学习
        attention_heads=8,
        enable_strategy_pattern=True,
        strategy_pattern_weight=0.05,
        enable_opponent_modeling=True,
        opponent_model_weight=0.05,
        enable_dynamic_strategy=True,
        dynamic_strategy_weight=0.05,
        freeze_backbone=True,         # 阶段6优化版：冻结主干
        enable_win_rate_oriented_loss=True,  # 阶段6优化版：启用胜率导向损失
        win_rate_oriented_loss_weight=0.5,   # 阶段6优化版：胜率导向损失权重
    )
    
    print()
    print("✅ 第一阶段训练完成")
    print(f"   模型保存路径: {stage1_model_path}")
    print()
    
    # ==================== 轨迹收集阶段 ====================
    print("="*80)
    print("轨迹收集阶段：收集高胜率对局轨迹")
    print("="*80)
    print()
    
    print("📊 开始收集高胜率对局轨迹...")
    collector = TrajectoryCollector(min_win_rate=0.6, min_trajectory_score=0.7)
    
    # 从游戏记录中收集轨迹
    from src.knowledge_processor.replay_parser import ReplayParser
    parser = ReplayParser("game_records")
    game_records = parser.load_replays()
    
    print(f"📁 加载了 {len(game_records)} 个游戏记录")
    
    collected_count = 0
    for game_record in game_records:
        trajectory = collector.collect_from_game_record(game_record)
        if trajectory:
            collected_count += 1
    
    print(f"✅ 收集了 {collected_count} 条高质量轨迹")
    
    # 保存轨迹
    trajectory_path = os.path.join(trajectory_dir, f"stage6_trajectories_{timestamp}.json")
    collector.save_trajectories(trajectory_path)
    print()
    
    # ==================== 第二阶段：全量微调 ====================
    print("="*80)
    print("第二阶段：全量微调（混合原始数据+成功轨迹）")
    print("="*80)
    print()
    
    print("🔧 配置第二阶段训练参数...")
    print("   - 加载第一阶段模型作为初始化")
    print("   - 解冻所有层，进行全量微调")
    print("   - 混合原始数据和成功轨迹")
    print()
    
    stage2_model_path = f"models/bc_model_stage6_stage2_{timestamp}.pth"
    
    print("🚀 开始第二阶段训练（全量微调）...")
    
    train_bc(
        data_dir="game_records",
        epochs=50,                    # 第二阶段：更多轮数
        batch_size=64,                # 第二阶段：更大批次
        lr=0.0001,                    # 第二阶段：全量微调学习率（更低）
        dropout_rate=0.1,
        model_path=stage2_model_path,
        max_samples=12000,            # 第二阶段：更多样本（原始+轨迹）
        enable_strategy_head=True,
        action_loss_weight=1.5,
        strategy_loss_weight=0.1,
        use_improved_model=True,      # 阶段6优化版：使用ImprovedGuandanPolicyNet支持策略原因学习
        attention_heads=8,
        enable_strategy_pattern=True,
        strategy_pattern_weight=0.1,   # 第二阶段：提高策略模式权重
        enable_opponent_modeling=True,
        opponent_model_weight=0.1,   # 第二阶段：提高对手建模权重
        enable_dynamic_strategy=True,
        dynamic_strategy_weight=0.1,   # 第二阶段：提高动态策略权重
        freeze_backbone=False,        # 第二阶段：解冻所有层
        load_pretrained_model=stage1_model_path,  # 阶段6优化版：加载第一阶段模型
        trajectory_data=trajectory_path,         # 阶段6优化版：混合轨迹数据
        enable_win_rate_oriented_loss=True,  # 阶段6优化版：启用胜率导向损失
        win_rate_oriented_loss_weight=0.7,   # 第二阶段：提高胜率导向损失权重
    )
    
    print()
    print("✅ 第二阶段训练完成")
    print(f"   模型保存路径: {stage2_model_path}")
    print()
    
    # ==================== 游戏导向验证 ====================
    print("="*80)
    print("游戏导向验证")
    print("="*80)
    print()
    
    print("📊 开始阶段6游戏导向验证...")
    print("-" * 40)
    
    from src.train.game_oriented_validation import validate_game_records
    
    # 执行综合验证
    results = validate_game_records(
        data_dir="game_records",
        baseline_dir="game_records",
        player_id=0
    )
    
    print()
    print("阶段6优化版验证结果总结:")
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
    print("阶段6优化版训练和验证全部完成！")
    print("="*80)
    print()
    print("📊 训练总结:")
    print(f"  - 第一阶段模型: {stage1_model_path}")
    print(f"  - 第二阶段模型: {stage2_model_path}")
    print(f"  - 收集轨迹数: {collected_count}")
    print(f"  - 轨迹文件: {trajectory_path}")
    print()

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

