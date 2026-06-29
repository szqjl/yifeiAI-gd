#!/usr/bin/env python3
"""WF-12: 复现 20260628091704590941 首出 action_index=973 决策链路。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

RECORD = ROOT / "game_records_v7" / (
    "20260628091704590941 [yf1_v7]-[opponent_1_3]-[11]-[2].json"
)
TARGET = ["ThreeWithTwo", "K", ["HK", "DK", "H8", "CT", "CT"]]
HAND = [
    "S2", "H2", "C3", "C3", "C4", "C5", "C6", "S7", "H7", "D7",
    "S9", "H9", "D9", "ST", "HT", "CT", "CT", "DT", "SQ", "HQ",
    "DQ", "SK", "SK", "HK", "DK", "HA", "H8",
]


def load_first_play_decision() -> dict:
    data = json.loads(RECORD.read_text(encoding="utf-8"))
    for d in data["my_decisions"]:
        if d.get("context", {}).get("stage") == "play" and d.get("action_index") == 973:
            return d
    raise SystemExit("decision 973 not found")


def rebuild_group_members(
    card_mask: Dict[str, tuple],
    group_type_map: Dict[str, str],
    hand: List[str],
) -> Dict[int, List[str]]:
    """从 hand + card_mask 反推 multiset group_members（补 JSON 重复 key 丢失）。"""
    from collections import Counter, defaultdict

    hand_c = Counter(hand)
    gid_cards: Dict[int, List[str]] = defaultdict(list)
    assigned: Counter = Counter()

    # 先按 card_mask 中每张牌所属 gid 分配
    for card, (gid, _, _) in card_mask.items():
        if gid >= 0:
            gid_cards[gid].append(card)
            assigned[card] += 1

    # 把 hand 里同牌串未分配的枚数补进同 gid（重复 key 场景）
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


def build_minimal_action_list(target_idx: int = 973) -> List:
    """构造 len=1234 的 actionList：0=PASS，1=Single/DT，973=目标三带二。"""
    al: List = [["PASS", "PASS", "PASS"]]
    al.append(["Single", "T", ["DT"]])
    al.append(["Single", "A", ["HA"]])
    while len(al) < target_idx:
        al.append(["Single", "3", ["C3"]])  # filler
    al.append(TARGET)
    while len(al) < 1234:
        al.append(["Pair", "2", ["S2", "H2"]])
    return al


def trace_pipeline(engine: UltimateWinRateEngineV7, gs: dict, al: List) -> None:
    from src.v.nn.guards.v7_guards import filter_action_list

    print("\n=== ① 组牌（已冻结为牌谱 card_mask）===")
    print(f"role={engine._current_role}")
    print(f"group_type_map={engine._group_type_map}")
    for gid, cards in sorted(engine._group_members.items()):
        gtype = engine._group_type_map.get(gid, "?")
        print(f"  gid={gid} type={gtype} cards={cards}")

    print("\n=== ⑤ GUA-075 主路径 ===")
    rec = engine._recommend_play(gs, al)
    print(f"recommend={rec}")
    if rec:
        mi = engine._match_actionList(rec, al)
        print(f"match_index={mi} action={al[mi] if mi >= 0 else None}")
        if mi >= 0:
            qg = engine._quick_guard_validate(mi, al, gs)
            print(f"quick_guard={qg}")
            broken = UltimateWinRateEngineV7._get_broken_core_type(
                al[mi], engine._card_mask, engine._group_type_map, engine._group_members
            )
            print(f"broken_core={broken}")

    print("\n=== 回退：Guard filter ===")
    try:
        filtered, action_map = filter_action_list(gs)
        print(f"guard: {len(al)} -> {len(filtered)}")
    except Exception as e:
        print(f"guard failed: {e}")
        filtered, action_map = al, list(range(len(al)))

    print("\n=== 回退：group_consistency_filter ===")
    group_actions, flt_map = engine._group_consistency_filter(filtered, gs)
    print(f"group_filter: {len(filtered)} -> {len(group_actions)}")

    target_in_group = any(
        a[0:3] == TARGET[0:3] and sorted(a[2]) == sorted(TARGET[2])
        for a in group_actions
    )
    print(f"ThreeWithTwo/K in group_actions? {target_in_group}")

    broken_tgt = UltimateWinRateEngineV7._get_broken_core_type(
        TARGET, engine._card_mask, engine._group_type_map, engine._group_members
    )
    print(f"TARGET broken_core={broken_tgt}")

    print("\n=== 回退：heuristic top-5 ===")
    from src.v.nn.guards.v7_guards import get_action_type

    hi = engine._heuristic_select(gs, group_actions)
    print(f"heuristic_pick idx={hi} action={group_actions[hi]}")

    # score top actions
    scores = []
    mask = engine._card_mask or {}

    def score_action(action):
        cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else action
        gids = set()
        for c in cards:
            ent = mask.get(str(c))
            if ent and ent[0] >= 0:
                gids.add(ent[0])
        consistent = len(gids) == 1
        broken = UltimateWinRateEngineV7._get_broken_core_type(
            action, engine._card_mask, engine._group_type_map, engine._group_members
        )
        return consistent, broken, gids

    for i, a in enumerate(group_actions[:20]):
        if get_action_type(a) == "PASS":
            continue
        scores.append((i, a[0], a[1], score_action(a)))
    for row in scores[:8]:
        print(f"  gidx={row[0]} {row[1]}/{row[2]} consistent={row[3][0]} broken={row[3][1]} gids={row[3][2]}")

    print("\n=== decide() 全链路 ===")
    idx = engine.decide(gs)
    chosen = al[idx] if idx < len(al) else None
    print(f"decide() -> {idx} action={chosen}")
    if chosen and chosen[0] == "ThreeWithTwo":
        print("FAIL: still playing destructive TWT via wrong index")
    elif idx == 973 and chosen != TARGET:
        print(f"OK: index 973 not forced; actual={chosen[:3] if chosen else None}")


def main() -> None:
    dec = load_first_play_decision()
    ctx = dec["context"]
    card_mask_raw = ctx["card_mask"]
    card_mask = {k: tuple(v) for k, v in card_mask_raw.items()}
    group_type_map = {int(k): v for k, v in ctx["group_type_map"].items()}
    group_members = rebuild_group_members(card_mask, ctx["group_type_map"], HAND)

    al = build_minimal_action_list(973)
    gs = {
        "myPos": 0,
        "curPos": -1,
        "greaterPos": -1,
        "greaterAction": [],
        "handCards": HAND,
        "actionList": al,
        "curRank": "8",
        "selfRank": "8",
        "oppoRank": "8",
        "publicInfo": [{}, {}, {}, {}],
        "numofplayers": [27, 27, 27, 27],
    }

    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=False)
    engine._card_mask = card_mask
    engine._group_type_map = group_type_map
    engine._group_members = group_members
    engine._current_role = ctx.get("role", "主攻")

    print("牌谱首出决策 trace — action_index=973")
    print(f"TARGET={TARGET}")
    trace_pipeline(engine, gs, al)


if __name__ == "__main__":
    main()
