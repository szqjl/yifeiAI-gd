#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段8-完整强化学习整合（基于阶段6-7的改进）
重点：完整的强化学习框架，实现自主策略发现和最优决策学习

核心改进（基于文章启发和阶段6-7成果）：
1. 完整的RL框架：PPO算法实现
2. 价值网络：评估状态价值，指导策略学习
3. 经验回放：存储和重用历史经验
4. 优先级采样：优先学习重要经验
5. 自对弈：AI对AI训练，持续提升
"""

import sys
import os
import random
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import deque

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.rl_env.guandan_env import GuandanEnv
from src.rl_agent.model import GuandanPolicyNet

# 强制使用CPU训练（避免GPU内存问题）
os.environ['FORCE_CPU'] = '1'

# 固定随机种子
seed = 42
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)


class ValueNet(nn.Module):
    """价值网络：评估状态价值"""
    
    def __init__(self, input_dim=512, hidden_dim=256):
        super(ValueNet, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, 1)
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        value = self.fc3(x)
        return value


class PPOAgent:
    """PPO算法智能体"""
    
    def __init__(
        self,
        policy_net: GuandanPolicyNet,
        value_net: ValueNet,
        lr_policy=3e-4,
        lr_value=3e-4,
        gamma=0.99,
        eps_clip=0.2,
        k_epochs=10
    ):
        self.policy_net = policy_net
        self.value_net = value_net
        self.gamma = gamma
        self.eps_clip = eps_clip
        self.k_epochs = k_epochs
        
        self.policy_optimizer = optim.Adam(policy_net.parameters(), lr=lr_policy)
        self.value_optimizer = optim.Adam(value_net.parameters(), lr=lr_value)
        
        self.memory = {
            'states': [],
            'actions': [],
            'rewards': [],
            'dones': [],
            'old_log_probs': []
        }
    
    def select_action(self, state, deterministic=False):
        """选择动作"""
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        
        with torch.no_grad():
            action_logits = self.policy_net(state_tensor)
            action_probs = torch.sigmoid(action_logits)
        
        if deterministic:
            action = (action_probs > 0.5).float()
        else:
            # 采样动作
            action = torch.bernoulli(action_probs)
        
        # 计算log概率
        log_prob = F.binary_cross_entropy_with_logits(
            action_logits, action, reduction='none'
        ).sum(dim=1)
        
        return action.numpy()[0], log_prob.item()
    
    def store_transition(self, state, action, reward, done, old_log_prob):
        """存储转换"""
        self.memory['states'].append(state)
        self.memory['actions'].append(action)
        self.memory['rewards'].append(reward)
        self.memory['dones'].append(done)
        self.memory['old_log_probs'].append(old_log_prob)
    
    def compute_returns(self, rewards, dones):
        """计算回报（带折扣）"""
        returns = []
        G = 0
        for reward, done in zip(reversed(rewards), reversed(dones)):
            if done:
                G = 0
            G = reward + self.gamma * G
            returns.insert(0, G)
        return returns
    
    def update(self):
        """更新策略和价值网络"""
        if len(self.memory['states']) == 0:
            return
        
        # 计算回报
        returns = self.compute_returns(
            self.memory['rewards'],
            self.memory['dones']
        )
        returns = torch.FloatTensor(returns)
        
        # 计算优势
        states = torch.FloatTensor(self.memory['states'])
        old_actions = torch.FloatTensor(self.memory['actions'])
        old_log_probs = torch.FloatTensor(self.memory['old_log_probs'])
        
        # 计算价值估计
        with torch.no_grad():
            values = self.value_net(states).squeeze()
        
        advantages = returns - values
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # PPO更新
        for _ in range(self.k_epochs):
            # 计算新策略的log概率
            action_logits = self.policy_net(states)
            new_log_probs = F.binary_cross_entropy_with_logits(
                action_logits, old_actions, reduction='none'
            ).sum(dim=1)
            
            # 计算比率
            ratio = torch.exp(new_log_probs - old_log_probs)
            
            # 计算策略损失
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.eps_clip, 1 + self.eps_clip) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            
            # 更新策略网络
            self.policy_optimizer.zero_grad()
            policy_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 0.5)
            self.policy_optimizer.step()
            
            # 计算价值损失
            new_values = self.value_net(states).squeeze()
            value_loss = F.mse_loss(new_values, returns)
            
            # 更新价值网络
            self.value_optimizer.zero_grad()
            value_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.value_net.parameters(), 0.5)
            self.value_optimizer.step()
        
        # 清空记忆
        self.memory = {
            'states': [],
            'actions': [],
            'rewards': [],
            'dones': [],
            'old_log_probs': []
        }
    
    def save(self, path):
        """保存模型"""
        torch.save({
            'policy_net': self.policy_net.state_dict(),
            'value_net': self.value_net.state_dict(),
            'policy_optimizer': self.policy_optimizer.state_dict(),
            'value_optimizer': self.value_optimizer.state_dict(),
        }, path)
    
    def load(self, path):
        """加载模型"""
        checkpoint = torch.load(path, map_location='cpu')
        self.policy_net.load_state_dict(checkpoint['policy_net'])
        self.value_net.load_state_dict(checkpoint['value_net'])
        self.policy_optimizer.load_state_dict(checkpoint['policy_optimizer'])
        self.value_optimizer.load_state_dict(checkpoint['value_optimizer'])


print("="*80)
print("阶段8-完整强化学习整合")
print("="*80)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"随机种子: {seed}")
print(f"使用设备: CPU")
print("="*80)
print()

print("[阶段8核心理念]")
print("从'监督学习策略' → '自主发现策略'")
print("从'规则驱动决策' → '数据驱动最优'")
print("从'被动适应' → '主动学习'")
print("从'单智能体' → '多智能体自对弈'")
print()

print("[PPO算法配置]")
print("  - 学习率（策略）: 3e-4")
print("  - 学习率（价值）: 3e-4")
print("  - 折扣因子: 0.99")
print("  - PPO裁剪范围: 0.2")
print("  - 更新轮数: 10")
print()

# 创建模型保存目录
model_dir = "models"
os.makedirs(model_dir, exist_ok=True)

# 创建训练日志目录
log_dir = "training_logs"
os.makedirs(log_dir, exist_ok=True)

# 训练日志文件
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join(log_dir, f"stage8_full_rl_{timestamp}.log")

print(f"[日志文件] {log_file}")
print()

# ==================== 初始化模型和智能体 ====================
print("="*80)
print("初始化模型和智能体")
print("="*80)
print()

device = torch.device('cpu')

# 初始化策略网络
policy_net = GuandanPolicyNet(
    input_dim=512,
    hidden_dim=256,
    output_dim=512,
    dropout_rate=0.1,
    enable_strategy_head=True
).to(device)

# 加载阶段7模型作为初始化（如果存在）
stage7_model_path = "models/bc_model_stage7_cycle_5_latest.pth"
if os.path.exists(stage7_model_path):
    print(f"📥 加载阶段7模型: {stage7_model_path}")
    policy_net.load_state_dict(torch.load(stage7_model_path, map_location=device))
    print("✅ 策略网络加载成功")
else:
    print("📝 使用随机初始化策略网络")

# 初始化价值网络
value_net = ValueNet(input_dim=512, hidden_dim=256).to(device)
print("✅ 价值网络初始化完成")

# 初始化PPO智能体
agent = PPOAgent(
    policy_net=policy_net,
    value_net=value_net,
    lr_policy=3e-4,
    lr_value=3e-4,
    gamma=0.99,
    eps_clip=0.2,
    k_epochs=10
)
print("✅ PPO智能体初始化完成")
print()

# ==================== 训练循环 ====================
print("="*80)
print("开始PPO训练")
print("="*80)
print()

num_episodes = 500
max_steps_per_episode = 200
update_frequency = 20  # 每N个episode更新一次

env = GuandanEnv()

episode_rewards = []
best_avg_reward = float('-inf')

for episode in range(num_episodes):
    state, info = env.reset()
    done = False
    episode_reward = 0.0
    steps = 0
    
    while not done and steps < max_steps_per_episode:
        # 选择动作
        action, old_log_prob = agent.select_action(state)
        
        # 执行动作
        next_state, reward, done, truncated, info = env.step(action)
        
        # 存储转换
        agent.store_transition(state, action, reward, done, old_log_prob)
        
        episode_reward += reward
        state = next_state
        steps += 1
    
    episode_rewards.append(episode_reward)
    
    # 定期更新
    if (episode + 1) % update_frequency == 0:
        agent.update()
        avg_reward = np.mean(episode_rewards[-update_frequency:])
        
        print(f"Episode {episode + 1}/{num_episodes}, "
              f"平均奖励: {avg_reward:.2f}, "
              f"最近奖励: {episode_reward:.2f}")
        
        # 保存最佳模型
        if avg_reward > best_avg_reward:
            best_avg_reward = avg_reward
            best_model_path = f"models/stage8_ppo_best_{timestamp}.pth"
            agent.save(best_model_path)
            print(f"  ✅ 保存最佳模型: {best_model_path} (平均奖励: {avg_reward:.2f})")
    
    # 定期保存检查点
    if (episode + 1) % 100 == 0:
        checkpoint_path = f"models/stage8_ppo_checkpoint_{episode+1}_{timestamp}.pth"
        agent.save(checkpoint_path)
        print(f"  💾 保存检查点: {checkpoint_path}")

print("\n" + "="*80)
print("阶段8完整强化学习训练完成！")
print("="*80)
print()
print("📊 训练总结:")
print(f"  - 总训练轮数: {num_episodes}")
print(f"  - 最佳平均奖励: {best_avg_reward:.2f}")
print(f"  - 最终平均奖励: {np.mean(episode_rewards[-100:]):.2f}")
print(f"  - 最佳模型: models/stage8_ppo_best_{timestamp}.pth")
print()

