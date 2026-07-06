# -*- coding: utf-8 -*-
"""GUA-090：stage_0 / stage_1 开局与初期入口构造态回归。"""

import logging

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_engine(*, role="助攻", card_mask=None, group_type_map=None, group_members=None):
    eng = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    eng.logger = logging.getLogger("test_gua090")
    eng.player_id = 0
    eng._card_mask = card_mask or {}
    eng._group_type_map = group_type_map or {}
    eng._group_members = group_members or {}
    eng._current_role = role
    eng._match_fail_type_mismatch = 0
    eng._match_fail_rank_mismatch = 0
    eng._match_fail_cards_mismatch = 0
    return eng


def _build_action_list(*actions):
    result = [[a_type, a_rank, cards] for a_type, a_rank, cards in actions]
    result.append(["PASS", "PASS", "PASS"])
    return result


def test_stage_open_plan_avoids_leading_level_single_when_safe_pair_exists():
    """开局 stage_0_1：若仅有高耗损级牌单张与安全小对，优先小对。"""
    hand_cards = ["H2", "S7", "H7"]
    card_mask = {
        "H2": (-1, 0.0, 0),
        "S7": (0, 0.0, 2),
        "H7": (0, 0.0, 2),
    }
    engine = _make_engine(
        role="助攻",
        card_mask=card_mask,
        group_type_map={0: "pair"},
    )
    action_list = _build_action_list(
        ("Single", "2", ["H2"]),
        ("Pair", "7", ["H7", "S7"]),
    )
    gs = {
        "_current_stage": "stage_1",
        "myPos": 0,
        "curPos": -1,
        "greaterPos": -1,
        "greaterAction": [],
        "handCards": hand_cards,
        "curRank": "2",
    }

    rec = engine._recommend_play(gs, action_list)

    assert rec is not None
    assert rec["type"] == "Pair"
    assert rec["rank"] == "7"
    assert rec["intent"] == "assist_feed_s1_small_pair"


def test_stage_open_plan_prefers_low_scatter_single_over_high_ace():
    """开局 stage_0_1：若同时有低耗损散单与高单 A，优先低耗损散单。"""
    hand_cards = ["SA", "C5", "S7", "H7"]
    card_mask = {
        "SA": (-1, 0.0, 0),
        "C5": (-1, 0.0, 0),
        "S7": (0, 0.0, 2),
        "H7": (0, 0.0, 2),
    }
    engine = _make_engine(
        role="主攻",
        card_mask=card_mask,
        group_type_map={0: "pair"},
    )
    action_list = _build_action_list(
        ("Single", "A", ["SA"]),
        ("Single", "5", ["C5"]),
        ("Pair", "7", ["H7", "S7"]),
    )
    gs = {
        "_current_stage": "stage_1",
        "myPos": 0,
        "curPos": -1,
        "greaterPos": -1,
        "greaterAction": [],
        "handCards": hand_cards,
        "curRank": "2",
    }

    rec = engine._recommend_play(gs, action_list)

    assert rec is not None
    # GUA-116：仅 1 张 <10 散单时不走 P1，命中 P4 小对 77
    assert rec["type"] == "Pair"
    assert rec["rank"] == "7"
    assert rec["cards"] == ["H7", "S7"]
    assert rec["intent"] == "main_p4_small_pair"


def test_stage_open_plan_yields_to_teammate_control():
    """开局 stage_0_1：队友控牌时，优先让道 PASS。"""
    hand_cards = ["C5", "S7", "H7"]
    card_mask = {
        "C5": (-1, 0.0, 0),
        "S7": (0, 0.0, 2),
        "H7": (0, 0.0, 2),
    }
    engine = _make_engine(
        role="助攻",
        card_mask=card_mask,
        group_type_map={0: "pair"},
    )
    action_list = _build_action_list(
        ("Single", "5", ["C5"]),
        ("Pair", "7", ["H7", "S7"]),
    )
    gs = {
        "_current_stage": "stage_1",
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 2,
        "greaterAction": ["Single", "8", ["S8"]],
        "handCards": hand_cards,
        "curRank": "2",
    }

    rec = engine._recommend_play(gs, action_list)

    assert rec is not None
    assert rec["type"] == "PASS"
    assert rec["intent"] == "assist_yield_teammate"


def test_stage_open_plan_ignites_bomb_when_sprint_fire_ready():
    """GUA-102：前中段整牌冲刺态成熟时，允许从最小跟单切到主动点火开炸。"""
    hand_cards = ["S4", "H4", "D4", "C4", "S5", "H5", "D5", "C5", "HK"]
    card_mask = {
        "S4": (0, 1.0, 4),
        "H4": (0, 1.0, 4),
        "D4": (0, 1.0, 4),
        "C4": (0, 1.0, 4),
        "S5": (1, 1.0, 4),
        "H5": (1, 1.0, 4),
        "D5": (1, 1.0, 4),
        "C5": (1, 1.0, 4),
        "HK": (-1, 0.0, 0),
    }
    engine = _make_engine(
        role="主攻",
        card_mask=card_mask,
        group_type_map={0: "bomb", 1: "bomb"},
    )
    action_list = _build_action_list(
        ("Single", "K", ["HK"]),
        ("Bomb", "4", ["S4", "H4", "D4", "C4"]),
        ("Bomb", "5", ["S5", "H5", "D5", "C5"]),
    )
    gs = {
        "_current_stage": "stage_1",
        "_phase_relation": {
            "sprint_fire_ready": True,
            "teammate_cover_confidence": 0.2,
        },
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "9", ["H9"]],
        "handCards": hand_cards,
        "curRank": "2",
    }

    rec = engine._recommend_play(gs, action_list)

    assert rec is not None
    assert rec["type"] == "Bomb"
    assert rec["rank"] == "4"
    assert rec["intent"] == "open_sprint_fire_bomb"


def test_stage_open_plan_keeps_min_press_when_not_sprint_fire_ready():
    """GUA-102：非冲刺态仍保持最小跟单，不应硬点火开炸。"""
    hand_cards = ["S4", "H4", "D4", "C4", "S5", "H5", "D5", "C5", "HK"]
    card_mask = {
        "S4": (0, 1.0, 4),
        "H4": (0, 1.0, 4),
        "D4": (0, 1.0, 4),
        "C4": (0, 1.0, 4),
        "S5": (1, 1.0, 4),
        "H5": (1, 1.0, 4),
        "D5": (1, 1.0, 4),
        "C5": (1, 1.0, 4),
        "HK": (-1, 0.0, 0),
    }
    engine = _make_engine(
        role="主攻",
        card_mask=card_mask,
        group_type_map={0: "bomb", 1: "bomb"},
    )
    action_list = _build_action_list(
        ("Single", "K", ["HK"]),
        ("Bomb", "4", ["S4", "H4", "D4", "C4"]),
        ("Bomb", "5", ["S5", "H5", "D5", "C5"]),
    )
    gs = {
        "_current_stage": "stage_1",
        "_phase_relation": {
            "sprint_fire_ready": False,
            "teammate_cover_confidence": 0.2,
        },
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "9", ["H9"]],
        "handCards": hand_cards,
        "curRank": "2",
    }

    rec = engine._recommend_play(gs, action_list)

    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["rank"] == "K"


def test_stage_open_plan_three_with_two_pressure_counter_avoids_first_round_pass():
    """敌方关键位以三带二反顶时，stage_0_1 不应继续走第一圈让道 PASS。"""
    hand_cards = [
        "S5", "H5",
        "S6", "H6", "C6", "D6",
        "S7", "D7",
        "C8",
        "S9", "S9", "H9", "D9",
        "ST", "DT", "DT", "H3",
        "CQ",
        "HA", "HA", "DA", "DA",
    ]
    card_mask = {
        "S5": (4, 0.0, 2),
        "H5": (4, 0.0, 2),
        "S6": (0, 1.0, 4),
        "H6": (0, 1.0, 4),
        "C6": (0, 1.0, 4),
        "D6": (0, 1.0, 4),
        "S7": (5, 0.0, 2),
        "D7": (5, 0.0, 2),
        "C8": (-1, 0.0, 1),
        "S9": (1, 1.0, 4),
        "H9": (1, 1.0, 4),
        "D9": (1, 1.0, 4),
        "ST": (2, 1.0, 4),
        "DT": (2, 1.0, 4),
        "H3": (2, 1.0, 4),
        "CQ": (-1, 0.0, 1),
        "HA": (3, 1.0, 4),
        "DA": (3, 1.0, 4),
    }
    engine = _make_engine(
        role="主攻",
        card_mask=card_mask,
        group_type_map={
            0: "bomb",
            1: "bomb",
            2: "bomb",
            3: "bomb",
            4: "pair",
            5: "pair",
        },
    )
    action_list = _build_action_list(
        ("ThreeWithTwo", "A", ["HA", "HA", "DA", "S5", "H5"]),
    )
    gs = {
        "_current_stage": "stage_1",
        "_belief": {"hand_counts": {0: 18, 1: 9, 2: 22, 3: 12}},
        "_phase_relation": {
            "critical_enemy_seat": 1,
            "enemy_shape_hint": "structured",
            "teammate_cover_confidence": 0.1,
            "same_type_suppressor_outside": True,
        },
        "myPos": 2,
        "curPos": 2,
        "greaterPos": 1,
        "greaterAction": ["ThreeWithTwo", "Q", ["SQ", "DQ", "DQ", "H8", "H8"]],
        "handCards": hand_cards,
        "curRank": "3",
    }

    rec = engine._recommend_play(gs, action_list)

    assert rec is not None
    assert rec["type"] == "ThreeWithTwo"
    assert rec["rank"] == "A"
