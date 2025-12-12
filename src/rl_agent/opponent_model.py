# -*- coding: utf-8 -*-
"""
对手建模系统
分析和预测对手的行为模式和策略倾向
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional
import numpy as np


class OpponentBehaviorEncoder(nn.Module):
    """
    对手行为编码器
    将对手的历史行为编码为特征向量
    """

    def __init__(self, action_dim=512, hidden_dim=128):
        super(OpponentBehaviorEncoder, self).__init__()

        self.action_encoder = nn.Sequential(
            nn.Linear(action_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1)
        )

        self.history_encoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1)
        )

        # 注意力机制来关注重要的历史行为
        self.attention = nn.MultiheadAttention(hidden_dim, num_heads=4, batch_first=True)

    def forward(self, opponent_actions: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        编码对手的行为序列

        Args:
            opponent_actions: 对手历史动作序列 (batch_size, seq_len, action_dim)
            mask: 注意力掩码 (batch_size, seq_len)

        Returns:
            对手行为特征向量 (batch_size, hidden_dim)
        """
        # 编码每个动作
        action_features = self.action_encoder(opponent_actions)  # (batch, seq, hidden)

        # 使用注意力聚合历史信息
        attn_output, _ = self.attention(action_features, action_features, action_features,
                                      key_padding_mask=mask)  # (batch, seq, hidden)

        # 聚合序列信息（取平均或使用特殊的聚合方式）
        behavior_features = torch.mean(attn_output, dim=1)  # (batch, hidden)

        # 最终编码
        final_features = self.history_encoder(behavior_features)  # (batch, hidden)

        return final_features


class OpponentTypeClassifier(nn.Module):
    """
    对手类型分类器
    将对手分为不同的类型（激进型、保守型、随机型等）
    """

    def __init__(self, feature_dim=128, num_types=5):
        super(OpponentTypeClassifier, self).__init__()

        self.classifier = nn.Sequential(
            nn.Linear(feature_dim, feature_dim // 2),
            nn.LayerNorm(feature_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(feature_dim // 2, num_types)
        )

    def forward(self, behavior_features: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        对手类型分类

        Args:
            behavior_features: 对手行为特征 (batch_size, feature_dim)

        Returns:
            logits: 分类logits (batch_size, num_types)
            probs: 分类概率 (batch_size, num_types)
        """
        logits = self.classifier(behavior_features)
        probs = F.softmax(logits, dim=-1)
        return logits, probs


class OpponentActionPredictor(nn.Module):
    """
    对手动作预测器
    基于对手类型和当前状态预测对手可能的动作
    """

    def __init__(self, state_dim=512, opponent_feature_dim=128, action_dim=512):
        super(OpponentActionPredictor, self).__init__()

        self.state_encoder = nn.Sequential(
            nn.Linear(state_dim, opponent_feature_dim),
            nn.LayerNorm(opponent_feature_dim),
            nn.ReLU(),
            nn.Dropout(0.1)
        )

        # 结合对手特征和状态特征进行预测
        self.combined_encoder = nn.Sequential(
            nn.Linear(opponent_feature_dim * 2, opponent_feature_dim),
            nn.LayerNorm(opponent_feature_dim),
            nn.ReLU(),
            nn.Dropout(0.1)
        )

        self.action_predictor = nn.Sequential(
            nn.Linear(opponent_feature_dim, opponent_feature_dim),
            nn.LayerNorm(opponent_feature_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(opponent_feature_dim, action_dim)
        )

    def forward(self, game_state: torch.Tensor, opponent_features: torch.Tensor) -> torch.Tensor:
        """
        预测对手可能的动作

        Args:
            game_state: 当前游戏状态 (batch_size, state_dim)
            opponent_features: 对手行为特征 (batch_size, feature_dim)

        Returns:
            predicted_actions: 预测的动作概率 (batch_size, action_dim)
        """
        # 编码游戏状态
        state_features = self.state_encoder(game_state)

        # 结合对手特征和状态特征
        combined = torch.cat([state_features, opponent_features], dim=-1)
        combined_features = self.combined_encoder(combined)

        # 预测动作
        action_logits = self.action_predictor(combined_features)
        action_probs = torch.sigmoid(action_logits)

        return action_probs


class OpponentModel(nn.Module):
    """
    完整的对手建模系统
    结合行为编码、类型分类和动作预测
    """

    def __init__(self, state_dim=512, action_dim=512, opponent_types=5):
        super(OpponentModel, self).__init__()

        self.opponent_types = opponent_types
        self.feature_dim = 128

        # 子模块
        self.behavior_encoder = OpponentBehaviorEncoder(action_dim, self.feature_dim)
        self.type_classifier = OpponentTypeClassifier(self.feature_dim, opponent_types)
        self.action_predictor = OpponentActionPredictor(state_dim, self.feature_dim, action_dim)

    def forward(self, game_state: torch.Tensor, opponent_actions: torch.Tensor,
                action_mask: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        """
        完整的前向传播

        Args:
            game_state: 当前游戏状态 (batch_size, state_dim)
            opponent_actions: 对手历史动作 (batch_size, seq_len, action_dim)
            action_mask: 动作序列掩码 (batch_size, seq_len)

        Returns:
            包含所有预测结果的字典
        """
        # 编码对手行为
        behavior_features = self.behavior_encoder(opponent_actions, action_mask)

        # 对手类型分类
        type_logits, type_probs = self.type_classifier(behavior_features)

        # 动作预测
        predicted_actions = self.action_predictor(game_state, behavior_features)

        return {
            'behavior_features': behavior_features,
            'opponent_type_logits': type_logits,
            'opponent_type_probs': type_probs,
            'predicted_opponent_actions': predicted_actions
        }

    def predict_opponent_type(self, opponent_actions: torch.Tensor) -> Tuple[int, float]:
        """
        预测对手类型

        Args:
            opponent_actions: 对手历史动作序列

        Returns:
            opponent_type: 对手类型ID
            confidence: 预测置信度
        """
        with torch.no_grad():
            # 编码行为
            behavior_features = self.behavior_encoder(opponent_actions.unsqueeze(0))

            # 类型分类
            _, type_probs = self.type_classifier(behavior_features)

            # 获取最可能的类型
            opponent_type = torch.argmax(type_probs, dim=-1).item()
            confidence = type_probs[0, opponent_type].item()

            return opponent_type, confidence


# 对手类型定义
OPPONENT_TYPES = {
    0: "aggressive",     # 激进型：喜欢炸弹和大牌
    1: "conservative",   # 保守型：稳扎稳打，避免风险
    2: "random",         # 随机型：行为不可预测
    3: "follower",       # 跟牌型：主要跟对手出牌
    4: "strategic"       # 战略型：有明确策略倾向
}


class OpponentAnalyzer:
    """
    对手分析器
    提供高层对手行为分析功能
    """

    @staticmethod
    def analyze_opponent_behavior(opponent_actions: List[Dict]) -> Dict[str, float]:
        """
        分析对手的行为特征

        Args:
            opponent_actions: 对手历史动作列表

        Returns:
            行为特征分析结果
        """
        if not opponent_actions:
            return {"analysis": "insufficient_data"}

        # 统计各种行为模式
        bomb_count = sum(1 for action in opponent_actions if '炸弹' in str(action) or 'B' in str(action))
        single_count = sum(1 for action in opponent_actions if 'Single' in str(action))
        pair_count = sum(1 for action in opponent_actions if 'Pair' in str(action))
        pass_count = sum(1 for action in opponent_actions if 'PASS' in str(action))

        total_actions = len(opponent_actions)

        if total_actions == 0:
            return {"analysis": "no_actions"}

        # 计算行为比率
        bomb_ratio = bomb_count / total_actions
        single_ratio = single_count / total_actions
        pair_ratio = pair_count / total_actions
        pass_ratio = pass_count / total_actions

        # 基于行为特征判断对手类型
        if bomb_ratio > 0.2:
            opponent_type = "aggressive"
        elif pass_ratio > 0.4:
            opponent_type = "conservative"
        elif single_ratio > 0.6:
            opponent_type = "follower"
        elif bomb_ratio < 0.05 and pass_ratio < 0.2:
            opponent_type = "strategic"
        else:
            opponent_type = "random"

        return {
            "opponent_type": opponent_type,
            "bomb_ratio": bomb_ratio,
            "single_ratio": single_ratio,
            "pair_ratio": pair_ratio,
            "pass_ratio": pass_ratio,
            "total_actions": total_actions
        }

    @staticmethod
    def get_opponent_type_description(opponent_type: str) -> str:
        """
        获取对手类型的详细描述

        Args:
            opponent_type: 对手类型

        Returns:
            描述文本
        """
        descriptions = {
            "aggressive": "激进型对手：喜欢使用炸弹和大牌，攻击性强，风险偏好高",
            "conservative": "保守型对手：稳扎稳打，避免使用大牌，风险偏好低",
            "random": "随机型对手：行为不可预测，没有明确策略倾向",
            "follower": "跟牌型对手：主要跟其他玩家出牌，被动性较强",
            "strategic": "战略型对手：有明确的策略思维，决策较为理性"
        }

        return descriptions.get(opponent_type, "未知类型对手")



if __name__ == "__main__":
    print("对手建模系统模块加载成功")
