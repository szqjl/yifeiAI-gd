# -*- coding: utf-8 -*-
"""GUA-084：五星炸保护 / SF 分支 BOMB_FIRST / 三带二禁吃炸对。"""
import pytest

from src.v.nn.features.grouping_engine import (
    _break_bombs_into_pool,
    _detect_three_with_two,
    _enumerate_plans,
    _parse_rank,
    _split_bomb_for_break,
    enumerate_groupings,
)

YF1_HAND = (
    "S2 H2 C3 C3 C4 C5 C6 S7 H7 D7 S9 H9 D9 ST HT CT CT DT "
    "SQ HQ DQ SK SK HK DK HA H8"
).split()
YF1_CUR_RANK = "8"


def _twt_pair_ranks(plan):
    return [_parse_rank(twt[1][0]) for twt in plan.three_with_twos]


def _ten_bomb(plan):
    for b in plan.bombs:
        if b and _parse_rank(b[0]) == "T":
            return sorted(b)
    return None


class TestSplitBombForBreak:
    def test_peel_zero_keeps_five_star(self):
        bomb = ["CT", "CT", "DT", "HT", "ST"]
        kept, peeled = _split_bomb_for_break(bomb, 0, "8")
        assert len(kept) == 5
        assert peeled == []

    def test_peel_one_keeps_four_core(self):
        bomb = ["CT", "CT", "DT", "HT", "ST"]
        kept, peeled = _split_bomb_for_break(bomb, 1, "8")
        assert len(kept) == 4
        assert len(peeled) == 1
        assert _parse_rank(peeled[0]) == "T"


class TestDetectThreeWithTwoBombGuard:
    def test_skips_t_pair_when_t_bomb_core_reserved(self):
        trips = [["S7", "H7", "D7"], ["S9", "H9", "D9"]]
        pairs = [["CT", "CT"], ["S2", "H2"]]
        twt, rem_t, _rem_p = _detect_three_with_two(
            trips, pairs, "8", bomb_core_ranks={"T"})
        assert len(twt) == 1
        assert _parse_rank(twt[0][1][0]) == "2"
        assert len(rem_t) == 1


class TestBreakBombsIntoPool:
    def test_five_star_not_fully_broken_when_peel_zero(self):
        bombs = [["CT", "CT", "DT", "HT", "ST"], ["SK", "SK", "HK", "DK"]]

        def _safe(b):
            from src.v.nn.features.grouping_engine import _card_rank_value
            return _card_rank_value(b[0], "8") <= 10

        kept, peeled = _break_bombs_into_pool(
            bombs,
            break_bombs=True,
            cur_rank="8",
            large_bomb_peel=0,
            safe_to_break_fn=_safe,
        )
        assert len(kept) == 2
        ten = next(b for b in kept if _parse_rank(b[0]) == "T")
        assert len(ten) == 5
        assert peeled == []


class TestYf1HandGrouping:
    def test_enumerate_includes_bomb_first_with_sf(self):
        plans = _enumerate_plans(YF1_HAND, YF1_CUR_RANK, dedup=False)
        bf = [p for p in plans if p.strategy == "BOMB_FIRST"]
        assert bf
        assert any(len(p.bombs) >= 2 for p in bf)

    def test_best_plan_keeps_five_star_ten_bomb(self):
        best = enumerate_groupings(YF1_HAND, YF1_CUR_RANK)[0]
        ten = _ten_bomb(best)
        assert ten is not None
        assert len(ten) == 5

    def test_best_plan_has_two_bombs(self):
        best = enumerate_groupings(YF1_HAND, YF1_CUR_RANK)[0]
        assert len(best.bombs) >= 2

    def test_best_plan_no_ten_pairs_in_twt(self):
        best = enumerate_groupings(YF1_HAND, YF1_CUR_RANK)[0]
        assert "T" not in _twt_pair_ranks(best)

    def test_best_twt_uses_deuce_pair(self):
        best = enumerate_groupings(YF1_HAND, YF1_CUR_RANK)[0]
        pair_ranks = _twt_pair_ranks(best)
        assert "2" in pair_ranks

    def test_bomb_first_plan_exists_in_enumeration(self):
        plans = _enumerate_plans(YF1_HAND, YF1_CUR_RANK, dedup=True)
        assert any(p.strategy == "BOMB_FIRST" for p in plans)
