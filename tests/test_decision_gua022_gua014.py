# -*- coding: utf-8 -*-
"""GUA-022 / GUA-014 决策层回归测试（重建）"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from communication.game_recorder import sync_pass_counters
from decision.stage_router import BasePhaseHandler, StageRouter
from decision.intelligent_router import IntelligentStageRouter
from decision.phase_handlers import OpeningPassiveHandler, OpeningActiveHandler
from decision.strategy_engine import (
    TeammateProtectionStrategy,
    TeamOffensiveStrategy,
    OpponentSprintWhenTeammateLeadsRule,
)
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


def test_build_context_team_offensive_fields(minimal_config):
    handler = _ContextProbeHandler(minimal_config)
    message = {
        "handCards": ["SK", "HK", "DK", "CK", "SA", "HA", "DA", "CA"] + ["S3"] * 19,
        "myPos": 2,
        "curRank": "2",
        "greaterPos": 1,
        "pass_num": 1,
        "my_pass_num": 0,
        "publicInfo": [
            {"rest": 25}, {"rest": 4}, {"rest": 25}, {"rest": 20},
        ],
        "curAction": ["Single", "8", ["S8"]],
    }
    ctx = handler._build_context(message)
    assert ctx["team_role"] in ("main_attacker", "balanced", "assist")
    assert ctx["min_opponent_cards"] == 4
    assert ctx["opponent_on_sprint"] is True
    assert ctx["should_seize_control"] is True
    assert "card_power" in ctx


def test_team_offensive_counters_opponent_single():
    strat = TeamOffensiveStrategy({})
    message = {
        "myPos": 2,
        "greaterPos": 1,
        "curRank": "2",
        "curAction": ["Single", "8", ["S8"]],
        "actionList": [["PASS"], ["Single", "T", ["ST"]]],
    }
    context = {
        "game_phase": "opening",
        "team_role": "main_attacker",
        "cur_rank": "2",
        "pass_num": 0,
        "my_pass_num": 0,
        "handcards": ["ST", "S9"],
    }
    assert strat.get_offensive_action(message, context) == 1


def test_protection_none_when_opponent_leads():
    strat = TeammateProtectionStrategy({})
    message = {
        "myPos": 2,
        "greaterPos": 1,
        "curAction": ["Single", "8", ["S8"]],
        "actionList": [["PASS"], ["Single", "T", ["ST"]]],
    }
    context = {
        "cards_left": {0: 25, 1: 25, 2: 25, 3: 25},
        "game_phase": "opening",
        "numofnext": 25,
    }
    assert strat.get_protection_action(message, context) is None


def test_yf2_opening_passive_not_approx_pass(minimal_config):
    """yf2 位：对手控牌且能压时不应 PASS（修复近似问题 PASS）。"""
    handler = OpeningPassiveHandler(minimal_config)
    message = {
        "handCards": ["ST", "S9", "S8", "S7", "S6", "S5", "S4", "S3"] + ["H3"] * 19,
        "myPos": 2,
        "greaterPos": 1,
        "curRank": "2",
        "curAction": ["Single", "8", ["S8"]],
        "publicInfo": [{"rest": 27}] * 4,
        "actionList": [["PASS"], ["Single", "T", ["ST"]]],
        "pass_num": 0,
        "my_pass_num": 0,
    }
    idx = handler.handle(message)
    assert idx == 1


def test_team_offensive_factor_penalizes_pass():
    eps = EnhancedPrioritySystem({})
    ctx = {"should_seize_control": True, "opponent_on_sprint": True, "min_opponent_cards": 4}
    assert eps._calculate_team_offensive_factor(["PASS"], ctx) == 0.0
    assert eps._calculate_team_offensive_factor(["Single", "T", ["ST"]], ctx) > 0.5


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


def test_single_splits_trips_by_rank_not_suit(minimal_config):
    handler = OpeningActiveHandler(minimal_config)
    hand = ["S4", "H4", "D4", "S7"]
    action = ["Single", "4", ["S4"]]
    assert handler._single_splits_trips_or_bomb(hand, action) is True
    assert handler._single_splits_trips_or_bomb(hand, ["Single", "7", ["S7"]]) is False


def test_split_impact_active_split_trips_heavy_penalty():
    eps = EnhancedPrioritySystem({})
    hand = ["S4", "H4", "D4", "S7"]
    context = {
        "handcards": hand,
        "game_phase": "opening",
        "is_passive": False,
        "scan_result": {},
    }
    split = ["Single", "4", ["S4"]]
    clean = ["Single", "7", ["S7"]]
    assert eps._calculate_split_impact_factor(split, context) < eps._calculate_split_impact_factor(clean, context)


def test_opening_passive_joker_before_split_high_pair(minimal_config):
    handler = OpeningPassiveHandler(minimal_config)
    hand = ["SJ", "HJ", "SR", "S5", "H5", "D5"]
    message = {
        "handCards": hand,
        "myPos": 0,
        "greaterPos": 1,
        "curRank": "2",
        "curAction": ["Single", "8", ["S8"]],
        "publicInfo": [{"rest": 20}, {"rest": 20}, {"rest": 20}, {"rest": 20}],
    }
    state = {
        "power": 5,
        "cur_rank": "2",
        "my_rest": 6,
        "teammate_rest_cards": 20,
        "opponent_rest_cards_list": [20, 20, 20, 20],
    }
    action_list = [
        ["PASS"],
        ["Single", "J", ["SJ"]],
        ["Single", "R", ["SR"]],
    ]
    idx = handler._handle_single_passive(message, action_list, state, 1, 0)
    assert idx == 2


def test_is_passive_play_lead_after_pass_is_active(minimal_config):
    router = StageRouter(minimal_config)
    message = {
        "curAction": ["PASS"],
        "curPos": 2,
        "greaterPos": 1,
        "actionList": [["PASS"], ["Single", "5", ["S5"]], ["Pair", "6", ["S6", "H6"]]],
    }
    assert router._is_passive_play(message) is False


def test_opening_passive_lead_after_pass_picks_non_pass(minimal_config):
    handler = OpeningPassiveHandler(minimal_config)
    hand = ["S5", "S6", "H6", "S7", "H7", "D7", "S8", "H8"]
    message = {
        "handCards": hand,
        "myPos": 2,
        "curPos": 1,
        "greaterPos": 0,
        "curRank": "2",
        "curAction": ["PASS"],
        "publicInfo": [{"rest": 20}] * 4,
        "actionList": [["PASS"], ["Single", "5", ["S5"]], ["Pair", "6", ["S6", "H6"]]],
    }
    idx = handler.handle(message)
    assert idx != 0


def test_yf2_teammate_single_excess_before_pass(minimal_config):
    """队友出单时先尝试多余单张顺走，不应提前 PASS。"""
    handler = OpeningPassiveHandler(minimal_config)
    hand = ["S3", "S4", "H5", "D5", "C5", "S6", "H6", "S7"]
    message = {
        "handCards": hand,
        "myPos": 2,
        "greaterPos": 0,
        "curRank": "2",
        "curAction": ["Single", "4", ["S4"]],
        "publicInfo": [{"rest": 20}, {"rest": 20}, {"rest": 20}, {"rest": 20}],
    }
    state = {
        "power": 5,
        "cur_rank": "2",
        "my_rest": 8,
        "teammate_rest_cards": 20,
        "opponent_rest_cards_list": [20, 20, 20, 20],
    }
    action_list = [
        ["PASS"],
        ["Single", "3", ["S3"]],
        ["Single", "6", ["S6"]],
    ]
    idx = handler._handle_single_passive(message, action_list, state, 0, 2)
    assert idx != 0


def test_intelligent_router_cache_does_not_replay_pass(minimal_config):
    """智能路由缓存命中 PASS 时仍须经 coerce，避免近似问题 PASS。"""
    base = StageRouter(minimal_config)
    base.set_handlers({
        "opening_active": OpeningActiveHandler(minimal_config),
        "opening_passive": OpeningPassiveHandler(minimal_config),
    })

    class _AlwaysPassHandler(OpeningPassiveHandler):
        def handle(self, message):
            return 0

    base.handlers["opening_passive"] = _AlwaysPassHandler(minimal_config)
    router = IntelligentStageRouter(minimal_config, base_router=base)
    msg = {
        "stage": "play",
        "myPos": 2,
        "curPos": 1,
        "greaterPos": 1,
        "curRank": "2",
        "curAction": ["Single", "8", ["S8"]],
        "handCards": ["ST", "S9", "S8", "S7", "S6", "S5", "S4", "S3"] + ["H3"] * 19,
        "publicInfo": [{"rest": 27}] * 4,
        "actionList": [["PASS"], ["Single", "T", ["ST"]], ["Single", "9", ["S9"]]],
    }
    first = router.route(msg)
    second = router.route(msg)
    assert first != 0
    assert second != 0
