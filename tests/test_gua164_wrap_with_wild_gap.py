"""
GUA-164：A-2-3(百搭)-4-5 wrap 直顺枚举。
- 锚点：yf1 27 张起手，bombs 锁 9/J，HA 当百搭应进 A-2-3(百搭)-4-5 直顺。
- 修复：`_detect_straights` wrap 段构造允许 gap=1 用 1 张百搭；引入 forward wrap
  (A 当 1 起头 → 2 → 3 → 4 → 5) 替代仅向后 tail 那一支。
"""
import pytest

from src.v.nn.features.grouping_engine import (
    _detect_straights,
    _basic_classify,
    _rank_groups,
    _parse_rank,
    enumerate_groupings,
    _parse_rank as _pr,  # alias used by ad-hoc helpers
)


YH1_HAND_27 = [
    "C2","C4","H5","H7","S7","S8","C8","H9","C9","D9","H9","C9",
    "ST","DT","HJ","SJ","DJ","SJ","HQ","CQ","CK","DK","HA","SA","CA","SB","SB",
]


def _prep_inputs(hand, cur_rank="A", wild_card="HA"):
    groups = _rank_groups(hand, cur_rank)
    singles, pairs, trips, bombs = _basic_classify(groups)
    non_wild_singles = [c for c in singles if c != wild_card]
    non_wild_pairs = [p for p in pairs if all(c != wild_card for c in p)]
    return non_wild_singles, non_wild_pairs, trips, [wild_card], bombs


def test_gua164_yf1_initial_hand_has_A2_5_straight():
    """Case ①：yf1 起手 27 张，9/J 在炸里。百搭 HA 应进入 A-2-3(百搭)-4-5 直顺。"""
    non_wild_singles, non_wild_pairs, trips, wilds, bombs = _prep_inputs(YH1_HAND_27)
    # 确认 9 / J 在炸里
    assert len(bombs) == 2
    bomb_ranks = {_parse_rank(c) for b in bombs for c in b}
    assert "9" in bomb_ranks and "J" in bomb_ranks

    straights, *_ = _detect_straights(
        non_wild_singles, non_wild_pairs, trips, "A", wilds,
    )
    target = {"SA", "C2", "HA", "C4", "H5"}
    found = any(target == set(s) for s in straights)
    assert found, f"expected A-2-3(HA 百搭)-4-5 直顺 in {straights}"


def test_gua164_minimal_5card_straight():
    """Case ②：5 张最简构造态 [SA,C2,HA,C4,H5] + curRank=A 应唯一含该直顺。"""
    best, plans = enumerate_groupings(["SA", "C2", "HA", "C4", "H5"], "A")
    target = {"SA", "C2", "HA", "C4", "H5"}
    found = any(
        any(target == set(s) for s in p.straights)
        for p in plans
    )
    assert found, f"expected A-2-3-4-5 (with HA) straight in {[p.straights for p in plans]}"


def test_gua164_no_two_no_wrap():
    """Case ③：手牌无 2 时 wrap 不启动；不得伪造 A-2 起头顺子。"""
    hand_no2 = ["H7","S7","S8","C8","H5","HA","SA","CA","HQ","CQ","CK","DK","SB"]
    best, plans = enumerate_groupings(hand_no2, "A")
    # 不应有任何含 '2' 的 5 牌直顺（因为手牌没 2）
    for p in plans:
        for s in p.straights:
            rank_set = {_parse_rank(c) for c in s}
            assert "2" not in rank_set, (
                f"unexpected wrap straight {s} when no 2 in hand"
            )


def test_gua164_straights_in_round_optimal_plan():
    """Case ④：yf1 锚点 27 张起手，ROUND_OPTIMAL 方案必须含 A-2-3(百搭)-4-5 直顺。"""
    best, plans = enumerate_groupings(YH1_HAND_27, "A")
    target = {"SA", "C2", "HA", "C4", "H5"}
    found_optimal = False
    for p in plans:
        if "ROUND_OPTIMAL" in p.strategy:
            for s in p.straights:
                if target.issubset(set(s)):
                    found_optimal = True
                    break
    assert found_optimal, (
        f"ROUND_OPTIMAL plan must include A-2-3(HA 百搭)-4-5 straight; "
        f"got {[p.straights for p in plans if 'ROUND_OPTIMAL' in p.strategy]}"
    )
