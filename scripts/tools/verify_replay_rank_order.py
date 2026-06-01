#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""随机抽一局 game_records，验证 1312 手牌列序（级牌在小王之后）。"""

import random
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts" / "tools"))

from communication.game_recorder import GameRecorder  # noqa: E402
from yf_replay import resolve_episode_levels  # noqa: E402

RECORD_RE = re.compile(
    r"^(\d+) \[([^\]]+)\]-\[([^\]]+)\]-\[(\d+)\]-\[([^\]]*)\]\.json$"
)
RANK_ORDER_AFTER_LEVEL = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]


def normalize_rank(rank_str):
    r = str(rank_str).strip().upper()
    if r in ("10", "T"):
        return "T"
    if r == "1":
        return "A"
    return r


def resolve_cur_rank(data, filename):
    levels = resolve_episode_levels(data, filename)
    m = RECORD_RE.match(filename)
    fn_level = m.group(5) if m else ""
    return levels["curRank"], fn_level


def hand_column_rank_order(cur_rank):
    level = normalize_rank(cur_rank)
    order = ["R", "B"]
    if level and level not in ("R", "B"):
        order.append(level)
    for rank in RANK_ORDER_AFTER_LEVEL:
        if rank != level:
            order.append(rank)
    return order, level


def card_rank(card):
    if not isinstance(card, str) or len(card) < 2:
        return None
    rank = card[1:]
    return "A" if rank == "1" else rank


def verify_record(path: Path) -> bool:
    data = GameRecorder.load_game(path)
    cur_rank, fn_level = resolve_cur_rank(data, path.name)
    order, level = hand_column_rank_order(cur_rank)

    hands = data.get("all_players_hands") or {}
    pid = data.get("player_id", 0)
    hand = hands.get(str(pid), hands.get(pid, data.get("initial_hand", [])))

    present = [r for r in order if r in {card_rank(c) for c in hand}]
    ok = True
    detail = "no level cards in hand"
    if level in present:
        bi = present.index("B") if "B" in present else -1
        li = present.index(level)
        ai = present.index("A") if "A" in present else len(present)
        if bi >= 0:
            ok = li == bi + 1
            detail = f"level@{li} right_after_B@{bi}"
        else:
            ok = li < ai
            detail = f"level@{li} before_A@{ai}"

    gi = data.get("game_info") or {}
    print("=" * 60)
    print(f"文件: {path.name}")
    print(f"game_id: {RECORD_RE.match(path.name).group(1) if RECORD_RE.match(path.name) else '?'}")
    print(f"round/level(文件名): {RECORD_RE.match(path.name).groups()[3:5] if RECORD_RE.match(path.name) else ('?','?')}")
    print(f"curRank: {cur_rank}  (文件名 level={fn_level})")
    print(f"selfRank/oppoRank: {gi.get('selfRank')} / {gi.get('oppoRank')}")
    print(f"列序: {' '.join(order)}")
    print(f"玩家{pid} 手牌 {len(hand)} 张，含级牌列: {present}")
    print(f"校验: {detail} -> {'PASS' if ok else 'FAIL'}")
    print()
    print("回放命令:")
    print(f'python "{REPO / "scripts/tools/yf_replay.py"}" "{path}"')
    print("=" * 60)
    return ok


def main():
    records_dir = REPO / "game_records"
    files = [f for f in records_dir.glob("*.json") if not f.name.startswith("enhanced_")]
    if not files:
        print("game_records 下无 JSON 记录")
        return 1
    pick = random.choice(files)
    print(f"随机抽取 ({len(files)} 局中): {pick.name}\n")
    return 0 if verify_record(pick) else 1


if __name__ == "__main__":
    raise SystemExit(main())
