# -*- coding: utf-8 -*-
"""GUA-234 阶段 C：Top3 缓存 + 局面触发重评分。

设计真源：V8-中期压顺灵活性-组牌-动态重组方案.md §8.3
"""

import copy

import pytest

from src.v.nn.features.grouping_engine import GroupingPlan, enumerate_groupings
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _sample_hand():
    return [
        "S2", "H2", "D3", "C3", "S4", "H4", "D5", "C5", "S6", "H6",
        "D7", "C7", "S8", "H8", "D9", "C9", "ST", "HT", "DJ", "CJ",
        "SQ", "HQ", "SK", "HK", "SA", "HA", "DA",
    ]


def test_run_grouping_engine_caches_top3():
    """_run_grouping_engine 应缓存 enumerate_groupings 的 Top3。"""
    engine = UltimateWinRateEngineV7(player_id=0)
    hand = _sample_hand()
    state = {"handCards": hand, "curRank": "A", "myPos": 0}
    engine._run_grouping_engine(state)
    assert engine._best_plan is not None
    assert len(engine._all_plans) >= 1
    assert engine._active_plan is engine._best_plan
    assert engine._card_mask


def test_replan_no_trigger_keeps_active_plan():
    """无触发条件 → 不切换 active_plan。"""
    engine = UltimateWinRateEngineV7(player_id=0)
    hand = _sample_hand()
    state = {
        "handCards": hand,
        "curRank": "A",
        "myPos": 0,
        "numofplayers": [27, 27, 27, 27],
        "_mid_feed_snapshot": {"opponent_consecutive": {}},
    }
    engine._run_grouping_engine(state)
    active_before = engine._active_plan
    engine._evaluate_replan_candidates(state)
    assert engine._active_plan is active_before
    assert state.get("_replan_trigger") is None


def test_replan_switches_on_opponent_consecutive_single():
    """对手连出 Single ≥2 → 局面 bonus 偏向散单多的 plan。"""
    engine = UltimateWinRateEngineV7(player_id=0)
    hand = _sample_hand()
    best, plans = enumerate_groupings(hand, "A")
    assert len(plans) >= 2

    plan_many_singles = max(plans, key=lambda p: len(p.singles))
    plan_few_singles = min(plans, key=lambda p: len(p.singles))
    if plan_many_singles is plan_few_singles:
        pytest.skip("本手牌 Top3 散单数无差异")

    # 让「散单多」的 plan 静态分略低但仍可切换
    plan_many_singles = copy.deepcopy(plan_many_singles)
    plan_many_singles.score = best.score - 0.05
    plan_many_singles.strategy = "TEST_MANY_SINGLES"
    plan_few_singles = copy.deepcopy(plan_few_singles)
    plan_few_singles.score = best.score
    plan_few_singles.strategy = "TEST_FEW_SINGLES"

    engine._all_plans = [plan_few_singles, plan_many_singles]
    engine._best_plan = plan_few_singles
    engine._active_plan = plan_few_singles
    engine._apply_active_plan(plan_few_singles)
    engine._dynamic_regroup_enabled = True
    engine._power_gate_tier = "强牌"

    state = {
        "handCards": hand,
        "curRank": "A",
        "myPos": 0,
        "numofplayers": [18, 18, 18, 18],
        "greaterAction": ["Single", "9", ["D9"]],
        "greaterPos": 3,
        "_mid_feed_snapshot": {"opponent_consecutive": {"Single": 2}},
    }
    engine._evaluate_replan_candidates(state)
    assert state.get("_replan_trigger") == "opponent_consecutive_Single_2"
    assert engine._active_plan.strategy == "TEST_MANY_SINGLES"
    assert state.get("_replan_switched") is True


def test_replan_blocked_when_plan_loss_too_high():
    """plan_loss 超 0.15 → 不切换。"""
    engine = UltimateWinRateEngineV7(player_id=0)
    hand = _sample_hand()
    best, plans = enumerate_groupings(hand, "A")
    alt = copy.deepcopy(plans[-1] if len(plans) > 1 else plans[0])
    alt.score = best.score - 0.25
    alt.strategy = "TEST_TOO_LOW"

    engine._all_plans = [best, alt]
    engine._best_plan = best
    engine._active_plan = best
    engine._apply_active_plan(best)
    engine._dynamic_regroup_enabled = True

    state = {
        "handCards": hand,
        "curRank": "A",
        "myPos": 0,
        "numofplayers": [18, 18, 18, 18],
        "_mid_feed_snapshot": {"opponent_consecutive": {"Pair": 2}},
        "greaterAction": ["Pair", "9", ["D9", "C9"]],
        "greaterPos": 1,
    }
    engine._evaluate_replan_candidates(state)
    assert engine._active_plan is best
    assert state.get("_replan_switched") is False


def test_replan_disabled_when_dynamic_regroup_off():
    """超强门禁关闭动态重组 → 不触发。"""
    engine = UltimateWinRateEngineV7(player_id=0)
    hand = _sample_hand()
    best, plans = enumerate_groupings(hand, "A")
    alt = copy.deepcopy(plans[-1] if len(plans) > 1 else plans[0])
    alt.strategy = "TEST_ALT"

    engine._all_plans = [best, alt]
    engine._active_plan = best
    engine._dynamic_regroup_enabled = False

    state = {
        "handCards": hand,
        "curRank": "A",
        "myPos": 0,
        "numofplayers": [18, 18, 18, 18],
        "_mid_feed_snapshot": {"opponent_consecutive": {"Single": 3}},
    }
    engine._evaluate_replan_candidates(state)
    assert state.get("_replan_trigger") is None
    assert engine._active_plan is best


def test_replan_teammate_close_trigger():
    """队友 rest≤5 → 触发重评分（未必切换）。"""
    engine = UltimateWinRateEngineV7(player_id=0)
    hand = _sample_hand()
    best, plans = enumerate_groupings(hand, "A")
    engine._all_plans = list(plans)
    engine._best_plan = best
    engine._active_plan = best
    engine._apply_active_plan(best)
    engine._dynamic_regroup_enabled = True

    state = {
        "handCards": hand,
        "curRank": "A",
        "myPos": 0,
        "numofplayers": [18, 18, 4, 18],
        "_mid_feed_snapshot": {},
        "_mid_feed_P": ["Pair", "Single"],
    }
    engine._evaluate_replan_candidates(state)
    assert state.get("_replan_trigger") == "teammate_close"
    assert "_replan_scores" in state
