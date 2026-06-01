#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extract play steps from a game record for replay_word.md."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts" / "tools"))

from communication.game_recorder import GameRecorder  # noqa: E402
from yf_replay import apply_tribute_back_to_hand  # noqa: E402

SUIT_DISPLAY = {"H": "\u2665", "D": "\u2666", "C": "\u2663", "S": "\u2660"}
RANK_DISPLAY = {"T": "10", "1": "A"}
NAMES = {0: "yf1_m3", 1: "对手@1", 2: "yf2_m3", 3: "对手@3"}


def fmt_card(card):
    if not isinstance(card, str) or len(card) < 2:
        return str(card)
    suit, rank = card[0], card[1:]
    if rank == "1":
        rank = "A"
    return f"{SUIT_DISPLAY.get(suit, suit)}{RANK_DISPLAY.get(rank, rank)}"


def parse_action(action):
    if isinstance(action, str):
        action = eval(action)
    if not isinstance(action, list) or len(action) < 1:
        return None
    at = (action[0] or "").upper()
    cards = action[2] if len(action) >= 3 else []
    return at, cards


def fmt_step(i, total, action):
    pos = action.get("cur_pos", -1)
    try:
        player = NAMES.get(int(pos), f"pos{pos}")
    except (TypeError, ValueError):
        player = f"pos{pos}"
    info = parse_action(action.get("cur_action"))
    header = f"{i}/{total}"
    if not info:
        raw = action.get("cur_action", "")
        return f"--- 第 {i} 步 ---\n{header}\n{player}\n{raw}"
    at, cards = info
    if at == "PASS":
        return f"--- 第 {i} 步 ---\n{header}\n{player}\n过"
    if isinstance(cards, list) and cards:
        names = " ".join(fmt_card(c) for c in cards)
        return f"--- 第 {i} 步 ---\n{header}\n{player}\n{names}"
    labels = {"TRIBUTE": "进贡", "BACK": "还贡", "DISPATCH": "发牌"}
    return f"--- 第 {i} 步 ---\n{header}\n{player}\n{labels.get(at, at)}"


def build_steps_section(fname: str) -> str:
    p = REPO / "game_records" / fname
    data = GameRecorder.load_game(p)
    actions = data.get("actions", [])
    total = len(actions)
    hands = data.get("all_players_hands", {})
    pid = data.get("player_id", 0)
    pos_key = str(pid)
    raw_hand = hands.get(pos_key, hands.get(pid, data.get("initial_hand", [])))
    if not isinstance(raw_hand, list):
        raw_hand = data.get("initial_hand", []) or []
    effective_hand = apply_tribute_back_to_hand(
        raw_hand, data.get("my_decisions", []), pid
    )

    lines = [
        "",
        "【发牌后有效起手（yf1 视角，已扣进贡/加收还贡）】",
        f"yf1_m3 | {effective_hand}",
        "",
        f"（贡前快照含 SB、无 S3，见 JSON initial_hand / all_players_hands）",
        "",
        f"【出牌步骤 · 共 {total} 步（与回放右下角复制块同格式：步数 / 玩家 / 牌）】",
        "",
    ]
    for i, action in enumerate(actions, 1):
        lines.append(fmt_step(i, total, action))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def strip_existing_sections(text: str) -> str:
    markers = ["\n【发牌后初始手牌", "\n【发牌后有效起手", "\n【出牌步骤"]
    cut = len(text)
    for marker in markers:
        idx = text.find(marker)
        if idx >= 0:
            cut = min(cut, idx)
    return text[:cut].rstrip()


def main():
    fname = sys.argv[1] if len(sys.argv) > 1 else (
        "20260531222316040665 [yf1_m3]-[opponent_1_3]-[40]-[K].json"
    )
    out = REPO / "replay_word.md"
    header = strip_existing_sections(out.read_text(encoding="utf-8"))
    section = build_steps_section(fname)
    out.write_text(header + section, encoding="utf-8")
    print(f"wrote {out} ({section.count('--- 第')} steps)")


if __name__ == "__main__":
    main()
