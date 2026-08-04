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


def test_p1_second_bigger_than_q_plays_first_smallest():
    """第二小 > Q 时出第一小（守大不破）。"""
    from src.v.nn.stage_main_attack_lead import _pick_p1_second_smallest
    assert _pick_p1_second_smallest(["S3", "HA"]) == "S3"
    assert _pick_p1_second_smallest(["S3", "DK"]) == "S3"
    # 第二小 == Q → 不触发，仍第二小
    assert _pick_p1_second_smallest(["S3", "HQ"]) == "HQ"
    # 第二小 < Q → 仍第二小
    assert _pick_p1_second_smallest(["S3", "D9"]) == "D9"


def test_p1_enemy_one_left_keeps_second_smallest():
    """对方剩 1 张时保持原逻辑（仍出第二小）。"""
    from src.v.nn.stage_main_attack_lead import _pick_p1_second_smallest
    assert _pick_p1_second_smallest(["S3", "HA"], enemy_one_left=True) == "HA"
    assert _pick_p1_second_smallest(["S3", "DK"], enemy_one_left=True) == "DK"


def test_p1_second_smallest_low_singles_unchanged():
    """P1 候选限 3-9，第二小不触发 >Q 改写 → 仍第二小。"""
    card_mask = {"S3": (-1, 0.0, 0), "D5": (-1, 0.0, 0), "HA": (-1, 0.0, 0)}
    engine = _make_engine(card_mask=card_mask)
    rec = recommend_main_attack_lead(
        engine, {"_current_stage": "stage_1"}, card_mask, list(card_mask), "2", "stage_1",
    )
    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["rank"] == "5"
    assert rec["intent"] == "main_p1_second_single"


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


def test_p3_leads_core_straight_with_bomb_recapture():
    """
    is_core 顺可整组领出（≠拆核）；回手=组内炸。
    构造：两顺 + 两炸，无 P1 累赘散单 → 应领最小整顺，非散单/拆炸。
    """
    # G0 Bomb/J, G1 Bomb/Q, G2 straight 45678, G3 straight 23456
    s_low = ["S2", "C3", "C4", "C5", "D6"]
    s_hi = ["D4", "H5", "S6", "H7", "H8"]
    bomb_j = ["SJ", "HJ", "CJ", "DJ"]
    bomb_q = ["SQ", "HQ", "CQ", "DQ"]
    card_mask = {}
    group_members = {
        0: bomb_j,
        1: bomb_q,
        2: s_hi,
        3: s_low,
    }
    group_type_map = {
        0: "Bomb",
        1: "Bomb",
        2: "straight",
        3: "straight",
    }
    for gid, cards in group_members.items():
        for c in cards:
            card_mask[c] = (gid, 1.0, len(cards))
    engine = _make_engine(
        card_mask=card_mask,
        group_type_map=group_type_map,
        group_members=group_members,
    )
    rec = recommend_main_attack_lead(
        engine, {}, card_mask, list(card_mask), "2", "stage_2",
    )
    assert rec is not None
    assert rec["type"] == "Straight"
    assert rec["intent"] == "main_p3_short_straight"
    assert set(rec["cards"]) == set(s_low)


def test_p2_leads_core_twt_with_bomb_recapture():
    """单手 core TWT + 炸作回手，stage_2：整组领三带二。"""
    trip = ["S6", "H6", "C6"]
    pair = ["S4", "H4"]
    bomb = ["SJ", "HJ", "CJ", "DJ"]
    card_mask = {}
    group_members = {0: trip, 1: pair, 2: bomb}
    group_type_map = {
        0: "trip_in_three_with_two",
        1: "pair_in_three_with_two",
        2: "Bomb",
    }
    for gid, cards in group_members.items():
        for c in cards:
            card_mask[c] = (gid, 1.0, len(cards))
    engine = _make_engine(
        card_mask=card_mask,
        group_type_map=group_type_map,
        group_members=group_members,
    )
    rec = recommend_main_attack_lead(
        engine, {}, card_mask, list(card_mask), "2", "stage_2",
    )
    assert rec is not None
    assert rec["type"] == "ThreeWithTwo"
    assert rec["intent"] == "main_p2_three_with_two"
    assert set(rec["cards"]) == set(trip + pair)


def test_whole_group_core_not_break_filter():
    """整组打出 core 顺：_get_broken_core_type 必须为 None（不算拆）。"""
    cards = ["S3", "S4", "S5", "S6", "S7"]
    card_mask = {c: (0, 1.0, 5) for c in cards}
    group_type_map = {0: "straight"}
    group_members = {0: list(cards)}
    engine = _make_engine(
        card_mask=card_mask,
        group_type_map=group_type_map,
        group_members=group_members,
    )
    broken = UltimateWinRateEngineV7._get_broken_core_type(
        ["Straight", "3", list(cards)],
        card_mask,
        group_type_map,
        group_members,
    )
    assert broken is None
    # 拆一张则算拆
    broken_part = UltimateWinRateEngineV7._get_broken_core_type(
        ["Single", "5", ["S5"]],
        card_mask,
        group_type_map,
        group_members,
    )
    assert broken_part == "straight"


def test_p3b_leads_two_trips_with_bomb_recapture():
    """炸 + 钢板：整组 TwoTrips 领出，不得拆成 Trips。"""
    bomb = ["C4", "D4", "H4", "S4"]
    t7 = ["H7", "C7", "S7"]
    t8 = ["S8", "H8", "C8"]
    card_mask = {}
    group_members = {0: bomb, 1: t7, 2: t8}
    group_type_map = {
        0: "Bomb",
        1: "trip_in_steel_plate",
        2: "trip_in_steel_plate",
    }
    for gid, cards in group_members.items():
        for c in cards:
            card_mask[c] = (gid, 1.0, len(cards))
    engine = _make_engine(
        card_mask=card_mask,
        group_type_map=group_type_map,
        group_members=group_members,
    )
    rec = recommend_main_attack_lead(
        engine, {}, card_mask, list(card_mask), "A", "stage_2",
    )
    assert rec is not None
    assert rec["type"] == "TwoTrips"
    assert rec["intent"] == "main_p3b_two_trips"
    assert set(rec["cards"]) == set(t7 + t8)


def test_partial_steel_trips_blocked_on_free_lead():
    """自由领出：半组 trip_in_steel_plate 的 Trips 须被 filter 拦掉。"""
    bomb = ["C4", "D4", "H4", "S4"]
    t7 = ["H7", "C7", "S7"]
    t8 = ["S8", "H8", "C8"]
    card_mask = {}
    group_members = {0: bomb, 1: t7, 2: t8}
    group_type_map = {
        0: "Bomb",
        1: "trip_in_steel_plate",
        2: "trip_in_steel_plate",
    }
    for gid, cards in group_members.items():
        for c in cards:
            card_mask[c] = (gid, 1.0, len(cards))
    engine = _make_engine(
        card_mask=card_mask,
        group_type_map=group_type_map,
        group_members=group_members,
    )
    engine._current_role = "主攻"
    engine.group_filter_bypass_count = 0
    engine.group_filtered_count = 0
    gs = {
        "myPos": 0,
        "curPos": -1,
        "greaterPos": -1,
        "handCards": list(card_mask.keys()),
        "curRank": "A",
        "numofplayers": [11, 12, 10, 12],
        "publicInfo": [{"rest": 11}, {"rest": 12}, {"rest": 10}, {"rest": 12}],
    }
    action_list = [
        ["Trips", "7", t7],
        ["TwoTrips", "7", t7 + t8],
        ["Bomb", "4", bomb],
    ]
    filtered, _ = engine._group_consistency_filter(action_list, gs)
    types = [a[0] for a in filtered]
    assert "Trips" not in types
    assert "TwoTrips" in types
    assert "Bomb" in types


def test_p3d_natural_trips_with_bomb_recapture():
    """天然 trips + 炸回手 → 整组 Trips 领出。"""
    trips = ["S5", "H5", "C5"]
    bomb = ["SJ", "HJ", "CJ", "DJ"]
    card_mask = {}
    group_members = {0: trips, 1: bomb}
    group_type_map = {0: "trips", 1: "Bomb"}
    for gid, cards in group_members.items():
        for c in cards:
            card_mask[c] = (gid, 1.0, len(cards))
    engine = _make_engine(
        card_mask=card_mask,
        group_type_map=group_type_map,
        group_members=group_members,
    )
    rec = recommend_main_attack_lead(
        engine, {}, card_mask, list(card_mask), "2", "stage_2",
    )
    assert rec is not None
    assert rec["type"] == "Trips"
    assert rec["intent"] == "main_p3d_trips"
    assert set(rec["cards"]) == set(trips)
