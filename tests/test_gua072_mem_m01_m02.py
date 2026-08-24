# -*- coding: utf-8 -*-
"""GUA-072 续：MEM-M01 大牌外出 + MEM-M02 同型压制。

设计真源：docs/knowledge/skills/04_common_skills/05_memory_skills.md §一；
PRINCIPLES_MAPPING.md §十五 MEM-M01/M02。
"""

import pytest

from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.features.rule_card_counter import RuleCardCounter
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_tracker(my_pos=0):
    t = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    t.init_from_hand([])
    return t


def _play(tracker, seat, cards):
    tracker.record_play(seat, [cards[0], "?", cards])


def _play_both_copies(tracker, card_type, seat_a=0, seat_b=1):
    _play(tracker, seat_a, [card_type])
    _play(tracker, seat_b, [card_type])


def _deplete_all_but_one_a_copy(tracker):
    """8~Q 全出；A 仅留 1 张 UNKNOWN；王全出（对子不受王干扰）。"""
    for rank in ["8", "9", "T", "J", "Q"]:
        for suit in ["S", "H", "D", "C"]:
            _play_both_copies(tracker, f"{suit}{rank}")
    for suit in ["S", "H", "D", "C"]:
        ct = f"{suit}A"
        _play(tracker, 0, [ct])
        _play(tracker, 1, [ct])
    tracker.card_state["SA"][1] = MemoryTracker.UNKNOWN
    _play_both_copies(tracker, "HR")
    _play_both_copies(tracker, "SB")


class TestMemM01HighCardSignal:
    """MEM-M01：王/级/A/K 外出计数。"""

    def test_high_card_signal_empty(self):
        t = _make_tracker()
        t.set_level_rank("3")
        c = RuleCardCounter(t)
        sig = c.get_high_card_signal()
        assert sig["hr_played"] == 0
        assert sig["sb_played"] == 0
        assert sig["level_rank"] == "3"
        assert sig["a_outside"] == 8
        assert sig["k_outside"] == 8
        assert sig["high_card_outside_total"] >= 12

    def test_high_card_signal_a_depleted(self):
        t = _make_tracker()
        for suit in ["S", "H", "D", "C"]:
            _play_both_copies(t, f"{suit}A")
        c = RuleCardCounter(t)
        sig = c.get_high_card_signal()
        assert sig["a_depleted"] is True
        assert sig["a_outside"] == 0

    def test_belief_includes_high_card_signal(self):
        t = _make_tracker()
        c = RuleCardCounter(t)
        b = c.get_belief()
        assert "high_card_signal" in b
        assert b["high_card_signal"]["k_outside"] == 8


class TestMemM02BombProfile:
    """MEM-M02：逐席炸弹档案。"""

    def test_bomb_profile_from_history(self):
        t = _make_tracker()
        cards = ["S8", "H8", "D8", "C8"]
        t.record_play(1, ["Bomb", "8", cards])
        c = RuleCardCounter(t)
        stats = c.get_bomb_stats()
        assert stats["has_played_bomb"][1] is True
        assert stats["has_played_bomb"][3] is False
        assert stats["max_bomb_rank_by_seat"][1] == "8"
        assert stats["max_bomb_size_by_seat"][1] == 4

    def test_bomb_profile_straight_flush_beats_bomb(self):
        t = _make_tracker()
        t.record_play(3, ["Bomb", "9", ["S9", "H9", "D9", "C9"]])
        sf = ["S5", "S6", "S7", "S8", "S9"]
        t.record_play(3, ["StraightFlush", "9", sf])
        c = RuleCardCounter(t)
        stats = c.get_bomb_stats()
        assert stats["max_bomb_size_by_seat"][3] == 5
        assert stats["max_bomb_rank_by_seat"][3] == "9"


class TestMemM02FormType:
    """MEM-M02：can_opponent_form_type 同型压制。"""

    def test_pair_needs_two_copies_not_one(self):
        t = _make_tracker(my_pos=0)
        _deplete_all_but_one_a_copy(t)
        c = RuleCardCounter(t)
        assert c.can_opponent_suppress(1, "K") is True
        assert c.can_opponent_form_type(1, "Pair", "K") is False
        assert c.can_opponent_form_type(1, "Single", "K") is True

    def test_type_weakness_blocks_form_type(self):
        t = _make_tracker(my_pos=0)
        t.record_pass(1, "Pair")
        t.record_pass(1, "Pair")
        c = RuleCardCounter(t)
        assert c.can_opponent_form_type(1, "Pair", "5") is False

    def test_hand_count_too_low_blocks_form_type(self):
        t = _make_tracker(my_pos=0)
        t.hand_counts[1] = 1
        c = RuleCardCounter(t)
        assert c.can_opponent_form_type(1, "Pair", "5") is False

    def test_belief_can_opp_form_type_current(self):
        t = _make_tracker(my_pos=0)
        _deplete_all_but_one_a_copy(t)
        gs = {
            "myPos": 0,
            "greaterPos": 1,
            "greaterAction": ["Pair", "K", ["SK", "HK"]],
        }
        c = RuleCardCounter(t)
        b = c.get_belief(gs)
        assert b["can_opp_suppress_current"] is True
        assert b["can_opp_form_type_current"] is False


class TestMemM02P0aGateUpgrade:
    """P0a 门控升级：Pair 场景用同型判断。"""

    def test_p0a_allows_pair_press_when_only_one_a_outside(self):
        hand = [
            "SA", "HA", "D3", "D4", "D5", "D6", "D7",
            "C3", "C4", "C5", "C6", "C7", "C8",
            "S3", "S4", "S5", "S6", "S7",
        ]
        tracker = _make_tracker()
        _deplete_all_but_one_a_copy(tracker)
        tracker.hand_counts[3] = 15

        rest = [c for c in hand if c not in ("SA", "HA")]
        engine = UltimateWinRateEngineV7(player_id=0)
        engine._card_mask = {
            c: (0 if c in ("SA", "HA") else -1, 0.0, 2 if c in ("SA", "HA") else 1)
            for c in hand
        }
        engine._group_type_map = {0: "pair"}
        engine._group_members = {0: ["SA", "HA"], -1: rest}
        engine._tracker = tracker

        state = {
            "myPos": 0,
            "greaterPos": 3,
            "greaterAction": ["Pair", "K", ["SK", "HK"]],
            "handCards": hand,
            "curRank": "A",
            "numofplayers": [len(hand), 27, 27, 15],
        }
        engine._inject_belief_vector(state)
        counter = RuleCardCounter(tracker)
        assert counter.can_opponent_form_type(3, "Pair", "K", state) is False

        rec = engine._recommend_min_press_impl(
            state,
            engine._card_mask,
            state["greaterAction"],
            "Pair",
            hand,
            "A",
        )
        assert rec is not None, "M02：仅 1 张 A 外出时 Pair/K 跟压应放行"
        assert rec["type"] == "Pair"
        assert rec["rank"] == "A"
