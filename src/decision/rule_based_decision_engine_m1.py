# -*- coding: utf-8 -*-
"""
基于规则的决策引擎 M1 (Rule-Based Decision Engine M1)
功能：
- 整合StageRouter和所有阶段处理器
- 提供统一的决策接口
- 实现硬编码规则引擎
- M1版本：从新开始，专注硬编码规则优化

版本说明：
- M1: 全新的硬编码规则引擎，基于阶段一架构重构
- M系列：硬编码规则引擎系列（与V系列区分）
- 与V5完全独立，不影响V5版本
"""

import logging
from typing import Dict, Optional
from .stage_router import StageRouter
from .phase_handlers import (
    OpeningActiveHandler, OpeningPassiveHandler,
    MidEarlyActiveHandler, MidEarlyPassiveHandler,
    MidLateActiveHandler, MidLatePassiveHandler,
    EndgameEarlyActiveHandler, EndgameEarlyPassiveHandler,
    EndgameLateActiveHandler, EndgameLatePassiveHandler,
    TributeHandler, BackHandler
)


class RuleBasedDecisionEngineM1:
    """
    基于规则的决策引擎 M1（主入口）
    
    特性：
    - 5阶段细分路由（开局、中局前期、中局后期、残局前期、残局后期）
    - 主动/被动出牌分离
    - 硬编码规则优化
    - 完全独立于V5版本
    - M系列：硬编码规则引擎系列
    - 胜负意识：每副牌目标 = 争头游，己方头游+二游即获胜（由 stage_router 注入 context['game_objective']）
    """
    
    def __init__(self, player_id: int = 0, config: Dict = None):
        """
        初始化M1决策引擎
        
        Args:
            player_id: 玩家ID
            config: 配置字典
        """
        self.player_id = player_id
        self.config = config or {}
        self.logger = logging.getLogger(f"RuleBasedM1-P{player_id}")
        
        # 初始化各阶段处理器
        self.handlers = {
            # 开局阶段（剩余牌数 > 20）
            'opening_active': OpeningActiveHandler(self.config),
            'opening_passive': OpeningPassiveHandler(self.config),
            # 中局前期（剩余牌数 15-20）
            'mid_early_active': MidEarlyActiveHandler(self.config),
            'mid_early_passive': MidEarlyPassiveHandler(self.config),
            # 中局后期（剩余牌数 10-15）
            'mid_late_active': MidLateActiveHandler(self.config),
            'mid_late_passive': MidLatePassiveHandler(self.config),
            # 残局前期（剩余牌数 5-10）
            'endgame_early_active': EndgameEarlyActiveHandler(self.config),
            'endgame_early_passive': EndgameEarlyPassiveHandler(self.config),
            # 残局后期（剩余牌数 ≤ 5）
            'endgame_late_active': EndgameLateActiveHandler(self.config),
            'endgame_late_passive': EndgameLatePassiveHandler(self.config),
        }
        
        # 特殊阶段处理器
        self.tribute_handler = TributeHandler(self.config)
        self.back_handler = BackHandler(self.config)
        
        # 创建阶段路由器并设置处理器
        base_router = StageRouter(self.config)
        base_router.set_handlers(self.handlers)
        base_router.set_special_handlers(
            tribute_handler=self.tribute_handler,
            back_handler=self.back_handler
        )
        
        # 根据配置选择使用基础路由器还是智能路由器
        use_intelligent_router = self.config.get('use_intelligent_router', False)
        if use_intelligent_router:
            try:
                from .intelligent_router import IntelligentStageRouter
                self.router = IntelligentStageRouter(self.config, base_router=base_router)
                self.logger.info("  - Router: Intelligent Router (with cache)")
            except ImportError as e:
                self.logger.warning(f"Failed to import IntelligentStageRouter: {e}, using base router")
                self.router = base_router
        else:
            self.router = base_router
            self.logger.info("  - Router: Base Router")
        
        # 验证策略引擎是否正常初始化
        strategy_engine_status = self._check_strategy_engine_status()
        
        self.logger.info("✓ RuleBasedDecisionEngineM1 initialized")
        self.logger.info(f"  - Player ID: {player_id}")
        self.logger.info(f"  - Phase Handlers: {len(self.handlers)}")
        self.logger.info(f"  - Special Handlers: Tribute, Back")
        self.logger.info(f"  - Series: M (Hardcoded Rules)")
        self.logger.info(f"  - Strategy Engine: {strategy_engine_status}")
    
    def _first_non_pass_index(self, action_list, handcards=None) -> int:
        """
        与 StageRouter 路由层兜底一致：在有多项可选时避免无依据地落到 PASS。
        优先返回首张通过手牌校验的非 PASS；否则返回首个非 PASS 索引。
        """
        if not action_list:
            return 0
        any_handler = next(iter(self.handlers.values()), None)
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0:
                if action[0] == "PASS":
                    continue
            elif action == "PASS":
                continue
            if handcards and any_handler and hasattr(any_handler, "_validate_action_cards"):
                if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                    if any_handler._validate_action_cards(action, handcards):
                        return i
            else:
                return i
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                self.logger.warning(f"Fallback: first non-PASS at index {i} (validation skipped or failed)")
                return i
            if not isinstance(action, list) and action != "PASS":
                return i
        return 0
    
    def _check_strategy_engine_status(self) -> str:
        """检查策略引擎状态"""
        # 检查第一个处理器（作为代表）的策略引擎状态
        first_handler = list(self.handlers.values())[0] if self.handlers else None
        if first_handler:
            has_protection = first_handler.teammate_protection is not None
            has_priority = first_handler.priority_system is not None
            has_card_value = first_handler.card_value_system is not None
            
            if has_protection and has_priority and has_card_value:
                return "✓ All strategies loaded (TeammateProtection, PrioritySystem, CardValueSystem)"
            else:
                missing = []
                if not has_protection:
                    missing.append("TeammateProtection")
                if not has_priority:
                    missing.append("PrioritySystem")
                if not has_card_value:
                    missing.append("CardValueSystem")
                return f"⚠️ Missing: {', '.join(missing)}"
        return "⚠️ No handlers available"
    
    def decide(self, message: Dict) -> int:
        """
        核心决策方法
        
        Args:
            message: 游戏状态消息，包含：
                - stage: 游戏阶段 ("play", "tribute", "back")
                - handCards: 手牌列表
                - actionList: 可选动作列表
                - curAction: 当前动作（被动出牌时）
                - 其他游戏状态信息
        
        Returns:
            决策结果索引（actionList中的索引）
        """
        try:
            action_list = message.get("actionList", [])
            
            # ⚠️ 增强手牌更新机制：优先使用服务器发送的最新handCards
            server_hand_cards = message.get("handCards", [])
            if server_hand_cards:
                # 服务器发送了最新手牌，使用服务器的（更准确）
                message['handCards'] = server_hand_cards
                self.logger.debug(f"Using server handCards: {len(server_hand_cards)} cards")
            else:
                # 如果没有服务器手牌，记录警告
                self.logger.warning("No handCards in message, using cached handCards if available")
            
            # 基本验证
            if not action_list:
                self.logger.warning("Empty action list, returning 0")
                return 0
            
            if len(action_list) == 1:
                return 0
            
            # 路由到对应的阶段处理器
            action_idx = self.router.route(message)
            
            # 验证结果
            if action_idx < 0 or action_idx >= len(action_list):
                self.logger.warning(f"Invalid action index {action_idx}, using 0")
                return 0
            
            # ⚠️ 最终验证：确保选择的动作中的卡牌在手牌中
            selected_action = action_list[action_idx] if action_idx < len(action_list) else None
            handcards = message.get("handCards", [])
            if selected_action and handcards:
                if isinstance(selected_action, list) and len(selected_action) > 0 and selected_action[0] != "PASS":
                    # 简单验证：检查动作中的卡牌是否在手牌中
                    action_cards = []
                    if len(selected_action) >= 3 and isinstance(selected_action[2], list):
                        action_cards = selected_action[2]
                    
                    if action_cards:
                        from collections import Counter
                        handcard_counts = Counter(handcards)
                        action_card_counts = Counter(action_cards)
                        
                        for card, count in action_card_counts.items():
                            if card not in handcard_counts or handcard_counts[card] < count:
                                self.logger.warning(
                                    f"Selected action {action_idx} contains cards not in handcards: {card}, "
                                    f"falling back to first non-PASS instead of PASS"
                                )
                                return self._first_non_pass_index(action_list, handcards)
            
            return action_idx
            
        except Exception as e:
            self.logger.error(f"Decision error: {e}", exc_info=True)
            return 0
    
    def get_phase_info(self, message: Dict) -> Dict:
        """
        获取当前游戏阶段信息（用于调试和分析）
        
        Args:
            message: 游戏状态消息
        
        Returns:
            阶段信息字典
        """
        handcards = message.get("handCards", [])
        my_remain = len(handcards) if handcards else 0
        stage = message.get("stage", "play")
        is_passive = self.router._is_passive_play(message)
        game_phase = self.router._get_game_phase(my_remain)
        
        return {
            "stage": stage,
            "game_phase": game_phase,
            "my_remain": my_remain,
            "is_passive": is_passive,
            "handler_key": f"{game_phase}_{'passive' if is_passive else 'active'}" if stage == "play" else stage
        }

