# -*- coding: utf-8 -*-
"""
多因素评估器 (Multi Factor Evaluator)
功能：
- 综合评估出牌动作的价值
- 结合牌型、剩余牌、配合、风险等因素
"""

from typing import Dict, List, Optional, Tuple
import sys
from pathlib import Path

# 将 src 目录添加到系统路径
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from game_logic.enhanced_state import EnhancedGameStateManager
from game_logic.hand_combiner import HandCombiner
from decision.cooperation import CooperationStrategy


class MultiFactorEvaluator:
    """多因素评估器类"""
    
    def __init__(self, state_manager: EnhancedGameStateManager, 
                 combiner: HandCombiner,
                 cooperation: CooperationStrategy):
        """
        初始化多因素评估器
        
        Args:
            state_manager: 游戏状态管理器
            combiner: 手牌组合器
            cooperation: 配合策略
        """
        self.state = state_manager
        self.combiner = combiner
        self.cooperation = cooperation
        
        # 评估权重配置
        self.weights = {
            "remaining_cards": 0.25,
            "card_type_value": 0.20,
            "cooperation": 0.20,
            "risk": 0.15,
            "timing": 0.10,
            "hand_structure": 0.10
        }
    
    def evaluate_all_actions(self, action_list: List[List], 
                            target_action: Optional[List] = None) -> List[Tuple[int, float]]:
        """
        评估所有可选动作
        
        Args:
            action_list: 动作列表
            target_action: 目标动作（被动出牌时）
        
        Returns:
            评估结果列表 [(索引, 分数), ...]，按分数降序排列
        """
        evaluations = []
        
        for idx, action in enumerate(action_list):
            if action[0] == "PASS":
                score = 0.0
            else:
                score = self._evaluate_action(action, target_action)
            evaluations.append((idx, score))
        
        # 按分数降序排序
        evaluations.sort(key=lambda x: x[1], reverse=True)
        return evaluations
    
    def _evaluate_action(self, action: List, target_action: Optional[List]) -> float:
        """
        评估单个动作
        
        Args:
            action: 动作
            target_action: 目标动作
        
        Returns:
            评估分数
        """
        scores = {}
        
        # 1. 牌型价值
        scores["card_type_value"] = self._evaluate_card_type_value(action)
        
        # 2. 剩余牌数影响
        scores["remaining_cards"] = self._evaluate_remaining_cards(action)
        
        # 3. 配合度
        scores["cooperation"] = self._evaluate_cooperation(action, target_action)
        
        # 4. 风险评估
        scores["risk"] = self._evaluate_risk(action)
        
        # 5. 时机评估
        scores["timing"] = self._evaluate_timing(action, target_action)
        
        # 6. 手牌结构影响
        scores["hand_structure"] = self._evaluate_hand_structure(action)
        
        # 计算加权总分
        total_score = sum(scores[factor] * self.weights[factor] 
                         for factor in scores)
        
        return total_score
    
    def _evaluate_card_type_value(self, action: List) -> float:
        """评估牌型价值"""
        if not action or action[0] == "PASS":
            return 0.0
        
        type_values = {
            "Bomb": 20.0,
            "StraightFlush": 18.0,
            "TwoTrips": 15.0,
            "ThreePair": 12.0,
            "Straight": 10.0,
            "ThreeWithTwo": 8.0,
            "Trips": 6.0,
            "Pair": 4.0,
            "Single": 2.0
        }
        
        base_value = type_values.get(action[0], 1.0)
        
        # 归一化到 0-1
        return min(base_value / 20.0, 1.0)
    
    def _evaluate_remaining_cards(self, action: List) -> float:
        """评估剩余牌数影响"""
        # 出牌越多，剩余越少，分数越高
        cards = action[2] if len(action) > 2 else []
        card_count = len(cards) if isinstance(cards, list) else 1
        
        # 假设初始27张牌
        return 1.0 - (card_count / 27.0)
    
    def _evaluate_cooperation(self, action: List, target_action: Optional[List]) -> float:
        """评估配合度"""
        if not target_action:
            return 0.5  # 主动出牌，默认配合度
        
        # 计算动作价值
        action_value = self.cooperation._calculate_action_value(action)
        target_value = self.cooperation._calculate_action_value(target_action)
        
        # 如果动作价值大于目标价值
        if action_value > target_value:
            diff = action_value - target_value
            if diff < 5:  # 价值差异小，配合度高
                return 0.8
            else:  # 价值差异大，配合度低
                return 0.4
        
        return 0.2  # 无法管上
    
    def _evaluate_risk(self, action: List) -> float:
        """评估风险"""
        # 炸弹风险高，单张对子风险低
        if action[0] == "Bomb":
            return 0.9  # 高风险
        elif action[0] in ["Single", "Pair"]:
            return 0.3  # 低风险
        else:
            return 0.6  # 中等风险
    
    def _evaluate_timing(self, action: List, target_action: Optional[List]) -> float:
        """评估时机"""
        # 暂未实现复杂时机评估
        return 0.5
    
    def _evaluate_hand_structure(self, action: List) -> float:
        """评估手牌结构影响"""
        # 暂未实现复杂结构评估
        return 0.5

