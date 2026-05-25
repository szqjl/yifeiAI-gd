# -*- coding: utf-8 -*-
"""GUA-022 / GUA-014 决策层回归测试（重建）"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from communication.game_recorder import sync_pass_counters
from decision.stage_router import BasePhaseHandler
from decision.phase_handlers import OpeningPassiveHandler
from decision.strategy_engine import TeammateProtectionStrategy, OpponentSprintWhenTeammateLeadsRule
from decision.enhanced_priority_system import EnhancedPrioritySystem


class _ContextProbeHandler(BasePhaseHandler):
    """仅用于探测 _build_context 的轻量处理器"""

    def handle(self, message):
        return 0


@pytest.fixture
def minimal_config():
    return {"use_enhanced_priority": False, "use_enhanced_collaboration": False}


def test_sync_pass_counters_global_and_self():
    p, mp = sync_pass_counters(0, 0, ["PASS"], 1, 0)
    assert p == 1 and mp == 0

    p, mp = sync_pass_counters(p, mp, ["PASS"], 0, 0)
    assert p == 2 and mp == 1

    p, mp = sync_pass_counters(p, mp, ["Single", "5", ["S5"]], 0, 0)
    assert p == 0 and mp == 0


def test_build_context_lalala_fields(minimal_config):
    handler = _ContextProbeHandler(minimal_config)
    message = {
        "handCards": ["S3"] * 20,
        "myPos": 0,
        "curRank": "2",
        "greaterPos": 2,
        "pass_num": 3,
        "my_pass_num": 1,
        "publicInfo": [
            {"rest": 20}, {"rest": 4}, {"rest": 8}, {"rest": 15},
        ],
        "curAction": ["Single", "5", ["S5"]],
    }
    ctx = handler._build_context(message)
    assert ctx["pass_num"] == 3
    assert ctx["my_pass_num"] == 1
    assert ctx["numofnext"] == 4
    assert ctx["numofpre"] == 15
    assert ctx["numoffri"] == 8
    assert ctx["numofgreaterPos"] == 8
    assert ctx["greater_pos"] == 2


def test_opponent_sprint_reduces_protection():
    rule = OpponentSprintWhenTeammateLeadsRule()
    message = {"greaterPos": 2, "myPos": 0}
    context = {"cards_left": {0: 15, 1: 4, 2: 12, 3: 20}}
    assert rule.evaluate(message, context) < 0


def test_full_protect_false_when_numofnext_le_4():
    strategy = TeammateProtectionStrategy({})
    message = {"myPos": 0, "curAction": ["Single", "K", ["SK"]]}
    context = {
        "cards_left": {0: 15, 1: 3, 2: 10, 3: 20},
        "numofnext": 3,
        "game_phase": "mid_early",
    }
    assert strategy._should_full_protect(message, context) is False


def test_choose_bomb_picks_smallest(minimal_config):
    handler = OpeningPassiveHandler(minimal_config)
    card_val = {"5": 5, "K": 13, "2": 15, "R": 17, "B": 16}
    small = ["Bomb", "5", ["S5", "H5", "D5", "C5"]]
    big = ["Bomb", "K", ["SK", "HK", "DK", "CK"]]
    action_list = [["PASS"], small, big]
    idx = handler._choose_bomb(
        [(1, small), (2, big)],
        handcards=["S5", "H5", "D5", "C5", "SK", "HK", "DK", "CK"],
        sorted_cards={"Bomb": []},
        bomb_info={},
        rank_card="H2",
        card_val=card_val,
        action_list=action_list,
    )
    assert idx == 1


def test_gua014_two_trips_preferred_over_trips_when_complex_kept():
    eps = EnhancedPrioritySystem({})
    context = {
        "handcards": ["S4", "H4", "D4", "C4", "S5", "H5", "D5"],
        "scan_result": {"complex_types": {"TwoTrips": [["S4", "H4", "D4", "S5", "H5", "D5"]]}},
        "game_phase": "opening",
        "is_active": True,
    }
    two_trips = ["TwoTrips", "4", ["S4", "H4", "D4", "S5", "H5", "D5"]]
    trips = ["Trips", "4", ["S4", "H4", "D4"]]
    score_tt = eps._calculate_hand_structure_factor(two_trips, {}, context)
    score_t = eps._calculate_hand_structure_factor(trips, {}, context)
    assert score_tt > score_t


def test_opening_passive_default_non_pass(minimal_config):
    handler = OpeningPassiveHandler(minimal_config)
    action_list = [["PASS"], ["Single", "5", ["S5"]], ["Pair", "6", ["S6", "H6"]]]
    idx = handler._default_passive_action(action_list, {"handCards": ["S5", "S6", "H6"]})
    assert idx != 0
