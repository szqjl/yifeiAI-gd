# -*- coding: utf-8 -*-
"""GUA-282：记忆队友领出圈，禁对敌方普通覆盖开炸；弱牌只跟单/对。

锚点 match=6a8da7ef0fbd680d7c834a41：队友领 TWT → 上家压 JJJ+77 →
V8 用 StraightFlush 开炸。应 PASS 让队友回手。
"""

from __future__ import annotations

import logging

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.stage_assist_feed import recommend_assist_lead
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


TWT_8 = ["ThreeWithTwo", "8", ["D8", "D8", "C8", "S3", "C3"]]
TWT_9 = ["ThreeWithTwo", "9", ["C9", "C9", "H9", "C3", "H3"]]
TWT_T = ["ThreeWithTwo", "T", ["HT", "CT", "CT", "H5", "S5"]]
TWT_J = ["ThreeWithTwo", "J", ["CJ", "CJ", "HJ", "C7", "H7"]]
SF = ["StraightFlush", "T", ["ST", "SJ", "SQ", "SK", "SA"]]
PASS = ["PASS", "PASS", "PASS"]


def _hist(seat, action):
    return {"pos": seat, "action": action}


def test_memory_same_trick_after_cover_and_two_pass():
    """p0 领 TWT → p1 压 → PASS×2 → p0 再压：本圈领出仍是队友 TWT。"""
    mt = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
    history = [
        _hist(0, TWT_8),
        _hist(1, TWT_9),
        _hist(2, PASS),
        _hist(3, PASS),
        _hist(0, TWT_T),
        _hist(1, TWT_J),
    ]
    mt.sync_trick_lead_from_history(history)
    assert mt.teammate_led_current_trick() is True
    assert mt.current_trick_lead_seat == 0
    assert mt.current_trick_lead_type == "ThreeWithTwo"
    assert mt.get_teammate_last_lead_type() == "ThreeWithTwo"


def test_memory_record_play_trailing_pass_keeps_lead():
    """record_pass 写入历史后，三 PASS 才换圈；两 PASS 再出仍同圈。"""
    mt = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
    mt.record_play(0, TWT_8)
    mt.record_play(1, TWT_9)
    mt.record_pass(2, "ThreeWithTwo")
    mt.record_pass(3, "ThreeWithTwo")
    mt.record_play(0, TWT_T)
    assert mt.teammate_led_current_trick() is True
    assert mt.current_trick_lead_type == "ThreeWithTwo"


def test_memory_enemy_lead_not_teammate():
    mt = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
    mt.sync_trick_lead_from_history([
        _hist(1, ["Pair", "T", ["ST", "HT"]]),
        _hist(2, PASS),
    ])
    assert mt.teammate_led_current_trick() is False
    assert mt.current_trick_lead_seat == 1


def _make_mid_engine(*, role="超强主攻"):
    eng = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    eng.logger = logging.getLogger("test_gua282")
    eng.player_id = 2
    eng._card_mask = {}
    eng._group_type_map = {"Bomb": 2, "StraightFlush": 1}
    eng._group_members = {}
    eng._current_role = role
    eng._match_fail_type_mismatch = 0
    eng._match_fail_rank_mismatch = 0
    eng._match_fail_cards_mismatch = 0
    eng._recommend_min_press_impl = lambda *a, **k: None
    eng._recommend_max_press_impl = lambda *a, **k: None
    eng._recommend_targeted_regroup_press = lambda *a, **k: None
    eng._find_joker_control_single = lambda *a, **k: None
    eng._r11_bomb_throttle_check = lambda *a, **k: (True, "critical_enemy")
    eng._recommend_bomb_from_mask = lambda *a, **k: {
        "type": "StraightFlush",
        "rank": "T",
        "cards": ["ST", "SJ", "SQ", "H2", "SA"],
    }
    eng._recommend_cheapest_bomb_from_action_list = lambda *a, **k: {
        "type": "StraightFlush",
        "rank": "T",
        "cards": ["ST", "SJ", "SQ", "H2", "SA"],
    }
    eng._mid_aggressive_value_check = lambda *a, **k: True
    tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
    tracker.sync_trick_lead_from_history([
        _hist(0, TWT_T),
        _hist(1, TWT_J),
    ])
    eng._tracker = tracker
    return eng


def _mid_gs():
    return {
        "_current_stage": "stage_2",
        "_belief": {"hand_counts": {0: 18, 1: 12, 2: 20, 3: 14}},
        "_phase_relation": {
            "critical_enemy_seat": 1,
            "enemy_shape_hint": "structured",
            "teammate_cover_confidence": 0.2,
            "same_type_suppressor_outside": False,
            "enemy_bomb_risk_max": 0.1,
            "sprint_fire_ready": False,
        },
        "myPos": 2,
        "curPos": 2,
        "greaterPos": 1,
        "greaterAction": TWT_J,
        "handCards": ["ST", "SJ", "SQ", "H2", "SA", "S7", "H7", "D7", "C7"],
        "curRank": "2",
        "actionList": [PASS, TWT_T, SF],
        "numofplayers": [18, 12, 20, 14],
    }


def test_super_attack_does_not_sf_bomb_teammate_twt_trick():
    """超强主攻跟上家 TWT（本圈队友领出）→ 不开 StraightFlush。"""
    engine = _make_mid_engine()
    gs = _mid_gs()
    rec = engine._stage_mid_dispatch(
        gs,
        engine._card_mask,
        gs["handCards"],
        "2",
        greater_action=TWT_J,
        greater_type="ThreeWithTwo",
        greater_rank="J",
        is_lead=False,
        is_teammate=False,
        is_upper=True,
        is_lower=False,
        teammate_pos=0,
    )
    assert rec is not None
    assert rec["type"] != "StraightFlush"
    assert rec["type"] != "Bomb"
    assert rec["type"] == "PASS"


def test_weak_follow_skips_twt_on_teammate_lead():
    """助攻跟队友领出的 TWT 圈 → PASS（只跟单/对）。"""
    engine = _make_mid_engine(role="助攻")
    engine._current_role = "助攻"
    gs = _mid_gs()
    rec = engine._gua282_weak_follow_on_teammate_lead(
        gs, greater_type="ThreeWithTwo", is_lead=False,
    )
    assert rec is not None
    assert rec["type"] == "PASS"
    assert rec.get("intent") == "gua282_weak_skip_non_pair"


def test_weak_follow_allows_single():
    engine = _make_mid_engine(role="助攻")
    rec = engine._gua282_weak_follow_on_teammate_lead(
        _mid_gs(), greater_type="Single", is_lead=False,
    )
    assert rec is None


def test_weak_lead_echoes_teammate_twt():
    """弱牌获得领出权 → 打记忆中队友上一圈领出的 ThreeWithTwo。"""
    engine = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    engine.logger = logging.getLogger("test_gua282_lead")
    engine.player_id = 2
    engine._card_mask = {}
    engine._group_type_map = {}
    engine._group_members = {}
    engine.INTERNAL_TO_PLATFORM_RANK = UltimateWinRateEngineV7.INTERNAL_TO_PLATFORM_RANK
    tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
    tracker.teammate_last_lead_type = "ThreeWithTwo"
    tracker.teammate_last_lead_rank = "8"
    engine._tracker = tracker
    action_list = [
        PASS,
        ["Single", "5", ["H5"]],
        ["Pair", "6", ["S6", "H6"]],
        ["ThreeWithTwo", "8", ["C8", "S8", "H8", "D3", "H3"]],
    ]
    rec = recommend_assist_lead(
        engine, {"_current_stage": "stage_1"}, {}, ["C8", "S8", "H8", "D3", "H3"],
        "2", "stage_1", 0, action_list,
    )
    assert rec is not None
    assert rec["type"] == "ThreeWithTwo"
    assert rec.get("intent") == "gua282_echo_teammate_lead"


def _q1_gs(*, action_list, numofplayers, tracker_history):
    hand = ["ST", "SJ", "SQ", "H2", "SA", "C8", "S8", "H8", "D3", "H3"]
    tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.sync_trick_lead_from_history(tracker_history)
    tracker.hand_counts = {i: numofplayers[i] for i in range(4)}
    return {
        "myPos": 2,
        "curPos": 2,
        "greaterPos": 1,
        "greaterAction": TWT_J,
        "handCards": list(hand),
        "actionList": action_list,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "numofplayers": list(numofplayers),
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {i: numofplayers[i] for i in range(4)},
            "opp_bomb_risks": {1: 0.0, 3: 0.0},
        },
        "_role": "主攻",
    }


def test_q1_only_sf_on_teammate_twt_trick_passes():
    """残局 Q1：队友领 TWT 圈、仅 SF 可压 → PASS，不开炸。"""
    gs = _q1_gs(
        action_list=[PASS, SF],
        numofplayers=[12, 8, 10, 9],
        tracker_history=[_hist(0, TWT_T), _hist(1, TWT_J)],
    )
    EndgamePreprocessor().preprocess(gs)
    rec = EndgameDecider()._q1_block_enemy(
        gs, gs["actionList"], gs["_endgame_context"],
    )
    assert rec is not None
    idx, act = rec
    assert act[0] == "PASS", f"队友领出圈不应 SF 开炸，实际 {act}"


def test_q1_same_type_twt_kept_when_teammate_led():
    """队友领出圈仍有 TWT 可跟 → 跟 TWT，不改 SF。"""
    gs = _q1_gs(
        action_list=[PASS, ["ThreeWithTwo", "Q", ["SQ", "HQ", "CQ", "D4", "C4"]], SF],
        numofplayers=[12, 8, 10, 9],
        tracker_history=[_hist(0, TWT_T), _hist(1, TWT_J)],
    )
    EndgamePreprocessor().preprocess(gs)
    rec = EndgameDecider()._q1_block_enemy(
        gs, gs["actionList"], gs["_endgame_context"],
    )
    assert rec is not None
    idx, act = rec
    assert act[0] != "StraightFlush"
    assert act[0] != "Bomb"
