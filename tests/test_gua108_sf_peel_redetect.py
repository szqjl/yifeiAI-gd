# -*- coding: utf-8 -*-
"""GUA-084/108：手牌级 SF 枚举 + peel 后重检同花顺。"""
import pytest

from src.v.nn.features.grouping_engine import (
    _enumerate_plans,
    _enumerate_sf_hand_candidates,
    _parse_rank,
    _parse_suit,
    enumerate_groupings,
)

# 副 34 贡还后 27 张（curRank=A）
ROUND34_HAND = (
    "S2,C3,D3,C4,D4,S5,S5,H5,D5,H6,D6,D7,D8,H9,H9,C9,D9,D9,"
    "CT,DT,HJ,DJ,SQ,HQ,SK,CK,CA"
).split(",")
ROUND34_RANK = "A"


def _sf_suits_ranks(sf):
    return [(_parse_suit(c), _parse_rank(c)) for c in sf]


def _has_diamond_sf_610_or_7j(plan):
    for sf in plan.straight_flushes:
        if len(sf) != 5:
            continue
        sr = _sf_suits_ranks(sf)
        if not all(s == "D" for s, _ in sr):
            continue
        ranks = sorted([r for _, r in sr], key=lambda r: "23456789TJQKA".index(r))
        if ranks == ["6", "7", "8", "9", "T"]:
            return True
        if ranks == ["7", "8", "9", "T", "J"]:
            return True
    return False


def _four_star_nine_bomb(plan):
    for b in plan.bombs:
        if len(b) == 4 and b and _parse_rank(b[0]) == "9":
            return sorted(b)
    return None


class TestSfHandCandidates:
    def test_round34_hand_enum_finds_sf_with_peeled_nine_bomb(self):
        bombs = [["C9", "D9", "D9", "H9", "H9"]]
        entries = _enumerate_sf_hand_candidates(
            ROUND34_HAND, ROUND34_RANK, [], bombs,
        )
        assert entries, "手牌 SF 枚举应产出候选"
        sf_keys = set()
        for nat, wild, _, _, _, _, res_bombs in entries:
            all_sf = nat + wild
            for sf in all_sf:
                sf_keys.add(tuple(sorted(sf)))
                ranks = sorted([_parse_rank(c) for c in sf], key=lambda r: "23456789TJQKA".index(r))
                if ranks in (["6", "7", "8", "9", "T"], ["7", "8", "9", "T", "J"]):
                    nine_bombs = [b for b in res_bombs if b and _parse_rank(b[0]) == "9"]
                    assert any(len(b) == 4 for b in nine_bombs), "♦6-10/7-J SF 应伴随四炸9"

        diamond_610 = {"D6", "D7", "D8", "D9", "DT"}
        diamond_7j = {"D7", "D8", "D9", "DT", "DJ"}
        assert sf_keys & {tuple(sorted(diamond_610)), tuple(sorted(diamond_7j))}


class TestRound34EnumeratePlans:
    def test_pre_dedup_includes_straight_flush_plan(self):
        plans = _enumerate_plans(ROUND34_HAND, ROUND34_RANK, dedup=False)
        sf_plans = [p for p in plans if p.straight_flushes]
        assert sf_plans, "去重前应至少有一方案含 StraightFlush"

    def test_sf_plan_has_four_star_nine_and_diamond_sf(self):
        plans = _enumerate_plans(ROUND34_HAND, ROUND34_RANK, dedup=False)
        sf_plans = [p for p in plans if _has_diamond_sf_610_or_7j(p)]
        assert sf_plans
        assert any(_four_star_nine_bomb(p) for p in sf_plans)

    def test_best_may_prefer_sf_when_scored(self):
        best, all_plans = enumerate_groupings(ROUND34_HAND, ROUND34_RANK)
        assert any(p.straight_flushes for p in all_plans)
