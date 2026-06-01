# -*- coding: utf-8 -*-
"""GUA-033：批跑后从 logs / batch 文件抽取三线对照证据。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _latest(pattern: str) -> Path | None:
    files = sorted(ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _grep_log(path: Path, pattern: str) -> list[str]:
    if not path or not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if re.search(pattern, line):
            out.append(line.strip())
    return out


def collect(target_games: int) -> dict:
    batch_file = ROOT / "batch_executor" / "current_batch.json"
    latest_vn = ROOT / "batch_executor" / "latest_victory_num.json"
    state_file = ROOT / "execution_state.json"

    batch_ctx = {}
    if batch_file.exists():
        batch_ctx = json.loads(batch_file.read_text(encoding="utf-8"))

    vn_payload = {}
    if latest_vn.exists():
        vn_payload = json.loads(latest_vn.read_text(encoding="utf-8"))

    state = {}
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))

    yf1_log = _latest("logs/yf1_m3_*.log")
    batch_log = _latest("logs/batch_executor_*.log")

    game_over = _grep_log(yf1_log, r"gameOver: curTimes=") if yf1_log else []
    game_result = _grep_log(yf1_log, r"gameResult RAW:") if yf1_log else []
    fallback = _grep_log(yf1_log, r"改用本批 gameOver 计数") if yf1_log else []
    vn_check = _grep_log(batch_log, r"批末 victoryNum") if batch_log else []
    exe_line = _grep_log(batch_log, r"游戏场数:") if batch_log else []

    vn = vn_payload.get("victoryNum", [])
    team_sum = (int(vn[0]) + int(vn[1])) if len(vn) >= 2 else None
    batch_games = batch_ctx.get("batch_games")

    return {
        "target_games": target_games,
        "batch_games_file": batch_ctx,
        "latest_victory_num": vn_payload,
        "execution_state": state,
        "exe_argv_lines": exe_line[:3],
        "gameOver_lines": game_over,
        "gameResult_raw_lines": game_result,
        "fallback_lines": fallback,
        "executor_vn_check": vn_check,
        "vn_team_sum": team_sum,
        "vn_ok_vs_batch": team_sum == batch_games if team_sum is not None and batch_games else None,
        "yf1_log": str(yf1_log) if yf1_log else None,
        "batch_log": str(batch_log) if batch_log else None,
    }


def main():
    tg = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(json.dumps(collect(tg), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
