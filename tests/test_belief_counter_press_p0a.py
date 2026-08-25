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

    def test_gate_allows_natural_press_when_opponent_can_suppress(self):
        """空记牌 + 自然散单：can_form 仅软风险，不硬拦（GUA-274）。"""
        hand = [
            "ST", "D3", "D4", "D5", "D6", "D7", "D8",
            "C3", "C4", "C5", "C6", "C7", "C8",
            "S3", "S4", "S5", "S6", "S7",
        ]
        tracker = _make_tracker()
        engine = _engine_with_single_press(hand, tracker=tracker)
        rec = _min_press(engine, hand)
        assert rec is not None, "P0a：自然散单不得仅因 can_form 硬拦"
        assert rec["cards"][0] == "ST"

    def test_gate_blocks_when_breaks_core_and_can_form(self):
        """拆对核出单 + 对手可反压 → 硬拦（直接测门控；走 card_mask 拆核路径）。"""
        hand = ["ST", "HT", "D3", "D4", "D5"]
        tracker = _make_tracker()
        engine = UltimateWinRateEngineV7(player_id=0)
        engine._card_mask = {
            "ST": (0, 1.0, 2),
            "HT": (0, 1.0, 2),
            "D3": (-1, 0.0, 1),
            "D4": (-1, 0.0, 1),
            "D5": (-1, 0.0, 1),
        }
        engine._group_type_map = {0: "pair"}
        engine._group_members = None  # 走 card_mask is_core 拆核判定
        engine._tracker = tracker
        state = {
            "myPos": 0,
            "greaterPos": 3,
            "curRank": "A",
            "handCards": hand,
            "_belief": {"hand_counts": {0: 18, 3: 15}, "opp_bomb_risks": {}},
        }
        engine._inject_belief_vector(state)
        assert engine._get_broken_core_type(
            ["Single", "T", ["ST"]],
            engine._card_mask,
            engine._group_type_map,
            None,
        ) == "pair"
        assert engine._belief_gate_counter_press(
            state, {"type": "Single", "rank": "T", "cards": ["ST"]}
        ) is True

    def test_gate_allows_loose_pair_j_vs_pair_t(self):
        """match 6a8d3d40：loose JJ 压 Pair/T，不得因 can_form 硬拦。"""
        hand = [
            "SJ", "HJ", "HQ", "SQ", "C2", "S2",
            "D3", "D3", "C3", "S3",
            "C4", "C4", "S4", "H4",
            "H6", "D7", "D8", "H9", "DT",
            "SK", "DA", "SB",
        ]
        tracker = _make_tracker(my_pos=2)
        engine = UltimateWinRateEngineV7(player_id=2)
        engine._card_mask = {
            "SJ": (3, 0.0, 2), "HJ": (3, 0.0, 2),
            "HQ": (4, 0.0, 2), "SQ": (4, 0.0, 2),
            "C2": (5, 0.0, 2), "S2": (5, 0.0, 2),
            "D3": (0, 1.0, 4), "C3": (0, 1.0, 4), "S3": (0, 1.0, 4),
            "C4": (1, 1.0, 4), "S4": (1, 1.0, 4), "H4": (1, 1.0, 4),
            "H6": (2, 1.0, 5), "D7": (2, 1.0, 5), "D8": (2, 1.0, 5),
            "H9": (2, 1.0, 5), "DT": (2, 1.0, 5),
            "SK": (-1, 0.0, 1), "DA": (-1, 0.0, 1), "SB": (-1, 0.0, 1),
        }
        # 第二枚 D3 / C4 需同 gid
        engine._card_mask["D3"] = (0, 1.0, 4)
        engine._group_type_map = {
            0: "Bomb", 1: "Bomb", 2: "straight",
            3: "pair", 4: "pair", 5: "pair",
        }
        engine._group_members = {
            0: ["D3", "D3", "C3", "S3"],
            1: ["C4", "C4", "S4", "H4"],
            2: ["H6", "D7", "D8", "H9", "DT"],
            3: ["SJ", "HJ"],
            4: ["HQ", "SQ"],
            5: ["C2", "S2"],
            -1: ["SK", "DA", "SB"],
        }
        engine._tracker = tracker
        state = {
            "myPos": 2,
            "greaterPos": 1,
            "greaterAction": ["Pair", "T", ["ST", "HT"]],
            "handCards": hand,
            "curRank": "2",
            "numofplayers": [20, 20, len(hand), 20],
        }
        engine._inject_belief_vector(state)
        rec = engine._recommend_min_press_impl(
            state,
            engine._card_mask,
            state["greaterAction"],
            "Pair",
            hand,
            "2",
        )
        assert rec is not None, "GUA-274：loose Pair/J 不得被 P0a 硬拦"
        assert rec["type"] == "Pair"
        assert rec["rank"] == "J"

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
