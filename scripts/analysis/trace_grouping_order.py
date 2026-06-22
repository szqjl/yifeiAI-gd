#!/usr/bin/env python3
"""Trace grouping engine pipeline order vs doc for a hand."""
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


def safe_break(bomb):
    return G._card_rank_value(bomb[0], R) <= 10 if bomb else True


def main():
    g = G._rank_groups(HAND, R)
    g.pop("__wild__", None)
    s, p, t, bombs = G._basic_classify(g)

    print("=== Step0 _basic_classify（枚举输入）===")
    for b in bombs:
        tag = "可拆(<=10)" if safe_break(b) else "保护(>10)"
        print(f"  {len(b)}星 {''.join(c[1] for c in b)}  [{tag}]")

    sf_singles = s[:]
    sf_pairs = [x[:] for x in p]
    sf_trips = [x[:] for x in t]
    safe_bomb_cards = []
    protected_bombs = []
    for b in bombs:
        if safe_break(b):
            safe_bomb_cards.extend(b)
        else:
            protected_bombs.append(b)

    print()
    print("=== Step1 SF池（文档：同花顺优先）===")
    print(f"  protected_bombs（保炸）: {len(protected_bombs)} → "
          f"{[''.join(c[1] for c in b) for b in protected_bombs]}")
    print(f"  safe_bomb_cards（≤10 已拆入池）: {len(safe_bomb_cards)} 张 → "
          f"ranks={sorted(set(c[1] for c in safe_bomb_cards))}")

    sf_all = (
        sf_singles
        + [x for px in sf_pairs for x in px]
        + [x for tx in sf_trips for x in tx]
        + safe_bomb_cards
    )
    sf_rg = G._rank_groups(sf_all, R)
    sf_rg.pop("__wild__", None)
    sf_cs, sf_cp, sf_ct, sf_cb = G._basic_classify(sf_rg)
    for bb in sf_cb:
        sf_cs.extend(bb)
    sf_nat, sf_n1, sf_p1, sf_t1, _ = G._detect_straight_flushes(sf_cs, sf_cp, sf_ct, R, [])
    print(f"  SF候选: {'有' if sf_nat else '无'} → 本手无同花顺")

    print()
    print("=== Step2-5 _make_plan_from_sf ×3（去重前）===")
    print("  文档顺序: SF → 4/5头炸 → 三带二/三连对/钢板/对子/顺子")
    print("  引擎 multi_pass 顺序: 三带二 → 顺子1 → 顺子2 → 三连对 → 钢板 → trip降级")
    print()

    wilds_all = G._rank_groups(HAND, R).get("__wild__", [])

    def make_plan(strategy, break_bombs, double_st):
        pool_s = list(sf_n1)
        pool_p = [p_[:] for p_ in sf_p1]
        pool_t = [t_[:] for t_ in sf_t1]
        pool_w = list(wilds_all[:])
        if break_bombs:
            for rb in protected_bombs:
                if safe_break(rb):
                    pool_s.extend(rb)
            remaining_bombs = [rb for rb in protected_bombs if not safe_break(rb)]
        else:
            remaining_bombs = list(protected_bombs)
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

    configs = [
        ("BOMB_FIRST", False, False, "不拆 protected"),
        ("ROUND_OPTIMAL", True, False, "可拆 protected(仅Q不可拆)"),
        ("ALL_COMBOS", True, True, "可拆 protected + 双顺子"),
    ]
    plans = [make_plan(c[0], c[1], c[2]) for c in configs]
    for p in plans:
        G._score_plan_v2(p, plans)

    hdr = f"{'策略':<14} {'break_prot':>10} {'2x顺':>5} {'炸':>3} {'牌力':>4} {'总分':>7} {'手轮':>4}  炸弹"
    print(hdr)
    print("-" * 80)
    for p, cfg in zip(plans, configs):
        bombs_s = "+".join("".join(c[1] for c in b) for b in p.bombs) or "(无)"
        print(
            f"{p.strategy:<14} {cfg[3]:>10} {'Y' if cfg[2] else 'N':>5} "
            f"{len(p.bombs):>3} {p.power_score:>4} {p.score:>7.4f} {p.num_rounds():>4}  {bombs_s}"
        )

    keys = []
    for p in plans:
        k = (
            len(p.singles), len(p.pairs), len(p.trips), len(p.bombs),
            len(p.straights), len(p.three_pairs), len(p.three_with_twos), len(p.steel_plates),
        )
        keys.append(k)
    print()
    print(f"结构指纹: {len(set(keys))} 种 → _enumerate_plans 去重后 {len(set(keys))} 方案")
    print()
    print("=== 结论要点 ===")
    print("1. ≤10 小炸(8/T) 在 Step1 SF池 已拆，BOMB_FIRST 也保不住")
    print("2. 仅 J/Q/K/A 炸留在 protected_bombs；本手只剩四Q")
    print("3. multi_pass 先顺子再三连对，与文档「三带二>三连对>对子>顺子」部分不一致")


if __name__ == "__main__":
    main()
