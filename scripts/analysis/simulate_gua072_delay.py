#!/usr/bin/env python3
"""Simulate delaying GUA-072 bomb break from Step1 to _make_plan_from_sf Step2."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.v.nn.features import grouping_engine as G

HAND = [
    "D2", "C3", "D3", "S5", "D5", "S6", "H6", "D6", "C7", "D7",
    "S8", "H8", "C8", "C8", "D8", "S9", "C9", "HT", "HT", "CT", "CT",
    "SQ", "HQ", "CQ", "DQ", "DK", "SA",
]
R = "J"


def _safe(bomb):
    return G._card_rank_value(bomb[0], R) <= 10 if bomb else True


def make_plan_delayed(bombs, singles, pairs, trips, wilds, strategy, break_bombs, double_st):
    """SF池不预拆小炸；拆弹仅在 _make_plan_from_sf Step2 且 break_bombs=True。"""
    pool_s = list(singles)
    pool_p = [p[:] for p in pairs]
    pool_t = [t[:] for t in trips]
    pool_w = list(wilds)

    if break_bombs:
        remaining_bombs = []
        for b in bombs:
            if _safe(b):
                pool_s.extend(b)
            else:
                remaining_bombs.append(b)
    else:
        remaining_bombs = [b[:] for b in bombs]

    up_bombs, pool_t, pool_w = G._upgrade_bombs_with_wilds(pool_t, pool_w)
    remaining_bombs = remaining_bombs + up_bombs

    pool_s, pool_p, pool_t, pool_w, straights, three_pairs, steel_plates, twt_list = (
        G._run_multi_pass_loop(pool_s, pool_p, pool_t, pool_w, R, double_st)
    )
    rem_all = pool_s + [x for px in pool_p for x in px] + [x for tx in pool_t for x in tx]
    rem_rg = G._rank_groups(rem_all, R)
    rem_rg.pop("__wild__", None)
    rem_rs, rem_rp, rem_rt, new_bombs = G._basic_classify(rem_rg)
    remaining_bombs = remaining_bombs + new_bombs
    return G._build_plan(
        rem_rs, rem_rp, rem_rt, remaining_bombs, straights, [], three_pairs, pool_w, R, strategy,
        three_with_twos=twt_list, steel_plates=steel_plates,
    )


def main():
    g = G._rank_groups(HAND, R)
    wilds = g.pop("__wild__", [])
    singles, pairs, trips, bombs = G._basic_classify(g)

    print("=== 现状（Step1 预拆 ≤10 炸）===")
    cur = G._enumerate_plans(HAND, R, dedup=False)
    for p in cur:
        print(f"  {p.strategy:14s} power={p.power_score} role={p.role:4s} score={p.score:.4f} bombs={len(p.bombs)}")

    print()
    print("=== 模拟：GUA-072 押后至 Step2（策略分支内 break_bombs 控制）===")
    print("  SF池：仅非炸牌；全部炸弹进 reserved_bombs")
    print()

    configs = [
        ("BOMB_FIRST", False, False),
        ("ROUND_OPTIMAL", True, False),
        ("ALL_COMBOS", True, True),
    ]
    plans = [
        make_plan_delayed(bombs, singles, pairs, trips, wilds, *c) for c in configs
    ]
    for p in plans:
        G._score_plan_v2(p, plans)

    plans.sort(key=lambda x: x.score, reverse=True)
    hdr = f"{'策略':<14} {'break':>5} {'炸':>3} {'power':>5} {'角色':<6} {'总分':>7} {'档次':<6} {'手轮':>4} {'单':>3}"
    print(hdr)
    print("-" * len(hdr.encode("utf-8")) + "-" * 20)
    for p in plans:
        br = "Y" if p.strategy != "BOMB_FIRST" else "N"
        print(
            f"{p.strategy:<14} {br:>5} {len(p.bombs):>3} {p.power_score:>5} {p.role:<6} "
            f"{p.score:>7.4f} {p.score_tier:<6} {p.num_rounds():>4} {len(p.singles):>3}"
        )

    best = plans[0]
    print()
    print(f"BEST={best.strategy} bombs={[len(b) for b in best.bombs]} "
          f"{[''.join(c[1] for c in b) for b in best.bombs]}")
    print(f"  三连对={len(best.three_pairs)} 三带二={len(best.three_with_twos)} 顺子={len(best.straights)}")

    bf = next(p for p in plans if p.strategy == "BOMB_FIRST")
    ro = next(p for p in plans if p.strategy == "ROUND_OPTIMAL")
    print()
    print("=== 对比 ===")
    print(f"BOMB_FIRST: {len(bf.bombs)}炸 power={bf.power_score} {bf.role} score={bf.score:.4f} 单张={len(bf.singles)}")
    print(f"ROUND_OPT:  {len(ro.bombs)}炸 power={ro.power_score} {ro.role} score={ro.score:.4f} 单张={len(ro.singles)} 三连对={len(ro.three_pairs)}")
    print(f"结构是否分化: {bf.to_dict()['Bomb'] != ro.to_dict()['Bomb'] or len(bf.three_pairs) != len(ro.three_pairs)}")


if __name__ == "__main__":
    main()
