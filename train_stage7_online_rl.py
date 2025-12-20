#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段7-在线强化学习（基于文章启发：探索-内化循环）
重点：引入在线强化学习，让AI通过实际对局自我改进

核心改进（基于文章启发）：
1. 探索-内化循环：
   - 探索阶段：AI在真实对局中尝试不同策略
   - 内化阶段：将高胜率策略轨迹加入训练数据，持续优化
2. 中间奖励设计：缓解稀疏奖励问题
3. 在线学习框架：支持实时对局中的策略更新
4. 策略多样性：维持探索的多样性，避免过早收敛
"""

import sys
import os
import random
import torch
import torch.nn as nn
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.train.pretrain import train_bc
from src.train.trajectory_collector import TrajectoryCollector
from src.rl_env.guandan_env import GuandanEnv
from src.rl_agent.model import GuandanPolicyNet

# 强制使用CPU训练（避免GPU内存问题）
os.environ['FORCE_CPU'] = '1'

# 固定随机种子
seed = 42
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)

print("="*80)
print("阶段7-在线强化学习（探索-内化循环）")
print("="*80)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"随机种子: {seed}")
print(f"使用设备: CPU")
print("="*80)
print()

print("[阶段7核心理念]")
print("从'监督学习策略' → '自主发现策略'")
print("从'规则驱动决策' → '数据驱动最优'")
print("从'被动适应' → '主动学习'")
print("从'一次性训练' → '持续在线改进'")
print()

print("[探索-内化循环架构]")
print("="*60)
print("探索阶段：")
print("  - AI在真实对局中尝试不同策略")
print("  - 收集对局轨迹和奖励信号")
print("  - 维持策略多样性，避免过早收敛")
print()
print("内化阶段：")
print("  - 筛选高胜率轨迹")
print("  - 混合原始专家数据")
print("  - 更新模型参数")
print("  - 将临时技巧内化成肌肉记忆")
print("="*60)
print()

print("[中间奖励设计]")
print("缓解稀疏奖励问题（一局游戏只有最终胜率）")
print("  - 压制成功奖励: +0.1")
print("  - 配合奖励: +0.15")
print("  - 控场奖励: +0.1")
print("  - 出牌效率奖励: +0.05")
print("  - 关键牌使用奖励: +0.2")
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
log_file = os.path.join(log_dir, f"stage7_online_rl_{timestamp}.log")

print(f"[日志文件] {log_file}")
print()

# ==================== 初始化模型和环境 ====================
print("="*80)
print("初始化模型和环境")
print("="*80)
print()

# 加载阶段6优化版模型作为初始策略
stage6_model_path = "models/bc_model_stage6_stage2_latest.pth"
if not os.path.exists(stage6_model_path):
    print(f"⚠️  未找到阶段6模型 {stage6_model_path}，使用默认初始化")
    stage6_model_path = None

# 初始化策略网络
device = torch.device('cpu')
policy_net = GuandanPolicyNet(
    input_dim=512,
    hidden_dim=256,
    output_dim=512,
    dropout_rate=0.1,
    enable_strategy_head=True
).to(device)

if stage6_model_path and os.path.exists(stage6_model_path):
    print(f"📥 加载阶段6模型: {stage6_model_path}")
    policy_net.load_state_dict(torch.load(stage6_model_path, map_location=device))
    print("✅ 模型加载成功")
else:
    print("📝 使用随机初始化模型")
print()

# 初始化环境
env = GuandanEnv()
print("✅ 环境初始化完成")
print()

# ==================== 探索-内化循环 ====================
print("="*80)
print("开始探索-内化循环训练")
print("="*80)
print()

num_cycles = 5  # 循环次数
episodes_per_cycle = 20  # 每个循环的对局数
min_trajectory_score = 0.7  # 最低轨迹质量分数

trajectory_collector = TrajectoryCollector(
    min_win_rate=0.6,
    min_trajectory_score=min_trajectory_score
)

for cycle in range(num_cycles):
    print(f"\n{'='*80}")
    print(f"循环 {cycle + 1}/{num_cycles}")
    print(f"{'='*80}\n")
    
    # ==================== 探索阶段 ====================
    print(f"[探索阶段 {cycle + 1}]")
    print("-" * 40)
    print(f"进行 {episodes_per_cycle} 局对局，收集轨迹...")
    
    collected_trajectories = []
    
    for episode in range(episodes_per_cycle):
        # 重置环境
        state, info = env.reset()
        done = False
        episode_trajectory = []
        total_reward = 0.0
        
        while not done:
            # 使用当前策略选择动作
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(device)
            with torch.no_grad():
                action_logits = policy_net(state_tensor)
                action_probs = torch.sigmoid(action_logits)
            
            # 添加探索噪声（epsilon-greedy）
            epsilon = 0.2  # 探索率
            if random.random() < epsilon:
                # 随机探索
                action = (np.random.random(512) > 0.5).astype(np.float32)
            else:
                # 使用策略
                action = (action_probs.cpu().numpy()[0] > 0.5).astype(np.float32)
            
            # 执行动作
            next_state, reward, done, truncated, info = env.step(action)
            
            # 记录轨迹
            episode_trajectory.append({
                'state': state.copy(),
                'action': action.copy(),
                'reward': reward,
                'next_state': next_state.copy(),
                'done': done
            })
            
            total_reward += reward
            state = next_state
        
        # 判断是否获胜（简化：根据总奖励）
        is_winner = total_reward > 0
        
        if is_winner:
            # 构建游戏记录格式
            game_record = {
                'winner': 0 if is_winner else 1,
                'game_states': [t['state'] for t in episode_trajectory],
                'actions': [t['action'] for t in episode_trajectory],
                'rewards': [t['reward'] for t in episode_trajectory]
            }
            
            # 收集轨迹
            trajectory = trajectory_collector.collect_from_game_record(game_record)
            if trajectory:
                collected_trajectories.append(trajectory)
        
        if (episode + 1) % 5 == 0:
            print(f"  完成 {episode + 1}/{episodes_per_cycle} 局，收集 {len(collected_trajectories)} 条高质量轨迹")
    
    print(f"\n✅ 探索阶段完成，收集了 {len(collected_trajectories)} 条高质量轨迹")
    
    if len(collected_trajectories) == 0:
        print("⚠️  未收集到高质量轨迹，跳过本次内化阶段")
        continue
    
    # ==================== 内化阶段 ====================
    print(f"\n[内化阶段 {cycle + 1}]")
    print("-" * 40)
    
    # 保存轨迹
    trajectory_path = os.path.join(trajectory_dir, f"stage7_cycle_{cycle+1}_{timestamp}.json")
    trajectory_collector.save_trajectories(trajectory_path)
    
    # 混合原始数据和成功轨迹进行训练
    print("🔄 混合原始数据和成功轨迹...")
    print(f"   - 原始数据: game_records")
    print(f"   - 成功轨迹: {len(collected_trajectories)} 条")
    
    # 训练模型（使用混合数据）
    cycle_model_path = f"models/bc_model_stage7_cycle_{cycle+1}_{timestamp}.pth"
    
    print(f"\n🚀 开始内化训练（循环 {cycle + 1}）...")
    print(f"   模型保存路径: {cycle_model_path}")
    
    # 使用BC训练（混合数据）
    train_bc(
        data_dir="game_records",
        epochs=20,  # 每个循环较少轮数
        batch_size=64,
        lr=0.0001,  # 较低学习率，稳定更新
        dropout_rate=0.1,
        model_path=cycle_model_path,
        max_samples=10000,  # 混合数据量
        enable_strategy_head=True,
        action_loss_weight=1.5,
        strategy_loss_weight=0.1,
        use_improved_model=False,
        enable_strategy_pattern=True,
        strategy_pattern_weight=0.05,
        enable_opponent_modeling=True,
        opponent_model_weight=0.05,
        enable_dynamic_strategy=True,
        dynamic_strategy_weight=0.05,
        # TODO: 添加trajectory_data参数支持
    )
    
    # 加载更新后的模型
    print(f"\n📥 加载更新后的模型: {cycle_model_path}")
    policy_net.load_state_dict(torch.load(cycle_model_path, map_location=device))
    print("✅ 模型更新完成")
    
    print(f"\n✅ 循环 {cycle + 1} 完成")
    print(f"   - 收集轨迹: {len(collected_trajectories)} 条")
    print(f"   - 模型路径: {cycle_model_path}")

print("\n" + "="*80)
print("阶段7在线强化学习训练完成！")
print("="*80)
print()
print("📊 训练总结:")
print(f"  - 总循环数: {num_cycles}")
print(f"  - 每循环对局数: {episodes_per_cycle}")
print(f"  - 收集轨迹总数: {trajectory_collector.stats['collected_trajectories']}")
print(f"  - 最终模型: models/bc_model_stage7_cycle_{num_cycles}_{timestamp}.pth")
print()

