# -*- coding: utf-8 -*-
"""
GUA-096: 净盘批跑后强制写入 v7-win-rate-history.md

设计目标:
- 不依赖用户记得写——靠脚本自动落盘
- 读 batch_executor/latest_victory_num.json (vn 真源) + game_records_v7/*.json (副数)
- 追加一行到 docs/guandan-brain/v7-win-rate-history.md
- 与现有格式兼容（看 v7-win-rate-history.md 现有行）

调用入口:
    python scripts/hooks/post_batch_log.py --gua-id "GUA-097" --change "..." [--games 3] [--cmd "..."]

约束:
- 静默 (--quiet) 或 verbose (默认)
- 失败不抛异常（避免阻塞批跑）
"""
import argparse
import json
import os
import sys
import datetime
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # D:\guandanscore\YiFeiAI-GD
VN_FILE = ROOT / "batch_executor" / "latest_victory_num.json"
WIN_RATE_HISTORY = ROOT / "docs" / "guandan-brain" / "v7-win-rate-history.md"
GAME_RECORDS_DIR = ROOT / "game_records_v7"


def load_vn():
    """读 vn 真源"""
    if not VN_FILE.exists():
        return None
    try:
        with open(VN_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] vn 读失败: {e}", file=sys.stderr)
        return None


def count_records():
    """数 game_records_v7/*.json"""
    if not GAME_RECORDS_DIR.exists():
        return 0
    return len(list(GAME_RECORDS_DIR.glob("*.json")))


def calc_team_win_rate(vn):
    """0+2 vs 1+3 队胜率 (按 AGENTS.md 三句数据口径)"""
    if not vn or len(vn) < 4:
        return None, None
    team_a = vn[0]
    team_b = vn[1]
    total = team_a + team_b
    if total == 0:
        return "0/0 (0%)", total
    return f"{team_a}/{total} ({team_a/total*100:.1f}%)", total


def append_history(date, gua_id, change, cmd, games, win_rate_str, total_games, records, note):
    """追加一行到 v7-win-rate-history.md (markdown 表格行)"""
    if not WIN_RATE_HISTORY.exists():
        print(f"[WARN] win-rate-history 文件不存在: {WIN_RATE_HISTORY}", file=sys.stderr)
        return False
    # 表格行格式 (与现有行对齐)
    row = f"| {date} | {gua_id} | {change} | `{cmd}` | {games} | {win_rate_str} | {records} | {note} |\n"
    try:
        with open(WIN_RATE_HISTORY, "a", encoding="utf-8") as f:
            f.write(row)
        return True
    except Exception as e:
        print(f"[ERROR] 追加失败: {e}", file=sys.stderr)
        return False


def main():
    p = argparse.ArgumentParser(description="GUA-096: 净盘后强制写 v7-win-rate-history.md")
    p.add_argument("--gua-id", required=True, help="目标 GUA 编号 (如 GUA-097)")
    p.add_argument("--change", required=True, help="改动摘要")
    p.add_argument("--cmd", default="python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3", help="批跑命令")
    p.add_argument("--games", type=int, default=3, help="局数 (3 的倍数)")
    p.add_argument("--note", default="(auto-logged by GUA-096 hook)", help="备注")
    p.add_argument("--quiet", action="store_true", help="静默模式")
    args = p.parse_args()

    vn_data = load_vn()
    if vn_data is None:
        print("[ERROR] vn 真源不可读，跳过日志 (GUA-096 失败 = 用户必须手动补登)", file=sys.stderr)
        sys.exit(1)

    vn = vn_data.get("victoryNum", [])
    if len(vn) >= 4 and (vn[0] != vn[2] or vn[1] != vn[3]):
        print(
            f"[WARN] victoryNum 队内镜像位不一致: {vn}，按工作流口径仅采用 [0] vs [1]",
            file=sys.stderr,
        )
    win_rate_str, total_games = calc_team_win_rate(vn)
    records = count_records()
    date = datetime.date.today().isoformat()

    if not args.quiet:
        print(f"[GUA-096] date={date} gua={args.gua_id} games={args.games} "
              f"vn={vn} win_rate={win_rate_str} records={records}")

    ok = append_history(date, args.gua_id, args.change, args.cmd, args.games,
                        win_rate_str, total_games, records, args.note)
    if not ok:
        sys.exit(2)
    if not args.quiet:
        print(f"[GUA-096] OK: 已写入 {WIN_RATE_HISTORY.name}")


if __name__ == "__main__":
    main()
