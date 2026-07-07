# -*- coding: utf-8 -*-
"""GUA-109: 顺子优先分支 vs 三带二贪心竞争方案并存。"""
from src.v.nn.features.grouping_engine import (
    enumerate_groupings,
    _enumerate_plans,
    _count_all_cards_in_plan,
    _parse_rank,
)

# 20260702195833037993 组牌竞争核心（curRank=2）：JJJ/KKK/22/66/QQ + 6-10 顺子关键张
# 默认序：JJJ+66 + KKK+22；顺子序：Straight 6-10 + JJJ+QQ + KKK+22
GUA109_STRAIGHT_HAND = [
    "CJ", "HJ", "DJ",
    "CK", "DK", "HK",
    "C2", "D2",
    "C6", "D6",
    "SQ", "HQ",
    "D7", "H8", "D9", "ST",
]
CUR_RANK = "2"


def _straight_rank_sets(plan):
    return [
        sorted(set(_parse_rank(c) for c in st))
        for st in plan.straights
    ]


def _twt_pairs(plan):
    return [(_parse_rank(t[0][0]), _parse_rank(t[1][0])) for t in plan.three_with_twos]


def _has_straight_6_to_10(plan) -> bool:
    return ["6", "7", "8", "9", "T"] in _straight_rank_sets(plan)


def test_gua109_enumerates_straight_before_twt_branch():
    all_plans = _enumerate_plans(GUA109_STRAIGHT_HAND, CUR_RANK)
    sb_twt = [p for p in all_plans if p.strategy == "STRAIGHT_BEFORE_TWT"]
    round_opt = [p for p in all_plans if p.strategy == "ROUND_OPTIMAL"]

    assert sb_twt, "应枚举 STRAIGHT_BEFORE_TWT 候选"
    assert any(_has_straight_6_to_10(p) for p in sb_twt)
    assert all(not _has_straight_6_to_10(p) for p in round_opt)


def test_gua109_straight_anchor_prefers_6_10_over_greedy_twt():
    best, _plans = enumerate_groupings(GUA109_STRAIGHT_HAND, CUR_RANK)

    assert best.strategy == "STRAIGHT_BEFORE_TWT"
    assert _has_straight_6_to_10(best)
    assert ("J", "Q") in _twt_pairs(best)
    assert ("K", "2") in _twt_pairs(best)
    assert ("J", "6") not in _twt_pairs(best)
    assert _count_all_cards_in_plan(best) == len(GUA109_STRAIGHT_HAND)

    round_opt = next(
        p for p in _enumerate_plans(GUA109_STRAIGHT_HAND, CUR_RANK)
        if p.strategy == "ROUND_OPTIMAL"
    )
    assert not round_opt.straights
    assert ("J", "6") in _twt_pairs(round_opt)
    assert best.score > round_opt.score
    assert best.num_rounds() < round_opt.num_rounds()


def test_gua109_straight_before_twt_plan_integrity_on_small_hand():
    hand = ["S6", "H7", "C8", "D9", "ST", "SJ", "HJ", "CJ", "SK", "HK", "CK", "S2", "H2"]
    _, plans = enumerate_groupings(hand, "2")
    for p in plans:
        assert _count_all_cards_in_plan(p) == len(hand)
