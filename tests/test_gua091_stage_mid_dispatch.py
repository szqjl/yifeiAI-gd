# -*- coding: utf-8 -*-
"""GUA-091: stage_2 中局入口构造态回归。"""

import logging

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_engine(*, role="主攻", card_mask=None):
    eng = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    eng.logger = logging.getLogger("test_gua091")
    eng.player_id = 0
    eng._card_mask = card_mask or {"S9": (-1, 0.0, 0)}
    eng._group_type_map = {}
    eng._group_members = {}
    eng._current_role = role
    eng._match_fail_type_mismatch = 0
    eng._match_fail_rank_mismatch = 0
    eng._match_fail_cards_mismatch = 0
    return eng


def _build_action_list(*actions):
    result = [[a_type, a_rank, cards] for a_type, a_rank, cards in actions]
    result.append(["PASS", "PASS", "PASS"])
    return result


def test_stage_mid_dispatch_yields_to_teammate_control():
    engine = _make_engine(role="助攻")
    gs = {
        "_current_stage": "stage_2",
        "_belief": {"hand_counts": {0: 12, 1: 9, 2: 3, 3: 8}},
        "_phase_relation": {
            "critical_enemy_seat": 1,
            "enemy_shape_hint": "single_heavy",
            "teammate_cover_confidence": 0.92,
            "same_type_suppressor_outside": False,
            "enemy_bomb_risk_max": 0.2,
        },
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 2,
        "greaterAction": ["Single", "Q", ["SQ"]],
        "handCards": ["S9", "HJ"],
        "curRank": "2",
    }

    rec = engine._recommend_play(gs, _build_action_list(("Single", "9", ["S9"])))

    assert rec is not None
    assert rec["type"] == "PASS"
    assert rec["intent"] == "assist_yield_teammate"


def test_stage_mid_dispatch_blocks_critical_lower_enemy_with_max_press():
    engine = _make_engine(role="主攻")
    engine._recommend_max_press_impl = lambda *args, **kwargs: {
        "type": "Single",
        "rank": "A",
        "cards": ["SA"],
    }
    gs = {
        "_current_stage": "stage_2",
        "_belief": {"hand_counts": {0: 12, 1: 3, 2: 7, 3: 8}},
        "_phase_relation": {
            "critical_enemy_seat": 1,
            "enemy_shape_hint": "single_heavy",
            "teammate_cover_confidence": 0.35,
            "same_type_suppressor_outside": False,
            "enemy_bomb_risk_max": 0.1,
        },
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Single", "9", ["H9"]],
        "handCards": ["SA", "HJ"],
        "curRank": "2",
    }
    action_list = _build_action_list(
        ("Single", "J", ["HJ"]),
        ("Single", "A", ["SA"]),
    )

    rec = engine._recommend_play(gs, action_list)

    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["rank"] == "A"
    assert rec["intent"] == "mid_block_critical_enemy"


def test_stage_mid_dispatch_uses_min_press_when_outside_suppressor_exists():
    engine = _make_engine(role="主攻")
    engine._recommend_min_press_impl = lambda *args, **kwargs: {
        "type": "Single",
        "rank": "J",
        "cards": ["HJ"],
    }
    gs = {
        "_current_stage": "stage_2",
        "_belief": {"hand_counts": {0: 11, 1: 7, 2: 6, 3: 8}},
        "_phase_relation": {
            "critical_enemy_seat": 1,
            "enemy_shape_hint": "unknown",
            "teammate_cover_confidence": 0.4,
            "same_type_suppressor_outside": True,
            "enemy_bomb_risk_max": 0.2,
        },
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "9", ["H9"]],
        "handCards": ["HJ", "SK"],
        "curRank": "2",
    }
    action_list = _build_action_list(
        ("Single", "J", ["HJ"]),
        ("Single", "K", ["SK"]),
    )

    rec = engine._recommend_play(gs, action_list)

    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["rank"] == "J"
    assert rec["intent"] == "mid_trade_min_press"


def test_stage_mid_dispatch_bombs_to_cutoff_critical_enemy_without_cover():
    engine = _make_engine(role="主攻")
    engine._recommend_max_press_impl = lambda *args, **kwargs: None
    engine._r11_bomb_throttle_check = lambda *args, **kwargs: (True, "critical_enemy")
    engine._recommend_bomb_from_mask = lambda *args, **kwargs: {
        "type": "Bomb",
        "rank": "8",
        "cards": ["S8", "H8", "D8", "C8"],
    }
    gs = {
        "_current_stage": "stage_2",
        "_belief": {"hand_counts": {0: 9, 1: 2, 2: 8, 3: 6}},
        "_phase_relation": {
            "critical_enemy_seat": 1,
            "enemy_shape_hint": "pair_heavy",
            "teammate_cover_confidence": 0.2,
            "same_type_suppressor_outside": False,
            "enemy_bomb_risk_max": 0.1,
        },
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Pair", "T", ["ST", "HT"]],
        "handCards": ["S8", "H8", "D8", "C8"],
        "curRank": "2",
    }
    action_list = _build_action_list(
        ("Bomb", "8", ["S8", "H8", "D8", "C8"]),
    )

    rec = engine._recommend_play(gs, action_list)

    assert rec is not None
    assert rec["type"] == "Bomb"
    assert rec["intent"] == "mid_bomb_cutoff:critical_enemy"


def test_stage_mid_dispatch_ignites_bomb_when_sprint_fire_ready():
    engine = _make_engine(
        role="主攻",
        card_mask={
            "S4": (0, 1.0, 4),
            "H4": (0, 1.0, 4),
            "D4": (0, 1.0, 4),
            "C4": (0, 1.0, 4),
            "S5": (1, 1.0, 4),
            "H5": (1, 1.0, 4),
            "D5": (1, 1.0, 4),
            "C5": (1, 1.0, 4),
            "HK": (-1, 0.0, 0),
        },
    )
    engine._group_type_map = {0: "Bomb", 1: "Bomb"}
    gs = {
        "_current_stage": "stage_2",
        "_belief": {"hand_counts": {0: 9, 1: 6, 2: 7, 3: 8}},
        "_phase_relation": {
            "critical_enemy_seat": 1,
            "enemy_shape_hint": "single_heavy",
            "teammate_cover_confidence": 0.25,
            "same_type_suppressor_outside": False,
            "enemy_bomb_risk_max": 0.1,
            "sprint_fire_ready": True,
        },
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "9", ["H9"]],
        "handCards": ["S4", "H4", "D4", "C4", "S5", "H5", "D5", "C5", "HK"],
        "curRank": "2",
    }
    action_list = _build_action_list(
        ("Single", "K", ["HK"]),
        ("Bomb", "4", ["S4", "H4", "D4", "C4"]),
        ("Bomb", "5", ["S5", "H5", "D5", "C5"]),
    )

    rec = engine._recommend_play(gs, action_list)

    assert rec is not None
    assert rec["type"] == "Bomb"
    assert rec["rank"] == "4"
    assert rec["intent"] == "mid_sprint_fire_bomb"


def test_stage_mid_dispatch_holds_bomb_when_rear_teammate_can_cover_enemy_out_single():
    engine = _make_engine(
        role="主攻",
        card_mask={
            "S9": (0, 1.0, 4),
            "H9": (0, 1.0, 4),
            "D9": (0, 1.0, 4),
            "C9": (0, 1.0, 4),
            "HA": (1, 1.0, 4),
            "DA": (1, 1.0, 4),
        },
    )
    engine._group_type_map = {0: "Bomb", 1: "Bomb"}
    engine._recommend_min_press_impl = lambda *args, **kwargs: None
    engine._r11_bomb_throttle_check = lambda *args, **kwargs: (True, "critical_enemy")
    engine._recommend_bomb_from_mask = lambda *args, **kwargs: {
        "type": "Bomb",
        "rank": "9",
        "cards": ["S9", "H9", "D9", "C9"],
    }
    gs = {
        "_current_stage": "stage_2",
        "_belief": {"hand_counts": {0: 12, 1: 0, 2: 17, 3: 12}},
        "_phase_relation": {
            "critical_enemy_seat": 1,
            "enemy_shape_hint": "single_heavy",
            "teammate_cover_confidence": 0.2,
            "teammate_rear_single_cover_confidence": 0.95,
            "same_type_suppressor_outside": False,
            "enemy_bomb_risk_max": 0.1,
            "sprint_fire_ready": True,
        },
        "myPos": 2,
        "curPos": 2,
        "greaterPos": 1,
        "greaterAction": ["Single", "3", ["D3"]],
        "handCards": [
            "S5", "H5", "S7", "D7", "C8",
            "S9", "H9", "D9", "C9",
            "HA", "HA", "DA", "DA",
        ],
        "curRank": "3",
    }
    action_list = _build_action_list(
        ("Bomb", "9", ["S9", "H9", "D9", "C9"]),
        ("Bomb", "A", ["HA", "HA", "DA", "DA"]),
    )

    rec = engine._recommend_play(gs, action_list)

    assert rec is not None
    assert rec["type"] == "PASS"
    assert rec["intent"] == "mid_hold_rear_teammate_single_cover"


def test_stage_mid_dispatch_three_with_two_pressure_counter_avoids_pass():
    """敌方关键位以三带二反顶时，stage_2 应允许受控续压而非 mid_no_same_type_pass。"""
    engine = _make_engine(
        role="主攻",
        card_mask={
            "S4": (3, 1.0, 2),
            "D4": (3, 1.0, 2),
            "C5": (4, 1.0, 2),
            "D5": (4, 1.0, 2),
            "C6": (5, 1.0, 2),
            "D6": (5, 1.0, 2),
            "S7": (0, 1.0, 4),
            "H7": (0, 1.0, 4),
            "D7": (0, 1.0, 4),
            "SK": (-1, 0.0, 1),
            "SA": (2, 0.0, 2),
            "CA": (2, 0.0, 2),
            "S3": (1, 1.0, 4),
            "C3": (1, 1.0, 4),
            "D3": (1, 1.0, 4),
            "HR": (-1, 0.0, 1),
        },
    )
    engine._group_type_map = {
        0: "Bomb",
        1: "Bomb",
        2: "pair",
        3: "pair_in_three_pair",
        4: "pair_in_three_pair",
        5: "pair_in_three_pair",
    }
    engine._group_members = {
        0: ["S7", "H7", "H7", "D7"],
        1: ["S3", "S3", "C3", "D3"],
        2: ["SA", "CA"],
        3: ["S4", "D4"],
        4: ["C5", "D5"],
        5: ["C6", "D6"],
    }
    gs = {
        "_current_stage": "stage_2",
        "_belief": {"hand_counts": {0: 18, 1: 9, 2: 22, 3: 12}},
        "_phase_relation": {
            "critical_enemy_seat": 1,
            "enemy_shape_hint": "structured",
            "teammate_cover_confidence": 0.1,
            "same_type_suppressor_outside": True,
            "enemy_bomb_risk_max": 1.0,
            "sprint_fire_ready": True,
        },
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 1,
        "greaterAction": ["ThreeWithTwo", "Q", ["SQ", "DQ", "DQ", "H8", "H8"]],
        "handCards": [
            "S4", "D4", "C5", "D5", "C6", "D6",
            "S7", "H7", "H7", "D7",
            "SK", "SA", "CA",
            "S3", "S3", "C3", "D3", "HR",
        ],
        "curRank": "3",
    }
    action_list = _build_action_list(
        ("ThreeWithTwo", "3", ["S3", "S3", "D3", "S4", "D4"]),
    )

    rec = engine._recommend_play(gs, action_list)

    assert rec is not None
    assert rec["type"] == "ThreeWithTwo"
    assert rec["rank"] == "3"


def test_mid_hold_skipped_when_teammate_already_finished():
    """队友已头游（remaining=0）不得 mid_hold_for_teammate PASS。"""
    engine = _make_engine(role="主攻")
    engine._recommend_min_press_impl = lambda *args, **kwargs: None
    engine._recommend_max_press_impl = lambda *args, **kwargs: None
    engine._r11_bomb_throttle_check = lambda *args, **kwargs: (False, "")
    engine._recommend_counter_bomb_in_action_list = lambda *args, **kwargs: {
        "type": "Bomb",
        "rank": "K",
        "cards": ["SK", "HK", "CK", "DK"],
    }
    gs = {
        "_current_stage": "stage_2",
        "_belief": {"hand_counts": {0: 14, 1: 16, 2: 0, 3: 8}},
        "_phase_relation": {
            "critical_enemy_seat": 3,
            "enemy_shape_hint": "unknown",
            # 即便误传高 cover，remaining=0 也必须跳过 hold
            "teammate_cover_confidence": 1.0,
            "teammate_rear_single_cover_confidence": 0.0,
            "same_type_suppressor_outside": True,
            "enemy_bomb_risk_max": 0.2,
            "sprint_fire_ready": False,
        },
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "K", ["HK"]],
        "handCards": ["SK", "HK", "CK", "DK", "H6", "C6", "D6"],
        "curRank": "A",
        "numofplayers": [14, 16, 0, 8],
    }
    action_list = _build_action_list(
        ("Bomb", "K", ["SK", "HK", "CK", "DK"]),
        ("Single", "A", ["HA"]),
    )
    # greaterPos=3 = 上家（myPos+3）→ is_upper 分支
    rec = engine._stage_mid_dispatch(
        gs,
        engine._card_mask,
        gs["handCards"],
        "A",
        greater_action=gs["greaterAction"],
        greater_type="Single",
        greater_rank="K",
        is_lead=False,
        is_teammate=False,
        is_upper=True,
        is_lower=False,
        teammate_pos=2,
    )
    assert rec is not None
    assert rec.get("intent") != "mid_hold_for_teammate"
    assert rec["type"] != "PASS" or rec.get("intent") == "mid_no_same_type_pass"
    # 有反炸推荐时应走出 bomb，而非 hold
    if rec["type"] == "Bomb":
        assert rec.get("intent") == "mid_counter_enemy_bomb"


def test_should_sprint_true_for_double_bomb_plus_twt():
    """双炸+TWT：语义 3 手，但冲刺能力成立 → should_sprint True。"""
    from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor

    hand = (
        ["S2", "H2", "C2", "D2"]
        + ["SK", "SK", "HK", "CK", "DK"]
        + ["H6", "C6", "D6", "D9", "D9"]
    )
    gs = {
        "handCards": hand,
        "myPos": 0,
        "numofplayers": [14, 16, 0, 8],
        "_group_type_map": {
            "Bomb": 2,
            "trip_in_three_with_two": 1,
            "pair_in_three_with_two": 1,
        },
    }
    EndgamePreprocessor().preprocess(gs)
    self_ctx = gs["_endgame_context"]["self"]
    assert self_ctx["has_two_clean_hands"] is False  # 3 手
    assert self_ctx["has_bomb"] is True
    assert self_ctx["should_sprint"] is True  # 冲刺能力 OR
