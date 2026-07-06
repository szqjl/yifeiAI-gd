# -*- coding: utf-8 -*-
"""GUA-072 子项：hr_with_opponents 接入 heuristic + 中局 dispatch。"""

import logging

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_engine(*, role="主攻", card_mask=None):
    eng = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    eng.logger = logging.getLogger("test_gua072_joker")
    eng.player_id = 0
    eng._card_mask = card_mask or {"S9": (-1, 0.0, 1), "SB": (-1, 0.0, 1), "HR": (-1, 0.0, 1)}
    eng._group_type_map = {}
    eng._group_members = {}
    eng._current_role = role
    eng._match_fail_type_mismatch = 0
    eng._match_fail_rank_mismatch = 0
    eng._match_fail_cards_mismatch = 0
    return eng


def _joker_belief(hr_with_opponents=0, sb_with_opponents=0):
    return {
        "joker_signal": {
            "hr_with_opponents": hr_with_opponents,
            "sb_with_opponents": sb_with_opponents,
            "hr_in_my_hand": 1,
            "sb_in_my_hand": 1,
        }
    }


def test_heuristic_prefers_pass_when_double_hr_outside_and_only_jokers_follow():
    engine = _make_engine()
    gs = {
        "myPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Single", "8", ["H8"]],
        "handCards": ["S9", "SB", "HR"],
        "curRank": "2",
        "numofplayers": [14, 14, 14, 14],
        "_belief": _joker_belief(hr_with_opponents=2),
    }
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "9", ["S9"]],
        ["Single", "B", ["SB"]],
        ["Single", "R", ["HR"]],
    ]
    idx = engine._heuristic_select(gs, action_list)
    assert action_list[idx][0] == "PASS"


def test_heuristic_prefers_sb_over_hr_when_opponent_has_hr():
    engine = _make_engine()
    gs = {
        "myPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Single", "A", ["HA"]],
        "handCards": ["SB", "HR"],
        "curRank": "2",
        "numofplayers": [14, 14, 14, 14],
        "_belief": _joker_belief(hr_with_opponents=1),
    }
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "B", ["SB"]],
        ["Single", "R", ["HR"]],
    ]
    idx = engine._heuristic_select(gs, action_list)
    assert action_list[idx][2] == ["SB"]


def test_recommend_lead_skips_joker_when_double_hr_outside():
    engine = _make_engine(
        card_mask={
            "HR": (-1, 0.0, 1),
            "S5": (-1, 0.0, 1),
            "H5": (0, 0.0, 2),
            "D5": (0, 0.0, 2),
        }
    )
    gs = {
        "_belief": _joker_belief(hr_with_opponents=2),
        "handCards": ["HR", "S5", "H5", "D5"],
        "curRank": "2",
    }
    rec = engine._recommend_lead_impl(gs, engine._card_mask, gs["handCards"], "2")
    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["cards"] == ["S5"]


def test_recommend_min_press_prefers_non_hr_when_opponent_has_hr():
    engine = _make_engine(
        card_mask={
            "SB": (-1, 0.0, 1),
            "HR": (-1, 0.0, 1),
            "SK": (-1, 0.0, 1),
        }
    )
    gs = {
        "_belief": _joker_belief(hr_with_opponents=1),
        "handCards": ["SB", "HR", "SK"],
        "curRank": "2",
    }
    greater = ["Single", "Q", ["HQ"]]
    rec = engine._recommend_min_press_impl(
        gs, engine._card_mask, greater, "Single", gs["handCards"], "2"
    )
    assert rec is not None
    assert rec["cards"] == ["SK"]


def test_stage_mid_dispatch_passes_instead_of_joker_min_press():
    engine = _make_engine(role="主攻")
    gs = {
        "_current_stage": "stage_2",
        "_belief": {
            "hand_counts": {0: 11, 1: 9, 2: 7, 3: 8},
            **_joker_belief(hr_with_opponents=2),
        },
        "_phase_relation": {
            "critical_enemy_seat": 1,
            "enemy_shape_hint": "unknown",
            "teammate_cover_confidence": 0.4,
            "same_type_suppressor_outside": False,
            "enemy_bomb_risk_max": 0.2,
        },
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "9", ["H9"]],
        "handCards": ["SB", "HR", "SK"],
        "curRank": "2",
    }
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "B", ["SB"]],
        ["Single", "R", ["HR"]],
        ["Single", "K", ["SK"]],
    ]
    rec = engine._recommend_play(gs, action_list)
    assert rec is not None
    assert rec["type"] == "PASS"
    assert rec["intent"] == "mid_hold_joker_vs_double_hr"


def test_stage_mid_lead_uses_safe_probe_when_double_hr_outside():
    engine = _make_engine(
        role="主攻",
        card_mask={"S6": (-1, 0.0, 1), "HR": (-1, 0.0, 1)},
    )
    gs = {
        "_current_stage": "stage_2",
        "_belief": {
            "hand_counts": {0: 12, 1: 9, 2: 8, 3: 8},
            **_joker_belief(hr_with_opponents=2),
        },
        "_phase_relation": {
            "critical_enemy_seat": 1,
            "enemy_shape_hint": "unknown",
            "teammate_cover_confidence": 0.4,
            "same_type_suppressor_outside": False,
            "enemy_bomb_risk_max": 0.1,
        },
        "myPos": 0,
        "curPos": 0,
        "greaterPos": -1,
        "greaterAction": ["PASS", "PASS", "PASS"],
        "handCards": ["S6", "HR"],
        "curRank": "2",
    }
    action_list = [
        ["Single", "6", ["S6"]],
        ["Single", "R", ["HR"]],
        ["PASS", "PASS", "PASS"],
    ]
    rec = engine._recommend_play(gs, action_list)
    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["cards"] == ["S6"]
    assert rec["intent"] == "mid_safe_structure_probe"
