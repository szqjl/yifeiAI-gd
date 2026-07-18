# -*- coding: utf-8 -*-
"""
GUA-NEW 实战级记忆模块 v2

在 MemoryTracker（确定性追踪 + 排除法）基础上，叠加牌型推断 + 角色意图推断，
目标：从"知道每张牌归谁"升级到"知道对手/队友手里有什么牌型 + 在组什么"。

能力分层：
  L1 牌张追踪（MemoryTracker 已有）：谁出过什么、还剩多少
  L2 牌型推断（本模块新增）：对手/队友可能持有的炸弹/顺子/三带二/对子/单张
  L3 角色意图推断（本模块新增）：主攻/助攻/超弱；冲刺窗口；送牌窗口
  L4 决策反馈（本模块可选）：根据 L2/L3 推断压/送/防

设计原则：
  - 不修改 MemoryTracker 既有 API，纯叠加
  - 不接 heuristic_select（保持 review 状态，后续按需接入）
  - 推断结果以 (pattern, probability) 元组返回，调用方按需使用
"""
from .memory_v2 import MemoryV2
from .bomb_inference import BombInference, BombCandidate
from .role_intent import RoleInferencer, RoleEstimate, SprintWindow

__all__ = [
    "MemoryV2",
    "BombInference",
    "BombCandidate",
    "RoleInferencer",
    "RoleEstimate",
    "SprintWindow",
]

from .adapter import MemoryV2Adapter
