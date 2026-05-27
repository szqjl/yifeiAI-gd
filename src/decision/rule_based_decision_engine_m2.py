# -*- coding: utf-8 -*-
"""
M2 决策引擎 — 重构版（硬编码精确规则，无分数累积+阈值保护）

与 M1 的核心区别：
1. 使用 M2 阶段处理器（phase_handlers_m2.py），不加载共享 TeammateProtectionStrategy
2. 保护逻辑内联在按牌型分发的处理器中
3. 开局主动恢复一手出完检查
4. PASS 次数降级链完整
5. 队友保护精确边界控制
"""

import logging
from typing import Dict, Optional
from .stage_router import StageRouter
from .phase_handlers_m2 import (
    M2OpeningActiveHandler, M2OpeningPassiveHandler,
    M2MidEarlyActiveHandler, M2MidEarlyPassiveHandler,
    M2MidLateActiveHandler, M2MidLatePassiveHandler,
    M2EndgameEarlyActiveHandler, M2EndgameEarlyPassiveHandler,
    M2EndgameLateActiveHandler, M2EndgameLatePassiveHandler,
    M2TributeHandler, M2BackHandler
)


class RuleBasedDecisionEngineM2:
    """
    M2 决策引擎（主入口）

    特性：
    - 5 阶段细分路由
    - 主动/被动出牌分离
    - 硬编码精确规则（lalala 风格）
    - 无分数累积+阈值保护
    - 完全独立于 V 系列
    """

    def __init__(self, player_id: int = 0, config: Dict = None):
        self.player_id = player_id
        self.config = config or {}
        self.logger = logging.getLogger(f"RuleBasedM2-P{player_id}")

        self.handlers = {
            'opening_active': M2OpeningActiveHandler(self.config),
            'opening_passive': M2OpeningPassiveHandler(self.config),
            'mid_early_active': M2MidEarlyActiveHandler(self.config),
            'mid_early_passive': M2MidEarlyPassiveHandler(self.config),
            'mid_late_active': M2MidLateActiveHandler(self.config),
            'mid_late_passive': M2MidLatePassiveHandler(self.config),
            'endgame_early_active': M2EndgameEarlyActiveHandler(self.config),
            'endgame_early_passive': M2EndgameEarlyPassiveHandler(self.config),
            'endgame_late_active': M2EndgameLateActiveHandler(self.config),
            'endgame_late_passive': M2EndgameLatePassiveHandler(self.config),
        }

        self.tribute_handler = M2TributeHandler(self.config)
        self.back_handler = M2BackHandler(self.config)

        base_router = StageRouter(self.config, disable_pass_coercion=True)
        base_router.set_handlers(self.handlers)
        base_router.set_special_handlers(
            tribute_handler=self.tribute_handler,
            back_handler=self.back_handler
        )

        self.router = base_router

        self.logger.info("RuleBasedDecisionEngineM2 initialized")
        self.logger.info(f"  - Player ID: {player_id}")
        self.logger.info(f"  - Series: M2 (Hardcoded Rules, refactored)")
        self.logger.info(f"  - Protection: inline lalala-style (no score accumulation)")

    def _first_non_pass_index(self, action_list, handcards=None) -> int:
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
                return i
            if not isinstance(action, list) and action != "PASS":
                return i
        return 0

    def decide(self, message: Dict) -> int:
        try:
            action_list = message.get("actionList", [])

            server_hand_cards = message.get("handCards", [])
            if server_hand_cards:
                message['handCards'] = server_hand_cards

            if not action_list:
                self.logger.warning("Empty action list, returning 0")
                return 0

            if len(action_list) == 1:
                return 0

            action_idx = self.router.route(message)

            if action_idx < 0 or action_idx >= len(action_list):
                self.logger.warning(f"Invalid action index {action_idx}, using 0")
                return 0

            selected_action = action_list[action_idx] if action_idx < len(action_list) else None
            handcards = message.get("handCards", [])
            if selected_action and handcards:
                if isinstance(selected_action, list) and len(selected_action) > 0 and selected_action[0] != "PASS":
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
