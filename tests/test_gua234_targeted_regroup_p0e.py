# -*- coding: utf-8 -*-
"""GUA-234 阶段 E：针对性重组 + 残手地板。"""

import pytest

from src.v.nn.dynamic_regroup import (
    check_regroup_exemption,
    collect_regroup_target_types,
    filter_regroup_candidate,
)
from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.features.rule_card_counter import RuleCardCounter
from src.v.nn.residual_hand_quality import evaluate_after_counter_action
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_tracker():
    t = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
    t.init_from_hand([])
    return t


def test_collect_regroup_targets_merges_opponent_and_feed_p():
    state = {
        "_mid_feed_P": ["Pair"],
        "_mid_feed_snapshot": {"opponent_consecutive": {"Straight": 2}},
    }
    targets = collect_regroup_target_types(state, "Straight")
    assert "Straight" in targets
    assert "ThreeWithTwo" in targets
    assert "Pair" in targets


def test_filter_regroup_veto_waste_residual():
    """§8.5 锚点 ①：压完残手废牌多 → 过滤。"""
    residual_cards = ["H3", "D3", "S5", "C5", "H6", "D7", "S8", "C9", "H9"]
    straight = ["CT", "DT", "HJ", "DJ", "HQ"]
    hand = residual_cards + straight
    residual = evaluate_after_counter_action(hand, straight, "2")
    assert residual.residual_floor_veto is True

    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = {c: (-1, 0.0, 1) for c in hand}
    engine._group_type_map = {}
    engine._group_members = {-1: hand}
    state = {
        "myPos": 0,
        "greaterPos": 3,
        "numofplayers": [27, 27, 27, 27],
        "curRank": "2",
    }
    rec = {"type": "Straight", "rank": "T", "cards": straight}
    ok, reason = filter_regroup_candidate(engine, state, rec, hand, "2")
    assert ok is False
    assert reason.startswith("residual_")


def test_filter_regroup_exempt_enemy_sprint_e2():
    """§8.5 锚点 ③：敌 rest≤5 + 无反压 → E2 豁免。"""
    residual_cards = ["H3", "D3", "S5", "C5", "H6", "D7", "S8", "C9", "H9"]
    straight = ["CT", "DT", "HJ", "DJ", "HQ"]
    hand = residual_cards + straight
    residual = evaluate_after_counter_action(hand, straight, "2")
    assert residual.residual_floor_veto

    engine = UltimateWinRateEngineV7(player_id=0)
    tracker = _make_tracker()
    for rank in ["8", "9", "T", "J", "Q", "K", "A"]:
        for suit in ["S", "H", "D", "C"]:
            tracker.record_play(0, [f"{suit}{rank}", "?", [f"{suit}{rank}"]])
            tracker.record_play(1, [f"{suit}{rank}", "?", [f"{suit}{rank}"]])
    tracker.record_play(0, ["HR", "?", ["HR"]])
    tracker.record_play(1, ["HR", "?", ["HR"]])
    tracker.record_play(0, ["SB", "?", ["SB"]])
    tracker.record_play(1, ["SB", "?", ["SB"]])
    engine._tracker = tracker
    engine._card_mask = {c: (-1, 0.0, 1) for c in hand}
    engine._group_type_map = {}
    engine._group_members = {-1: hand}

    state = {
        "myPos": 0,
        "greaterPos": 3,
        "numofplayers": [27, 27, 27, 4],
        "curRank": "2",
    }
    engine._inject_belief_vector(state)
    counter = RuleCardCounter(tracker)
    assert counter.can_opponent_suppress(3, "T") is False

    rec = {"type": "Straight", "rank": "T", "cards": straight}
    exempt = check_regroup_exemption(state, rec, engine, residual)
    assert exempt == "E2"

    ok, reason = filter_regroup_candidate(engine, state, rec, hand, "2")
    assert ok is True
    assert reason == "exempt_E2"


def test_targeted_regroup_press_filters_bad_candidate():
    """集成：废牌残手候选被 regroup 过滤 → None。"""
    hand = [
        "C3", "D3", "H3", "S3", "C4", "D4", "H4", "S4", "C5", "D5", "H5", "S5",
        "C6", "D6", "H6", "S6", "C7", "D7",
        "C9", "H9", "CT", "DT", "HJ", "DJ", "HQ", "SK", "CK",
    ]
    card_mask = {c: (-1, 0.0, 1) for c in hand}
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {}
    engine._group_members = {-1: hand}
    engine._dynamic_regroup_enabled = True
    engine._tracker = _make_tracker()

    state = {
        "myPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Straight", "5", ["C3", "D4", "H5", "S6", "C7"]],
        "handCards": hand,
        "curRank": "2",
        "numofplayers": [27, 27, 27, 27],
        "_mid_feed_snapshot": {"opponent_consecutive": {"Straight": 2}},
    }
    engine._inject_belief_vector(state)
    rec = engine._recommend_targeted_regroup_press(
        state,
        card_mask,
        state["greaterAction"],
        "Straight",
        hand,
        "2",
    )
    # 若无合法候选或全被 floor 否决 → None 亦可
    if rec is not None:
        ok, _ = filter_regroup_candidate(engine, state, rec, hand, "2")
        assert ok is True
