# -*- coding: utf-8 -*-
"""
IDecisionProvider — M3 决策引擎稳定契约（草案 v0.1）

V-learn / V-nn 客户端应只依赖本接口 + src/m/platform，不直接 import M1 代际实现。
物理文件仍位于 src/decision/；本契约定义行为边界，渐进迁移见 src/m/、src/v/。
"""

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable

DECISION_PROVIDER_CONTRACT_VERSION = "0.1-draft"

# 平台 act 消息（type=act, stage=play 等）；完整字段见 docs/README 与 game_recorder
ActMessage = Dict[str, Any]


@runtime_checkable
class IDecisionProvider(Protocol):
    """掼蛋 AI 决策提供者：输入平台 act 消息，返回 actionList 下标。"""

    player_id: int

    def decide(self, message: ActMessage) -> int:
        """选择 actionList 中的 actIndex（含 PASS=0 的合法下标）。"""
        ...


def is_decision_provider(obj: object) -> bool:
    """运行时检查对象是否满足 IDecisionProvider 行为契约。"""
    if not isinstance(obj, IDecisionProvider):
        return False
    if not callable(getattr(obj, "decide", None)):
        return False
    player_id = getattr(obj, "player_id", None)
    return isinstance(player_id, int)


class DecisionProviderAdapter:
    """将任意带 decide(message)->int 的对象适配为显式契约包装（不修改原引擎）。"""

    def __init__(self, engine: object, player_id: int):
        if not callable(getattr(engine, "decide", None)):
            raise TypeError("engine must implement decide(message) -> int")
        self._engine = engine
        self.player_id = int(player_id)

    def decide(self, message: ActMessage) -> int:
        return int(self._engine.decide(message))
