# -*- coding: utf-8 -*-
"""
轨迹收集器 - 收集高胜率对局轨迹
基于文章启发：收集探索中成功的轨迹，用于后续训练

核心功能：
1. 收集高胜率对局的完整轨迹
2. 标记轨迹中的关键决策点
3. 计算轨迹质量分数
4. 支持轨迹筛选和过滤
"""

import os
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class TrajectoryCollector:
    """轨迹收集器 - 收集和筛选高质量对局轨迹"""
    
    def __init__(self, min_win_rate: float = 0.6, min_trajectory_score: float = 0.7):
        """
        初始化轨迹收集器
        
        Args:
            min_win_rate: 最低胜率阈值（只收集胜率>=此值的对局）
            min_trajectory_score: 最低轨迹质量分数（只收集分数>=此值的轨迹）
        """
        self.min_win_rate = min_win_rate
        self.min_trajectory_score = min_trajectory_score
        self.trajectories = []
        self.stats = {
            'total_games': 0,
            'high_win_rate_games': 0,
            'collected_trajectories': 0,
            'filtered_trajectories': 0
        }
    
    def collect_from_game_record(self, game_record: Dict) -> Optional[List[Dict]]:
        """
        从单局游戏记录中收集轨迹
        
        Args:
            game_record: 游戏记录字典，包含：
                - game_info: 游戏基本信息
                - all_players_hands: 所有玩家手牌
                - game_states: 游戏状态序列
                - actions: 动作序列
                - winner: 获胜方
        
        Returns:
            如果轨迹质量达标，返回轨迹列表；否则返回None
        """
        self.stats['total_games'] += 1
        
        # 检查胜率
        winner = game_record.get('winner', -1)
        if winner == -1:
            return None
        
        # 判断目标玩家是否获胜（假设player_id=0）
        target_player_id = 0
        is_winner = (winner == target_player_id or winner == target_player_id + 2)
        
        if not is_winner:
            return None
        
        self.stats['high_win_rate_games'] += 1
        
        # 提取轨迹
        trajectory = self._extract_trajectory(game_record, target_player_id)
        
        # 计算轨迹质量分数
        trajectory_score = self._calculate_trajectory_score(trajectory, game_record)
        
        if trajectory_score >= self.min_trajectory_score:
            trajectory['score'] = trajectory_score
            trajectory['timestamp'] = datetime.now().isoformat()
            self.trajectories.append(trajectory)
            self.stats['collected_trajectories'] += 1
            return trajectory
        else:
            self.stats['filtered_trajectories'] += 1
            return None
    
    def _extract_trajectory(self, game_record: Dict, player_id: int) -> List[Dict]:
        """
        从游戏记录中提取轨迹
        
        Args:
            game_record: 游戏记录
            player_id: 目标玩家ID
        
        Returns:
            轨迹列表，每个元素包含：
                - state: 状态向量
                - action: 动作
                - reward: 即时奖励（中间奖励）
                - is_key_decision: 是否为关键决策点
        """
        trajectory = []
        game_states = game_record.get('game_states', [])
        actions = game_record.get('actions', [])
        
        # 计算中间奖励
        intermediate_rewards = self._calculate_intermediate_rewards(game_record, player_id)
        
        for i, (state, action) in enumerate(zip(game_states, actions)):
            if state.get('current_player') != player_id:
                continue
            
            # 判断是否为关键决策点
            is_key_decision = self._is_key_decision(state, action, i, len(game_states))
            
            trajectory.append({
                'state': state,
                'action': action,
                'reward': intermediate_rewards.get(i, 0.0),
                'is_key_decision': is_key_decision,
                'step': i,
                'game_phase': state.get('game_phase', 0)
            })
        
        return trajectory
    
    def _calculate_intermediate_rewards(self, game_record: Dict, player_id: int) -> Dict[int, float]:
        """
        计算中间奖励（缓解稀疏奖励问题）
        
        基于文章启发：设计中间奖励信号，避免只依赖最终胜率
        
        Args:
            game_record: 游戏记录
            player_id: 目标玩家ID
        
        Returns:
            步骤索引到奖励的映射
        """
        rewards = {}
        game_states = game_record.get('game_states', [])
        actions = game_record.get('actions', [])
        
        for i, (state, action) in enumerate(zip(game_states, actions)):
            if state.get('current_player') != player_id:
                continue
            
            reward = 0.0
            
            # 1. 压制成功奖励（成功压制对手）
            if self._is_successful_suppression(state, action):
                reward += 0.1
            
            # 2. 配合奖励（与队友配合良好）
            if self._is_good_cooperation(state, action, player_id):
                reward += 0.15
            
            # 3. 控场奖励（控制局面）
            if self._is_controlling(state, action):
                reward += 0.1
            
            # 4. 出牌效率奖励（减少手牌数）
            hand_size = len(state.get('hand', []))
            if hand_size < 10:  # 手牌较少时给予奖励
                reward += 0.05
            
            # 5. 关键牌使用奖励（在关键时刻使用炸弹等）
            if self._is_key_card_usage(state, action):
                reward += 0.2
            
            rewards[i] = reward
        
        return rewards
    
    def _is_successful_suppression(self, state: Dict, action: Dict) -> bool:
        """判断是否成功压制对手"""
        # 简化实现：如果出牌后对手无法跟牌，视为成功压制
        action_type = action.get('action_type', '')
        if action_type in ['Bomb', 'bomb']:
            return True
        return False
    
    def _is_good_cooperation(self, state: Dict, action: Dict, player_id: int) -> bool:
        """判断是否与队友配合良好"""
        # 简化实现：如果队友需要帮助时出牌，视为配合良好
        teammate_id = (player_id + 2) % 4
        teammate_hand_size = state.get('player_rest_cards', [0, 0, 0, 0])[teammate_id]
        if teammate_hand_size < 5 and action.get('action_type') != 'PASS':
            return True
        return False
    
    def _is_controlling(self, state: Dict, action: Dict) -> bool:
        """判断是否控制局面"""
        # 简化实现：如果出牌后获得出牌权，视为控场
        return action.get('action_type') != 'PASS'
    
    def _is_key_card_usage(self, state: Dict, action: Dict) -> bool:
        """判断是否在关键时刻使用关键牌"""
        action_type = action.get('action_type', '')
        game_phase = state.get('game_phase', 0)
        
        # 残局阶段使用炸弹等关键牌
        if game_phase == 2 and action_type in ['Bomb', 'bomb']:
            return True
        
        return False
    
    def _is_key_decision(self, state: Dict, action: Dict, step: int, total_steps: int) -> bool:
        """
        判断是否为关键决策点
        
        Args:
            state: 当前状态
            action: 当前动作
            step: 当前步骤
            total_steps: 总步骤数
        
        Returns:
            是否为关键决策点
        """
        # 1. 游戏开始和结束阶段
        if step < 5 or step > total_steps - 5:
            return True
        
        # 2. 使用炸弹等关键牌
        action_type = action.get('action_type', '')
        if action_type in ['Bomb', 'bomb']:
            return True
        
        # 3. 残局阶段
        if state.get('game_phase', 0) == 2:
            return True
        
        # 4. 手牌数较少时
        hand_size = len(state.get('hand', []))
        if hand_size < 5:
            return True
        
        return False
    
    def _calculate_trajectory_score(self, trajectory: List[Dict], game_record: Dict) -> float:
        """
        计算轨迹质量分数
        
        Args:
            trajectory: 轨迹列表
            game_record: 游戏记录
        
        Returns:
            轨迹质量分数（0-1）
        """
        if not trajectory:
            return 0.0
        
        score = 0.0
        
        # 1. 关键决策点比例（30%）
        key_decisions = sum(1 for t in trajectory if t.get('is_key_decision', False))
        key_decision_ratio = key_decisions / len(trajectory) if trajectory else 0
        score += key_decision_ratio * 0.3
        
        # 2. 平均中间奖励（30%）
        avg_reward = np.mean([t.get('reward', 0.0) for t in trajectory])
        score += min(avg_reward * 2, 1.0) * 0.3  # 归一化到0-1
        
        # 3. 轨迹长度合理性（20%）
        # 轨迹不应该太短（说明被动）也不应该太长（说明效率低）
        optimal_length = 30  # 假设最优轨迹长度
        length_score = 1.0 - abs(len(trajectory) - optimal_length) / optimal_length
        length_score = max(0, min(1, length_score))
        score += length_score * 0.2
        
        # 4. 最终获胜（20%）
        winner = game_record.get('winner', -1)
        if winner == 0 or winner == 2:
            score += 0.2
        
        return min(score, 1.0)
    
    def save_trajectories(self, output_path: str):
        """保存收集的轨迹到文件"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        output_data = {
            'metadata': {
                'collection_time': datetime.now().isoformat(),
                'min_win_rate': self.min_win_rate,
                'min_trajectory_score': self.min_trajectory_score,
                'stats': self.stats
            },
            'trajectories': self.trajectories
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已保存 {len(self.trajectories)} 条轨迹到 {output_path}")
        print(f"📊 统计信息：")
        print(f"   - 总对局数: {self.stats['total_games']}")
        print(f"   - 高胜率对局: {self.stats['high_win_rate_games']}")
        print(f"   - 收集轨迹数: {self.stats['collected_trajectories']}")
        print(f"   - 过滤轨迹数: {self.stats['filtered_trajectories']}")
    
    def load_trajectories(self, input_path: str):
        """从文件加载轨迹"""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.trajectories = data.get('trajectories', [])
        self.stats = data.get('metadata', {}).get('stats', self.stats)
        
        print(f"✅ 已加载 {len(self.trajectories)} 条轨迹")
    
    def get_trajectories(self, min_score: Optional[float] = None) -> List[Dict]:
        """
        获取轨迹列表
        
        Args:
            min_score: 最低分数阈值（可选）
        
        Returns:
            轨迹列表
        """
        if min_score is None:
            return self.trajectories
        
        return [t for t in self.trajectories if t.get('score', 0) >= min_score]

