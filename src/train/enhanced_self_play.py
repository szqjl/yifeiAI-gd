# -*- coding: utf-8 -*-
"""
增强版自我对弈训练脚本
添加了以下功能：
1. 模型评估和选择（自动评估并保存最佳模型）
2. 检查点保存（定期保存训练检查点）
3. 经验回放（Experience Replay）
4. 训练进度监控
"""

import sys
import os
import numpy as np
import random
from collections import deque
import json
from datetime import datetime
import torch

# **修复**：设置Windows控制台编码为UTF-8
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.rl_env.guandan_env import GuandanEnv
from src.rl_agent.agent import PPOAgent
from src.knowledge_processor.strategy_encoder import StrategyEncoder


def set_seed(seed=42):
    """固定随机种子，确保训练可复现"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


class ExperienceReplayBuffer:
    """经验回放缓冲区"""
    
    def __init__(self, capacity=10000):
        self.buffer = deque(maxlen=capacity)
        self.capacity = capacity
    
    def push(self, state, action, log_prob, reward, next_state, done):
        """存储经验"""
        self.buffer.append((state, action, log_prob, reward, next_state, done))
    
    def sample(self, batch_size):
        """随机采样一批经验"""
        if len(self.buffer) < batch_size:
            return list(self.buffer)
        return random.sample(self.buffer, batch_size)
    
    def __len__(self):
        return len(self.buffer)


def evaluate_agent(agent, env, num_episodes=10):
    """
    评估智能体的表现（胜率）
    
    Args:
        agent: PPOAgent实例
        env: GuandanEnv实例
        num_episodes: 评估回合数
    
    Returns:
        win_rate: 胜率（0-1）
        avg_reward: 平均奖励
    """
    wins = 0
    total_reward = 0
    
    for _ in range(num_episodes):
        state, _ = env.reset()
        done = False
        episode_reward = 0
        current_player = 0  # 假设评估玩家0
        
        while not done:
            action, _ = agent.select_action(state)
            next_state, reward, done, _, info = env.step(action)
            
            # 检查是否获胜
            state_dict = env.engine.get_state()
            finished_players = state_dict.get('finished_players', [])
            
            # 如果当前玩家完成，且是前两名，算作获胜
            if current_player in finished_players and len(finished_players) <= 2:
                wins += 1
                break
            
            state = next_state
            episode_reward += reward
            
            # 更新当前玩家（简化处理）
            current_player = (current_player + 1) % 4
        
        total_reward += episode_reward
    
    win_rate = wins / num_episodes
    avg_reward = total_reward / num_episodes
    
    return win_rate, avg_reward


def train_enhanced_self_play(
    max_episodes=1000,
    max_timesteps=200,
    update_timestep=500,
    eval_interval=100,
    checkpoint_interval=200,
    replay_buffer_size=10000,
    batch_size=64,
    pretrained_model_path="models/bc_model_v1.pth",
    learning_rate=0.0001,  # 最优配置：降低学习率以提高稳定性
    seed=42,  # 最优配置：固定随机种子确保可复现
    early_stop_patience=20  # 最优配置：早停耐心值
):
    """
    增强版自我对弈训练
    
    **最优配置（基于历次训练效果汇总.md）**:
    - max_episodes: 500-1000（充分训练，确保收敛）
    - learning_rate: 0.0001（降低以提高稳定性）
    - seed: 42（固定随机种子，确保可复现）
    - 学习率衰减: StepLR(step_size=50, gamma=0.5)（每50轮衰减50%）
    - early_stop_patience: 20（连续20轮无改进自动停止）
    - 自动保存最佳模型（基于平均奖励）
    
    Args:
        max_episodes: 最大训练回合数（推荐500-1000）
        max_timesteps: 每回合最大步数
        update_timestep: 每多少步更新一次策略
        eval_interval: 每多少回合评估一次
        checkpoint_interval: 每多少回合保存一次检查点
        replay_buffer_size: 经验回放缓冲区大小
        batch_size: 批次大小
        pretrained_model_path: 预训练模型路径
        learning_rate: 学习率（推荐0.0001）
        seed: 随机种子（推荐42）
        early_stop_patience: 早停耐心值（推荐20）
    """
    print("="*60)
    print("增强版自我对弈训练（修复版）")
    print("="*60)
    print(f"最大回合数: {max_episodes}")
    print(f"学习率: {learning_rate} (已优化)")
    print(f"随机种子: {seed} (固定)")
    print(f"评估间隔: {eval_interval} 回合")
    print(f"检查点间隔: {checkpoint_interval} 回合")
    print(f"早停耐心值: {early_stop_patience} 回合")
    print(f"经验回放缓冲区大小: {replay_buffer_size}")
    print("="*60)
    
    # **修复1**: 固定随机种子
    set_seed(seed)
    print(f"[修复] 已设置随机种子: {seed}")
    
    # 1. 初始化环境和智能体
    env = GuandanEnv()
    eval_env = GuandanEnv()  # 独立的评估环境
    # **修复2**: 降低学习率以提高稳定性
    agent = PPOAgent(input_dim=512, action_dim=512, lr=learning_rate)
    strategy_encoder = StrategyEncoder()
    
    # **修复3**: 添加学习率衰减调度器
    from torch.optim.lr_scheduler import StepLR
    scheduler = StepLR(agent.optimizer, step_size=50, gamma=0.5)
    print(f"[修复] 已添加学习率衰减（每50轮衰减50%）")
    
    # 加载预训练模型
    if os.path.exists(pretrained_model_path):
        print(f"加载预训练模型: {pretrained_model_path}")
        agent.load(pretrained_model_path)
    
    # 2. 初始化经验回放缓冲区
    replay_buffer = ExperienceReplayBuffer(capacity=replay_buffer_size)
    
    # 3. 训练统计
    best_win_rate = 0.0
    best_episode = 0
    best_avg_reward = float('-inf')  # **修复4**: 跟踪最佳平均奖励
    no_improve_count = 0  # **修复5**: 早停计数器
    training_stats = {
        'episodes': [],
        'rewards': [],
        'win_rates': [],
        'avg_rewards': []
    }
    
    # 4. 创建输出目录
    os.makedirs("models", exist_ok=True)
    os.makedirs("training_logs", exist_ok=True)
    
    # 5. 训练循环
    timestep = 0
    memory = []
    
    print("\n开始训练...\n")
    
    for i_episode in range(1, max_episodes + 1):
        state, _ = env.reset()
        current_ep_reward = 0
        episode_memory = []
        
        for t in range(max_timesteps):
            timestep += 1
            
            # 选择动作
            action, log_prob = agent.select_action(state)
            
            # 执行动作
            next_state, reward, done, _, info = env.step(action)
            
            # 计算Shaping Reward
            action_cards_indices = [i for i, x in enumerate(action) if x == 1]
            state_dict = env.engine.get_state()
            current_player = state_dict.get('current_player', 0)
            hands = state_dict.get('hands', {})
            hand_cards = hands.get(current_player, [])
            
            action_cards = []
            if action_cards_indices:
                for idx in action_cards_indices:
                    if idx < len(hand_cards):
                        action_cards.append(hand_cards[idx])
            
            # 判断动作类型
            action_type = "PASS"
            if len(action_cards) == 1:
                action_type = "Single"
            elif len(action_cards) == 2:
                action_type = "Pair"
            elif len(action_cards) == 3:
                action_type = "Trips"
            elif len(action_cards) >= 5:
                action_type = "Straight"
            
            # 判断游戏阶段
            opponent_rest_cards = []
            for i in range(4):
                if i != current_player:
                    opponent_rest_cards.append(len(hands.get(i, [])))
            min_opponent_cards = min(opponent_rest_cards) if opponent_rest_cards else 27
            
            if min_opponent_cards >= 20:
                game_phase = "opening"
            elif min_opponent_cards >= 10:
                game_phase = "mid"
            else:
                game_phase = "endgame"
            
            # 计算shaping reward
            shaping = strategy_encoder.calculate_shaping_reward(
                state_dict=state_dict,
                action_cards=action_cards,
                action_type=action_type,
                game_phase=game_phase,
                cur_rank="2"
            )
            
            total_reward = reward + shaping
            
            # 存储到经验回放缓冲区
            replay_buffer.push(state.copy(), action.copy(), log_prob, total_reward, next_state.copy(), done)
            
            # 存储到当前回合记忆（用于PPO更新）
            memory.append((state, action, log_prob, total_reward, done))
            episode_memory.append((state, action, log_prob, total_reward, done))
            
            state = next_state
            current_ep_reward += total_reward
            
            # PPO更新（使用当前回合记忆）
            if timestep % update_timestep == 0 and len(memory) > 0:
                agent.update(memory)
                memory = []
            
            if done:
                break
        
        # 记录训练统计
        training_stats['episodes'].append(i_episode)
        training_stats['rewards'].append(current_ep_reward)
        
        # **修复6**: 更新学习率
        scheduler.step()
        current_lr = agent.optimizer.param_groups[0]['lr']
        
        # **修复7**: 跟踪最佳平均奖励（用于早停）
        if len(training_stats['rewards']) >= 10:
            recent_avg_reward = np.mean(training_stats['rewards'][-10:])
            if recent_avg_reward > best_avg_reward:
                best_avg_reward = recent_avg_reward
                no_improve_count = 0
                # 保存最佳模型（基于平均奖励）
                best_reward_model_path = "models/best_reward_model.pth"
                agent.save(best_reward_model_path)
            else:
                no_improve_count += 1
        
        # **修复8**: 早停机制
        if no_improve_count >= early_stop_patience:
            print(f"\n[早停] 连续{early_stop_patience}轮无改进，停止训练")
            print(f"最佳平均奖励: {best_avg_reward:.2f} (Episode {i_episode - early_stop_patience})")
            break
        
        # 定期评估
        if i_episode % eval_interval == 0:
            print(f"\n[评估] Episode {i_episode}")
            win_rate, avg_reward = evaluate_agent(agent, eval_env, num_episodes=10)
            training_stats['win_rates'].append(win_rate)
            training_stats['avg_rewards'].append(avg_reward)
            
            print(f"  胜率: {win_rate:.2%}")
            print(f"  平均奖励: {avg_reward:.2f}")
            print(f"  经验回放缓冲区: {len(replay_buffer)}/{replay_buffer_size}")
            
            # 保存最佳模型
            if win_rate > best_win_rate:
                best_win_rate = win_rate
                best_episode = i_episode
                best_model_path = "models/best_ppo_model.pth"
                agent.save(best_model_path)
                print(f"  ✅ 保存最佳模型: {best_model_path} (胜率: {win_rate:.2%})")
        
        # 定期保存检查点
        if i_episode % checkpoint_interval == 0:
            checkpoint_path = f"models/checkpoint_ep{i_episode}.pth"
            agent.save(checkpoint_path)
            print(f"[检查点] Episode {i_episode}: 保存检查点 {checkpoint_path}")
        
        # 定期打印训练进度
        if i_episode % 10 == 0:
            avg_reward_10 = np.mean(training_stats['rewards'][-10:])
            print(f"Episode {i_episode}/{max_episodes} | 奖励: {current_ep_reward:.2f} | 近10回合平均: {avg_reward_10:.2f} | 学习率: {current_lr:.6f} | 无改进计数: {no_improve_count}/{early_stop_patience}")
        
        # 保存训练日志
        if i_episode % 50 == 0:
            log_path = f"training_logs/training_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(training_stats, f, indent=2, ensure_ascii=False)
    
    # 6. 训练完成
    print("\n" + "="*60)
    print("训练完成！")
    print("="*60)
    print(f"最佳模型: models/best_ppo_model.pth")
    print(f"最佳胜率: {best_win_rate:.2%} (Episode {best_episode})")
    print(f"最终模型: models/ppo_model_final.pth")
    
    # 保存最终模型
    agent.save("models/ppo_model_final.pth")
    
    # 保存最终训练统计
    final_log_path = f"training_logs/final_training_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(final_log_path, 'w', encoding='utf-8') as f:
        json.dump(training_stats, f, indent=2, ensure_ascii=False)
    
    print(f"训练日志: {final_log_path}")
    print("="*60)


if __name__ == "__main__":
    train_enhanced_self_play(
        max_episodes=1000,
        eval_interval=100,
        checkpoint_interval=200,
        replay_buffer_size=10000
    )

