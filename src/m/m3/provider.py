# -*- coding: utf-8 -*-
"""M3 决策引擎的 IDecisionProvider 适配（底层仍为 on_message）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from contracts import ActMessage
from decision.m3_decision_engine import M3DecisionEngine

if TYPE_CHECKING:
    pass


class M3DecisionProvider:
    """将 M3DecisionEngine.on_message 适配为 contracts.decide 契约。"""

    def __init__(self, player_id: int):
        self.player_id = int(player_id)
        self._engine = M3DecisionEngine(self.player_id)

    def decide(self, message: ActMessage) -> int:
        result = self._engine.on_message(message)
        return int(result) if result is not None else 0
