# -*- coding: utf-8 -*-
"""MemoryTracker 贡牌/抗贡算王（04_calculation_skills §二.1 + 06_game_flow）。"""

import pytest

from src.v.nn.features.memory_tracker import MemoryTracker


def _tracker(my_pos=0, hand=None):
    t = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    t.init_from_hand(hand or [])
    t.set_level_rank("2")
    return t


class TestAntiTribute:
    def test_single_anti_pos_both_hr(self):
        """抗贡：单席双 HR。"""
        t = _tracker(my_pos=0)
        t.record_anti_tribute([3])
        hr = t.get_joker_tracking()["HR"]
        assert hr["with_opponents"] == 2
        assert hr["unknown"] == 0
        assert hr["played"] == 0

    def test_two_anti_pos_split_hr(self):
        """抗贡：两席各持 1 HR（共 2 张大王）。"""
        t = _tracker(my_pos=0)
        t.record_anti_tribute([1, 3])
        hr = t.get_joker_tracking()["HR"]
        assert hr["with_opponents"] == 2
        assert hr["unknown"] == 0


class TestTributeTransfer:
    def test_tribute_hr_not_marked_played(self):
        """进贡 HR 是转移，不是打出。"""
        t = _tracker(my_pos=1)
        t.record_tribute_transfer(3, 0, "HR")
        hr = t.get_joker_tracking()["HR"]
        assert hr["played"] == 0
        assert hr["with_opponents"] == 1

    def test_tribute_to_teammate_marks_partner_side(self):
        t = _tracker(my_pos=0)
        t.record_tribute_transfer(3, 2, "HR")
        hr = t.get_joker_tracking()["HR"]
        assert hr["played"] == 0
        assert hr["with_teammate"] == 1

    def test_tribute_from_my_hand_to_opponent(self):
        t = _tracker(my_pos=3, hand=["HR", "S2"])
        t.sync_my_jokers(["HR", "S2"])
        t.record_tribute_transfer(3, 0, "HR")
        hr = t.get_joker_tracking()["HR"]
        assert hr["in_my_hand"] == 0
        assert hr["with_opponents"] == 1
        assert hr["played"] == 0

    def test_tribute_outgoing_does_not_mark_played(self):
        t = _tracker(my_pos=3, hand=["HR"])
        t.sync_my_jokers(["HR"])
        t.record_play(3, ["tribute", "tribute", ["HR"]])
        hr = t.get_joker_tracking()["HR"]
        assert hr["played"] == 0


class TestTributeRules:
    def test_double_tribute_level_cards_all_jokers_with_receivers(self):
        """双进贡都是级牌 → 四王在吃贡方（头游/二游一侧）。"""
        t = _tracker(my_pos=0)
        t.set_level_rank("2")
        t.sync_tribute_phase_from_state(
            tribute_result=[[3, 0, "S2"], [1, 2, "H2"]],
            cur_rank="2",
        )
        hr = t.get_joker_tracking()["HR"]
        sb = t.get_joker_tracking()["SB"]
        for jt in (hr, sb):
            located = jt["in_my_hand"] + jt["with_teammate"] + jt["with_opponents"]
            assert located == 2
            assert jt["unknown"] == 0

    def test_single_tribute_hr_distribution(self):
        """单贡末游贡 HR → 三游无王时 HR 不在我手，SB/HR 按上下游分布。"""
        t = _tracker(my_pos=1, hand=[])
        t.sync_my_jokers([])
        t.sync_tribute_phase_from_state(
            tribute_result=[[3, 0, "HR"]],
            cur_rank="2",
        )
        hr = t.get_joker_tracking()["HR"]
        sb = t.get_joker_tracking()["SB"]
        hr_located = hr["in_my_hand"] + hr["with_teammate"] + hr["with_opponents"]
        assert hr_located >= 1
        assert sb["in_my_hand"] + sb["with_teammate"] + sb["with_opponents"] >= 1
        assert hr["in_my_hand"] == 0
        assert sb["in_my_hand"] == 0

    def test_sync_from_game_state_dedup(self):
        t = _tracker()
        payload = [[3, 0, "HR"]]
        t.sync_tribute_phase_from_state(tribute_result=payload, cur_rank="2")
        hr1 = t.get_joker_tracking()["HR"]["with_opponents"]
        t.sync_tribute_phase_from_state(tribute_result=payload, cur_rank="2")
        hr2 = t.get_joker_tracking()["HR"]["with_opponents"]
        assert hr1 == hr2


class TestPlayHeuristics:
    def test_hr_pair_implies_sb_remaining(self):
        t = _tracker(my_pos=0)
        t.record_play(1, ["Pair", "HR", ["HR", "HR"]])
        sb = t.get_joker_tracking()["SB"]
        assert sb["with_opponents"] >= 1

    def test_hr_then_sb_implies_sb_pair(self):
        t = _tracker(my_pos=0)
        t.record_play(1, ["Single", "HR", ["HR"]])
        t.record_play(1, ["Single", "SB", ["SB"]])
        sb = t.get_joker_tracking()["SB"]
        assert sb["played"] == 1
        assert sb["with_opponents"] == 1
        assert sb["unknown"] == 0
