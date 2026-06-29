#!/usr/bin/env python3
"""WF-12: 复现 20260628091704590941 步9 yf1 Single/C5 决策链路。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.v.nn.guards.v7_guards import filter_action_list
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

RECORD = ROOT / "game_records_v7" / (
    "20260628091704590941 [yf1_v7]-[opponent_1_3]-[11]-[2].json"
)


def rebuild_group_members(card_mask, hand):
    from collections import Counter, defaultdict

    hand_c = Counter(hand)
    gid_cards = defaultdict(list)
    assigned = Counter()
    for card, (gid, _, _) in card_mask.items():
        if gid >= 0:
            gid_cards[gid].append(card)
            assigned[card] += 1
    for card, cnt in hand_c.items():
        extra = cnt - assigned[card]
        if extra <= 0:
            continue
        info = card_mask.get(card)
        if info and info[0] >= 0:
            gid_cards[info[0]].extend([card] * extra)
    scatter = [c for c in hand if card_mask.get(c, (-1, 0, 1))[0] < 0]
    if scatter:
        gid_cards[-1] = scatter
    return dict(gid_cards)


def load_step9_decision():
    data = json.loads(RECORD.read_text(encoding="utf-8"))
    play = [d for d in data["my_decisions"] if d.get("context", {}).get("stage") == "play"]
    # 0=首出TWT, 1=PASS, 2=C5
    return play[2]


def build_action_list(hand, greater_action, cur_rank="8"):
    """构造含 PASS + 可压 Single/4 的最小 actionList（步9 共17项量级）。"""
    al = [["PASS", "PASS", "PASS"]]
    # 散牌单张可压 H4
    from src.v.nn.guards.v7_guards import get_card_rank, get_card_value

    ga_val = get_card_value("H4", cur_rank)
    singles = []
    for c in sorted(set(hand)):
        if get_card_value(c, cur_rank) > ga_val:
            r = get_card_rank(c)
            singles.append(["Single", r, [c]])
    singles.sort(key=lambda a: get_card_value(a[2][0], cur_rank))
    al.extend(singles)
    return al


def main():
    dec = load_step9_decision()
    ctx = dec["context"]
    hand = ctx["handCards"]
    card_mask = {k: tuple(v) for k, v in ctx["card_mask"].items()}
    gtm = {int(k): v for k, v in ctx["group_type_map"].items()}
    gm = rebuild_group_members(card_mask, hand)

    greater = ["Single", "4", ["H4"]]
    al = build_action_list(hand, greater)
    gs = {
        "myPos": 0,
        "curPos": 3,
        "greaterPos": 3,
        "greaterAction": greater,
        "handCards": hand,
        "actionList": al,
        "curRank": "8",
        "selfRank": "8",
        "oppoRank": "8",
        "publicInfo": [{}, {}, {}, {}],
        "numofplayers": [22, 27, 27, 27],
    }

    eng = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=False)
    eng._card_mask = card_mask
    eng._group_type_map = gtm
    eng._group_members = gm
    eng._current_role = ctx.get("role", "主攻")
    UltimateWinRateEngineV7._run_grouping_engine = lambda self, gs: None

    print("=== WF-12 步9/86 yf1 Single/C5 ===")
    print(f"record action_index={dec['action_index']} action={dec['action']}")
    print(f"role={eng._current_role} hand={len(hand)} actionList_size(record)={ctx['actionList_size']}")
    print(f"greaterPos=3 greaterAction={greater}")
    print("scatter:", [c for c, v in card_mask.items() if v[0] < 0])

    rec = eng._recommend_play(gs, al)
    print(f"\nL2 GUA-075 recommend={rec}")
    if rec:
        mi = eng._match_actionList(rec, al)
        print(f"  match_index={mi} action={al[mi] if mi >= 0 else None}")
        if mi >= 0:
            qg = eng._quick_guard_validate(mi, al, gs)
            broken = UltimateWinRateEngineV7._get_broken_core_type(
                al[mi], card_mask, gtm, gm)
            print(f"  quick_guard={qg} broken_core={broken}")

    filtered, am = filter_action_list(gs)
    ga, flt = eng._group_consistency_filter(filtered, gs)
    print(f"\nL3 guard {len(al)}->{len(filtered)}  L4 group {len(filtered)}->{len(ga)}")

    hi = eng._heuristic_select(gs, ga)
    print(f"L7 heuristic idx={hi} action={ga[hi] if hi < len(ga) else None}")

    idx = eng.decide(gs)
    print(f"\ndecide() -> {idx} {al[idx] if idx < len(al) else None}")


if __name__ == "__main__":
    main()
