# -*- coding: utf-8 -*-
"""
决策引擎 (Decision Engine)
功能：
- 主动/被动出牌决策
- 配合策略集成
- 多因素评估
- 决策时间控制
- 快速决策模式
- 进贡/还贡决策
"""

import random
import sys
from typing import Dict, List, Optional
from pathlib import Path

# 将 src 目录添加到系统路径
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from game_logic.enhanced_state import EnhancedGameStateManager
from game_logic.hand_combiner import HandCombiner
from decision.cooperation import CooperationStrategy
from decision.card_type_handlers import CardTypeHandlerFactory
from decision.multi_factor_evaluator import MultiFactorEvaluator
from decision.decision_timer import DecisionTimer


class DecisionEngine:
    """决策引擎类，负责所有出牌决策"""
    
    def __init__(self, state_manager: EnhancedGameStateManager, max_decision_time: float = 0.8):
        self.state = state_manager
        self.combiner = HandCombiner()
        self.cooperation = CooperationStrategy(state_manager)
        self.evaluator = MultiFactorEvaluator(state_manager, self.combiner, self.cooperation)
        self.timer = DecisionTimer(max_decision_time)
    
    def decide(self, message: Dict) -> int:
        """
        核心决策方法
        
        Args:
            message: 游戏状态消息
        
        Returns:
            决策结果索引
        """
        # 开始计时
        self.timer.start()
        
        action_list = message.get("actionList", [])
        if not action_list:
            return 0
        
        # 只有一个动作（通常是PASS或必出），直接返回
        if len(action_list) == 1:
            return 0
        
        # 获取当前阶段
        stage = message.get("stage", "play")
        
        try:
            if stage == "play":
                if self.state.is_passive_play():
                    # 被动出牌（管牌）
                    return self.passive_decision(message, action_list)
                else:
                    # 主动出牌
                    return self.active_decision(message, action_list)
            elif stage == "tribute":
                return self.tribute_decision(message, action_list)
            elif stage == "back":
                return self.back_decision(message, action_list)
            else:
                # 其他阶段，随机选择
                index_range = message.get("indexRange", len(action_list) - 1)
                return random.randint(0, index_range)
        finally:
            # 检查决策时间
            elapsed = self.timer.get_elapsed_time()
            if elapsed > self.timer.max_time * 0.8:
                print(f"Warning: Decision took {elapsed:.3f}s (Max {self.timer.max_time}s)")
    
    def active_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        主动出牌决策
        
        Args:
            message: 游戏消息
            action_list: 可选动作列表
        
        Returns:
            决策结果索引
        """
        handcards = message.get("handCards", [])
        rank = message.get("curRank", "2")
        
        # 多因素评估所有动作
        evaluations = self.evaluator.evaluate_all_actions(action_list, None)
        
        # 如果超时，返回评估分最高的动作
        if self.timer.check_timeout():
            if evaluations:
                return evaluations[0][0]
            return 0
        
        # 选择非PASS的最佳动作
        for idx, score in evaluations:
            action = action_list[idx]
            if action[0] != "PASS":
                # 再次检查超时
                if self.timer.check_timeout():
                    return idx
                return idx
        
        return 0
    
    def passive_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        被动出牌决策（管牌）
        
        Args:
            message: 游戏消息
            action_list: 可选动作列表
        
        Returns:
            决策结果索引
        """
        cur_action = message.get("curAction")
        greater_action = message.get("greaterAction")
        handcards = message.get("handCards", [])
        rank = message.get("curRank", "2")
        
        target_action = greater_action if greater_action else cur_action
        
        # 1. 配合策略评估
        cooperation_result = self.cooperation.get_cooperation_strategy(
            action_list, cur_action, greater_action
        )
        
        # 2. 如果建议PASS，则PASS
        if cooperation_result.get("should_pass"):
            return 0
        
        # 3. 如果建议接管，选择最佳动作
        if cooperation_result.get("should_take_over"):
            best_index = cooperation_result.get("best_action_index")
            if best_index is not None:
                return best_index
        
        # 4. 使用特定牌型处理器
        if target_action and target_action[0] != "PASS":
            card_type = target_action[0]
            handler = CardTypeHandlerFactory.get_handler(
                card_type, self.state, self.combiner
            )
            
            if handler:
                # 如果超时
                if self.timer.check_timeout():
                    # 快速决策
                    return self._quick_decision(action_list, target_action)
                
                result = handler.handle_passive(
                    action_list, target_action, handcards, rank
                )
                
                if result != -1:
                    return result
        
        # 5. 多因素评估
        if not self.timer.check_timeout():
            evaluations = self.evaluator.evaluate_all_actions(action_list, target_action)
            for idx, score in evaluations:
                if action_list[idx][0] != "PASS":
                    return idx
        
        # 6. 默认PASS
        return 0
    
    def _quick_decision(self, action_list: List[List], target_action: List) -> int:
        """
        快速决策（超时保护）
        
        Args:
            action_list: 可选动作列表
            target_action: 目标动作
        
        Returns:
            决策结果索引
        """
        if not target_action or target_action[0] == "PASS":
            # 主动出牌，选择第一个非PASS动作
            for i, action in enumerate(action_list[1:], 1):
                if action[0] != "PASS":
                    return i
            return 0
        
        # 被动出牌，选择比目标大的最小动作
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
            message: 游戏消息
            action_list: 可选动作列表
        
        Returns:
            决策结果索引
        """
        # 获取当前级牌（红桃）
        cur_rank = message.get("curRank", "2")
        rank_card = f"H{cur_rank}"  # 红桃级牌
        
        # 如果有进贡动作
        if len(action_list) > 0:
            first_action = action_list[0]
            if isinstance(first_action, list) and len(first_action) > 2:
                if rank_card in first_action[2]:
                    # 如果包含级牌，优先保留
                    if len(action_list) > 1:
                        return 1
        
        return 0
    
    def back_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        还贡决策
        
        Args:
            message: 游戏消息
            action_list: 可选动作列表
        
        Returns:
            决策结果索引
        """
        # 默认选择第一个动作
        
        # TODO: 实现更智能的还贡策略
        return 0

