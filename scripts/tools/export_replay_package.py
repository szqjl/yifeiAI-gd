#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""导出单副牌谱为视频思路文件夹：game_records_v7 + replay_word + YF_REPLAY.bat。"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from communication.game_recorder import GameRecorder  # noqa: E402

RECORD_RE = re.compile(
    r"^(\d+) \[([^\]]+)\]-\[([^\]]+)\]-\[(\d+)\]-\[([^\]]*)\]\.json$"
)

SUIT_DISPLAY = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}
RANK_DISPLAY = {"T": "10", "1": "A"}
PLAYER_LABELS = {
    0: "玩家0 (yf1)",
    1: "玩家1 (对手@1)",
    2: "玩家2 (yf2)",
    3: "玩家3 (对手@3)",
}


def fmt_card(card: str) -> str:
    if not isinstance(card, str) or len(card) < 2:
        return str(card)
    suit, rank = card[0], card[1:]
    if rank == "1":
        rank = "A"
    return f"{SUIT_DISPLAY.get(suit, suit)}{RANK_DISPLAY.get(rank, rank)}"


def parse_action(action) -> tuple[str, list]:
    if isinstance(action, str):
        try:
            action = json.loads(action.replace("'", '"'))
        except json.JSONDecodeError:
            action = eval(action, {"__builtins__": {}})
    if not isinstance(action, list) or not action:
        return "", []
    at = str(action[0] or "")
    cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else []
    return at, cards


def fmt_action_line(action) -> str:
    at, cards = parse_action(action)
    if at.upper() == "PASS":
        return "过"
    if at.lower() in ("tribute",):
        return "进贡 " + " ".join(fmt_card(c) for c in cards)
    if at.lower() in ("back",):
        return "还贡 " + " ".join(fmt_card(c) for c in cards)
    if cards:
        return " ".join(fmt_card(c) for c in cards)
    return at or "?"


def _match_yf_decision(action: dict, decisions: list, used: set) -> dict | None:
    """按 cur_pos + action 粗匹配本步 yf 决策记录。"""
    cpos = action.get("cur_pos")
    cur = action.get("cur_action")
    for idx, md in enumerate(decisions):
        if idx in used:
            continue
        ctx = md.get("context") or {}
        if ctx.get("myPos") != cpos:
            continue
        md_act = md.get("action")
        if md_act == cur or str(md_act) == str(cur):
            used.add(idx)
            return md
    return None


def build_replay_word(
    record_path: Path,
    data: dict,
    *,
    anchor_steps: list[int] | None = None,
    notes: str = "",
) -> str:
    m = RECORD_RE.match(record_path.name)
    if not m:
        raise ValueError(f"无法解析文件名: {record_path.name}")
    game_id, player_name, opponent, round_num, level = m.groups()
    gi = data.get("game_info") or {}
    actions = data.get("actions") or []
    decisions = data.get("my_decisions") or []
    total = len(actions)
    anchor_steps = anchor_steps or []

    lines = [
        f"游戏记录：{record_path.name}",
        f"game_id：{game_id}",
        f"副次：第 {round_num} 副",
        f"开局级牌标签：[{level}]（分析以 act·play 的 curRank 为准）",
        f"本方/对方级：{gi.get('selfRank', '?')} / {gi.get('oppoRank', '?')}",
        f"录制视角：{player_name}（player_id={data.get('player_id')})",
        f"总步数：{total}",
        "",
        "【回放】",
        f"双击本目录 YF_REPLAY.bat，或在仓库根目录执行：",
        f'  YF_REPLAY.bat "{record_path.as_posix()}"',
        "",
    ]
    if notes:
        lines.extend(["【说明】", notes, ""])

    if anchor_steps:
        lines.append("【锚点步（视频重点）】")
        for s in anchor_steps:
            if 1 <= s <= total:
                a = actions[s - 1]
                pl = PLAYER_LABELS.get(a.get("cur_pos", -1), f"玩家{a.get('cur_pos')}")
                lines.append(f"  步 {s}/{total} · {pl} · {fmt_action_line(a.get('cur_action'))}")
        lines.append("")

    hands = data.get("all_players_hands") or {}
    lines.append("【发牌后初始手牌（JSON 快照）】")
    for pos in range(4):
        cards = hands.get(str(pos), hands.get(pos, []))
        lines.append(f"{PLAYER_LABELS[pos]} | {cards}")
    lines.append("")

    lines.append(
        f"【出牌步骤 · 共 {total} 步（格式与回放右下角复制块一致：步数 / 玩家 / 牌）】"
    )
    lines.append("")

    used_md: set[int] = set()
    for i, action in enumerate(actions, 1):
        cpos = action.get("cur_pos", -1)
        pl = PLAYER_LABELS.get(cpos, f"玩家{cpos}")
        tag = " ★锚点" if i in anchor_steps else ""
        lines.append(f"--- 第 {i} 步{tag} ---")
        lines.append(f"{i}/{total}")
        lines.append(pl)
        lines.append(fmt_action_line(action.get("cur_action")))
        md = _match_yf_decision(action, decisions, used_md)
        if md and cpos == data.get("player_id"):
            layer = md.get("layer") or ""
            intent = (md.get("context") or {}).get("intent") or md.get("intent")
            extra = []
            if layer:
                extra.append(f"layer={layer}")
            if intent:
                extra.append(f"intent={intent}")
            if extra:
                lines.append(f"【yf决策】{' · '.join(extra)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_yf_replay_bat(export_dir: Path, record_rel: Path, repo_root: Path) -> None:
    bat = export_dir / "YF_REPLAY.bat"
    json_abs = (export_dir / record_rel).resolve()
    repo = repo_root.resolve()
    content = f"""@echo off
chcp 65001 >nul 2>&1
set "REPO={repo}"
set "RECORD={json_abs}"
echo ========================================
echo YiFei AI Replay - 本副导出包
echo ========================================
echo 牌谱: %RECORD%
echo 仓库: %REPO%
echo.
if not exist "%REPO%\\scripts\\tools\\yf_replay.py" (
  echo [ERROR] 未找到回放程序，请确认 REPO 路径正确。
  pause
  exit /b 1
)
if not exist "%RECORD%" (
  echo [ERROR] 牌谱文件不存在。
  pause
  exit /b 1
)
cd /d "%REPO%"
py scripts\\tools\\yf_replay.py "%RECORD%"
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo [ERROR] Replay failed with exit code %EXITCODE%
  pause
)
exit /b %EXITCODE%
"""
    bat.write_text(content, encoding="utf-8-sig")


def export_package(
    record_path: Path,
    out_dir: Path,
    *,
    repo_root: Path = REPO,
    anchor_steps: list[int] | None = None,
    notes: str = "",
    copy_trace: bool = True,
) -> Path:
    record_path = record_path.resolve()
    if not record_path.is_file():
        raise FileNotFoundError(record_path)

    out_dir = out_dir.resolve()
    gr_dir = out_dir / "game_records_v7"
    gr_dir.mkdir(parents=True, exist_ok=True)

    dest_json = gr_dir / record_path.name
    shutil.copy2(record_path, dest_json)

    data = GameRecorder.load_game(dest_json)
    replay_word = build_replay_word(
        dest_json, data, anchor_steps=anchor_steps, notes=notes
    )
    (out_dir / "replay_word.md").write_text(replay_word, encoding="utf-8")

    record_rel = Path("game_records_v7") / record_path.name
    write_yf_replay_bat(out_dir, record_rel, repo_root)

    if copy_trace:
        trace = repo_root / "game_decision_traces" / f"{data.get('game_id')}.jsonl"
        if trace.is_file():
            td = out_dir / "game_decision_traces"
            td.mkdir(exist_ok=True)
            shutil.copy2(trace, td / trace.name)

  # 尝试合并同 game_id 的队友 JSON（若仓库内有）
    game_id = data.get("game_id")
    m = RECORD_RE.match(record_path.name)
    if m:
        round_num, suffix = m.group(4), m.group(5)
        my_name = m.group(2)
        mate = "yf1_v7" if "yf2" in my_name else "yf2_v7"
        for sibling in (repo_root / "game_records_v7").glob(f"{game_id}*"):
            sm = RECORD_RE.match(sibling.name)
            if not sm or sm.group(2) != mate:
                continue
            if sm.group(4) == round_num and sm.group(5) == suffix:
                shutil.copy2(sibling, gr_dir / sibling.name)
                break

    readme = out_dir / "README.txt"
    readme.write_text(
        "\n".join(
            [
                "掼蛋回放导出包",
                f"game_id: {game_id}",
                "",
                "1. 双击 YF_REPLAY.bat 打开 GUI 回放",
                "2. 右下角可复制当前步（步数/玩家/牌）",
                "3. replay_word.md 含全部 74 步文字稿 + yf 决策标注",
                "",
                f"依赖仓库: {repo_root}",
            ]
        ),
        encoding="utf-8",
    )
    return out_dir


def main():
    parser = argparse.ArgumentParser(description="导出单副牌谱回放包")
    parser.add_argument("record", type=Path, help="game_records_v7 下的 JSON 路径")
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="导出目录（将创建 game_records_v7 + replay_word + bat）",
    )
    parser.add_argument("--anchor", type=int, nargs="*", default=[45])
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    out = export_package(
        args.record,
        args.out,
        anchor_steps=args.anchor or None,
        notes=args.note,
    )
    print(f"exported -> {out}")


if __name__ == "__main__":
    main()
