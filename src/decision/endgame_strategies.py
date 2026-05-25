# -*- coding: utf-8 -*-
"""
残局策略 (Endgame Strategies)
功能：
- 为残局处理器提供多种残局策略
- 策略作为残局处理器的内部策略使用
- M1版本：残局策略库
"""

from typing import Dict, List, Optional
from abc import ABC, abstractmethod
import logging
try:
    from game_logic.guandan_constants import DEFAULT_REST_CARDS
except ImportError:
    DEFAULT_REST_CARDS = 27


class EndgameStrategy(ABC):
    """残局策略基类（供残局处理器内部使用）"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def execute(self, message: Dict, context: Dict) -> Optional[int]:
        """执行残局策略"""
        pass


class RushStrategy(EndgameStrategy):
    """冲刺策略：快速出完牌"""
    
    def execute(self, message: Dict, context: Dict) -> Optional[int]:
        """执行冲刺策略（提升：更智能的出牌顺序）"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return None
        
        # 优先级1: 一手出完
        for i, action in enumerate(action_list):
            if action[0] == "PASS":
                continue
            if len(action) > 2 and len(action[2]) == len(handcards):
                self.logger.info("RushStrategy: 一手出完")
                return i
        
        # 优先级2: 出最大牌型（快速减少牌数）
        return self._select_largest_action(action_list)
    
    def _select_largest_action(self, action_list: List) -> Optional[int]:
        """选择最大的动作（牌数最多）"""
        max_cards = 0
        best_idx = None
        
        for i, action in enumerate(action_list):
            if action[0] == "PASS":
                continue
            if len(action) > 2:
                card_count = len(action[2]) if isinstance(action[2], list) else 0
                if card_count > max_cards:
                    max_cards = card_count
                    best_idx = i
        
        return best_idx if best_idx is not None else 0


class DefendStrategy(EndgameStrategy):
    """防守策略：保护队友"""
    
    def execute(self, message: Dict, context: Dict) -> Optional[int]:
        """执行防守策略（保护队友）"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return None
        
        # 如果队友牌数很少，优先PASS让队友出
        teammate_remain = context.get("teammate_rest_cards", DEFAULT_REST_CARDS)
        if teammate_remain <= 3:
            self.logger.info("DefendStrategy: 队友牌数少，PASS保护")
            return 0  # PASS
        
        # 否则，选择能压制对手的最小动作
        cur_action = message.get("curAction", [])
        if cur_action:
            return self._select_minimal_beat_action(action_list, cur_action)
        
        # 主动出牌：选择最小动作
        return self._select_smallest_action(action_list)
    
    def _select_minimal_beat_action(self, action_list: List, cur_action: List) -> Optional[int]:
        """选择能管住当前动作的最小动作"""
        cur_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
        
        for i, action in enumerate(action_list):
            if action[0] == "PASS":
                continue
            if action[0] == cur_type:
                return i
        
        return 0
    
    def _select_smallest_action(self, action_list: List) -> Optional[int]:
        """选择最小的动作（牌数最少）"""
        min_cards = float('inf')
        best_idx = None
        
        for i, action in enumerate(action_list):
            if action[0] == "PASS":
                continue
            if len(action) > 2:
                card_count = len(action[2]) if isinstance(action[2], list) else 0
                if card_count < min_cards:
                    min_cards = card_count
                    best_idx = i
        
        return best_idx if best_idx is not None else 0


class CooperateStrategy(EndgameStrategy):
    """配合策略：配合队友"""
    
    def execute(self, message: Dict, context: Dict) -> Optional[int]:
        """执行配合策略（配合队友）"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return None
        
        # 如果队友是最大动作者，让队友出
        greater_pos = message.get("greaterPos", -1)
        my_pos = message.get("myPos", 0)
        teammate_pos = (my_pos + 2) % 4
        
        if greater_pos == teammate_pos:
            self.logger.info("CooperateStrategy: 队友是最大动作者，PASS配合")
            return 0  # PASS
        
        # 否则，选择能帮助队友的动作
        teammate_remain = context.get("teammate_rest_cards", DEFAULT_REST_CARDS)
        if teammate_remain <= 5:
            # 队友牌少，选择能送牌的动作
            return self._select_helpful_action(action_list, context)
        
        # 正常出牌
        return self._select_smart_action(action_list, handcards)
    
    def _select_helpful_action(self, action_list: List, context: Dict) -> Optional[int]:
        """选择能帮助队友的动作"""
        # 简化实现：选择对子或三带二（队友容易接）
        for i, action in enumerate(action_list):
            if action[0] == "PASS":
                continue
            if action[0] in ["Pair", "ThreeWithTwo"]:
                return i
        
        return 0
    
    def _select_smart_action(self, action_list: List, handcards: List) -> Optional[int]:
        """智能选择动作"""
        # 优先一手出完
        for i, action in enumerate(action_list):
            if action[0] == "PASS":
                continue
            if len(action) > 2 and len(action[2]) == len(handcards):
                return i
        
        return 0


class ControlStrategy(EndgameStrategy):
    """控制策略：控制节奏"""
    
    def execute(self, message: Dict, context: Dict) -> Optional[int]:
        """执行控制策略（控制节奏）"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return None
        
        # 如果对手牌数少，需要压制
        opponents_remain = context.get("opponent_rest_cards_list", [])
        min_opponent_remain = min(opponents_remain) if opponents_remain else DEFAULT_REST_CARDS
        
        if min_opponent_remain <= 3:
            # 对手快走完，需要压制
            return self._select_suppress_action(action_list, message)
        
        # 否则，控制节奏，选择中等大小的动作
        return self._select_control_action(action_list)
    
    def _select_suppress_action(self, action_list: List, message: Dict) -> Optional[int]:
        """选择压制动作"""
        cur_action = message.get("curAction", [])
        if cur_action:
            # 被动出牌：选择能管住的动作
            cur_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
            for i, action in enumerate(action_list):
                if action[0] == "PASS":
                    continue
                if action[0] == cur_type:
                    return i
        
        # 主动出牌：选择炸弹或大牌
        for i, action in enumerate(action_list):
            if action[0] == "Bomb":
                return i
        
        return 0
    
    def _select_control_action(self, action_list: List) -> Optional[int]:
        """选择控制动作（中等大小）"""
        # 选择对子或三张（中等牌型）
        for i, action in enumerate(action_list):
            if action[0] == "PASS":
                continue
            if action[0] in ["Pair", "Trips"]:
                return i
        
        return 0


class EndgameStrategySelector:
    """残局策略选择器（供残局处理器使用）"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.strategies = {
            'rush': RushStrategy(config),
            'defend': DefendStrategy(config),
            'cooperate': CooperateStrategy(config),
            'control': ControlStrategy(config),
        }
        self.logger = logging.getLogger("EndgameStrategySelector")
    
    def select_strategy(self, message: Dict, context: Dict) -> EndgameStrategy:
        """选择最佳残局策略"""
        endgame_type = self._classify_endgame(message, context)
        strategy = self.strategies.get(endgame_type, self.strategies['rush'])
        self.logger.info(f"Selected endgame strategy: {endgame_type}")
        return strategy
    
    def _classify_endgame(self, message: Dict, context: Dict) -> str:
        """残局分类（提升：多维度分类）"""
        my_remain = context.get("my_remain", DEFAULT_REST_CARDS)
        teammate_remain = context.get("teammate_rest_cards", DEFAULT_REST_CARDS)
        opponents_remain = context.get("opponent_rest_cards_list", [])
        max_opponent_remain = max(opponents_remain) if opponents_remain else DEFAULT_REST_CARDS
        
        # 分类1: 冲刺型（自己牌少，需要快速出完）
        if my_remain <= 3 and max_opponent_remain >= 8:
            return 'rush'
        
        # 分类2: 防守型（队友牌少，需要保护）
        if teammate_remain <= 3 and my_remain <= 5:
            return 'defend'
        
        # 分类3: 配合型（队友牌少，需要配合）
        if teammate_remain <= 5 and my_remain <= 5:
            return 'cooperate'
        
        # 分类4: 控制型（对手牌少，需要控制节奏）
        min_opponent_remain = min(opponents_remain) if opponents_remain else DEFAULT_REST_CARDS
        if my_remain <= 5 and min_opponent_remain <= 5:
            return 'control'
        
        return 'rush'  # 默认

