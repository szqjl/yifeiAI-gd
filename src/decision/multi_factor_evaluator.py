# -*- coding: utf-8 -*-
"""
多因素评估系统 (Multi-Factor Evaluator)
功能：
- 综合评估多个因素
- 计算动作的综合评分
- 支持权重调整
"""

from typing import Dict, List, Optional, Tuple
from ..game_logic.enhanced_state import EnhancedGameStateManager
from ..game_logic.hand_combiner import HandCombiner
from .cooperation import CooperationStrategy


class MultiFactorEvaluator:
    """多因素评估器"""
    
    def __init__(self, state_manager: EnhancedGameStateManager,
                 hand_combiner: HandCombiner,
                 cooperation: CooperationStrategy):
        self.state = state_manager
        self.combiner = hand_combiner
        self.cooperation = cooperation
        
        # 评估权重（可调整）
        self.weights = {
            "remaining_cards": 0.25,      # 剩余牌数因素
            "card_type_value": 0.20,      # 牌型大小因素
            "cooperation": 0.20,          # 配合因素
            "risk": 0.15,                 # 风险因素
            "timing": 0.10,               # 时机因素
            "hand_structure": 0.10        # 手牌结构因素
        }
    
    def evaluate_action(self, action: List, action_index: int,
                       cur_action: Optional[List] = None,
                       action_list: List[List] = None) -> float:
        """
        评估动作的综合评分
        
        Args:
            action: 要评估的动作
            action_index: 动作索引
            cur_action: 当前需要压制的动作（被动出牌时）
            action_list: 所有可选动作列表
        
        Returns:
            综合评分（数值越大越好）
        """
        if action[0] == "PASS":
            return self._evaluate_pass(cur_action)
        
        scores = {}
        
        # 1. 剩余牌数因素
        scores["remaining_cards"] = self._evaluate_remaining_cards_factor(action)
        
        # 2. 牌型大小因素
        scores["card_type_value"] = self._evaluate_card_type_value(action, cur_action)
        
        # 3. 配合因素
        scores["cooperation"] = self._evaluate_cooperation_factor(action, cur_action)
        
        # 4. 风险因素
        scores["risk"] = self._evaluate_risk_factor(action)
        
        # 5. 时机因素
        scores["timing"] = self._evaluate_timing_factor()
        
        # 6. 手牌结构因素
        scores["hand_structure"] = self._evaluate_hand_structure_factor(action)
        
        # 计算加权总分
        total_score = sum(
            scores[factor] * self.weights[factor]
            for factor in scores
        )
        
        return total_score
    
    def _evaluate_remaining_cards_factor(self, action: List) -> float:
        """
        评估剩余牌数因素
        
        Returns:
            评分（0-100）
        """
        my_remain = len(self.state.hand_cards)
        teammate_remain = self.state.get_teammate_remain_cards()
        opponent_remain = self.state.get_opponent_remain_cards()
        
        # 如果自己牌很少，优先出牌
        if my_remain <= 5:
            return 100
        
        # 如果队友牌很少，考虑配合
        if teammate_remain <= 5:
            return 80
        
        # 如果对手牌很少，应该压制
        min_opponent = min(opponent_remain) if opponent_remain else 27
        if min_opponent <= 5:
            return 90
        
        # 正常情况
        return 50
    
    def _evaluate_card_type_value(self, action: List,
                                 cur_action: Optional[List]) -> float:
        """
        评估牌型大小因素
        
        Returns:
            评分（0-100）
        """
        action_value = self.cooperation._calculate_action_value(action)
        
        if cur_action:
            cur_value = self.cooperation._calculate_action_value(cur_action)
            # 如果能压制，根据压制幅度评分
            if action_value > cur_value:
                diff = action_value - cur_value
                # 压制幅度越小越好（节省牌力）
                if diff <= 2:
                    return 90
                elif diff <= 5:
                    return 70
                else:
                    return 50
            else:
                return 0  # 无法压制
        else:
            # 主动出牌，选择小牌
            if action_value <= 10:
                return 80
            elif action_value <= 14:
                return 60
            else:
                return 40
    
    def _evaluate_cooperation_factor(self, action: List,
                                    cur_action: Optional[List]) -> float:
        """
        评估配合因素
        
        Returns:
            评分（0-100）
        """
        if not cur_action:
            return 50  # 主动出牌，配合因素不重要
        
        # 评估配合机会
        evaluation = self.cooperation.evaluate_cooperation_opportunity(
            [action], cur_action
        )
        
        if evaluation["should_support"]:
            # 应该配合，PASS得分高
            if action[0] == "PASS":
                return 100
            else:
                return 20  # 不应该出牌
        elif evaluation["should_take_over"]:
            # 应该接替，出牌得分高
            if action[0] != "PASS":
                return 90
            else:
                return 30
        
        return 50  # 正常情况
    
    def _evaluate_risk_factor(self, action: List) -> float:
        """
        评估风险因素
        
        Returns:
            评分（0-100）
        """
        pass_num, my_pass_num = self.state.get_pass_count()
        
        # 如果连续PASS次数过多，出牌风险降低
        if pass_num >= 7 or my_pass_num >= 5:
            if action[0] != "PASS":
                return 80  # 应该出牌
        
        # 如果手牌很少，出牌风险降低
        if len(self.state.hand_cards) <= 5:
            if action[0] != "PASS":
                return 90
        
        # 如果出的是大牌（炸弹），风险较高
        if action[0] in ["Bomb", "StraightFlush"]:
            return 40  # 风险较高
        
        return 60  # 正常风险
    
    def _evaluate_timing_factor(self) -> float:
        """
        评估时机因素
        
        Returns:
            评分（0-100）
        """
        # 根据游戏阶段评分
        stage = self.state.stage
        if stage == "play":
            # 根据当前等级评分
            cur_rank = self.state.cur_rank
            if cur_rank == "A":
                return 90  # 关键阶段
            elif cur_rank in ["K", "Q"]:
                return 70
            else:
                return 50
        
        return 50
    
    def _evaluate_hand_structure_factor(self, action: List) -> float:
        """
        评估手牌结构因素
        
        Returns:
            评分（0-100）
        """
        handcards = self.state.hand_cards
        rank = self.state.cur_rank
        
        # 分析手牌结构
        sorted_cards, _ = self.combiner.combine_handcards(handcards, rank)
        
        # 检查动作中的牌是否破坏手牌结构
        action_cards = set(action[2])
        
        # 检查是否破坏顺子
        if sorted_cards.get("Straight"):
            straight_cards = set(sorted_cards["Straight"][0])
            if action_cards & straight_cards:
                return 30  # 破坏顺子，评分低
        
        # 检查是否破坏同花顺
        if sorted_cards.get("StraightFlush"):
            flush_cards = set(sorted_cards["StraightFlush"][0])
            if action_cards & flush_cards:
                return 20  # 破坏同花顺，评分很低
        
        # 检查是否破坏对子
        if action[0] == "Single":
            for pair in sorted_cards.get("Pair", []):
                if action[2][0] in pair:
                    return 40  # 破坏对子，评分较低
        
        # 如果动作中的牌是单张成员，评分高
        if action[0] == "Single":
            if action[2][0] in sorted_cards.get("Single", []):
                return 80
        
        # 如果动作中的牌是对子成员，评分高
        if action[0] == "Pair":
            for pair in sorted_cards.get("Pair", []):
                if action[2][0] in pair:
                    return 80
        
        return 60  # 正常情况
    
    def _evaluate_pass(self, cur_action: Optional[List]) -> float:
        """
        评估PASS动作
        
        Returns:
            评分（0-100）
        """
        if not cur_action:
            return 0  # 主动出牌时不应该PASS
        
        # 评估配合因素
        evaluation = self.cooperation.evaluate_cooperation_opportunity(
            [["PASS", "PASS", "PASS"]], cur_action
        )
        
        if evaluation["should_support"]:
            return 100  # 应该配合，PASS得分高
        
        # 如果无法压制，PASS是合理选择
        return 50
    
    def evaluate_all_actions(self, action_list: List[List],
                            cur_action: Optional[List] = None) -> List[Tuple[int, float]]:
        """
        评估所有动作
        
        Args:
            action_list: 所有可选动作列表
            cur_action: 当前需要压制的动作
        
        Returns:
            [(动作索引, 评分), ...] 列表，按评分降序排列
        """
        evaluations = []
        
        for i, action in enumerate(action_list):
            score = self.evaluate_action(action, i, cur_action, action_list)
            evaluations.append((i, score))
        
        # 按评分降序排列
        evaluations.sort(key=lambda x: x[1], reverse=True)
        
        return evaluations
    
    def get_best_action(self, action_list: List[List],
                       cur_action: Optional[List] = None) -> int:
        """
        获取最佳动作索引
        
        Args:
            action_list: 所有可选动作列表
            cur_action: 当前需要压制的动作
        
        Returns:
            最佳动作索引
        """
        evaluations = self.evaluate_all_actions(action_list, cur_action)
        if evaluations:
            return evaluations[0][0]
        return 0
    
    def update_weights(self, weights: Dict[str, float]):
        """
        更新评估权重
        
        Args:
            weights: 新的权重字典
        """
        self.weights.update(weights)
        
        # 归一化权重
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

