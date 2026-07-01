# -*- coding: utf-8 -*-
import pytest

from src.v.nn.features.grouping_engine import enumerate_groupings, _enumerate_plans


def _max_score(plans, *, strategy=None):
    scoped = [p for p in plans if strategy is None or p.strategy == strategy]
    assert scoped, f"missing plans for strategy={strategy}"
    return max(p.score for p in scoped)


def test_gua108_yf1_enumerates_bridge_straight_and_beats_keep_bomb_baseline():
    hand = [
        "H2", "C2", "C2", "D2",
        "H3", "D3",
        "S4", "H4", "C4", "D4",
        "S5", "C5", "D5",
        "S7", "C7",
        "D8", "C9", "DT",
        "HJ", "CJ", "CJ", "DJ",
        "HQ",
        "SK", "SK", "CK",
        "HA",
    ]

    best, plans = enumerate_groupings(hand, "A")
    bridge_plans = [p for p in plans if p.strategy == "STRAIGHT_BRIDGE"]

    assert bridge_plans, "应枚举出 STRAIGHT_BRIDGE 候选"
    assert any(p.straights for p in bridge_plans), "桥接候选中应至少有一手顺子"
    assert best.strategy == "STRAIGHT_BRIDGE", "yf1 锚点应由桥接顺子候选成为最优"

    keep_bomb_baseline = max(
        p.score
        for p in plans
        if p.strategy in {"ROUND_OPTIMAL", "ALL_COMBOS", "BOMB_FIRST"}
    )
    assert best.score > keep_bomb_baseline
    assert best.num_rounds() < min(
        p.num_rounds()
        for p in plans
        if p.strategy in {"ROUND_OPTIMAL", "ALL_COMBOS", "BOMB_FIRST"}
    )


def test_gua108_yf2_boundary_does_not_degenerate_into_always_break_bomb():
    hand = [
        "S3", "S3", "H3", "C3",
        "D4", "C5",
        "S6", "S6", "H6",
        "S7", "H7", "C7", "D7",
        "D8",
        "S9", "S9", "H9", "D9",
        "HT", "HT",
        "SQ", "CQ", "CQ", "DQ",
        "HK", "HA", "DA",
    ]

    all_plans = _enumerate_plans(hand, "A")
    bridge_plans = [p for p in all_plans if p.strategy == "STRAIGHT_BRIDGE"]
    non_bridge_plans = [p for p in all_plans if p.strategy != "STRAIGHT_BRIDGE"]

    assert non_bridge_plans, "边界样本至少应保留非桥接方案"
    if bridge_plans:
        assert _max_score(non_bridge_plans) > _max_score(bridge_plans)

    best, _ = enumerate_groupings(hand, "A")
    assert best.strategy != "STRAIGHT_BRIDGE", "yf2 边界样本不应退化成逢顺必拆炸"
