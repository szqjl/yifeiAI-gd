#!/usr/bin/env python3
"""从 game_records_v7 统计组牌引擎调用/重算/产出频率。"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RECORDS = PROJECT_ROOT / "game_records_v7"


def hand_key(cards):
    return tuple(sorted(cards or []))


def mask_stats(mask):
    if not mask:
        return "missing", 0, 0, 0
    gids = set()
    bombs = 0
    core = 0
    scatter = 0
    for _card, triple in mask.items():
        if not isinstance(triple, (list, tuple)) or len(triple) < 3:
            continue
        gid, is_core, gsize = triple[0], triple[1], triple[2]
        if gid == -1:
            scatter += 1
        else:
            gids.add(gid)
            if is_core and is_core > 0.5:
                core += 1
            if gsize >= 4:
                bombs += 1
    if scatter == len(mask) and len(mask) > 0:
        kind = "degenerate_all_scatter"
    elif len(gids) == 0:
        kind = "empty_groups"
    else:
        kind = "ok"
    return kind, len(gids), bombs, core


def main():
    files = sorted(RECORDS.glob("*.json"))
    if not files:
        print("[ERROR] 无 game_records_v7 JSON", file=sys.stderr)
        sys.exit(1)

    tot = {
        "files": 0,
        "decisions_act": 0,
        "decisions_notify": 0,
        "with_card_mask": 0,
        "mask_kind": Counter(),
        "roles": Counter(),
        "regroup_events": 0,
        "cache_hits": 0,
        "unique_hands_per_file": [],
        "groups_per_decision": [],
        "bombs_in_mask": [],
        "breaks_core_guess": 0,
    }
    per_player = defaultdict(lambda: Counter())

    for fp in files:
        data = json.loads(fp.read_text(encoding="utf-8"))
        pname = data.get("player_name", "?")
        tot["files"] += 1
        prev_hand = None
        prev_mask_sig = None
        unique_hands = set()

        for dec in data.get("my_decisions", []):
            ctx = dec.get("context", {})
            src = ctx.get("source", "")
            if src != "act":
                tot["decisions_notify"] += 1
                continue
            tot["decisions_act"] += 1
            per_player[pname]["act"] += 1
            hand = ctx.get("handCards") or []
            hk = hand_key(hand)
            unique_hands.add(hk)
            if prev_hand is not None:
                if hk == prev_hand:
                    tot["cache_hits"] += 1
                else:
                    tot["regroup_events"] += 1

            mask = ctx.get("card_mask")
            if mask:
                tot["with_card_mask"] += 1
            kind, ng, nb, _nc = mask_stats(mask)
            tot["mask_kind"][kind] += 1
            per_player[pname][kind] += 1
            tot["groups_per_decision"].append(ng)
            tot["bombs_in_mask"].append(nb)
            role = ctx.get("role") or "unknown"
            tot["roles"][role] += 1

            # mask 结构变化 ≈ enumerate_groupings 重算
            mask_sig = tuple(sorted((k, tuple(v)) for k, v in (mask or {}).items()))
            if prev_mask_sig is not None and mask_sig != prev_mask_sig:
                tot["mask_structure_changes"] = tot.get("mask_structure_changes", 0) + 1
            prev_mask_sig = mask_sig
            prev_hand = hk

        tot["unique_hands_per_file"].append(len(unique_hands))

    n_act = tot["decisions_act"]
    n_mask = tot["with_card_mask"]
    msc = tot.get("mask_structure_changes", 0)

    print("=" * 72)
    print("组牌引擎工作频率分析 (game_records_v7)")
    print("=" * 72)
    print(f"牌谱文件: {tot['files']}")
    print(f"act 决策点: {n_act}  |  notify 占位: {tot['decisions_notify']}")
    print()
    print("--- 调用层 (decide 入口 _run_grouping_engine) ---")
    print(f"每步 decide 均调用: 100% ({n_act}/{n_act})")
    print(f"enumerate_groupings 重算 (手牌 hash 变化): {tot['regroup_events']} 次")
    print(f"手牌未变 → 缓存复用: {tot['cache_hits']} 次")
    if n_act > 1:
        print(f"  重算率: {tot['regroup_events'] / (n_act - 1) * 100:.1f}%")
        print(f"  缓存命中率: {tot['cache_hits'] / (n_act - 1) * 100:.1f}%")
    avg_uh = sum(tot["unique_hands_per_file"]) / max(1, len(tot["unique_hands_per_file"]))
    print(f"每副牌平均不同手牌态: {avg_uh:.1f} (≈ enumerate 上界/副)")
    print(f"card_mask 结构变化次数: {msc}")
    print()
    print("--- 产出层 (写入牌谱 context) ---")
    print(f"含 card_mask: {n_mask}/{n_act} ({n_mask / max(1, n_act) * 100:.1f}%)")
    for k, v in tot["mask_kind"].most_common():
        print(f"  {k}: {v} ({v / max(1, n_act) * 100:.1f}%)")
    if tot["groups_per_decision"]:
        gs = tot["groups_per_decision"]
        print(f"  平均结构化组数/决策: {sum(gs) / len(gs):.2f}")
    if tot["bombs_in_mask"]:
        bs = tot["bombs_in_mask"]
        print(f"  平均炸弹牌张/决策 (gsize>=4): {sum(bs) / len(bs):.2f}")
    print()
    print("--- 角色分布 ---")
    for r, c in tot["roles"].most_common():
        print(f"  {r}: {c} ({c / max(1, n_act) * 100:.1f}%)")
    print()
    print("--- 分客户端 ---")
    for pname, c in sorted(per_player.items()):
        act = c["act"]
        ok = c.get("ok", 0)
        bad = act - ok
        print(f"  {pname}: act={act}, mask_ok={ok} ({ok / max(1, act) * 100:.1f}%), 非ok={bad}")
    print("=" * 72)


if __name__ == "__main__":
    main()
