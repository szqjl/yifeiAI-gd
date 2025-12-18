# -*- coding: utf-8 -*-
"""
阶段处理器 (Phase Handlers)
功能：
- 实现各阶段的专门处理器（开局、中局前期、中局后期、残局前期、残局后期）
- 每个阶段有主动和被动两个处理器
- 每个处理器专注于该阶段的策略优化
"""

from typing import Dict, List, Optional
from .stage_router import BasePhaseHandler


class OpeningActiveHandler(BasePhaseHandler):
    """开局主动出牌处理器（优化：专注于建立牌型结构）"""
    
    def handle(self, message: Dict) -> int:
        """开局策略：专注于建立牌型结构，不考虑快速出完"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return 0
        
        # 开局不需要检查"一手出完"（优化：避免不必要的检查）
        # 开局策略：建立牌型结构
        return self._build_structure_strategy(message, action_list)
    
    def _build_structure_strategy(self, message: Dict, action_list: List) -> int:
        """建立牌型结构策略（开局专用）"""
        # 开局优先级：小单张 → 三连对/钢板 → 顺子 → 三带二 → 三张 → 对子
        priority_order = ['Single', 'ThreePair', 'TwoTrips', 'Straight', 
                         'ThreeWithTwo', 'Trips', 'Pair']
        
        for card_type in priority_order:
            for i, action in enumerate(action_list):
                if action[0] == card_type and action[0] != "PASS":
                    # 开局优先出小牌
                    if card_type == 'Single':
                        # 选择最小的单张
                        return i
                    return i
        
        return 0


class OpeningPassiveHandler(BasePhaseHandler):
    """开局被动出牌处理器"""
    
    def handle(self, message: Dict) -> int:
        """开局被动出牌策略"""
        # TODO: 实现开局被动出牌逻辑
        action_list = message.get("actionList", [])
        if len(action_list) > 1:
            return 1  # 暂时返回第一个非PASS动作
        return 0


class MidEarlyActiveHandler(BasePhaseHandler):
    """中局前期主动出牌处理器（剩余牌数 15-20）"""
    
    def handle(self, message: Dict) -> int:
        """中局前期策略：控制节奏，配合队友，开始考虑出完"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return 0
        
        # 检查两手出完
        two_hand_idx = self._check_two_hand_complete(action_list, handcards)
        if two_hand_idx is not None:
            return two_hand_idx
        
        # 中局前期优先级：对子 → 三张 → 单张 → 其他
        priority_order = ['Pair', 'Trips', 'Single', 'ThreeWithTwo', 
                         'ThreePair', 'TwoTrips', 'Straight']
        
        for card_type in priority_order:
            for i, action in enumerate(action_list):
                if action[0] == card_type and action[0] != "PASS":
                    return i
        
        return 0
    
    def _check_two_hand_complete(self, action_list: List, handcards: List) -> Optional[int]:
        """检查两手出完"""
        # TODO: 实现两手出完检查逻辑
        return None


class MidEarlyPassiveHandler(BasePhaseHandler):
    """中局前期被动出牌处理器"""
    
    def handle(self, message: Dict) -> int:
        """中局前期被动出牌策略"""
        # TODO: 实现中局前期被动出牌逻辑
        action_list = message.get("actionList", [])
        if len(action_list) > 1:
            return 1
        return 0


class MidLateActiveHandler(BasePhaseHandler):
    """中局后期主动出牌处理器（剩余牌数 10-15）"""
    
    def handle(self, message: Dict) -> int:
        """中局后期策略：积极出牌，配合队友，准备冲刺"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return 0
        
        # 检查一手出完
        one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx
        
        # 检查两手出完
        two_hand_idx = self._check_two_hand_complete(action_list, handcards)
        if two_hand_idx is not None:
            return two_hand_idx
        
        # 中局后期优先级：单张 → 对子 → 三张 → 其他
        priority_order = ['Single', 'Pair', 'Trips', 'ThreeWithTwo', 
                         'ThreePair', 'TwoTrips', 'Straight']
        
        for card_type in priority_order:
            for i, action in enumerate(action_list):
                if action[0] == card_type and action[0] != "PASS":
                    return i
        
        return 0
    
    def _check_two_hand_complete(self, action_list: List, handcards: List) -> Optional[int]:
        """检查两手出完"""
        # TODO: 实现两手出完检查逻辑
        return None


class MidLatePassiveHandler(BasePhaseHandler):
    """中局后期被动出牌处理器"""
    
    def handle(self, message: Dict) -> int:
        """中局后期被动出牌策略"""
        # TODO: 实现中局后期被动出牌逻辑
        action_list = message.get("actionList", [])
        if len(action_list) > 1:
            return 1
        return 0


class EndgameEarlyActiveHandler(BasePhaseHandler):
    """残局前期主动出牌处理器（剩余牌数 5-10）"""
    
    def handle(self, message: Dict) -> int:
        """残局前期策略：快速出牌，保护队友，争取先手"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return 0
        
        # 优先级1: 一手出完
        one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx
        
        # 优先级2: 出最大牌型（快速减少牌数）
        return self._select_largest_action(action_list)
    
    def _select_largest_action(self, action_list: List) -> int:
        """选择最大牌型（残局专用）"""
        largest_idx = 0
        largest_size = 0
        
        for i, action in enumerate(action_list):
            if not action or action[0] == "PASS":
                continue
            action_size = len(action[2]) if len(action) > 2 else 1
            if action_size > largest_size:
                largest_size = action_size
                largest_idx = i
        
        return largest_idx


class EndgameEarlyPassiveHandler(BasePhaseHandler):
    """残局前期被动出牌处理器"""
    
    def handle(self, message: Dict) -> int:
        """残局前期被动出牌策略"""
        # TODO: 实现残局前期被动出牌逻辑
        action_list = message.get("actionList", [])
        if len(action_list) > 1:
            return 1
        return 0


class EndgameLateActiveHandler(BasePhaseHandler):
    """残局后期主动出牌处理器（剩余牌数 ≤ 5）"""
    
    def handle(self, message: Dict) -> int:
        """残局后期策略：全力冲刺，一手出完优先，快速结束"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return 0
        
        # 优先级1: 一手出完（残局最重要）
        one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx
        
        # 优先级2: 出最大牌型（快速减少牌数）
        return self._select_largest_action(action_list)
    
    def _select_largest_action(self, action_list: List) -> int:
        """选择最大牌型（残局专用）"""
        largest_idx = 0
        largest_size = 0
        
        for i, action in enumerate(action_list):
            if not action or action[0] == "PASS":
                continue
            action_size = len(action[2]) if len(action) > 2 else 1
            if action_size > largest_size:
                largest_size = action_size
                largest_idx = i
        
        return largest_idx


class EndgameLatePassiveHandler(BasePhaseHandler):
    """残局后期被动出牌处理器"""
    
    def handle(self, message: Dict) -> int:
        """残局后期被动出牌策略"""
        # TODO: 实现残局后期被动出牌逻辑
        action_list = message.get("actionList", [])
        if len(action_list) > 1:
            return 1
        return 0


class TributeHandler(BasePhaseHandler):
    """进贡处理器"""
    
    def handle(self, message: Dict) -> int:
        """进贡决策"""
        # TODO: 实现进贡逻辑
        action_list = message.get("actionList", [])
        if action_list:
            return 0
        return 0


class BackHandler(BasePhaseHandler):
    """还贡处理器"""
    
    def handle(self, message: Dict) -> int:
        """还贡决策"""
        # TODO: 实现还贡逻辑
        action_list = message.get("actionList", [])
        if action_list:
            return 0
        return 0

