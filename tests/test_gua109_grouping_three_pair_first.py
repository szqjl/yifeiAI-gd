# -*- coding: utf-8 -*-
"""GUA-109: 三连对优先分支 vs 双三带二竞争方案并存。"""
from src.v.nn.features.grouping_engine import (
    enumerate_groupings,
    _enumerate_plans,
    _count_all_cards_in_plan,
    _parse_rank,
)

# 20260706222548831117 副10 yf1 贡后首出前 27 张，curRank=A
GUA109_YF1_HAND = [
    "S2", "H2", "C2", "D3", "D3", "H4", "C4", "S5", "H5", "S6",
    "D7", "D7", "H8", "D8", "H9", "C9", "D9", "ST", "HT", "CT", "CT",
    "SQ", "CQ", "DQ", "DQ", "HK", "SA",
]
CUR_RANK = "A"


def _has_three_pair_334455(plan) -> bool:
    for tp in plan.three_pairs:
        ranks = sorted(_parse_rank(c) for pr in tp for c in pr)
        if ranks == ["3", "3", "4", "4", "5", "5"]:
            return True
    return False


def test_gua109_enumerates_three_pair_first_branch():
    all_plans = _enumerate_plans(GUA109_YF1_HAND, CUR_RANK)
    tp_first = [p for p in all_plans if p.strategy == "THREE_PAIR_FIRST"]
    twt_first = [
        p for p in all_plans
        if p.strategy in {"ROUND_OPTIMAL", "ALL_COMBOS", "BOMB_FIRST"}
    ]

    assert tp_first, "应枚举 THREE_PAIR_FIRST 候选"
    assert any(p.three_pairs for p in tp_first), "THREE_PAIR_FIRST 应含三连对结构"
    assert all(p.three_with_twos for p in twt_first), "默认序仍应保留双三带二方案"


def test_gua109_yf1_anchor_prefers_334455_over_double_twt():
    best, _plans = enumerate_groupings(GUA109_YF1_HAND, CUR_RANK)

    assert best.strategy == "THREE_PAIR_FIRST"
    assert _has_three_pair_334455(best), "最优应含 334455 三连对"
    assert _count_all_cards_in_plan(best) == len(GUA109_YF1_HAND)

    round_opt = next(
        p for p in _enumerate_plans(GUA109_YF1_HAND, CUR_RANK)
        if p.strategy == "ROUND_OPTIMAL"
    )
    assert not round_opt.three_pairs
    assert best.score > round_opt.score
    assert best.num_rounds() < round_opt.num_rounds()
    assert best.power_score >= 2


def test_gua109_three_pair_first_plan_integrity_on_small_hand():
    hand = ["S3", "H3", "C3", "D3", "S4", "H4", "C5", "H5", "S6", "H6"]
    _, plans = enumerate_groupings(hand, "2")
    for p in plans:
        assert _count_all_cards_in_plan(p) == len(hand)
