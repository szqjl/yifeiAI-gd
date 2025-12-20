# -*- coding: utf-8 -*-
"""
策略模式识别器
识别和分类不同的策略模式
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class StrategyPatternRecognizer(nn.Module):
    """
    策略模式识别器
    基于游戏状态识别当前采用的策略模式
    """

    def __init__(self, input_dim=512, pattern_types=8, hidden_dim=256):
        super(StrategyPatternRecognizer, self).__init__()

        self.pattern_types = pattern_types

        # 策略模式特征提取器
        self.pattern_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1)
        )

        # 策略模式分类器
        self.pattern_classifier = nn.Linear(hidden_dim // 2, pattern_types)

        # 策略模式置信度输出
        self.pattern_confidence = nn.Linear(hidden_dim // 2, 1)

    def forward(self, state_features):
        """
        识别策略模式

        Args:
            state_features: 状态特征向量 (batch_size, input_dim)

        Returns:
            pattern_logits: 策略模式logits (batch_size, pattern_types)
            confidence: 策略模式识别置信度 (batch_size, 1)
        """
        # 提取策略模式特征
        pattern_features = self.pattern_encoder(state_features)

        # 策略模式分类
        pattern_logits = self.pattern_classifier(pattern_features)

        # 置信度评估
        confidence = torch.sigmoid(self.pattern_confidence(pattern_features))

        return pattern_logits, confidence

    def predict_pattern(self, state_features):
        """
        预测最可能的策略模式

        Args:
            state_features: 状态特征向量

        Returns:
            pattern_id: 策略模式ID
            confidence: 置信度
        """
        with torch.no_grad():
            pattern_logits, confidence = self.forward(state_features)
            pattern_probs = F.softmax(pattern_logits, dim=-1)
            pattern_id = torch.argmax(pattern_probs, dim=-1)
            return pattern_id.item(), confidence.item()


# 策略模式定义
STRATEGY_PATTERNS = {
    0: "bomb_strategy",      # 炸弹流：频繁使用炸弹
    1: "control_strategy",   # 控制流：控制关键牌
    2: "follow_strategy",    # 跟牌流：主要跟牌
    3: "suppress_strategy",  # 压制流：压制对手
    4: "protect_strategy",   # 保护流：保护队友
    5: "group_strategy",     # 组牌流：组合出牌
    6: "discard_strategy",   # 出牌流：快速出牌
    7: "unknown_strategy"    # 未知策略
}

PATTERN_NAMES = {v: k for k, v in STRATEGY_PATTERNS.items()}


class StrategyPatternAnalyzer:
    """
    策略模式分析器
    分析和解释策略模式的特征
    """

    @staticmethod
    def analyze_pattern_features(pattern_logits, confidence):
        """
        分析策略模式的特征

        Args:
            pattern_logits: 策略模式logits (batch_size, pattern_types)
            confidence: 置信度 (batch_size, 1)

        Returns:
            analysis: 策略模式分析结果
        """
        pattern_probs = F.softmax(pattern_logits, dim=-1)
        top_pattern = torch.argmax(pattern_probs, dim=-1).item()
        top_prob = pattern_probs[0, top_pattern].item()  # 取第一个样本

        analysis = {
            'primary_pattern': STRATEGY_PATTERNS[top_pattern],
            'pattern_confidence': top_prob,
            'overall_confidence': confidence.item() if torch.is_tensor(confidence) else confidence,
            'pattern_distribution': {
                STRATEGY_PATTERNS[i]: pattern_probs[0, i].item()
                for i in range(len(STRATEGY_PATTERNS))
            }
        }

        return analysis

    @staticmethod
    def get_pattern_description(pattern_name):
        """
        获取策略模式的详细描述

        Args:
            pattern_name: 策略模式名称

        Returns:
            description: 策略模式描述
        """
        descriptions = {
            "bomb_strategy": "炸弹流：倾向于保存和使用炸弹牌，关键时刻使用炸弹压制对手",
            "control_strategy": "控制流：控制关键级牌和重要单牌，限制对手的选择空间",
            "follow_strategy": "跟牌流：主要跟对手出牌，保持灵活性和观望态度",
            "suppress_strategy": "压制流：主动出大牌压制对手，争夺主动权",
            "protect_strategy": "保护流：优先保护队友利益，协同队友行动",
            "group_strategy": "组牌流：注重牌型组合，寻找最佳的组合出牌时机",
            "discard_strategy": "出牌流：快速出牌，减少手牌压力，追求速度",
            "unknown_strategy": "未知策略：无法识别的策略模式"
        }

        return descriptions.get(pattern_name, "未知策略模式")


def create_strategy_pattern_labels(game_history, player_actions):
    """
    基于游戏历史和玩家动作创建策略模式标签

    Args:
        game_history: 游戏历史记录
        player_actions: 玩家动作序列

    Returns:
        pattern_labels: 策略模式标签序列
    """
    # 这里应该实现基于游戏历史的策略模式标注逻辑
    # 目前返回一个简化的示例实现

    pattern_labels = []

    # 简化的策略模式识别逻辑（可以根据实际需求扩展）
    bomb_count = sum(1 for action in player_actions if '炸弹' in str(action) or 'B' in str(action))
    total_actions = len(player_actions)

    if total_actions > 0:
        bomb_ratio = bomb_count / total_actions

        if bomb_ratio > 0.3:
            pattern_labels = [0] * len(player_actions)  # bomb_strategy
        elif len([a for a in player_actions if '控制' in str(a)]) > total_actions * 0.4:
            pattern_labels = [1] * len(player_actions)  # control_strategy
        else:
            pattern_labels = [7] * len(player_actions)  # unknown_strategy
    else:
        pattern_labels = [7]  # unknown_strategy

    return pattern_labels


if __name__ == "__main__":
    # 测试策略模式识别器
    print("测试策略模式识别器")
    print("=" * 50)

    # 创建识别器
    recognizer = StrategyPatternRecognizer(input_dim=512, pattern_types=8)

    # 测试输入
    test_input = torch.randn(2, 512)
    pattern_logits, confidence = recognizer(test_input)

    print(f"输入形状: {test_input.shape}")
    print(f"策略模式输出形状: {pattern_logits.shape}")
    print(f"置信度输出形状: {confidence.shape}")

    # 分析结果
    analyzer = StrategyPatternAnalyzer()
    for i in range(test_input.size(0)):
        analysis = analyzer.analyze_pattern_features(
            pattern_logits[i:i+1], confidence[i:i+1]
        )
        print(f"\n样本 {i+1}:")
        print(f"  主要策略: {analysis['primary_pattern']}")
        print(f"  策略置信度: {analysis['pattern_confidence']:.3f}")
        print(f"  整体置信度: {analysis['overall_confidence']:.3f}")

        description = analyzer.get_pattern_description(analysis['primary_pattern'])
        print(f"  策略描述: {description}")

    print("\n✅ 策略模式识别器测试完成")
