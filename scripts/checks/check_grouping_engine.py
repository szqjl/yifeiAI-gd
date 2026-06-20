# -*- coding: utf-8 -*-
"""
组牌引擎独立测试脚本（GUA-062 v2 4 维评分验证）。

用法：
    python scripts/checks/check_grouping_engine.py                           # 默认测试手牌
    python scripts/checks/check_grouping_engine.py --hand RJ,RJ,S6,CA,HA,HA,SA,DK,SK,DQ,DJ,CJ,CT,ST,D9,C9,D8,D7,C7,C7,H5,D4,S3,D2,C2,H2,H2   # 自定义手牌
    python scripts/checks/check_grouping_engine.py --rank 4                  # 指定级牌（默认 3）

输出：
    - 所有枚举方案的评分明细表（bomb/rounds/recovery/flexibility/de_singleton/总分）
    - 27/27 完整性校验
    - best_plan 摘要
"""

from __future__ import annotations

import sys
import os
import argparse

# 确保 src/ 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from v.nn.features.grouping_engine import enumerate_groupings


DEFAULT_HAND = [
    "HR", "HR", "S6",
    "CA", "HA", "HA", "SA",
    "DK", "SK", "DQ", "DJ", "CJ",
    "CT", "ST", "D9", "C9",
    "D8", "D7", "C7", "C7",
    "H5", "D4", "S3",
    "D2", "C2", "H2", "H2",
]


def card_count(plan) -> int:
    """统计方案覆盖的牌数（应为 27）。"""
    count = (
        len(plan.singles)
        + sum(len(pr) for pr in plan.pairs)
        + sum(len(t) for t in plan.trips)
        + sum(len(b) for b in plan.bombs)
        + sum(len(s) for s in plan.straights)
        + sum(len(sf) for sf in plan.straight_flushes)
        + sum(sum(len(pr) for pr in tp) for tp in plan.three_pairs)
    )
    # 三带二：每个消耗 5 张牌（1 trip + 1 pair）
    if plan.three_with_twos:
        count += sum(len(twt[0]) + len(twt[1]) for twt in plan.three_with_twos)
    # 钢板：每个消耗 6 张牌（2 trips）
    if plan.steel_plates:
        count += sum(sum(len(t) for t in sp) for sp in plan.steel_plates)
    return count


def main():
    parser = argparse.ArgumentParser(description="组牌引擎独立测试")
    parser.add_argument("--hand", default=",".join(DEFAULT_HAND),
                        help="手牌，逗号分隔（如 RJ,RJ,S6,CA,...）")
    parser.add_argument("--rank", default="3", help="级牌 rank（默认 3）")
    args = parser.parse_args()

    hand = [h.strip() for h in args.hand.split(",") if h.strip()]
    cur_rank = args.rank

    print(f"\n{'='*72}")
    print(f"  组牌引擎独立测试 — GUA-062 v2（4 维评分）")
    print(f"{'='*72}")
    print(f"  手牌 ({len(hand)} 张): {' '.join(hand)}")
    print(f"  级牌: {cur_rank}")
    print()

    best_plan, plans = enumerate_groupings(hand, cur_rank)

    # 完整性校验
    all_ok = all(card_count(p) == 27 for p in plans)
    print(f"  {'✓' if all_ok else '✗'} 27/27 完整性: {'全部通过' if all_ok else '存在非27方案!'}")
    print(f"  方案总数: {len(plans)}")
    print()

    # 方案明细表
    header = f"  {'策略':18s} {'总分':>7s} {'牌力':>6s} {'手数':>6s} {'回收':>6s} {'灵活':>6s} {'火力角色':>8s} {'结构档次':>8s} {'单张':>4s} {'炸弹数':>5s} {'手轮':>4s}"
    print(header)
    print("  " + "-" * 70)

    for p in plans:
        n_rounds = p.num_rounds()
        marker = " ← BEST" if p is best_plan else ""
        print(
            f"  {p.strategy:18s} "
            f"{p.score:7.4f} "
            f"{p.bomb_score:6.3f} "
            f"{p.rounds_score:6.3f} "
            f"{p.recovery_score:6.3f} "
            f"{p.flexibility_score:6.3f} "
            f"{p.role:8s} "
            f"{p.score_tier:8s} "
            f"{len(p.singles):4d} "
            f"{len(p.bombs):5d} "
            f"{n_rounds:4d}"
            f"{marker}"
        )

    # 所有方案摘要
    for p in plans:
        print(f"\n  {'='*70}")
        print(f"  Plan: {p.strategy}  score={p.score:.4f}  role={p.role}(火力)  tier={p.score_tier}(结构)  power={p.power_score}")
        print(f"  炸弹: {len(p.bombs)}  {' '.join(str(b) for b in p.bombs) if p.bombs else '(无)'}")
        print(f"  三连对: {' '.join(str(tp) for tp in p.three_pairs) if p.three_pairs else '(无)'}")
        if p.three_with_twos:
            print(f"  三带二: {' '.join(str(twt[0])+'-'+str(twt[1]) for twt in p.three_with_twos)}")
        if p.steel_plates:
            print(f"  钢板:   {' '.join(str(sp) for sp in p.steel_plates)}")
        print(f"  顺子: {' '.join(str(s) for s in p.straights) if p.straights else '(无)'}")
        print(f"  同花顺: {' '.join(str(sf) for sf in p.straight_flushes) if p.straight_flushes else '(无)'}")
        print(f"  三张: {' '.join(str(t) for t in p.trips) if p.trips else '(无)'}")
        print(f"  对子: {' '.join(str(pr) for pr in p.pairs) if p.pairs else '(无)'}")
        print(f"  单张: {' '.join(str(s) for s in p.singles) if p.singles else '(无)'}")

    # 权重验证（用 best_plan）
    bp = best_plan
    print(f"\n  {'='*70}")
    print(f"  4 维权重: 牌力×0.5 + 手数×0.3 + 回收×0.1 + 灵活×0.1")
    recomputed = (
        0.5 * bp.bomb_score
        + 0.3 * bp.rounds_score
        + 0.1 * bp.recovery_score
        + 0.1 * bp.flexibility_score
    )
    match = abs(bp.score - recomputed) < 0.001
    print(f"  {'✓' if match else '✗'} 总分验证: {bp.score:.4f} ≈ {recomputed:.4f}")
    print()


if __name__ == "__main__":
    main()
