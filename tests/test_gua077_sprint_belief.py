# -*- coding: utf-8 -*-
"""GUA-077 P0：``get_sprint_belief()`` / MEM-M07 冲刺门控信念骨架。"""

import pytest

from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.features.rule_card_counter import RuleCardCounter
from src.v.nn.features.sprint_belief import SprintBelief


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
    for rank in ["8", "9", "T", "J", "Q"]:
        for suit in ["S", "H", "D", "C"]:
            ct = f"{suit}{rank}"
            _play_both_copies(tracker, ct)
    for suit in ["S", "H", "D", "C"]:
        ct = f"{suit}A"
        _play(tracker, 0, [ct])
        _play(tracker, 1, [ct])
    tracker.card_state["SA"][1] = MemoryTracker.UNKNOWN
    _play_both_copies(tracker, "HR")
    _play_both_copies(tracker, "SB")


class TestSprintBeliefSkeleton:
    def test_returns_sprint_belief_dataclass(self):
        t = _make_tracker()
        belief = RuleCardCounter(t).get_sprint_belief()
        assert isinstance(belief, SprintBelief)
        assert belief.enemy_min_remaining == 27
        assert belief.enemy_any_remaining_eq_1 is False

    def test_field_max_single_when_enemies_cannot_hold(self):
        t = _make_tracker(my_pos=0)
        t.hand_counts[1] = 0
        t.hand_counts[3] = 0
        belief = RuleCardCounter(t).get_sprint_belief(probe_single_candidates=["T", "K"])
        assert belief.my_single_is_field_max["T"] is True
        assert belief.my_single_is_field_max["K"] is True
        assert belief.probe_single_rank == "T"

    def test_single_not_field_max_when_higher_rank_outside(self):
        t = _make_tracker(my_pos=0)
        _deplete_all_but_one_a_copy(t)
        c = RuleCardCounter(t)
        belief = c.get_sprint_belief(probe_single_candidates=["T", "K"])
        assert belief.my_single_is_field_max["K"] is False
        assert belief.probe_single_rank == "T"

    def test_enemy_can_beat_single_per_seat(self):
        t = _make_tracker(my_pos=0)
        _deplete_all_but_one_a_copy(t)
        belief = RuleCardCounter(t).get_sprint_belief(probe_single_candidates=["K"])
        assert belief.enemy_can_beat_single[1]["K"] is True
        assert belief.enemy_can_beat_single[3]["K"] is True

    def test_enemy_min_remaining_from_game_state(self):
        t = _make_tracker(my_pos=0)
        gs = {"numofplayers": [10, 1, 8, 12], "myPos": 0}
        belief = RuleCardCounter(t).get_sprint_belief(game_state=gs)
        assert belief.enemy_min_remaining == 1
        assert belief.enemy_any_remaining_eq_1 is True

    def test_enemy_twt_unlikely_after_pass_weakness(self):
        t = _make_tracker(my_pos=0)
        t.record_pass(1, "ThreeWithTwo")
        t.record_pass(1, "ThreeWithTwo")
        belief = RuleCardCounter(t).get_sprint_belief()
        assert belief.enemy_twt_unlikely[1] is True
        assert belief.enemy_twt_unlikely[3] is False

    def test_any_enemy_can_beat_twt(self):
        t = _make_tracker(my_pos=0)
        t.hand_counts[1] = 10
        t.hand_counts[3] = 10
        c = RuleCardCounter(t)
        belief = c.get_sprint_belief(twt_trip_ranks=["K"])
        assert "K" in belief.any_enemy_can_beat_twt
        assert isinstance(belief.any_enemy_can_beat_twt["K"], bool)

    def test_to_dict_roundtrip_keys(self):
        t = _make_tracker()
        d = RuleCardCounter(t).get_sprint_belief().to_dict()
        assert "my_single_is_field_max" in d
        assert "enemy_can_beat_twt" in d
        assert "enemy_bomb_risk_on_lead" in d

    def test_type_weakness_blocks_twt_form(self):
        t = _make_tracker(my_pos=0)
        for seat in (1, 3):
            t.record_pass(seat, "ThreeWithTwo")
            t.record_pass(seat, "ThreeWithTwo")
        c = RuleCardCounter(t)
        belief = c.get_sprint_belief(twt_trip_ranks=["5"])
        assert belief.enemy_can_beat_twt[3]["5"] is False
        assert belief.enemy_can_beat_twt[1]["5"] is False
        assert belief.any_enemy_can_beat_twt["5"] is False
