# -*- coding: utf-8 -*-
"""GUA-116：主攻领出 P1 / P4 / defer 构造态。"""

import logging

from src.v.nn.stage_main_attack_lead import recommend_main_attack_lead
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_engine(*, card_mask=None, group_type_map=None, group_members=None):
    eng = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    eng.logger = logging.getLogger("test_gua116")
    eng.player_id = 0
    eng._card_mask = card_mask or {}
    eng._group_type_map = group_type_map or {}
    eng._group_members = group_members or {}
    eng.INTERNAL_TO_PLATFORM_RANK = UltimateWinRateEngineV7.INTERNAL_TO_PLATFORM_RANK
    eng.RANK_ORDER = UltimateWinRateEngineV7.RANK_ORDER
    return eng


def test_p1_second_smallest_with_two_low_singles():
    card_mask = {
        "S3": (-1, 0.0, 0),
        "C5": (-1, 0.0, 0),
        "H7": (-1, 0.0, 0),
    }
    engine = _make_engine(card_mask=card_mask)
    rec = recommend_main_attack_lead(
        engine, {"_current_stage": "stage_1"}, card_mask, list(card_mask), "2", "stage_1",
    )
    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["rank"] == "5"
    assert rec["intent"] == "main_p1_second_single"


def test_p1_joker_triggers_second_smallest():
    card_mask = {"SB": (-1, 0.0, 0), "S4": (-1, 0.0, 0), "C6": (-1, 0.0, 0)}
    engine = _make_engine(card_mask=card_mask)
    rec = recommend_main_attack_lead(
        engine, {}, card_mask, list(card_mask), "2", "stage_1",
    )
    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["rank"] == "6"


def test_p4_small_pair_when_no_p1():
    card_mask = {
        "S9": (0, 0.0, 2),
        "H9": (0, 0.0, 2),
        "SK": (1, 0.0, 2),
        "HK": (1, 0.0, 2),
    }
    engine = _make_engine(card_mask=card_mask, group_type_map={0: "pair", 1: "pair"})
    rec = recommend_main_attack_lead(
        engine, {}, card_mask, list(card_mask), "2", "stage_1",
    )
    assert rec is not None
    assert rec["type"] == "Pair"
    assert rec["rank"] == "9"
    assert rec["intent"] == "main_p4_small_pair"


def test_l11_defer_single_twt_in_stage_1():
    """仅 1 手 TWT + stage_1 → 不 P2，落 P4 小对。"""
    card_mask = {
        "S3": (0, 0.0, 2),
        "H3": (0, 0.0, 2),
        "S6": (1, 1.0, 3),
        "H6": (1, 1.0, 3),
        "C6": (1, 1.0, 3),
        "S4": (2, 1.0, 2),
        "H4": (2, 1.0, 2),
    }
    group_type_map = {
        0: "pair",
        1: "trip_in_three_with_two",
        2: "pair_in_three_with_two",
    }
    group_members = {
        0: ["S3", "H3"],
        1: ["S6", "H6", "C6"],
        2: ["S4", "H4"],
    }
    engine = _make_engine(
        card_mask=card_mask,
        group_type_map=group_type_map,
        group_members=group_members,
    )
    rec = recommend_main_attack_lead(
        engine, {}, card_mask, list(card_mask), "2", "stage_1",
    )
    assert rec is not None
    assert rec["type"] == "Pair"
    assert rec["rank"] == "3"


def test_wf12_orphan_falls_p4_not_bare_high_single():
    """WF-12 锚点简化：orphan J + 小对 → P4 小对非裸 J。"""
    card_mask = {
        "HJ": (-1, 0.0, 0),
        "S4": (0, 0.0, 2),
        "H4": (0, 0.0, 2),
    }
    engine = _make_engine(card_mask=card_mask, group_type_map={0: "pair"})
    rec = recommend_main_attack_lead(
        engine, {}, card_mask, list(card_mask), "2", "stage_2",
    )
    assert rec is not None
    assert rec["type"] == "Pair"
    assert rec["rank"] == "4"
