# -*- coding: utf-8 -*-
"""GUA-117：stage_1 助攻领出 S1-1 / S1-2 / S1-2b 构造态。"""

import logging

from src.v.nn.stage_assist_feed import _feed_stage1_fallback, _feed_stage1_open
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_engine(*, card_mask=None, group_type_map=None, group_members=None):
    eng = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    eng.logger = logging.getLogger("test_gua117_stage1")
    eng.player_id = 0
    eng._card_mask = card_mask or {}
    eng._group_type_map = group_type_map or {}
    eng._group_members = group_members or {}
    eng.INTERNAL_TO_PLATFORM_RANK = UltimateWinRateEngineV7.INTERNAL_TO_PLATFORM_RANK
    eng.RANK_ORDER = UltimateWinRateEngineV7.RANK_ORDER
    return eng


def test_s1_1_prefers_below_ten_pair_includes_nines():
    """S1-1：10 点以下最小对（含 99，不含 TT）。"""
    card_mask = {
        "S9": (0, 0.0, 2),
        "H9": (0, 0.0, 2),
        "ST": (1, 0.0, 2),
        "HT": (1, 0.0, 2),
    }
    engine = _make_engine(card_mask=card_mask, group_type_map={0: "pair", 1: "pair"})
    rec = _feed_stage1_open(engine, {}, card_mask, ["S9", "H9", "ST", "HT"], "2")
    assert rec is not None
    assert rec["type"] == "Pair"
    assert rec["rank"] == "9"
    assert rec["intent"] == "assist_feed_s1_small_pair"


def test_s1_1_skips_level_rank_pair_when_cur_rank_in_range():
    """S1-1：curRank=5 时 55 为级牌对，应选更小非级牌对 33。"""
    card_mask = {
        "S3": (0, 0.0, 2),
        "H3": (0, 0.0, 2),
        "S5": (1, 0.0, 2),
        "H5": (1, 0.0, 2),
    }
    engine = _make_engine(card_mask=card_mask, group_type_map={0: "pair", 1: "pair"})
    rec = _feed_stage1_open(engine, {}, card_mask, ["S3", "H3", "S5", "H5"], "5")
    assert rec is not None
    assert rec["type"] == "Pair"
    assert rec["rank"] == "3"


def test_s1_2b_skips_level_single_when_cur_rank_is_two():
    """S1-2b：无 6–10 散单时出第二小散单（单 2 + 单 5 → 出 5）。"""
    card_mask = {
        "S2": (-1, 0.0, 0),
        "C5": (-1, 0.0, 0),
    }
    engine = _make_engine(card_mask=card_mask)
    rec = _feed_stage1_open(engine, {}, card_mask, ["S2", "C5"], "2")
    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["rank"] == "5"
    assert rec["intent"] == "assist_feed_s1_second_single"


def test_s1_2b_second_bigger_than_q_plays_first_smallest():
    """S1-2b：第二小 > Q 时出第一小（守大不破）。"""
    card_mask = {
        "S5": (-1, 0.0, 0),
        "HA": (-1, 0.0, 0),
    }
    engine = _make_engine(card_mask=card_mask)
    rec = _feed_stage1_open(engine, {}, card_mask, ["S5", "HA"], "2")
    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["rank"] == "5"
    assert rec["intent"] == "assist_feed_s1_second_single"


def test_s1_2b_enemy_one_left_keeps_second_smallest():
    """对方剩 1 张时保持原逻辑（仍出第二小）。"""
    card_mask = {
        "S5": (-1, 0.0, 0),
        "HA": (-1, 0.0, 0),
    }
    engine = _make_engine(card_mask=card_mask)
    gs = {"numofplayers": [3, 1, 9, 8]}
    rec = _feed_stage1_open(engine, gs, card_mask, ["S5", "HA"], "2")
    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["rank"] == "A"
    assert rec["intent"] == "assist_feed_s1_second_single"


def test_s1_2_prefers_mid_single_over_second_smallest():
    """S1-2 主路径：有 6–10 中单时仍出最小中单，不走第二小。"""
    card_mask = {
        "S2": (-1, 0.0, 0),
        "C5": (-1, 0.0, 0),
        "H7": (-1, 0.0, 0),
    }
    engine = _make_engine(card_mask=card_mask)
    rec = _feed_stage1_open(engine, {}, card_mask, ["S2", "C5", "H7"], "2")
    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["rank"] == "7"
    assert rec["intent"] == "assist_feed_s1_mid_single"


def test_s1_fallback_prefers_pair_over_straight():
    """S1-×：无 S1 路径时从 actionList fallback，禁顺子，选对子。"""
    action_list = [
        ["PASS"],
        ["Straight", "6", ["S3", "H4", "D5", "C6", "S7"]],
        ["Pair", "T", ["ST", "HT"]],
    ]
    rec = _feed_stage1_fallback(action_list, "2")
    assert rec is not None
    assert rec["type"] == "Pair"
    assert rec["rank"] == "T"
    assert rec["intent"] == "assist_feed_s1_fallback"


def test_recommend_stage1_uses_fallback_when_open_empty():
    """stage_1：组牌无散单时仍从 actionList 领出（非 None 回退）。"""
    card_mask = {
        "S3": (0, 0.0, 5),
        "H4": (0, 0.0, 5),
        "D5": (0, 0.0, 5),
        "C6": (0, 0.0, 5),
        "S7": (0, 0.0, 5),
    }
    engine = _make_engine(
        card_mask=card_mask,
        group_type_map={0: "straight"},
    )
    action_list = [
        ["Straight", "6", ["S3", "H4", "D5", "C6", "S7"]],
        ["PASS"],
    ]
    from src.v.nn.stage_assist_feed import recommend_assist_lead

    rec = recommend_assist_lead(
        engine,
        {},
        card_mask,
        ["S3", "H4", "D5", "C6", "S7"],
        "2",
        "stage_1",
        2,
        action_list,
    )
    assert rec is not None
    assert rec["type"] == "Straight"
    assert rec["intent"] == "assist_feed_s1_fallback"
