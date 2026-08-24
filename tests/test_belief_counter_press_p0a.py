# -*- coding: utf-8 -*-
"""P0a 信念薄切片：跟压路径 can_opponent_suppress 门控。

设计真源：V8-中期压顺灵活性-组牌-动态重组方案.md §3.4 P0a。
"""

import pytest

from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.features.rule_card_counter import RuleCardCounter
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_tracker(my_pos=0):
    tracker = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand([])
    return tracker


def _play_both_copies(tracker, card_type, seat_a=0, seat_b=1):
    tracker.record_play(seat_a, [card_type, "?", [card_type]])
    tracker.record_play(seat_b, [card_type, "?", [card_type]])


def _engine_with_single_press(hand, tracker=None):
    """对手 Single/9，我方有 JT 可压（rank=T）。"""
    card_mask = {c: (-1, 0.0, 1) for c in hand}
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {}
    engine._group_members = {-1: list(hand)}
    engine._current_role = "主攻"
    if tracker is not None:
        engine._tracker = tracker
    return engine


def _state(hand, greater_pos=3, hand_counts=None):
    state = {
        "myPos": 0,
        "greaterPos": greater_pos,
        "greaterAction": ["Single", "9", ["D9"]],
        "handCards": hand,
        "curRank": "A",
    }
    if hand_counts is not None:
        state["_belief"] = {"hand_counts": hand_counts}
    return state


def _min_press(engine, hand, **kw):
    state = _state(hand, **kw)
    engine._inject_belief_vector(state)
    return engine._recommend_min_press_impl(
        state,
        engine._card_mask,
        state["greaterAction"],
        "Single",
        hand,
        "A",
    )


class TestBeliefGateCounterPress:
    """P0a：信念门控跟压 vs PASS。"""

    def test_gate_blocks_when_opponent_can_suppress(self):
        """空记牌 → 对手很可能还能压 T → 拦截跟压。"""
        hand = [
            "ST", "D3", "D4", "D5", "D6", "D7", "D8",
            "C3", "C4", "C5", "C6", "C7", "C8",
            "S3", "S4", "S5", "S6", "S7",
        ]
        tracker = _make_tracker()
        engine = _engine_with_single_press(hand, tracker=tracker)
        rec = _min_press(engine, hand)
        assert rec is None, "P0a：对手可反压 rank=T 时应拦截跟压"

    def test_gate_allows_when_cannot_suppress(self):
        """高牌耗尽 → 对手无法压 7 → 放行跟压。"""
        hand = [
            "S8", "D3", "D4", "D5", "D6", "D7",
            "C3", "C4", "C5", "C6", "C7", "C8",
            "S3", "S4", "S5", "S6", "S7",
        ]
        tracker = _make_tracker()
        for rank in ["8", "9", "T", "J", "Q", "K", "A"]:
            for suit in ["S", "H", "D", "C"]:
                _play_both_copies(tracker, f"{suit}{rank}")
        _play_both_copies(tracker, "HR")
        _play_both_copies(tracker, "SB")
        state = {
            "myPos": 0,
            "greaterPos": 3,
            "greaterAction": ["Single", "6", ["D6"]],
            "handCards": hand,
            "curRank": "A",
        }
        engine = _engine_with_single_press(hand, tracker=tracker)
        engine._inject_belief_vector(state)
        counter = RuleCardCounter(tracker)
        assert counter.can_opponent_suppress(3, "7") is False
        rec = engine._recommend_min_press_impl(
            state,
            engine._card_mask,
            state["greaterAction"],
            "Single",
            hand,
            "A",
        )
        assert rec is not None
        assert rec["type"] == "Single"
        assert rec["rank"] == "7"

    def test_gate_exempt_self_sprint(self):
        """自己 rest≤5 → 残局自救豁免，不因信念拦截。"""
        hand = [
            "ST", "D3", "D4", "D5", "D6",
            "C3", "C4", "C5", "C6", "C7",
            "S3", "S4", "S5", "S6", "S7",
            "S8", "C8", "D8",
        ]
        tracker = _make_tracker()
        tracker.hand_counts[0] = 4
        tracker.hand_counts[3] = 15
        engine = _engine_with_single_press(hand, tracker=tracker)
        rec = _min_press(engine, hand)
        assert rec is not None
        assert rec["cards"][0] == "ST"

    def test_gate_exempt_enemy_sprint(self):
        """控牌对手 rest≤5 → 敌冲刺阻断豁免。"""
        hand = [
            "ST", "D3", "D4", "D5", "D6", "D7", "D8",
            "C3", "C4", "C5", "C6", "C7", "C8",
            "S3", "S4", "S5", "S6", "S7",
        ]
        tracker = _make_tracker()
        tracker.hand_counts[0] = 18
        tracker.hand_counts[3] = 4
        engine = _engine_with_single_press(hand, tracker=tracker)
        rec = _min_press(engine, hand)
        assert rec is not None
        assert rec["cards"][0] == "ST"

    def test_gate_skipped_without_tracker(self):
        """无 tracker → 不门控，保持原跟压行为。"""
        hand = [
            "ST", "D3", "D4", "D5", "D6", "D7", "D8",
            "C3", "C4", "C5", "C6", "C7", "C8",
            "S3", "S4", "S5", "S6", "S7",
        ]
        engine = _engine_with_single_press(hand, tracker=None)
        rec = _min_press(engine, hand)
        assert rec is not None
        assert rec["cards"][0] == "ST"

    def test_belief_gate_direct_teammate_skip(self):
        """队友控牌 → 不门控。"""
        engine = UltimateWinRateEngineV7(player_id=0)
        tracker = _make_tracker()
        engine._tracker = tracker
        rec = {"type": "Single", "rank": "T", "cards": ["ST"]}
        state = {"myPos": 0, "greaterPos": 2, "curRank": "A"}
        engine._inject_belief_vector(state)
        assert engine._belief_gate_counter_press(state, rec) is False
