# -*- coding: utf-8 -*-
"""
配合策略模块 (Cooperation Strategy)
功能：
- 识别队友意图
- 判断是否需要配合
- 制定配合策略
- 评估配合效果
"""

from typing import Dict, List, Optional, Tuple
from ..game_logic.enhanced_state import EnhancedGameStateManager


class CooperationStrategy:
    """配合策略模块"""
    
    def __init__(self, state_manager: EnhancedGameStateManager):
        self.state = state_manager
        
        # 配合策略参数
        self.support_threshold = 15  # 队友牌型值大于此值时，应该PASS
        self.danger_threshold = 4   # 对手剩余牌数小于此值时，应该配合
        self.max_val_threshold = 14  # 最大牌值阈值
    
    def should_support_teammate(self, cur_action_value: float) -> bool:
        """
        判断是否应该配合队友（PASS让队友继续）
        
        Args:
            cur_action_value: 当前需要压制的牌型值
        
        Returns:
            True: 应该PASS配合，False: 应该压制
        """
        # 1. 检查是否是队友出的牌
        if not self.state.is_teammate_action():
            return False
        
        # 2. 获取对手剩余牌数
        opponent_remain = self.state.get_opponent_remain_cards()
        min_opponent_remain = min(opponent_remain) if opponent_remain else 27
        
        # 3. 获取队友剩余牌数
        teammate_remain = self.state.get_teammate_remain_cards()
        
        # 4. 判断策略
        # 如果队友牌很大且对手牌不多，应该PASS
        if cur_action_value >= self.support_threshold:
            if min_opponent_remain <= self.danger_threshold:
                return True
        
        # 如果队友牌很大（接近最大），应该PASS
        if cur_action_value >= self.max_val_threshold:
            return True
        
        # 如果队友牌数很少（快出完了），应该配合
        if teammate_remain <= 5:
            return True
        
        return False
    
    def should_take_over(self, cur_action_value: float, 
                        my_action_value: float) -> bool:
        """
        判断是否应该接替队友（当队友牌不够大时）
        
        Args:
            cur_action_value: 当前需要压制的牌型值
            my_action_value: 自己可以出的牌型值
        
        Returns:
            True: 应该接替，False: 不应该接替
        """
        # 1. 检查是否是队友出的牌
        if not self.state.is_teammate_action():
            return False
        
        # 2. 如果队友牌不够大，但自己可以压制
        if cur_action_value < self.support_threshold:
            if my_action_value > cur_action_value:
                # 获取对手剩余牌数
                opponent_remain = self.state.get_opponent_remain_cards()
                min_opponent_remain = min(opponent_remain) if opponent_remain else 27
                
                # 如果对手牌不多，应该接替
                if min_opponent_remain <= self.danger_threshold:
                    return True
        
        return False
    
    def evaluate_cooperation_opportunity(self, action_list: List[List],
                                        cur_action: Optional[List]) -> Dict:
        """
        评估配合机会
        
        Args:
            action_list: 可选动作列表
            cur_action: 当前需要压制的动作
        
        Returns:
            评估结果字典
        """
        if not cur_action or cur_action[0] == "PASS":
            return {
                "should_pass": False,
                "should_support": False,
                "should_take_over": False,
                "reason": "no_action_to_beat"
            }
        
        # 计算当前动作的值
        cur_action_value = self._calculate_action_value(cur_action)
        
        # 判断是否应该配合
        should_support = self.should_support_teammate(cur_action_value)
        
        # 判断是否应该接替
        should_take_over = False
        best_my_action = None
        best_my_value = 0
        
        if not should_support:
            # 寻找可以压制的最佳动作
            for i, action in enumerate(action_list[1:], 1):  # 跳过PASS
                if action[0] == "PASS":
                    continue
                
                action_value = self._calculate_action_value(action)
                if action_value > cur_action_value and action_value > best_my_value:
                    best_my_value = action_value
                    best_my_action = i
                    should_take_over = self.should_take_over(
                        cur_action_value, action_value
                    )
        
        return {
            "should_pass": should_support,
            "should_support": should_support,
            "should_take_over": should_take_over,
            "best_action_index": best_my_action if should_take_over else None,
            "cur_action_value": cur_action_value,
            "best_my_value": best_my_value,
            "reason": "support_teammate" if should_support else 
                     ("take_over" if should_take_over else "normal_play")
        }
    
    def _calculate_action_value(self, action: List) -> float:
        """
        计算动作的值（用于比较大小）
        
        Args:
            action: 动作 [type, rank, cards]
        
        Returns:
            动作值（数值越大越强）
        """
        if action[0] == "PASS":
            return 0
        
        # 卡牌值映射
        card_value = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
            "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
            "B": 16, "R": 17
        }
        
        action_type = action[0]
        rank = action[1]
        cards = action[2]
        
        base_value = card_value.get(rank, 0)
        
        # 根据牌型调整
        if action_type == "Bomb":
            # 炸弹：基础值 + (数量-4) * 16
            base_value += (len(cards) - 4) * 16
        elif action_type == "StraightFlush":
            # 同花顺：基础值 + 32
            base_value += 32
        elif action_type in ["ThreeWithTwo", "TwoTrips"]:
            # 三带二、钢板：基础值 + 5
            base_value += 5
        elif action_type == "ThreePair":
            # 三连对：基础值 + 3
            base_value += 3
        
        return base_value
    
    def get_cooperation_strategy(self, action_list: List[List],
                                 cur_action: Optional[List],
                                 greater_action: Optional[List]) -> Dict:
        """
        获取配合策略
        
        Args:
            action_list: 可选动作列表
            cur_action: 当前动作
            greater_action: 最大动作
        
        Returns:
            策略建议字典
        """
        # 使用最大动作进行评估
        target_action = greater_action if greater_action else cur_action
        
        evaluation = self.evaluate_cooperation_opportunity(
            action_list, target_action
        )
        
        return {
            **evaluation,
            "teammate_pos": self.state.teammate_pos,
            "teammate_remain": self.state.get_teammate_remain_cards(),
            "opponent_remain": self.state.get_opponent_remain_cards(),
        }

