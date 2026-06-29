#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""认证/复现：actionList 仅 PASS 统计（归档报告见 docs/analysis/archive/南邮离线平台-actionList候选缺失观测报告.md）"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.v.nn.guards.v7_guards import get_action_type, get_card_rank, get_card_value

REPORT_CASES = [
    {
        "id": 1,
        "file": "20260628201953141540 [yf2_v7]-[opponent_1_3]-[4]-[2].json",
        "match": lambda c: (
            c.get("handCards_size") == 1
            and c.get("handCards") == ["DA"]
            and (c.get("greaterAction") or [None])[0] == "Single"
        ),
    },
    {
        "id": 2,
        "file": "20260628201953682662 [yf1_v7]-[opponent_1_3]-[5]-[2].json",
        "match": lambda c: (
            c.get("handCards") == ["H2", "H2", "D2", "D4"]
            and (c.get("greaterAction") or [None])[0] == "Pair"
            and (c.get("greaterAction") or [None, None])[1] == "6"
        ),
    },
    {
        "id": 3,
        "file": "20260628201953682662 [yf1_v7]-[opponent_1_3]-[5]-[2].json",
        "match": lambda c: (
            c.get("handCards") == ["H2", "H2", "D2", "D4"]
            and (c.get("greaterAction") or [None])[0] == "Trips"
        ),
    },
    {
        "id": 4,
        "file": "20260628201951214091 [yf1_v7]-[opponent_1_3]-[2]-[2].json",
        "match": lambda c: (
            set(c.get("handCards") or []) >= {"S2", "H2", "C2", "D2"}
            and (c.get("greaterAction") or [None])[0] == "Bomb"
            and (c.get("greaterAction") or [None, None])[1] == "7"
        ),
    },
    {
        "id": 5,
        "file": "20260628201953682662 [yf1_v7]-[opponent_1_3]-[5]-[2].json",
        "match": lambda c: (
            c.get("handCards_size") == 25
            and (c.get("greaterAction") or [None])[0] == "StraightFlush"
        ),
    },
]


def _rank_counts(hand: List[str], cur_rank: str) -> Counter:
    c: Counter = Counter()
    for card in hand:
        c[get_card_rank(card)] += 1
    return c


def _greater_strength(ga: List, cur_rank: str) -> Tuple[str, int, int]:
    """返回 (type, primary_rank_value, n_cards) 粗粒度强度。"""
    gtype = ga[0]
    grank = str(ga[1]) if len(ga) > 1 else ""
    cards = ga[2] if len(ga) > 2 and isinstance(ga[2], list) else []
    n = len(cards)
    if gtype == "Single":
        return gtype, get_card_value(cards[0], cur_rank), 1
    if gtype in ("Pair", "Trips", "Bomb"):
        rv = get_card_value(grank, cur_rank) if grank not in ("PASS", "SB", "HR", "R", "B") else 0
        if gtype == "Single" and cards:
            rv = get_card_value(cards[0], cur_rank)
        return gtype, rv, n if gtype == "Bomb" else {"Pair": 2, "Trips": 3}.get(gtype, n)
    if gtype == "StraightFlush":
        return gtype, get_card_value(grank, cur_rank), 5
    return gtype, 0, n


def hand_can_beat_same_type(hand: List[str], ga: List, cur_rank: str) -> Tuple[bool, str]:
    """客户端侧独立判断：同型是否存在可压 greaterAction 的牌（不含改炸/SF 复杂枚举）。"""
    if not ga or ga[0] in ("PASS", None) or not hand:
        return False, "无有效 greaterAction"
    gtype, gval, gn = _greater_strength(ga, cur_rank)
    counts = _rank_counts(hand, cur_rank)

    if gtype == "Single":
        for card in hand:
            if get_card_value(card, cur_rank) > gval:
                return True, f"单张 {card}({get_card_value(card, cur_rank)}) > {gval}"
        return False, f"无单张 > {gval}"

    if gtype == "Pair":
        for r, cnt in counts.items():
            if cnt >= 2 and get_card_value(r, cur_rank) > gval:
                return True, f"对子 rank={r} val={get_card_value(r, cur_rank)} > {gval}"
        return False, f"无对子 > {gval}"

    if gtype == "Trips":
        for r, cnt in counts.items():
            if cnt >= 3 and get_card_value(r, cur_rank) > gval:
                return True, f"三张 rank={r} val={get_card_value(r, cur_rank)} > {gval}"
        return False, f"无三张 > {gval}"

    if gtype == "Bomb":
        for r, cnt in counts.items():
            if cnt >= 4:
                rv = get_card_value(r, cur_rank)
                if cnt > gn or (cnt == gn and rv > gval):
                    return True, f"炸弹 {cnt}×{r} val={rv} 可压 {gn}×{ga[1]}"
        return False, f"无更大炸弹"

    if gtype == "StraightFlush":
        for r, cnt in counts.items():
            if cnt >= 4:
                return True, f"有 {cnt} 张 {r} 可组炸弹改压 SF"
        return False, "未检测到 4+ 同点（SF 改压需更完整枚举）"

    return False, f"未覆盖牌型 {gtype}"


def is_pass_only(ctx: Dict[str, Any]) -> bool:
    if ctx.get("actionList_size") != 1:
        return False
    sample = ctx.get("actionList_sample") or []
    if sample and sample[0].get("type") == "PASS":
        return True
    return ctx.get("stage") == "play" and ctx.get("source") == "act"


def iter_play_decisions(record: dict):
    for d in record.get("my_decisions") or []:
        ctx = d.get("context") or {}
        if ctx.get("stage") != "play" or ctx.get("source") != "act":
            continue
        yield d, ctx


def load_record(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def verify_report_cases(records_dir: Path) -> None:
    print("=" * 60)
    print("§ 报告五案例 — 牌谱锚点 + 独立可压判定")
    print("=" * 60)
    for case in REPORT_CASES:
        path = records_dir / case["file"]
        rec = load_record(path)
        found = None
        for d, ctx in iter_play_decisions(rec):
            if case["match"](ctx) and is_pass_only(ctx):
                found = (d, ctx)
                break
        print(f"\n案例 {case['id']}  {case['file']}")
        if not found:
            print("  ❌ 未在牌谱中找到匹配的 pass-only 决策点")
            continue
        _, ctx = found
        ga = ctx.get("greaterAction")
        hand = ctx.get("handCards") or []
        cur = str(ctx.get("curRank") or "2")
        can, reason = hand_can_beat_same_type(hand, ga, cur)
        sample = ctx.get("actionList_sample")
        print(f"  curRank={cur}  hand({len(hand)}): {hand[:8]}{'...' if len(hand)>8 else ''}")
        print(f"  greaterAction: {ga}")
        print(f"  actionList_sample: {sample}")
        print(f"  平台仅 PASS: ✅ 已复现 (actionList_size=1)")
        print(f"  同型可压(客户端规则): {'✅ 是 — 平台疑似漏候选' if can else '⚠️ 否 — ' + reason}")


def batch_stats(glob_pat: str, records_dir: Path) -> None:
    files = sorted(records_dir.glob(glob_pat))
    total = pass_only = 0
    can_beat = need_bomb = legit_pass = 0
    hand_bins = Counter()
    gpos_bins = Counter()

    for path in files:
        rec = load_record(path)
        for _, ctx in iter_play_decisions(rec):
            total += 1
            if not is_pass_only(ctx):
                continue
            pass_only += 1
            hs = ctx.get("handCards_size") or len(ctx.get("handCards") or [])
            if hs <= 5:
                hand_bins["≤5"] += 1
            elif hs <= 10:
                hand_bins["6-10"] += 1
            elif hs <= 15:
                hand_bins["11-15"] += 1
            elif hs <= 20:
                hand_bins["16-20"] += 1
            else:
                hand_bins["21+"] += 1
            gpos_bins[ctx.get("greaterPos", -1)] += 1

            ga = ctx.get("greaterAction")
            hand = ctx.get("handCards") or []
            cur = str(ctx.get("curRank") or "2")
            if not ga or ga[0] in ("PASS", None):
                legit_pass += 1
                continue
            can, _ = hand_can_beat_same_type(hand, ga, cur)
            if can:
                can_beat += 1
            elif get_action_type(ga) == "StraightFlush":
                need_bomb += 1
            else:
                _, _, gn = _greater_strength(ga, cur)
                counts = _rank_counts(hand, cur)
                has_bomb = any(v >= 4 for v in counts.values())
                if has_bomb and get_action_type(ga) != "Bomb":
                    need_bomb += 1
                else:
                    legit_pass += 1

    print("\n" + "=" * 60)
    print(f"§ 批跑复现  glob={glob_pat}  files={len(files)}")
    print("=" * 60)
    print(f"决策点(play/act): {total}")
    print(f"actionList 仅 PASS: {pass_only} ({100*pass_only/max(1,total):.1f}%)")
    sub = pass_only or 1
    print(f"  同型可压(粗判): {can_beat} ({100*can_beat/sub:.1f}%)")
    print(f"  可能需炸弹/SF改压: {need_bomb} ({100*need_bomb/sub:.1f}%)")
    print(f"  PASS 合理(粗判): {legit_pass} ({100*legit_pass/sub:.1f}%)")
    print("手牌数分布(pass-only):")
    for k in ["≤5", "6-10", "11-15", "16-20", "21+"]:
        print(f"  {k}: {hand_bins[k]} ({100*hand_bins[k]/sub:.1f}%)")
    print("greaterPos 分布:")
    for pos in sorted(gpos_bins):
        print(f"  {pos}: {gpos_bins[pos]} ({100*gpos_bins[pos]/sub:.1f}%)")


def evidence_matches(records_dir: Path, evidence_dir: Path) -> None:
    print("\n" + "=" * 60)
    print("§ evidence 备份 vs game_records_v7 一致性")
    print("=" * 60)
    for ev in sorted(evidence_dir.glob("*.json")):
        src = records_dir / ev.name
        if not src.exists():
            print(f"  ❌ 源牌谱缺失: {ev.name}")
            continue
        a, b = load_record(src), load_record(ev)
        na, nb = len(a.get("my_decisions") or []), len(b.get("my_decisions") or [])
        same = na == nb and a.get("game_id") == b.get("game_id")
        print(f"  {ev.name}: decisions {na} vs {nb}  game_id一致={a.get('game_id')==b.get('game_id')}  {'✅' if same else '⚠️'}")


def main():
    records_dir = ROOT / "game_records_v7"
    evidence_dir = ROOT / "docs" / "analysis" / "evidence"
    verify_report_cases(records_dir)
    batch_stats("202606282019*.json", records_dir)
    if evidence_dir.is_dir():
        evidence_matches(records_dir, evidence_dir)
    print("\n§ 客户端 normalize_action_list: 仅规范 action[2] 字符串，不增删候选 (v7_game_recorder.py)")


if __name__ == "__main__":
    main()
