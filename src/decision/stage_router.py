# -*- coding: utf-8 -*-
"""
阶段路由器 (Stage Router)
功能：
- 根据游戏状态和剩余牌数，路由到对应的阶段处理器
- 实现5阶段细分路由（开局、中局前期、中局后期、残局前期、残局后期）
- 支持主动/被动出牌路由
- 支持特殊阶段处理（进贡/还贡）
"""

from typing import Dict, Optional
from abc import ABC, abstractmethod


class BasePhaseHandler(ABC):
    """阶段处理器基类（优化：统一接口，减少代码重复）"""
    
    def __init__(self, config: Dict):
        self.config = config
    
    @abstractmethod
    def handle(self, message: Dict) -> int:
        """处理出牌（子类实现）"""
        pass
    
    def _check_one_hand_complete(self, action_list: list, handcards: list) -> Optional[int]:
        """检查一手出完（所有阶段都可能需要，但实现可能不同）"""
        for i, action in enumerate(action_list):
            if len(action) > 2 and len(action[2]) == len(handcards):
                return i
        return None


class StageRouter:
    """阶段路由器（优化：阶段细分路由，提升决策质量和速度）"""
    
    def __init__(self, config: Dict):
        self.config = config
        # 初始化各阶段处理器（优化：直接路由到专门处理器）
        self.handlers = {
            # 开局阶段（剩余牌数 > 20）
            'opening_active': None,  # 将在后续实现
            'opening_passive': None,
            # 中局前期（剩余牌数 15-20）
            'mid_early_active': None,
            'mid_early_passive': None,
            # 中局后期（剩余牌数 10-15）
            'mid_late_active': None,
            'mid_late_passive': None,
            # 残局前期（剩余牌数 5-10）
            'endgame_early_active': None,
            'endgame_early_passive': None,
            # 残局后期（剩余牌数 ≤ 5）
            'endgame_late_active': None,
            'endgame_late_passive': None,
        }
        # 特殊阶段处理器
        self.tribute_handler = None  # 将在后续实现
        self.back_handler = None
    
    def set_handlers(self, handlers: Dict[str, BasePhaseHandler]):
        """设置各阶段处理器"""
        self.handlers.update(handlers)
    
    def set_special_handlers(self, tribute_handler=None, back_handler=None):
        """设置特殊阶段处理器"""
        if tribute_handler:
            self.tribute_handler = tribute_handler
        if back_handler:
            self.back_handler = back_handler
    
    def route(self, message: Dict) -> int:
        """路由到对应阶段处理器（优化：直接路由，无额外判断）"""
        stage = message.get("stage", "play")
        handcards = message.get("handCards", [])
        my_remain = len(handcards) if handcards else 0
        
        # 特殊阶段处理（进贡/还贡）
        if stage == "tribute":
            if self.tribute_handler:
                return self.tribute_handler.handle(message)
            return 0
        elif stage == "back":
            if self.back_handler:
                return self.back_handler.handle(message)
            return 0
        
        # 打牌阶段：根据剩余牌数和出牌类型直接路由
        if stage == "play":
            # 判断游戏阶段（优化：在路由层直接判断）
            game_phase = self._get_game_phase(my_remain)
            
            # 判断主动/被动出牌
            is_passive = self._is_passive_play(message)
            
            # 直接路由到专门处理器（优化：一步到位，无额外判断）
            handler_key = f"{game_phase}_{'passive' if is_passive else 'active'}"
            handler = self.handlers.get(handler_key)
            
            if handler:
                return handler.handle(message)
        
        return 0
    
    def _get_game_phase(self, my_remain: int) -> str:
        """获取游戏阶段（优化：细分为5个阶段）"""
        if my_remain > 20:
            return "opening"        # 开局
        elif my_remain > 15:
            return "mid_early"      # 中局前期
        elif my_remain > 10:
            return "mid_late"       # 中局后期
        elif my_remain > 5:
            return "endgame_early"  # 残局前期
        else:
            return "endgame_late"   # 残局后期
    
    def _is_passive_play(self, message: Dict) -> bool:
        """判断是否为被动出牌"""
        cur_action = message.get("curAction")
        return cur_action is not None and len(cur_action) > 0

