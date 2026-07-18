# -*- coding: utf-8 -*-
"""
GUA-057 Phase 0 任务 5：heuristic 信念规则 ⑨ 草案 + 等价性测试

目的：实现方案 v2 §7.2 的 _heuristic_belief_bomb_risk()，
      关键不变量是 belief_vector=None 或全 0 时返回 0.0（降级等价），
      保证 _heuristic_select 接入 belief 后无回归。

接口：
  _heuristic_belief_bomb_risk(action, belief_vector, card_mask, game_state) -> float

测试（tests/test_gua057_belief_bomb_risk.py）：
  1. belief=None（降级路径）→ 0.0
  2. belief 全 0 → 0.0
  3. belief 对手高概率持更大炸弹 → -200
  4. belief 对手高概率持同点炸弹 → -100
  5. 末局 + 高信念炸弹风险 → -300
"""
from __future__ import annotations
from typing import Any, Dict, Optional

import numpy as np


# OPPONENT_HAND 索引 = 2（与方案 §2.2 状态定义一致）
OPPONENT_HAND_IDX = 2

# 平台 13 个 rank（2 最小，A 最大，王炸独立）
_RANK_ORDER = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]


def _rank_to_idx(rank: str) -> int:
    if rank in _RANK_ORDER:
        return _RANK_ORDER.index(rank)
    return -1  # 王炸 / 未知


def _get_bomb_slots_with_rank_gt(rank: str) -> np.ndarray:
    """返回 rank 大于给定 rank 的所有炸弹槽位（按牌型槽位映射）。

    Phase 1 简化版映射（slot_idx % 54 = 牌型槽位）：
      - slot 0-53 = 牌型 1-54（rank 升序 + 花色 + 王）
      - slot 54-107 = 牌型 1-54 副本 2

    对于每个牌型，rank 越大 → 槽位 idx 越大（54 种按 ALL_CARD_TYPES 顺序）。
    Phase 1 简化：所有同 rank 炸弹的 slot 集合 = [rank_idx*4 : rank_idx*4+4] × 2
    """
    rank_idx = _rank_to_idx(rank)
    if rank_idx < 0:
        return np.array([], dtype=np.int64)
    # rank > rank_idx 的所有槽位（前 rank_idx 个 rank 的 4 个花色 × 2 副本）
    higher_slots = []
    for r in range(rank_idx + 1, len(_RANK_ORDER)):
        base = r * 4
        higher_slots.extend([base, base + 1, base + 2, base + 3])
        # 副本 2：base + 54
        higher_slots.extend([base + 54, base + 55, base + 56, base + 57])
    # 王炸 (SB, HR) 总是 > 任何 rank
    sb_idx = 52
    hr_idx = 53
    higher_slots.extend([sb_idx, sb_idx + 54, hr_idx, hr_idx + 54])
    return np.array(higher_slots, dtype=np.int64)


def _get_bomb_slots_with_rank_eq(rank: str) -> np.ndarray:
    """返回 rank 等于给定 rank 的炸弹槽位（同点 4 张）。"""
    rank_idx = _rank_to_idx(rank)
    if rank_idx < 0:
        return np.array([], dtype=np.int64)
    base = rank_idx * 4
    return np.array([
        base, base + 1, base + 2, base + 3,
        base + 54, base + 55, base + 56, base + 57,
    ], dtype=np.int64)


def _heuristic_belief_bomb_risk(
    action: Dict[str, Any],
    belief_vector: Optional[np.ndarray],
    card_mask: Optional[np.ndarray] = None,
    game_state: Optional[Dict[str, Any]] = None,
) -> float:
    """信念驱动炸弹风险规避评分。

    触发条件：
      - belief_vector 非空（NN 已推理）
      - action 是非 PASS 出牌动作

    评分规则：
      1. 动作含 4 张同牌（疑似自己炸弹），检查 belief 中对手持有更大炸弹概率
         → opp_higher_bomb = sum(P(slot in OPPONENT_HAND) for slot in all_bomb_slots with rank > action.rank)
         → 若 > 0.5 扣 200 分（不出炸，避免被压）
      2. 动作出单张/对子（非炸），检查 belief 中对手持有该牌点炸弹概率
         → opp_bomb_same = sum(P(slot in OPPONENT_HAND) for slot in bomb_slots of action.rank)
         → 若 > 0.3 扣 100 分
      3. 末局（hand_size<=5, stage=play）信念权重 ×1.5
    """
    # ========== 降级路径：belief 不可用时与无 belief 完全等价 ==========
    if belief_vector is None:
        return 0.0
    if not isinstance(belief_vector, np.ndarray):
        return 0.0
    if belief_vector.shape != (108, 3):
        return 0.0

    score = 0.0
    opp_hand_prob = belief_vector[:, OPPONENT_HAND_IDX]

    action_cards = action.get("cards", [])
    action_rank = action.get("rank", "0")

    game_state = game_state or {}
    hand_cards = game_state.get("handCards", [])
    hand_size = len(hand_cards) if isinstance(hand_cards, list) else 27
    stage = game_state.get("stage", "play")
    is_endgame = (hand_size <= 5 and stage == "play")
    endgame_mult = 1.5 if is_endgame else 1.0

    # 规则 1: 自己疑似炸出 → 检查对手更大炸弹
    if len(action_cards) == 4:
        higher_bomb_slots = _get_bomb_slots_with_rank_gt(str(action_rank))
        if higher_bomb_slots.size > 0:
            opp_higher_bomb = float(opp_hand_prob[higher_bomb_slots].sum())
            if opp_higher_bomb > 0.5:
                score -= 200.0 * endgame_mult

    # 规则 2: 出小牌（非 4 张同牌）→ 检查对手同点炸弹
    if len(action_cards) != 4:
        bomb_slots_same = _get_bomb_slots_with_rank_eq(str(action_rank))
        if bomb_slots_same.size > 0:
            opp_bomb_same = float(opp_hand_prob[bomb_slots_same].sum())
            if opp_bomb_same > 0.3:
                score -= 100.0 * endgame_mult

    return score
