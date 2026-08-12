# -*- coding: utf-8 -*-
"""
自动败招归因 — 不完美信息确定性检测（v4）
R1/R3/R4（R2 已删：报单跟出是规则强制，非败招）。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from src.v.nn.endgame.endgame_solver import (
    _enumerate_natural_actions, beats,
)

PASS_ACT = ["PASS", "", []]


def _cards_of_action(act):
    if not act:
        return []
    if isinstance(act, list) and len(act) >= 3 and isinstance(act[2], list):
        return [str(c) for c in act[2]]
    return [str(c) for c in act]


def _is_pass(act):
    return bool(act) and (act[0] == "PASS" or (isinstance(act[0], str) and act[0].upper() == "PASS"))


def _one_play_actions(hand, cur_rank):
    """能一手出完的合法动作（n == len(hand)），仅自然牌型（不把级牌当万能）。"""
    return [p for p in _enumerate_natural_actions(hand, cur_rank)
            if len(_cards_of_action(p)) == len(hand)]


def _hand_key(h):
    return tuple(sorted(str(c) for c in h))


def analyze_record(d):
    """
    以 actions 日志为唯一真源做确定性败招检测。
    决策点 = actions 中 cur_pos==my_seat 的条目（cur_action + greater_action 均为真实执行流）。
    自己手牌 = initial_hand 按 actions 顺序扣减自己已出（已验证可靠，不依赖 my_decisions 快照）。
    级牌 = my_decisions.context.curRank（副内恒定；game_info.curRank 恒 "2" 不可信）。
    """
    seat = d.get("player_id")
    my_seat = int(seat) if seat is not None else 0
    initial_hand = d.get("initial_hand") or []
    actions = d.get("actions") or []
    game_rank = (d.get("game_info") or {}).get("curRank", "2")
    # 真实级牌：game_info.curRank 恒为开局 "2" 不可信；取 my_decisions 首个非 None
    # context.curRank（副内级牌恒定，2~A 全覆盖），无则回退 "2"。
    real_rank = game_rank
    for md in d.get("my_decisions") or []:
        cr = (md.get("context") or {}).get("curRank")
        if cr is not None:
            real_rank = str(cr)
            break

    results = []
    hand = Counter(str(c) for c in initial_hand)
    for a in actions:
        if a.get("cur_pos") != my_seat:
            continue
        cur_rank = (a.get("context") or {}).get("curRank") or real_rank
        cur_rank = str(cur_rank)
        actual = a.get("cur_action")
        if not actual:
            continue
        greater = a.get("greater_action")
        if greater is None or (isinstance(greater, list) and len(greater) >= 1 and _is_pass(greater)):
            greater = PASS_ACT
        n = sum(hand.values())
        a_pass = _is_pass(actual)
        g_pass = _is_pass(greater)

        if not (1 <= n <= 10):
            # 出牌后仍要更新手牌
            if not a_pass:
                hand -= Counter(str(c) for c in _cards_of_action(actual))
            continue

        rule = None
        detail = None

        # R1 报单不压：手剩1张、能压过 greater、却 PASS
        if n == 1 and a_pass and not g_pass:
            my_cards = list(hand.elements())
            single = ["Single", "", [str(my_cards[0])]]
            if beats(single, greater, cur_rank):
                rule = "R1_报单不压"
                detail = "手剩%s能压过 %s 却PASS" % (
                    my_cards[0], json.dumps(greater, ensure_ascii=False))

        # R3 一手清拆牌：仅自由领出(greater=PASS)时，手牌能一手出完却拆散
        if rule is None and not a_pass and g_pass:
            one_plays = _one_play_actions(list(hand.elements()), cur_rank)
            if one_plays:
                remain = n - len(_cards_of_action(actual))
                if remain > 0 and not any(same_action(actual, p) for p in one_plays):
                    rule = "R3_一手清拆牌"
                    detail = "手牌可一手出完(%d个整牌动作) 却出 %s (剩%d张)" % (
                        len(one_plays), json.dumps(actual, ensure_ascii=False), remain)

        # R4 临门不炸：手牌很少(≤5)且有可压 Bomb 却 PASS
        if rule is None and a_pass and n <= 5 and not g_pass:
            bombs = [p for p in _enumerate_natural_actions(list(hand.elements()), cur_rank)
                     if p[0] in ("Bomb", "StraightFlush") and beats(p, greater, cur_rank)]
            if bombs:
                rule = "R4_临门不炸"
                detail = "手%d张 有%d个可压炸弹却PASS" % (n, len(bombs))

        results.append({
            "ts": a.get("timestamp", ""), "my_pos": my_seat,
            "hand": sorted(hand.elements(), key=_sort_key), "hand_size": n,
            "actual": actual, "greater": greater, "cur_rank": cur_rank,
            "rule": rule, "detail": detail,
        })

        # 更新手牌
        if not a_pass:
            hand -= Counter(str(c) for c in _cards_of_action(actual))
    return results


def _sort_key(c):
    """排序用：王>级牌位置；仅用于展示排序，不影响判定。"""
    return str(c)


def same_action(a, b):
    if a is None or b is None:
        return False
    if _is_pass(a) and _is_pass(b):
        return True
    if _is_pass(a) != _is_pass(b):
        return False
    ta = a[0] if a else ""
    tb = b[0] if b else ""
    if ta != tb:
        return False
    ca = sorted(_cards_of_action(a))
    cb = sorted(_cards_of_action(b))
    return ca == cb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", type=str, default="")
    ap.add_argument("--pattern", type=str, default="game_records_v8/*.json")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(ROOT, args.pattern)))
    if args.limit:
        files = files[:args.limit]
    print(f"扫描 {len(files)} 个文件")

    all_results = []
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        results = analyze_record(d)
        for r in results:
            r["file"] = os.path.basename(f)
            r["game_id"] = d.get("game_id")
        all_results.extend(results)

    print("=" * 70)
    total_dec = len(all_results)
    rule_hit = [r for r in all_results if r["rule"]]
    print(f"残局决策点总数: {total_dec}；命中败招规则: {len(rule_hit)} 个")
    by_rule = defaultdict(int)
    for r in rule_hit:
        by_rule[r["rule"]] += 1
    for k in sorted(by_rule):
        print(f"  {k}: {by_rule[k]}")
    print()
    if rule_hit:
        print("── 败招清单 ──")
        for r in rule_hit[:30]:
            print(f"  [{r['rule']}] {r['file'][:40]} pos={r['my_pos']} hand={r['hand_size']}张")
            print(f"    hand={json.dumps(r['hand'], ensure_ascii=False)} greater={json.dumps(r['greater'], ensure_ascii=False)}")
            print(f"    V8={json.dumps(r['actual'], ensure_ascii=False)}  {r['detail']}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"total_decisions": total_dec, "rules_hit": len(rule_hit),
                       "results": all_results}, fh, ensure_ascii=False, indent=1)
        print(f"\n已写出 {args.out}")


if __name__ == "__main__":
    main()
