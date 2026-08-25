# -*- coding: utf-8 -*-
"""GUA-077 P2：SprintStepPicker 记忆门控改序。"""

from src.v.nn.endgame.sprint_step_picker import (
    SprintStepPicker,
    _apply_belief_reorder,
)
from src.v.nn.features.sprint_belief import SprintBelief


def _seq(single_rank: str, twt_rank: str):
    return [
        {"action_type": "Single", "target_rank": single_rank, "step_role": "probe"},
        {"action_type": "ThreeWithTwo", "target_rank": twt_rank},
    ]


class TestBeliefReorder:
    def test_enemy_one_leads_twt(self):
        belief = SprintBelief(enemy_any_remaining_eq_1=True)
        out = _apply_belief_reorder(_seq("4", "K"), belief)
        assert out[0]["action_type"] == "ThreeWithTwo"

    def test_twt_weakness_leads_twt(self):
        belief = SprintBelief(enemy_twt_unlikely={1: True, 3: False})
        out = _apply_belief_reorder(_seq("4", "K"), belief)
        assert out[0]["action_type"] == "ThreeWithTwo"

    def test_field_max_single_first(self):
        belief = SprintBelief(my_single_is_field_max={"4": True})
        out = _apply_belief_reorder(_seq("4", "K"), belief)
        assert out[0]["action_type"] == "Single"

    def test_single_not_max_twt_safe(self):
        belief = SprintBelief(
            my_single_is_field_max={"4": False},
            any_enemy_can_beat_twt={"K": False},
        )
        out = _apply_belief_reorder(_seq("4", "K"), belief)
        assert out[0]["action_type"] == "ThreeWithTwo"


class TestSprintStepPickerMatch:
    def test_picks_first_step_from_action_list(self):
        picker = SprintStepPicker()
        play_seq = [{"action_type": "ThreeWithTwo", "target_rank": "K"}]
        action_list = [
            ["PASS", "PASS", []],
            ["ThreeWithTwo", "K", ["SK", "HK", "DK", "S3", "H3"]],
        ]
        hit = picker.pick_lead_step(
            {"curRank": "2"},
            play_seq,
            None,
            action_list,
        )
        assert hit == (1, action_list[1])

    def test_belief_reorder_before_match(self):
        picker = SprintStepPicker()
        play_seq = _seq("4", "K")
        action_list = [
            ["ThreeWithTwo", "K", ["SK", "HK", "DK", "S4", "H4"]],
            ["Single", "4", ["S4"]],
        ]
        belief = SprintBelief(enemy_any_remaining_eq_1=True)
        hit = picker.pick_lead_step(
            {"curRank": "2"},
            play_seq,
            belief,
            action_list,
        )
        assert hit[0] == 0
        assert hit[1][0] == "ThreeWithTwo"
