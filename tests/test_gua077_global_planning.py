# -*- coding: utf-8 -*-
"""GUA-077 P1：GroupingPlan.play_sequence / _plan_play_order。"""

from src.v.nn.features.grouping_engine import (
    GroupingPlan,
    PlayStep,
    _plan_play_order,
    enumerate_groupings,
)


class TestPlanPlayOrder:
    def test_advanced_01_two_twt_chain(self):
        """advanced_01：10 张两手三带二（333+22 → AAA+66）。"""
        plan = GroupingPlan(
            cur_rank="2",
            three_with_twos=[
                (["S3", "H3", "D3"], ["S2", "H2"]),
                (["SA", "HA", "DA"], ["S6", "H6"]),
            ],
        )
        seq = _plan_play_order(plan, "2")
        assert len(seq) == 2
        assert all(s.action_type == "ThreeWithTwo" for s in seq)
        assert seq[0].target_rank == "3"
        assert seq[1].target_rank == "A"

    def test_advanced_05_three_twt_chain(self):
        """advanced_05：11 张三手连环三带二。"""
        plan = GroupingPlan(
            cur_rank="2",
            three_with_twos=[
                (["S5", "H5", "D5"], ["S4", "H4"]),
                (["S8", "H8", "D8"], ["S7", "H7"]),
                (["SK", "HK", "DK"], ["SQ", "HQ"]),
            ],
        )
        seq = _plan_play_order(plan, "2")
        assert len(seq) == 3
        assert [s.target_rank for s in seq] == ["5", "8", "K"]

    def test_steel_before_twt(self):
        plan = GroupingPlan(
            cur_rank="2",
            steel_plates=[[["S6", "H6", "D6"], ["S7", "H7", "D7"]]],
            three_with_twos=[(["S9", "H9", "D9"], ["S3", "H3"])],
        )
        seq = _plan_play_order(plan, "2")
        assert seq[0].action_type == "TwoTrips"
        assert seq[1].action_type == "ThreeWithTwo"

    def test_bomb_plus_single_probe_first(self):
        plan = GroupingPlan(
            cur_rank="2",
            bombs=[["S8", "H8", "D8", "C8"]],
            singles=["DT"],
        )
        seq = _plan_play_order(plan, "2")
        assert len(seq) == 2
        assert seq[0].action_type == "Single"
        assert seq[0].step_role == "probe"
        assert seq[1].action_type == "Bomb"

    def test_singles_marked_probe(self):
        plan = GroupingPlan(cur_rank="2", singles=["D4", "DT", "HA"])
        seq = _plan_play_order(plan, "2")
        assert len(seq) == 3
        assert all(s.step_role == "probe" for s in seq)
        assert seq[0].target_rank == "4"

    def test_enumerate_groupings_attaches_sequence(self):
        hand = ["S3", "H3", "D3", "S2", "H2", "SA", "HA", "DA", "S6", "H6"]
        best, plans = enumerate_groupings(hand, "2")
        assert len(best.play_sequence) >= 1
        assert all(isinstance(s, PlayStep) for s in best.play_sequence)
        assert plans[0].play_sequence
