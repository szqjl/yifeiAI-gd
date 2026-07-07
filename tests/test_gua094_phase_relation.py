# -*- coding: utf-8 -*-
"""GUA-094: phase relation 最小闭环测试。"""

import logging

import pytest

from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.features.rule_card_counter import RuleCardCounter
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_tracker(my_pos=0):
    tracker = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand([])
    return tracker


class TestRuleCardCounterPhaseRelation:
    def test_enemy_shape_hint_follows_critical_enemy(self):
        tracker = _make_tracker()
        tracker.hand_counts[1] = 2
        tracker.hand_counts[3] = 9
        counter = RuleCardCounter(tracker)

        phase_relation = counter.infer_phase_relation(
            {
                "greaterPos": 1,
                "greaterAction": ["Pair", "K", ["HK", "DK"]],
                "actionList": [["PASS", "PASS", "PASS"]],
            }
        )

        assert phase_relation["critical_enemy_seat"] == 1
        assert phase_relation["enemy_shape_hint"] == "pair_heavy"
        assert phase_relation["enemy_shape_hints"][1] == "pair_heavy"
        assert phase_relation["enemy_bomb_risk_max"] == pytest.approx(1.0)

    def test_teammate_cover_confidence_boosts_on_teammate_bomb_control(self):
        tracker = _make_tracker()
        tracker.hand_counts[2] = 2
        counter = RuleCardCounter(tracker)

        phase_relation = counter.infer_phase_relation(
            {
                "greaterPos": 2,
                "greaterAction": ["Bomb", "8", ["S8", "H8", "D8", "C8"]],
                "actionList": [["PASS", "PASS", "PASS"]],
            }
        )

        assert phase_relation["teammate_cover_confidence"] == pytest.approx(1.0)
        assert phase_relation["same_type_suppressor_outside"] is False

    def test_same_type_suppressor_outside_uses_current_legal_beater(self):
        tracker = _make_tracker()
        counter = RuleCardCounter(tracker)

        phase_relation = counter.infer_phase_relation(
            {
                "greaterPos": 1,
                "greaterAction": ["Single", "9", ["H9"]],
                "actionList": [
                    ["PASS", "PASS", "PASS"],
                    ["Single", "K", ["HK"]],
                    ["Pair", "3", ["S3", "H3"]],
                ],
            }
        )

        assert phase_relation["same_type_suppressor_outside"] is True

    def test_rear_teammate_single_cover_confidence_rises_on_enemy_out_single(self):
        tracker = _make_tracker(my_pos=2)
        tracker.hand_counts[0] = 12
        tracker.hand_counts[1] = 0
        tracker.hand_counts[2] = 17
        tracker.hand_counts[3] = 12
        counter = RuleCardCounter(tracker)

        phase_relation = counter.infer_phase_relation(
            {
                "greaterPos": 1,
                "greaterAction": ["Single", "3", ["D3"]],
                "actionList": [
                    ["PASS", "PASS", "PASS"],
                    ["Bomb", "9", ["S9", "S9", "H9", "D9"]],
                ],
            }
        )

        assert phase_relation["teammate_rear_single_cover_confidence"] > 0.9


class TestUltimateWinRateEnginePhaseRelationInject:
    def test_engine_injects_phase_relation_to_game_state(self):
        engine = UltimateWinRateEngineV7(player_id=0)
        tracker = _make_tracker()
        tracker.hand_counts[1] = 5
        tracker.hand_counts[2] = 3
        engine._tracker = tracker

        game_state = {
            "greaterPos": 1,
            "greaterAction": ["Single", "T", ["HT"]],
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Single", "K", ["HK"]],
            ],
        }

        engine._inject_phase_relation(game_state)

        assert "_phase_relation" in game_state
        assert game_state["_phase_relation"]["critical_enemy_seat"] == 1
        assert game_state["_phase_relation"]["same_type_suppressor_outside"] is True

    def test_engine_injects_sprint_fire_ready_from_grouping_state(self):
        engine = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
        engine.player_id = 0
        engine._tracker = _make_tracker()
        engine._card_mask = {
            "S4": (0, 1.0, 4),
            "H4": (0, 1.0, 4),
            "D4": (0, 1.0, 4),
            "C4": (0, 1.0, 4),
            "S5": (1, 1.0, 4),
            "H5": (1, 1.0, 4),
            "D5": (1, 1.0, 4),
            "C5": (1, 1.0, 4),
            "S7": (2, 0.0, 2),
            "H7": (2, 0.0, 2),
            "HK": (-1, 0.0, 0),
        }
        engine._group_type_map = {0: "Bomb", 1: "Bomb", 2: "pair"}
        engine._group_members = {}
        engine._current_role = "主攻"
        engine.logger = logging.getLogger("test_gua094")

        game_state = {
            "handCards": ["S4", "H4", "D4", "C4", "S5", "H5", "D5", "C5", "S7", "H7", "HK"],
            "greaterPos": 3,
            "greaterAction": ["Single", "9", ["H9"]],
            "actionList": [["PASS", "PASS", "PASS"]],
        }

        engine._inject_phase_relation(game_state)

        assert game_state["_phase_relation"]["sprint_fire_ready"] is True
        assert game_state["_phase_relation"]["bomb_count"] == 2
        assert game_state["_phase_relation"]["natural_turn_count"] == 4
        assert game_state["_phase_relation"]["single_residue"] == 1
