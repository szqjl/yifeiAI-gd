# -*- coding: utf-8 -*-
"""残手质量地板纯函数测试（V8 动态组牌 §3.3.2–3.3.3 / §8.5）。"""

from __future__ import annotations

import pytest

from src.v.nn.features.grouping_engine import GroupingPlan
from src.v.nn.residual_hand_quality import (
    check_residual_floor_veto,
    compute_has_anchor,
    compute_residual_metrics,
    evaluate_after_counter_action,
    evaluate_residual_hand,
    evaluate_residual_plan,
    residual_hand_after_action,
)

# ── §8.5 锚点 ①：废牌簇多且无锚点 → F1/F2 否决 ─────────────────────

def test_f1_waste_units_no_anchor_veto():
    """多块废牌簇、无续打锚点 → residual_floor_veto（F1/F2）。"""
    plan = GroupingPlan(
        cur_rank="2",
        singles=["H3", "D4", "S5", "C6", "H7", "D8"],
        pairs=[],
        trips=[],
        bombs=[],
        straights=[],
        straight_flushes=[],
        three_pairs=[],
        three_with_twos=[],
        steel_plates=[],
    )
    result = evaluate_residual_plan(plan, "2", residual_hand_size=6)
    assert result.metrics.waste_units >= 3
    assert result.metrics.has_anchor is False
    assert result.residual_floor_veto is True
    assert "F1" in result.floor_reasons


def test_f2_high_waste_ratio_veto():
    """残手 ≥8 张且废牌占比 ≥55%、无锚点 → F2。"""
    plan = GroupingPlan(
        cur_rank="2",
        singles=["H3", "D4", "S5", "C6", "H7", "D8"],
        pairs=[["C9", "H9"]],
        trips=[],
        bombs=[],
        straights=[],
        straight_flushes=[],
        three_pairs=[],
        three_with_twos=[],
        steel_plates=[],
    )
    result = evaluate_residual_plan(plan, "2", residual_hand_size=8)
    assert result.metrics.waste_units >= 3
    assert result.metrics.has_anchor is False
    assert "F2" in result.floor_reasons


def test_f1_bomb_anchor_not_veto():
    """有炸弹锚点 → 不因 F1 否决（即使废牌簇多）。"""
    hand = ["H3", "D4", "S5", "C6", "HA", "CA", "DA", "SA"]
    result = evaluate_residual_hand(hand, cur_rank="2")
    assert result.metrics.has_anchor is True
    assert result.residual_floor_veto is False
    assert result.floor_reasons == ()


# ── §8.5 锚点 ②：三连对拆顺后残手全废（用户场景示意）──────────────

def test_three_pair_break_residual_all_waste_veto():
    """
    模拟拆三连对压顺后：剩多张小单/小对、无 ≥10 锚点结构 → 否决。
    """
    # 压完 Straight 后剩：小对 33/55 + 多个 <10 单张
    residual = [
        "H3", "D3",
        "S5", "C5",
        "H6", "D7", "S8", "C9", "H9",
    ]
    result = evaluate_residual_hand(residual, cur_rank="2")
    assert result.metrics.waste_units >= 3
    assert result.metrics.has_anchor is False
    assert result.residual_floor_veto is True
    assert "F1" in result.floor_reasons


def test_evaluate_after_counter_action_subtracts_cards():
    """evaluate_after_counter_action = 手牌减动作牌后再评估。"""
    hand = [
        "C9", "H9", "CT", "DT", "HJ", "DJ", "HQ", "DQ", "SK", "CK",
        "H3", "D4", "S5",
    ]
    straight_cards = ["C9", "CT", "HJ", "HQ", "SK"]
    expected_residual = residual_hand_after_action(hand, straight_cards)
    result = evaluate_after_counter_action(hand, straight_cards, cur_rank="2")
    assert len(expected_residual) == len(hand) - len(straight_cards)
    re_eval = evaluate_residual_hand(expected_residual, cur_rank="2")
    assert result.metrics.waste_units == re_eval.metrics.waste_units
    assert result.metrics.has_anchor == re_eval.metrics.has_anchor


# ── F3 / F4 ─────────────────────────────────────────────────────────

def test_f3_low_power_many_low_singles_veto():
    """牌力崩溃 + 无锚点 + 多个小单 → F3。"""
    plan = GroupingPlan(
        cur_rank="2",
        singles=["H3", "D4", "S5", "C6"],
        pairs=[],
        trips=[],
        bombs=[],
        straights=[],
        straight_flushes=[],
        three_pairs=[],
        three_with_twos=[],
        steel_plates=[],
    )
    metrics = compute_residual_metrics(plan, "2", residual_hand_size=4)
    veto, reasons = check_residual_floor_veto(metrics)
    assert metrics.residual_power < 1
    assert metrics.low_singles >= 2
    assert veto is True
    assert "F3" in reasons


def test_f4_worse_rounds_and_power_drop():
    """残手轮次更散且牌力降 ≥2 → F4。"""
    plan = GroupingPlan(
        cur_rank="2",
        singles=["H3", "D4", "S5", "C6", "H7", "D8"],
        pairs=[["C9", "H9"]],
        trips=[],
        bombs=[],
        straights=[],
        straight_flushes=[],
        three_pairs=[],
        three_with_twos=[],
        steel_plates=[],
    )
    metrics = compute_residual_metrics(plan, "2", residual_hand_size=8)
    veto, reasons = check_residual_floor_veto(
        metrics,
        baseline_rounds=3,
        baseline_power=5,
    )
    assert metrics.residual_rounds > 3
    assert metrics.residual_power <= 3
    assert veto is True
    assert "F4" in reasons


# ── 锚点结构识别 ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "plan_kwargs,expect_anchor",
    [
        ({"bombs": [["HA", "CA", "DA", "SA"]]}, True),
        ({"three_pairs": [[["HJ", "DJ"], ["HQ", "DQ"], ["HK", "DK"]]]}, True),
        (
            {
                "straights": [["CT", "DT", "HJ", "HQ", "SK"]],
            },
            True,
        ),
        (
            {
                "three_with_twos": [(["CT", "DT", "ST"], ["H3", "D3"])],
            },
            True,
        ),
        (
            {
                "pairs": [["HJ", "DJ"]],
            },
            True,
        ),
        (
            {
                "singles": ["H3", "D4", "S5"],
                "pairs": [["C5", "H5"]],
            },
            False,
        ),
    ],
)
def test_has_anchor_detection(plan_kwargs, expect_anchor):
    plan = GroupingPlan(cur_rank="2", **plan_kwargs)
    assert compute_has_anchor(plan, "2") is expect_anchor


def test_residual_quality_score_in_range():
    hand = ["HA", "CA", "DA", "SA", "HK", "CK"]
    result = evaluate_residual_hand(hand, cur_rank="2")
    assert 0.0 <= result.residual_quality_score <= 1.0
    assert result.residual_quality_score >= 0.5


def test_residual_hand_after_action_raises_on_invalid_card():
    with pytest.raises(ValueError, match="不在手牌"):
        residual_hand_after_action(["H3", "D4"], ["H5"])
