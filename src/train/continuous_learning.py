# -*- coding: utf-8 -*-
"""
持续学习模块
支持在线学习和增量更新
"""

import sys
import os
import torch
import numpy as np
from collections import deque
import json
from datetime import datetime

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

from src.rl_agent.agent import PPOAgent
from src.knowledge_processor.strategy_encoder import StrategyEncoder


class ModelVersionManager:
    """模型版本管理器"""
    
    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        self.version_file = os.path.join(model_dir, "model_versions.json")
        self.versions = self._load_versions()
    
    def _load_versions(self):
        """加载版本信息"""
        if os.path.exists(self.version_file):
            with open(self.version_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def save_version(self, agent, version_name, metadata=None):
        """保存模型版本"""
        version_info = {
            'version': version_name,
            'timestamp': datetime.now().isoformat(),
            'path': os.path.join(self.model_dir, f"model_v{version_name}.pth"),
            'metadata': metadata or {}
        }
        
        # 保存模型
        agent.save(version_info['path'])
        
        # 更新版本列表
        self.versions.append(version_info)
        
        # 保存版本信息
        with open(self.version_file, 'w', encoding='utf-8') as f:
            json.dump(self.versions, f, indent=2, ensure_ascii=False)
        
        return version_info
    
    def load_version(self, agent, version_name):
        """加载指定版本的模型"""
        for version_info in self.versions:
            if version_info['version'] == version_name:
                agent.load(version_info['path'])
                return version_info
        raise ValueError(f"版本 {version_name} 不存在")
    
    def list_versions(self):
        """列出所有版本"""
        return self.versions
    
    def get_latest_version(self):
        """获取最新版本"""
        if not self.versions:
            return None
        return sorted(self.versions, key=lambda x: x['timestamp'])[-1]


class ContinuousLearner:
    """持续学习器"""
    
    def __init__(self, agent, replay_buffer_size=5000, batch_size=32, update_threshold=100):
        """
        初始化持续学习器
        
        Args:
            agent: PPOAgent实例
            replay_buffer_size: 经验回放缓冲区大小
            batch_size: 批次大小
            update_threshold: 更新阈值（积累多少经验后更新）
        """
        self.agent = agent
        self.replay_buffer = deque(maxlen=replay_buffer_size)
        self.batch_size = batch_size
        self.update_threshold = update_threshold
        self.update_count = 0
        self.strategy_encoder = StrategyEncoder()
    
    def add_experience(self, state, action, log_prob, reward, next_state, done, info=None):
        """
        添加新的经验
        
        Args:
            state: 当前状态
            action: 动作
            log_prob: 动作的对数概率
            reward: 奖励
            next_state: 下一状态
            done: 是否结束
            info: 额外信息（用于计算shaping reward）
        """
        # 计算shaping reward（如果有info）
        shaping = 0.0
        if info:
            action_cards = info.get('action_cards', [])
            action_type = info.get('action_type', 'PASS')
            game_phase = info.get('game_phase', 'mid')
            state_dict = info.get('state_dict', {})
            
            shaping = self.strategy_encoder.calculate_shaping_reward(
                state_dict=state_dict,
                action_cards=action_cards,
                action_type=action_type,
                game_phase=game_phase,
                cur_rank=info.get('cur_rank', '2')
            )
        
        total_reward = reward + shaping
        
        # 存储经验
        self.replay_buffer.append((state, action, log_prob, total_reward, next_state, done))
        
        # 检查是否需要更新
        self.update_count += 1
        if self.update_count >= self.update_threshold:
            self.update()
            self.update_count = 0
    
    def update(self):
        """从经验回放缓冲区更新模型"""
        if len(self.replay_buffer) < self.batch_size:
            return
        
        # 随机采样一批经验
        batch = np.random.choice(len(self.replay_buffer), size=min(self.batch_size, len(self.replay_buffer)), replace=False)
        memory = [self.replay_buffer[i] for i in batch]
        
        # 更新智能体
        self.agent.update(memory)
    
    def get_buffer_size(self):
        """获取缓冲区大小"""
        return len(self.replay_buffer)
    
    def clear_buffer(self):
        """清空缓冲区"""
        self.replay_buffer.clear()


def online_learn_from_replay(agent, replay_file, model_version_manager=None):
    """
    从对局回放中在线学习
    
    Args:
        agent: PPOAgent实例
        replay_file: 回放文件路径
        model_version_manager: 模型版本管理器（可选）
    """
    print(f"从回放文件学习: {replay_file}")
    
    # TODO: 实现从回放文件中提取经验并学习
    # 这里需要解析回放文件，提取状态-动作-奖励序列
    # 然后使用ContinuousLearner进行增量学习
    
    pass


if __name__ == "__main__":
    # 示例：持续学习
    from src.rl_agent.agent import PPOAgent
    
    agent = PPOAgent(input_dim=512, action_dim=512)
    
    # 加载现有模型
    if os.path.exists("models/best_ppo_model.pth"):
        agent.load("models/best_ppo_model.pth")
    
    # 创建持续学习器
    learner = ContinuousLearner(agent, replay_buffer_size=5000, batch_size=32)
    
    # 创建版本管理器
    version_manager = ModelVersionManager()
    
    print("持续学习模块已初始化")
    print(f"经验缓冲区大小: {learner.get_buffer_size()}")
    print(f"模型版本数: {len(version_manager.list_versions())}")

