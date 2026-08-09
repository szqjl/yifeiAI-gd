# -*- coding: utf-8 -*-
"""
GUA-223 / CardCountingNetwork-训练方案 §8 Phase 0 ⑤
stage_onehot(7) + tribute_transfer_events 输入编码器

> 真源：docs/guandan-brain/CardCountingNetwork-训练方案.md §2.1 评审发现 + §8 Phase 0 ⑤
> 关联：GUA-223 / GUA-057 / 训练方案 §2.1

`stage_onehot`（7 维）：
  0: beginning（发牌阶段）
  1: tribute（进贡阶段）
  2: anti-tribute（抗贡阶段）
  3: back（还贡阶段）
  4: play（出牌阶段 · 训练数据主流）
  5: episodeOver（一副结束）
  6: gameOver（整局结束）

`tribute_transfer_events`（变长 → 定长 padding）：
  每事件 dict：
    - type: "tribute" | "back" | "anti-tribute" | "double_tribute"
    - from_seat: int (0..3)
    - to_seat: int (0..3)
    - card: V8 字符串（如 'D2', 'H2'）
  默认 padding 长度 = 5（max 5 个事件）；不够补零事件。

不动档：本模块只新增文件 + 提供编码接口，不修改任何已有模块。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import numpy as np


# === 常量 ===

STAGE_NAMES = [
    "beginning",     # 0
    "tribute",       # 1
    "anti-tribute",  # 2
    "back",          # 3
    "play",          # 4
    "episodeOver",   # 5
    "gameOver",      # 6
]
STAGE_DIM = len(STAGE_NAMES)  # 7

TRIBUTE_EVENT_TYPES = ["tribute", "back", "anti-tribute", "double_tribute", "none"]
TRIBUTE_EVENT_DIM = 6  # type(5) + from_seat(1-4 = 4 席 0-3 + invalid) + to_seat(0-3 + invalid) + card(54 slots)
# 实际更简单：每事件 = type_onehot(5) + from_onehot(4) + to_onehot(4) + card_slot(54) = 67 维
TRIBUTE_EVENT_VEC_DIM = 5 + 4 + 4 + 54  # = 67

TRIBUTE_MAX_EVENTS = 5
TRIBUTE_VEC_DIM = TRIBUTE_MAX_EVENTS * TRIBUTE_EVENT_VEC_DIM  # = 335


# === 工具：slot ↔ V8 字符串 ===

_SLOT_TO_V8: Dict[int, str] = {}
_V8_TO_SLOT: Dict[str, int] = {}

BZ_RANK_STR = "A23456789TJQK"
BZ_SUIT_MAP = {0: "H", 1: "D", 2: "S", 3: "C"}


def _build_slot_maps() -> None:
    for value in range(13):
        for suit_idx in range(4):
            v8 = f"{BZ_SUIT_MAP[suit_idx]}{BZ_RANK_STR[value]}"
            slot = value * 4 + suit_idx
            _SLOT_TO_V8[slot] = v8
            _V8_TO_SLOT[v8] = slot
    _SLOT_TO_V8[52] = "SB"
    _SLOT_TO_V8[53] = "HR"
    _V8_TO_SLOT["SB"] = 52
    _V8_TO_SLOT["HR"] = 53


_build_slot_maps()


def v8_to_slot(v8: str) -> int:
    return _V8_TO_SLOT[v8]


def slot_to_v8(slot: int) -> str:
    return _SLOT_TO_V8[slot]


# === stage_onehot ===

def stage_to_onehot(stage: str) -> np.ndarray:
    """stage 字符串 → 7 维 one-hot 向量。"""
    vec = np.zeros(STAGE_DIM, dtype=np.float32)
    if stage in STAGE_NAMES:
        vec[STAGE_NAMES.index(stage)] = 1.0
    else:
        # 未知 stage：one-hot 全 0（不归一化，让模型学习）
        pass
    return vec


def stages_to_onehots(stages: List[str]) -> np.ndarray:
    """多步 stage 列表 → (N, 7) one-hot 矩阵。"""
    return np.stack([stage_to_onehot(s) for s in stages], axis=0)


# === tribute_transfer_events ===

def _empty_event() -> np.ndarray:
    """返回 1 个 67 维零事件向量。"""
    return np.zeros(TRIBUTE_EVENT_VEC_DIM, dtype=np.float32)


def tribute_event_to_vec(event: Dict[str, Any]) -> np.ndarray:
    """单个 tribute event dict → 67 维向量。

    event 必须含 type / from_seat / to_seat / card；缺字段用 0 填充。
    """
    vec = np.zeros(TRIBUTE_EVENT_VEC_DIM, dtype=np.float32)
    # type onehot (0-4)
    et = event.get("type", "none")
    if et in TRIBUTE_EVENT_TYPES:
        vec[TRIBUTE_EVENT_TYPES.index(et)] = 1.0
    # from_seat onehot (5-8)
    fs = event.get("from_seat", -1)
    if isinstance(fs, int) and 0 <= fs < 4:
        vec[5 + fs] = 1.0
    # to_seat onehot (9-12)
    ts = event.get("to_seat", -1)
    if isinstance(ts, int) and 0 <= ts < 4:
        vec[9 + ts] = 1.0
    # card slot onehot (13-66, 54 维)
    card = event.get("card")
    if isinstance(card, str) and card in _V8_TO_SLOT:
        vec[13 + v8_to_slot(card)] = 1.0
    return vec


def tribute_events_to_vec(events: List[Dict[str, Any]]) -> np.ndarray:
    """变长 event 列表 → 定长 (5*67,) 向量，不够补 0。"""
    vec = np.zeros(TRIBUTE_VEC_DIM, dtype=np.float32)
    for i, ev in enumerate(events[:TRIBUTE_MAX_EVENTS]):
        vec[i * TRIBUTE_EVENT_VEC_DIM: (i + 1) * TRIBUTE_EVENT_VEC_DIM] = tribute_event_to_vec(ev)
    return vec


# === Botzone 适配：从 global_state 推断 stage_onehot + tribute_events ===

def infer_stage_from_global(global_state: Dict[str, Any]) -> str:
    """从 Botzone global_state 推断当前 stage。

    global_state keys:
      - "tribute": 0/1（是否进贡阶段）
      - "resist": true/false（是否抗贡）
      - "return_cards": dict（还贡事件）
      - "tribute_cards": dict（进贡事件）
      - "first" / "last": 本副首出/末出玩家

    简化推断：Botzone 在线 API 实际 stage 由请求的 `stage` 字段给出，本函数
    是 fallback 推断。优先使用 ETL 已抽取的 stage 字段。
    """
    if not global_state:
        return "beginning"
    tribute = global_state.get("tribute", 0)
    resist = global_state.get("resist", False)
    return_cards = global_state.get("return_cards", {})
    tribute_cards = global_state.get("tribute_cards", {})
    if tribute and resist:
        return "anti-tribute"
    if tribute:
        return "tribute"
    if return_cards:
        return "back"
    if not tribute and not return_cards:
        return "play"
    return "play"


def build_input_features(
    stage: Optional[str],
    global_state: Optional[Dict[str, Any]],
    tribute_events: Optional[List[Dict[str, Any]]] = None,
) -> np.ndarray:
    """拼装 stage_onehot(7) + tribute_events_vec(335) = 342 维输入。"""
    stage_name = stage if stage else infer_stage_from_global(global_state or {})
    stage_vec = stage_to_onehot(stage_name)
    tribute_vec = tribute_events_to_vec(tribute_events or [])
    return np.concatenate([stage_vec, tribute_vec])