# -*- coding: utf-8 -*-
"""GUA-022 / GUA-014：共用决策层单元测试（不启动对局）。"""
import pytest

from src.decision.strategy_engine import (
    TeammateProtectionStrategy,
    OpponentSprintWhenTeammateLeadsRule,
)


def test_opponent_sprint_rule_reduces_protect_when_opponent_low_and_teammate_leading():
    rule = OpponentSprintWhenTeammateLeadsRule()
    # 座位 0，队友为 2；当前最大为队友 2
    message = {"greaterPos": 2, "myPos": 0}
    context = {
        "cards_left": {0: 20, 1: 5, 2: 12, 3: 18},
    }
    assert rule.evaluate(message, context) < 0


def test_opponent_sprint_rule_neutral_when_opponent_not_threat():
    rule = OpponentSprintWhenTeammateLeadsRule()
    message = {"greaterPos": 2, "myPos": 0}
    context = {
        "cards_left": {0: 20, 1: 18, 2: 12, 3: 18},
    }
    assert rule.evaluate(message, context) == 0.0


def test_teammate_protection_default_threshold_raised():
    strat = TeammateProtectionStrategy({})
    assert strat.config.get("protection_threshold", 2.25) >= 2.2


def test_dynamic_threshold_opening_stricter_than_base():
    strat = TeammateProtectionStrategy({})
    message = {}
    context = {"game_phase": "opening"}
    t = strat._get_dynamic_threshold(message, context)
    assert t >= 2.25 * 1.1


def test_should_not_full_protect_when_opponent_sprinting():
    strat = TeammateProtectionStrategy({})
    message = {"myPos": 0, "curAction": ["Single", "9", ["H9"]]}
    context = {
        "cards_left": {0: 12, 1: 3, 2: 9, 3: 13},
    }
    assert strat._should_full_protect(message, context) is False


def test_find_minimal_action_prefers_non_bomb():
    strat = TeammateProtectionStrategy({})
    message = {
        "curAction": ["Single", "8", ["H8"]],
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Bomb", "T", ["ST", "HT", "CT", "DT"]],
            ["Single", "9", ["S9"]],
        ],
    }
    idx = strat._find_minimal_action(message, {"cur_rank": "2"})
    assert idx == 2


def test_trips_downrank_when_complex_types_present():
    from src.decision.enhanced_priority_system import EnhancedPrioritySystem

    eps = EnhancedPrioritySystem(
        {"use_enhanced_priority": True},
        base_priority_system=None,
    )
    cand = ["Trips", "9", [["S9", "C9", "D9"]]]
    context = {
        "handcards": ["S9", "C9", "D9", "H5"],
        "scan_result": {"complex_types": {"TwoTrips": ["dummy"]}},
        "game_phase": "opening",
    }
    score_with = eps._calculate_hand_structure_factor(cand, {}, context)
    context2 = {**context, "scan_result": {}}
    score_without = eps._calculate_hand_structure_factor(cand, {}, context2)
    assert score_with <= score_without
