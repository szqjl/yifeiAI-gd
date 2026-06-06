#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate replay_word.md from a game record JSON."""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from communication.game_recorder import GameRecorder  # noqa: E402

RECORD_RE = re.compile(
    r"^(\d+) \[([^\]]+)\]-\[([^\]]+)\]-\[(\d+)\]-\[([^\]]*)\]\.json$"
)

LABELS = {
    0: "玩家0 (yf1_m3)",
    1: "玩家1 (对手@1)",
    2: "玩家2 (yf2_m3)",
    3: "玩家3 (对手@3)",
}


def is_pass(cur_action):
    return bool(cur_action) and cur_action[0] == "PASS"


def group_trick_rounds(actions):
    """Split actions into 掼蛋「轮」：从领出到该手牌权结束。"""
    groups = []
    current = []
    for i, action in enumerate(actions):
        ca = action.get("cur_action", [])
        gpos = action.get("greater_pos", -1)
        cpos = action.get("cur_pos", -1)

        if i > 0 and current and not is_pass(ca):
            prev_ca = actions[i - 1].get("cur_action", [])
            if gpos == -1 or (gpos == cpos and is_pass(prev_ca)):
                groups.append(current)
                current = []

        current.append(action)

    if current:
        groups.append(current)
    return groups


def main():
    record_path = REPO / (
        "game_records/20260529223719968305 [yf2_m3]-[opponent_1_3]-[19]-[K].json"
    )
    out_path = REPO / "replay_word.md"

    data = GameRecorder.load_game(record_path)
    m = RECORD_RE.match(record_path.name)
    if not m:
        raise SystemExit("filename parse failed")

    game_id, _player_name, _opponent, round_num, level = m.groups()
    gi = data.get("game_info") or {}
    self_rank = gi.get("selfRank", "2")
    oppo_rank = gi.get("oppoRank", "K")

    all_hands = data.get("all_players_hands", {})
    actions = data.get("actions", [])
    groups = group_trick_rounds(actions)

    replay_py = REPO / "scripts" / "tools" / "yf_replay.py"
    record_abs = record_path.resolve()
    replay_cmd_ps = (
        f'python "{replay_py}" "{record_abs}"'
    )
    replay_cmd_bat = (
        f'.\\YF_REPLAY.bat "game_records\\{record_path.name}"'
    )

    lines = [
        f"游戏记录：{record_path.name}",
        f"game_id：{game_id}",
        f"round：{round_num}",
        f"level：{level}",
        f"级数：本方 {self_rank} / 对方 {oppo_rank}",
        "",
        "回放命令（PowerShell，复制下面整行执行，不要只复制路径）：",
        "",
        "```powershell",
        replay_cmd_ps,
        "```",
        "",
        "或已在仓库根目录时：",
        "",
        "```powershell",
        replay_cmd_bat,
        "```",
        "",
        "【发牌后初始手牌】",
    ]
    for pos in range(4):
        cards = all_hands.get(str(pos), all_hands.get(pos, []))
        lines.append(f"{LABELS[pos]} | {cards}")

    lines.extend(["", "【出牌步骤】"])
    for ri, group in enumerate(groups, 1):
        lines.append(f"--- 第 {ri} 轮 ---")
        for action in group:
            cpos = action.get("cur_pos", -1)
            ca = action.get("cur_action", [])
            name = LABELS.get(cpos, f"玩家{cpos}")
            lines.append(f"{name} | {ca}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"written {out_path} ({len(groups)} rounds, {len(actions)} steps)")


if __name__ == "__main__":
    main()
