# -*- coding: utf-8 -*-
"""GUA-251 验证：枚举新增 NO_SF_DOUBLE_BOMB 候选（无 SF 双炸流）。"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.features.grouping_engine import (
    _enumerate_plans, _enumerate_plans_cached, enumerate_groupings,
    _count_all_cards_in_plan,
)

# match 6a865b7d0fbd680d7c7c028b（curRank=2）：27 张，TTT+QQQ+双 H2 配子
HAND_27 = [
    "C3", "CT", "D2", "D3", "D5", "D6", "D9", "DA", "DQ",
    "H2", "H2", "H8", "HA", "HQ", "HR",
    "S4", "S4", "S5", "S6", "S8", "S9", "SB", "SK", "SK", "SQ", "ST", "ST",
]


def test_gua251_no_sf_double_bomb_candidate_generated():
    """双配子手牌应生成 NO_SF_DOUBLE_BOMB 双炸候选。"""
    plans = _enumerate_plans(HAND_27, "2")
    no_sf = [p for p in plans if p.strategy == "NO_SF_DOUBLE_BOMB"]
    assert len(no_sf) == 1, f"应恰好生成 1 个 NO_SF_DOUBLE_BOMB，实际 {len(no_sf)}"
    p = no_sf[0]
    assert len(p.bombs) >= 2, f"NO_SF_DOUBLE_BOMB 应含双炸，实际 bombs={p.bombs}"
    assert not p.straight_flushes, "NO_SF_DOUBLE_BOMB 不应含同花顺"
    assert _count_all_cards_in_plan(p) == len(HAND_27)


def test_gua251_no_sf_double_bomb_beats_sf_plans():
    """本手牌 NO_SF_DOUBLE_BOMB 应为最优方案（多炸加分显现）。"""
    best, plans = enumerate_groupings(HAND_27, "2")
    assert best.strategy == "NO_SF_DOUBLE_BOMB", \
        f"最优方案应 NO_SF_DOUBLE_BOMB，实际 {best.strategy}"
    assert best.power_score >= 8, f"NO_SF 双炸方案 power 应 ≥8，实际 {best.power_score}"
    # 双炸 = TTTT + QQQQ（各用 1 个 H2 配子）
    assert len(best.bombs) == 2
    # 每炸 4 张（3 张真牌 + 1 配子）
    for b in best.bombs:
        assert len(b) == 4, f"炸弹应 4 张: {b}"


def test_gua251_no_sf_double_bomb_completeness():
    """方案完整性：覆盖全部 27 张手牌。"""
    plans = _enumerate_plans_cached(tuple(HAND_27), "2")
    for p in plans:
        if p.strategy == "NO_SF_DOUBLE_BOMB":
            assert _count_all_cards_in_plan(p) == len(HAND_27)


def test_gua251_single_wild_hand_keeps_sf():
    """单配子 + 真 4 头炸手牌：SF 方案仍可能最优，NO_SF 候选合法存在。"""
    # 真炸弹 TTTT + 单 H2 配子 + SF 材料（梅花 3-7）
    hand = [
        "CT", "DT", "HT", "ST",          # TTTT 真炸
        "H2",                             # 1 配子
        "C3", "C4", "C5", "C6", "C7",    # 梅花顺
        "SJ", "DJ", "HJ", "SJ",          # 零散
    ]
    plans = _enumerate_plans(hand, "2")
    no_sf = [p for p in plans if p.strategy == "NO_SF_DOUBLE_BOMB"]
    assert len(no_sf) <= 1, "NO_SF_DOUBLE_BOMB 至多 1 个"