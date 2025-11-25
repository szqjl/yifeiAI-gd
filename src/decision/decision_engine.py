# -*- coding: utf-8 -*-
"""
决策引擎模块 (Decision Engine)
功能：
- 主动/被动决策分离
- 调用配合策略
- 综合评估和决策
- 集成牌型专门处理
- 集成多因素评估
- 集成时间控制
"""

import random
from typing import Dict, List, Optional
from ..game_logic.enhanced_state import EnhancedGameStateManager
from ..game_logic.hand_combiner import HandCombiner
from .cooperation import CooperationStrategy
from .card_type_handlers import CardTypeHandlerFactory
from .multi_factor_evaluator import MultiFactorEvaluator
from .decision_timer import DecisionTimer


class DecisionEngine:
    """决策引擎（主动/被动分离）"""
    
    def __init__(self, state_manager: EnhancedGameStateManager, max_decision_time: float = 0.8):
        self.state = state_manager
        self.combiner = HandCombiner()
        self.cooperation = CooperationStrategy(state_manager)
        self.evaluator = MultiFactorEvaluator(state_manager, self.combiner, self.cooperation)
        self.timer = DecisionTimer(max_decision_time)
    
    def decide(self, message: Dict) -> int:
        """
        主决策函数（带时间控制）
        
        Args:
            message: 平台发送的act消息
        
        Returns:
            选择的动作索引
        """
        # 开始计时
        self.timer.start()
        
        action_list = message.get("actionList", [])
        if not action_list:
            return 0
        
        # 如果只有一个动作，直接返回
        if len(action_list) == 1:
            return 0
        
        # 根据游戏阶段选择决策方式
        stage = message.get("stage", "play")
        
        try:
            if stage == "play":
                if self.state.is_passive_play():
                    # 被动出牌（需要压制）
                    return self.passive_decision(message, action_list)
                else:
                    # 主动出牌（率先出牌或接风）
                    return self.active_decision(message, action_list)
            elif stage == "tribute":
                return self.tribute_decision(message, action_list)
            elif stage == "back":
                return self.back_decision(message, action_list)
            else:
                # 其他情况随机选择
                index_range = message.get("indexRange", len(action_list) - 1)
                return random.randint(0, index_range)
        finally:
            # 记录决策时间
            elapsed = self.timer.get_elapsed_time()
            if elapsed > self.timer.max_time * 0.8:
                print(f"Warning: Decision took {elapsed:.3f}s (接近超时 {self.timer.max_time}s)")
    
    def active_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        主动出牌决策（率先出牌或接风）
        
        Args:
            message: 平台消息
            action_list: 可选动作列表
        
        Returns:
            选择的动作索引
        """
        handcards = message.get("handCards", [])
        rank = message.get("curRank", "2")
        
        # 使用多因素评估系统
        evaluations = self.evaluator.evaluate_all_actions(action_list, None)
        
        # 检查时间，如果时间不够，直接返回最佳动作
        if self.timer.check_timeout():
            if evaluations:
                return evaluations[0][0]
            return 0
        
        # 优先选择评分高的动作
        for idx, score in evaluations:
            action = action_list[idx]
            if action[0] != "PASS":
                # 检查时间
                if self.timer.check_timeout():
                    return idx
                return idx
        
        return 0
    
    def passive_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        被动出牌决策（需要压制）
        
        Args:
            message: 平台消息
            action_list: 可选动作列表
        
        Returns:
            选择的动作索引
        """
        cur_action = message.get("curAction")
        greater_action = message.get("greaterAction")
        handcards = message.get("handCards", [])
        rank = message.get("curRank", "2")
        
        target_action = greater_action if greater_action else cur_action
        
        # 1. 评估配合机会
        cooperation_result = self.cooperation.get_cooperation_strategy(
            action_list, cur_action, greater_action
        )
        
        # 2. 如果应该配合队友，返回PASS
        if cooperation_result.get("should_pass"):
            return 0
        
        # 3. 如果需要接替队友，选择最佳动作
        if cooperation_result.get("should_take_over"):
            best_index = cooperation_result.get("best_action_index")
            if best_index is not None:
                return best_index
        
        # 4. 使用牌型专门处理器
        if target_action and target_action[0] != "PASS":
            card_type = target_action[0]
            handler = CardTypeHandlerFactory.get_handler(
                card_type, self.state, self.combiner
            )
            
            if handler:
                # 检查时间
                if self.timer.check_timeout():
                    # 超时，使用快速决策
                    return self._quick_decision(action_list, target_action)
                
                result = handler.handle_passive(
                    action_list, target_action, handcards, rank
                )
                
                if result != -1:
                    return result
        
        # 5. 使用多因素评估系统作为备选
        if not self.timer.check_timeout():
            evaluations = self.evaluator.evaluate_all_actions(action_list, target_action)
            for idx, score in evaluations:
                if action_list[idx][0] != "PASS":
                    return idx
        
        # 6. 如果无法压制或超时，返回PASS
        return 0
    
    def _quick_decision(self, action_list: List[List], target_action: List) -> int:
        """
        快速决策（超时时的备选方案）
        
        Args:
            action_list: 可选动作列表
            target_action: 目标动作
        
        Returns:
            动作索引
        """
        if not target_action or target_action[0] == "PASS":
            # 主动出牌，选择第一个非PASS动作
            for i, action in enumerate(action_list[1:], 1):
                if action[0] != "PASS":
                    return i
            return 0
        
        # 被动出牌，快速寻找可以压制的动作
        target_value = self.cooperation._calculate_action_value(target_action)
        for i, action in enumerate(action_list[1:], 1):
            if action[0] == "PASS":
                continue
            action_value = self.cooperation._calculate_action_value(action)
            if action_value > target_value:
                return i
        
        return 0
    
    def tribute_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        进贡决策
        
        Args:
            message: 平台消息
            action_list: 可选动作列表
        
        Returns:
            选择的动作索引
        """
        # 策略：避免进贡主牌
        cur_rank = message.get("curRank", "2")
        rank_card = f"H{cur_rank}"  # 主牌通常是红桃
        
        # 检查第一个动作是否包含主牌
        if len(action_list) > 0:
            first_action = action_list[0]
            if isinstance(first_action, list) and len(first_action) > 2:
                if rank_card in first_action[2]:
                    # 如果有第二个动作，选择第二个
                    if len(action_list) > 1:
                        return 1
        
        return 0
    
    def back_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        还贡决策
        
        Args:
            message: 平台消息
            action_list: 可选动作列表
        
        Returns:
            选择的动作索引
        """
        # 策略：还贡小牌
        # TODO: 实现更智能的还贡策略
        
        # 临时实现：选择第一个动作
        return 0

