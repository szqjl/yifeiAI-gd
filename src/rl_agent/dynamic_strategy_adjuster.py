# -*- coding: utf-8 -*-
"""
动态策略调整器
根据局面变化和对手行为动态调整策略
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional
import numpy as np


class SituationEvaluator(nn.Module):
    """
    局面评估器
    评估当前游戏局面的特点和难度
    """

    def __init__(self, state_dim=512, hidden_dim=128):
        super(SituationEvaluator, self).__init__()

        self.state_encoder = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1)
        )

        self.opponent_encoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1)
        )

        # 局面特征提取
        self.situation_features = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1)
        )

        # 局面难度评估
        self.difficulty_evaluator = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()  # 输出0-1之间的难度分数
        )

        # 局面类型分类（开局、中局、残局、关键局等）
        self.situation_classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim // 2, 5)  # 5种局面类型
        )

    def forward(self, game_state: torch.Tensor, opponent_features: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        """
        评估当前局面

        Args:
            game_state: 游戏状态 (batch_size, state_dim)
            opponent_features: 对手特征 (batch_size, hidden_dim)

        Returns:
            局面评估结果
        """
        # 编码游戏状态
        state_features = self.state_encoder(game_state)

        if opponent_features is not None:
            # 编码对手信息
            opp_features = self.opponent_encoder(opponent_features)
            combined = torch.cat([state_features, opp_features], dim=-1)
        else:
            # 如果没有对手信息，使用状态特征的副本
            combined = torch.cat([state_features, state_features], dim=-1)

        # 提取局面特征
        situation_features = self.situation_features(combined)

        # 评估局面难度
        difficulty_score = self.difficulty_evaluator(situation_features)

        # 分类局面类型
        situation_logits = self.situation_classifier(situation_features)
        situation_probs = F.softmax(situation_logits, dim=-1)

        return {
            'situation_features': situation_features,
            'difficulty_score': difficulty_score,
            'situation_logits': situation_logits,
            'situation_probs': situation_probs
        }


class StrategyWeightAdjuster(nn.Module):
    """
    策略权重调整器
    根据局面特征动态调整不同策略的权重
    """

    def __init__(self, strategy_count=7, situation_feature_dim=128):
        super(StrategyWeightAdjuster, self).__init__()

        self.strategy_count = strategy_count

        # 策略权重预测器
        self.weight_predictor = nn.Sequential(
            nn.Linear(situation_feature_dim, situation_feature_dim),
            nn.LayerNorm(situation_feature_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(situation_feature_dim, strategy_count),
            nn.Softmax(dim=-1)  # 输出策略权重分布
        )

        # 策略切换预测器
        self.switch_predictor = nn.Sequential(
            nn.Linear(situation_feature_dim, situation_feature_dim // 2),
            nn.LayerNorm(situation_feature_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(situation_feature_dim // 2, strategy_count)
        )

    def forward(self, situation_features: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        计算策略权重和切换概率

        Args:
            situation_features: 局面特征 (batch_size, feature_dim)

        Returns:
            strategy_weights: 策略权重分布 (batch_size, strategy_count)
            switch_logits: 策略切换logits (batch_size, strategy_count)
        """
        strategy_weights = self.weight_predictor(situation_features)
        switch_logits = self.switch_predictor(situation_features)

        return strategy_weights, switch_logits


class DynamicStrategyAdjuster(nn.Module):
    """
    动态策略调整器
    结合局面评估和策略调整的完整系统
    """

    def __init__(self, state_dim=512, strategy_count=7):
        super(DynamicStrategyAdjuster, self).__init__()

        self.strategy_count = strategy_count
        self.feature_dim = 128

        # 子模块
        self.situation_evaluator = SituationEvaluator(state_dim, self.feature_dim)
        self.strategy_adjuster = StrategyWeightAdjuster(strategy_count, self.feature_dim)

    def forward(self, game_state: torch.Tensor, opponent_features: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        """
        动态策略调整

        Args:
            game_state: 游戏状态 (batch_size, state_dim)
            opponent_features: 对手特征 (batch_size, feature_dim)

        Returns:
            策略调整结果
        """
        # 评估当前局面
        situation_results = self.situation_evaluator(game_state, opponent_features)

        # 计算策略权重和切换概率
        strategy_weights, switch_logits = self.strategy_adjuster(situation_results['situation_features'])

        # 策略切换概率（softmax归一化）
        switch_probs = F.softmax(switch_logits, dim=-1)

        return {
            **situation_results,
            'strategy_weights': strategy_weights,
            'switch_logits': switch_logits,
            'switch_probs': switch_probs
        }

    def recommend_strategy(self, game_state: torch.Tensor, current_strategy: int,
                          opponent_features: Optional[torch.Tensor] = None) -> Dict[str, any]:
        """
        推荐新的策略

        Args:
            game_state: 当前游戏状态
            current_strategy: 当前策略ID
            opponent_features: 对手特征

        Returns:
            策略推荐结果
        """
        with torch.no_grad():
            results = self.forward(game_state.unsqueeze(0), opponent_features.unsqueeze(0) if opponent_features is not None else None)

            # 获取推荐策略
            recommended_strategy = torch.argmax(results['strategy_weights'], dim=-1).item()
            confidence = results['strategy_weights'][0, recommended_strategy].item()

            # 判断是否需要切换
            switch_prob = results['switch_probs'][0, recommended_strategy].item()

            # 局面难度
            difficulty = results['difficulty_score'].item()

            # 局面类型
            situation_type = torch.argmax(results['situation_probs'], dim=-1).item()

            return {
                'recommended_strategy': recommended_strategy,
                'current_strategy': current_strategy,
                'should_switch': recommended_strategy != current_strategy,
                'switch_confidence': switch_prob,
                'overall_confidence': confidence,
                'situation_difficulty': difficulty,
                'situation_type': situation_type,
                'strategy_weights': results['strategy_weights'].squeeze(0).tolist()
            }


# 局面类型定义
SITUATION_TYPES = {
    0: "opening",      # 开局：牌局初期
    1: "mid_game",     # 中局：牌局中期
    2: "end_game",     # 残局：牌局后期
    3: "critical",     # 关键局：重要时刻
    4: "normal"        # 普通局：常规局面
}

# 策略定义（与策略模式保持一致）
STRATEGIES = {
    0: "bomb_strategy",
    1: "control_strategy",
    2: "follow_strategy",
    3: "suppress_strategy",
    4: "protect_strategy",
    5: "group_strategy",
    6: "discard_strategy"
}


class StrategyManager:
    """
    策略管理器
    提供高层策略管理和调整功能
    """

    def __init__(self, strategy_adjuster: DynamicStrategyAdjuster):
        self.adjuster = strategy_adjuster
        self.current_strategy = 2  # 默认跟牌策略

    def update_strategy(self, game_state: torch.Tensor, opponent_features: Optional[torch.Tensor] = None) -> Dict[str, any]:
        """
        更新策略选择

        Args:
            game_state: 当前游戏状态
            opponent_features: 对手特征

        Returns:
            策略更新结果
        """
        recommendation = self.adjuster.recommend_strategy(game_state, self.current_strategy, opponent_features)

        old_strategy = self.current_strategy
        if recommendation['should_switch']:
            self.current_strategy = recommendation['recommended_strategy']

        return {
            **recommendation,
            'old_strategy': old_strategy,
            'strategy_changed': old_strategy != self.current_strategy
        }

    def get_current_strategy_info(self) -> Dict[str, any]:
        """
        获取当前策略信息

        Returns:
            当前策略的详细信息
        """
        return {
            'strategy_id': self.current_strategy,
            'strategy_name': STRATEGIES[self.current_strategy],
            'strategy_description': self._get_strategy_description(self.current_strategy)
        }

    def _get_strategy_description(self, strategy_id: int) -> str:
        """
        获取策略描述

        Args:
            strategy_id: 策略ID

        Returns:
            策略描述
        """
        descriptions = {
            0: "炸弹策略：使用炸弹压制对手，适合激进局面",
            1: "控制策略：控制关键牌，限制对手选择",
            2: "跟牌策略：跟随对手出牌，保持灵活性",
            3: "压制策略：主动出大牌压制对手",
            4: "保护策略：保护队友，协同作战",
            5: "组牌策略：注重牌型组合，寻找最佳时机",
            6: "出牌策略：快速出牌，减少手牌压力"
        }

        return descriptions.get(strategy_id, "未知策略")


def analyze_strategy_adaptation(strategy_history: List[Dict]) -> Dict[str, float]:
    """
    分析策略适应的效果

    Args:
        strategy_history: 策略调整历史记录

    Returns:
        适应性分析结果
    """
    if not strategy_history:
        return {"analysis": "insufficient_data"}

    # 统计策略切换频率
    switches = sum(1 for record in strategy_history if record.get('strategy_changed', False))
    total_decisions = len(strategy_history)

    switch_rate = switches / total_decisions if total_decisions > 0 else 0

    # 分析策略分布
    strategy_counts = {}
    for record in strategy_history:
        strategy_id = record.get('recommended_strategy', 0)
        strategy_counts[strategy_id] = strategy_counts.get(strategy_id, 0) + 1

    # 计算适应性指标
    strategy_diversity = len(strategy_counts) / 7  # 7种策略
    most_used_strategy = max(strategy_counts.values()) / total_decisions if strategy_counts else 0

    return {
        "total_decisions": total_decisions,
        "strategy_switches": switches,
        "switch_rate": switch_rate,
        "strategy_diversity": strategy_diversity,
        "strategy_concentration": most_used_strategy,
        "strategy_distribution": strategy_counts
    }



if __name__ == "__main__":
    print("动态策略调整器模块加载成功")
