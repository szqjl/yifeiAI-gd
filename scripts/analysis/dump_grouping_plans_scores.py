#!/usr/bin/env python3
"""Dump all grouping plans with power_score and score breakdown."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.v.nn.features.grouping_engine import (
    _enumerate_plans,
    enumerate_groupings,
    _count_all_cards_in_plan,
    _rank_groups,
    _basic_classify,
)

# 20260621224308510816 贡后首步 27 张
HAND = [
    "D2", "C3", "D3", "S5", "D5", "S6", "H6", "D6", "C7", "D7",
    "S8", "H8", "C8", "C8", "D8", "S9", "C9", "HT", "HT", "CT", "CT",
    "SQ", "HQ", "CQ", "DQ", "DK", "SA",
]
CUR_RANK = "J"


def struct_summary(p) -> str:
    d = p.to_dict()
    parts = []
    bombs = d.get("Bomb", [])
    if bombs:
        parts.append("炸[" + "+".join("".join(c[1] for c in b) for b in bombs) + "]")
    if d.get("ThreePair"):
        parts.append(f"三连对{len(d['ThreePair'])}")
    if d.get("ThreeWithTwo"):
        parts.append(f"三带二{len(d['ThreeWithTwo'])}")
    if d.get("Trips"):
        parts.append(f"三张{len(d['Trips'])}")
    if d.get("Pair"):
        parts.append(f"对{len(d['Pair'])}")
    if d.get("Single"):
        parts.append(f"单{len(d['Single'])}")
    if d.get("Straight"):
        parts.append(f"顺{len(d['Straight'])}")
    return " ".join(parts)


def main():
    all_plans = _enumerate_plans(HAND, CUR_RANK)
    all_plans.sort(key=lambda p: p.score, reverse=True)
    best, top3 = enumerate_groupings(HAND, CUR_RANK)
    top3_ids = {id(p) for p in top3}

    print("牌谱: 20260621224308510816 第16副 yf1 贡后首步")
    print(f"手牌 27 张 | curRank={CUR_RANK}")
    print(f"_enumerate_plans 去重方案数: {len(all_plans)}")
    print(f"enumerate_groupings Top3 数: {len(top3)}")
    print()

    g = _rank_groups(HAND, CUR_RANK)
    wild = g.pop("__wild__", [])
    _, _, _, init_bombs = _basic_classify(g)
    print("--- _basic_classify 初始炸弹（枚举输入）---")
    for b in init_bombs:
        print(f"  {len(b)}星: {b} ({''.join(c[1] for c in b)})")
    print()

    hdr = (
        f"{'#':>2} {'策略':<14} {'完整':>4} {'牌力':>4} {'角色':<8} "
        f"{'总分':>6} {'档次':<6} {'牌力分':>6} {'手数分':>6} {'回收分':>6} {'灵活分':>6} "
        f"{'手轮':>4} {'炸数':>3}  结构"
    )
    print(hdr)
    print("-" * len(hdr.encode("utf-8")) + "-" * 40)

    for i, p in enumerate(all_plans, 1):
        complete = _count_all_cards_in_plan(p) == len(HAND)
        tags = []
        if id(p) == id(best):
            tags.append("BEST")
        if id(p) in top3_ids:
            tags.append("top3")
        tag = f" [{','.join(tags)}]" if tags else ""
        print(
            f"{i:>2} {p.strategy:<14} {str(complete):>4} {p.power_score:>4} {p.role:<8} "
            f"{p.score:>6.4f} {getattr(p, 'score_tier', '?'):<6} "
            f"{p.bomb_score:>6.4f} {p.rounds_score:>6.4f} {p.recovery_score:>6.4f} {p.flexibility_score:>6.4f} "
            f"{p.num_rounds():>4} {len(p.bombs):>3}  {struct_summary(p)}{tag}"
        )

    print()
    print("--- 各方案炸弹明细 ---")
    for i, p in enumerate(all_plans, 1):
        bombs = [list(b) for b in p.bombs]
        print(f"  #{i} {p.strategy:14s} 总分={p.score:.4f} 牌力={p.power_score}  bombs={bombs}")

    print()
    print("评分公式: 总分 = 0.5×牌力分 + 0.3×手数分 + 0.1×回收分 + 0.1×灵活分")
    print("牌力分 = min(power_score/10, 1.0)")


if __name__ == "__main__":
    main()
