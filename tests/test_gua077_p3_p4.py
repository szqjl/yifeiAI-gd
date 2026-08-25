# -*- coding: utf-8 -*-
"""GUA-077 P3/P4：中局软引导 + 被炸 plan_b 切换。"""

from types import SimpleNamespace

import pytest

from src.v.nn.endgame.sprint_step_picker import try_soft_lead_from_play_sequence
from src.v.nn.features.grouping_engine import (
    GroupingPlan,
    PlayStep,
    _build_plan_b_sequences,
    _plan_play_order,
)
from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


class TestPlanBSequences:
    def test_probe_then_twt_drops_probe(self):
        seq = [
            PlayStep("Single", "4", step_role="probe"),
            PlayStep("ThreeWithTwo", "K"),
        ]
        alts = _build_plan_b_sequences(seq)
        assert len(alts) == 1
        assert alts[0][0].action_type == "ThreeWithTwo"

    def test_bomb_single_plan_b_is_bomb_only(self):
        seq = _plan_play_order(
            GroupingPlan(
                cur_rank="2",
                bombs=[["S8", "H8", "D8", "C8"]],
                singles=["DT"],
            ),
            "2",
        )
        alts = _build_plan_b_sequences(seq)
        assert any(len(a) == 1 and a[0].action_type == "Bomb" for a in alts)


class TestSoftLeadMidgame:
    def test_soft_lead_skips_endgame_hand_size(self):
        engine = SimpleNamespace(_active_plan=GroupingPlan(cur_rank="2", singles=["D4"]))
        gs = {
            "handCards": ["D4"] * 10,
            "_active_play_sequence": [{"action_type": "Single", "target_rank": "4"}],
            "actionList": [["Single", "4", ["D4"]]],
        }
        assert try_soft_lead_from_play_sequence(engine, gs, "2") is None

    def test_soft_lead_matches_twt_in_action_list(self):
        plan = GroupingPlan(
            cur_rank="2",
            three_with_twos=[(["SK", "HK", "DK"], ["S3", "H3"])],
        )
        plan.play_sequence = _plan_play_order(plan, "2")
        engine = SimpleNamespace(
            _active_plan=plan,
            _card_mask={},
            _group_type_map={},
            _group_members={},
        )
        gs = {
            "handCards": ["SK", "HK", "DK", "S3", "H3"] + ["D4"] * 8,
            "_active_play_sequence": [s.to_dict() for s in plan.play_sequence],
            "actionList": [
                ["PASS", "PASS", []],
                ["ThreeWithTwo", "K", ["SK", "HK", "DK", "S3", "H3"]],
            ],
        }
        rec = try_soft_lead_from_play_sequence(engine, gs, "2")
        assert rec is not None
        assert rec["intent"] == "gua077_soft_lead"
        assert rec["type"] == "ThreeWithTwo"


class TestPlanBSwitch:
    def test_detect_and_switch_after_enemy_bomb(self):
        engine = UltimateWinRateEngineV7(player_id=0)
        tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand([])
        tracker.record_play(0, ["Single", "4", ["S4"]])
        tracker.record_play(1, ["Bomb", "9", ["S9", "H9", "D9", "C9"]])
        engine._tracker = tracker

        plan = GroupingPlan(cur_rank="2")
        plan.play_sequence = [
            PlayStep("Single", "4", step_role="probe"),
            PlayStep("ThreeWithTwo", "K"),
        ]
        plan.plan_b_sequences = _build_plan_b_sequences(plan.play_sequence)
        engine._active_plan = plan

        gs = {"myPos": 0, "_play_sequence_plan_b": [
            [s.to_dict() for s in plan.plan_b_sequences[0]]
        ]}
        assert engine._detect_enemy_bombed_after_our_lead(gs) is True
        engine._maybe_switch_play_sequence_plan_b(gs)
        assert gs.get("_gua077_play_sequence_mode") == "plan_b"
        assert gs["_active_play_sequence"][0]["action_type"] == "ThreeWithTwo"
