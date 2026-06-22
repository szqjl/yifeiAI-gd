#!/usr/bin/env python3
"""Compare dedicated SF detection (Step1) vs multi_pass-only grouping for straight flush."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.v.nn.features.grouping_engine import (
    _rank_groups,
    _basic_classify,
    _detect_straight_flushes,
    _run_multi_pass_loop,
    enumerate_groupings,
    _enumerate_plans,
)

# 天然双同花顺 + 杂牌（test_grouping_engine 同类）
HAND_SF = [
    "S2", "S3", "S4", "S5", "S6",
    "H2", "H3", "H4", "H5", "H6",
    "D7", "C7", "D7", "C7",
    "D8", "C8", "D8",
    "D9", "C9",
    "ST", "HT", "DT",
    "SJ", "HJ",
    "SQ", "HQ",
    "SK",
    "SA",
]
R = "2"

# 逢人配补 1 张成 SF（非炸池）
HAND_SF_WILD = ["S3", "S4", "S5", "S6", "S7", "H9", "H8", "H7", "H6", "H5"] + ["H2"] * 17
# simpler: 4同花 + 1 wild
HAND_SF_WILD = (
    ["S3", "S4", "S5", "S6"]  # 4 spades
    + ["H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9", "HT", "HJ", "HQ", "HK", "HA"]
    + ["D2", "D3", "D4", "D5", "D6", "D7", "D8"]
)
# cur_rank 3 → H3 is wild
R_W = "3"


def count_sf_in_plan(plan):
    return len(plan.straight_flushes)


def multipass_only_sf(singles, pairs, trips, wilds, cur_rank):
    """仅用 multi_pass（无 Step1 SF 检测）能否组出同花顺？"""
    s, p, t, w, straights, tp, sp, twt = _run_multi_pass_loop(
        singles[:], [x[:] for x in pairs], [x[:] for x in trips], wilds[:], cur_rank, True
    )
    return len(straights), 0  # multi_pass 无 SF 输出


def main():
    print("=== 1. multi_pass 能否替代 SF 检测？ ===")
    g = _rank_groups(HAND_SF, R)
    wilds = g.pop("__wild__", [])
    s, p, t, bombs = _basic_classify(g)
    st_count, sf_count = multipass_only_sf(s, p, t, wilds, R)
    sf_nat, *_ = _detect_straight_flushes(s, p, t, R, wilds)
    print(f"  双同花顺手牌: _detect_straight_flushes → {len(sf_nat)} 组 SF")
    print(f"  同手牌 multi_pass 仅产出顺子(st)={st_count} 组, SF={sf_count} 组")
    print("  结论: multi_pass 不含同花顺检测，不能替代 Step1 SF 检测\n")

    print("=== 2. 押后拆炸后 SF 检测仍有效？ ===")
    plans = _enumerate_plans(HAND_SF, R, dedup=False)
    sf_plans = [p for p in plans if p.straight_flushes]
    print(f"  方案数={len(plans)}  含SF方案={len(sf_plans)}")
    if sf_plans:
        p = max(sf_plans, key=lambda x: len(x.straight_flushes))
        print(f"  最佳SF方案: {p.strategy} SF数={len(p.straight_flushes)} "
              f"score={p.score:.4f} role={p.role}")
        for sf in p.straight_flushes[:2]:
            print(f"    SF: {sf}")
    print()

    print("=== 3. SF 检测 vs 把 SF 塞进 multi_pass（时序） ===")
    print("  文档顺序: SF → 炸弹 → 连牌")
    print("  若 SF 在 multi_pass 之后: 三带二/三连对/顺子会先消耗 SF 所需同花张 → 漏组或降档")
    print("  Step1 专用 SF 检测: 先锁定 SF，再 multi_pass 去单化 → 与文档一致\n")

    print("=== 4. GUA-080 三炸手（押后后） ===")
    h80 = [
        "D2", "C3", "D3", "S5", "D5", "S6", "H6", "D6", "C7", "D7",
        "S8", "H8", "C8", "C8", "D8", "S9", "C9", "HT", "HT", "CT", "CT",
        "SQ", "HQ", "CQ", "DQ", "DK", "SA",
    ]
    best, top = enumerate_groupings(h80, "J")
    print(f"  best={best.strategy} power={best.power_score} role={best.role} "
          f"score={best.score:.4f} bombs={len(best.bombs)} SF={len(best.straight_flushes)}")
    pre = _enumerate_plans(h80, "J", dedup=False)
    for p in pre:
        print(f"    {p.strategy:14s} power={p.power_score} role={p.role:4s} "
              f"bombs={len(p.bombs)} tp={len(p.three_pairs)}")


if __name__ == "__main__":
    main()
