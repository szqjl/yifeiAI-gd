#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 game_records/ 提取决策模式并生成可读报告。

支持 M1/M2/M3 三种记录结构（字段差异自动识别）：
  - M1 / M3: actions[] / my_decisions[] 二选一，含 cur_pos / cur_action
  - M2:      my_decisions[] 含 action_index / action / context.decision_count

输出：
  - 标准输出：每位玩家的决策摘要
  - --md OUT.md：写入 markdown 报告（按 game_id 聚合）

使用：
  python scripts/analyze_decisions.py                          # 扫描 game_records/
  python scripts/analyze_decisions.py --records DIR --md OUT.md
  python scripts/analyze_decisions.py --player yf1_m1          # 只看 yf1_m1
  python scripts/analyze_decisions.py --top-n 20               # 只输出最近 20 个文件
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


CARD_TYPE_KEYS = ("Single", "Pair", "Trips", "ThreePair", "ThreeWithTwo",
                  "TripsPair", "TwoTrips", "Straight", "StraightFlush",
                  "Bomb", "PASS", "tribute", "back")

# 游戏记录文件名格式：「<game_id> [<player_name>]-[opponent_..]-[<round>]-[<level>].json」
RECORD_NAME_RE = re.compile(r"^(\d+) \[([^\]]+)\]-\[([^\]]+)\]-\[(\d+)\]-\[([^\]]*)\]\.json$")


def iter_records(records_dir: Path, player_filter: str = None, top_n: int = None):
    files = sorted(records_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if top_n:
        files = files[:top_n]
    for fp in files:
        m = RECORD_NAME_RE.match(fp.name)
        if not m:
            continue
        game_id, player_name = m.group(1), m.group(2)
        if player_filter and player_filter not in player_name:
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"[WARN] 跳过 {fp.name}: {e}", file=sys.stderr)
            continue
        yield fp, game_id, player_name, data


def extract_self_decisions(data: dict, player_pos: int):
    """统一返回该玩家自己的决策列表，每项 dict: {action_type, action, greater_action, decision_count?}"""
    out = []
    # 先尝试 my_decisions（M2 风格）
    if isinstance(data.get("my_decisions"), list):
        for i, d in enumerate(data["my_decisions"]):
            act = d.get("action") or []
            ctx = d.get("context") or {}
            out.append({
                "action_type": (act[0] if len(act) >= 1 else None),
                "rank":        (act[1] if len(act) >= 2 else None),
                "cards":       (act[2] if len(act) >= 3 else None),
                "action_index": d.get("action_index"),
                "decision_count": ctx.get("decision_count", i + 1),
                "passive": None,  # M2 记录里没有 greater_action，无法判定
            })
        return out

    # 否则用 actions[]（M1/M3 风格）：根据 cur_pos == 自己 过滤
    if isinstance(data.get("actions"), list) and player_pos is not None:
        seq = 0
        for a in data["actions"]:
            if a.get("cur_pos") != player_pos:
                continue
            seq += 1
            cur = a.get("cur_action") or []
            greater = a.get("greater_action") or []
            # 被动 = 当前最大动作不是自己刚出的（greater_pos != cur_pos）
            passive = a.get("greater_pos") not in (None, a.get("cur_pos"))
            out.append({
                "action_type": (cur[0] if len(cur) >= 1 else None),
                "rank":        (cur[1] if len(cur) >= 2 else None),
                "cards":       (cur[2] if len(cur) >= 3 else None),
                "action_index": None,
                "decision_count": seq,
                "passive": passive,
                "greater_type": (greater[0] if greater and len(greater) >= 1 else None),
            })
    return out


def summarize(decisions: list) -> dict:
    """对一份玩家决策序列做统计。"""
    n = len(decisions)
    type_counter = Counter(d["action_type"] for d in decisions)
    passive_known = [d for d in decisions if d.get("passive") is not None]
    passive_n = sum(1 for d in passive_known if d["passive"])
    pass_n = type_counter.get("PASS", 0)
    bomb_n = type_counter.get("Bomb", 0)
    first_bomb = next(
        (d["decision_count"] for d in decisions if d["action_type"] == "Bomb"),
        None
    )
    bomb_ranks = Counter(d["rank"] for d in decisions if d["action_type"] == "Bomb" and d.get("rank"))
    return {
        "total_decisions": n,
        "type_counts": dict(type_counter),
        "pass_rate": (pass_n / n) if n else 0.0,
        "bomb_count": bomb_n,
        "first_bomb_at": first_bomb,
        "bomb_ranks": dict(bomb_ranks),
        "passive_decisions": passive_n,
        "passive_known_total": len(passive_known),
        "passive_rate": (passive_n / len(passive_known)) if passive_known else None,
    }


def render_markdown(rows, out_path: Path):
    lines = ["# 决策模式提取报告", "",
             f"扫描了 **{len(rows)}** 条玩家记录。", "",
             "| game | round | player | pos | 决策数 | PASS率 | 炸弹 | 首炸@ | 被动率 | 主要牌型 |",
             "|------|-------|--------|-----|--------|--------|------|-------|--------|----------|"]
    for r in rows:
        s = r["summary"]
        top_types = sorted(s["type_counts"].items(), key=lambda kv: -kv[1])[:3]
        top_str = ", ".join(f"{k}×{v}" for k, v in top_types)
        passive = f"{s['passive_rate']*100:.0f}%" if s["passive_rate"] is not None else "-"
        first_bomb = s["first_bomb_at"] if s["first_bomb_at"] is not None else "-"
        lines.append(
            f"| {r['game_id']} | {r['round']} | {r['player_name']} | {r['player_pos']} | "
            f"{s['total_decisions']} | {s['pass_rate']*100:.0f}% | "
            f"{s['bomb_count']} | {first_bomb} | {passive} | {top_str} |"
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--records", default="game_records", help="游戏记录目录（默认 game_records）")
    ap.add_argument("--player", default=None, help="只统计文件名含此子串的玩家，比如 yf1_m1")
    ap.add_argument("--top-n", type=int, default=None, help="只取最近 N 个文件")
    ap.add_argument("--md", default=None, help="额外输出 markdown 报告到此路径")
    args = ap.parse_args()

    records_dir = Path(args.records)
    if not records_dir.is_dir():
        print(f"[FATAL] 目录不存在: {records_dir}", file=sys.stderr)
        return 1

    rows = []
    aggregate = defaultdict(lambda: {"games": 0, "bombs": 0, "passes": 0, "decisions": 0})
    for fp, game_id, player_name, data in iter_records(records_dir, args.player, args.top_n):
        m = RECORD_NAME_RE.match(fp.name)
        round_num = int(m.group(4)) if m else 0
        player_pos = data.get("player_id")
        decisions = extract_self_decisions(data, player_pos)
        if not decisions:
            continue
        s = summarize(decisions)
        rows.append({
            "game_id": game_id,
            "round": round_num,
            "player_name": player_name,
            "player_pos": player_pos,
            "summary": s,
        })
        a = aggregate[player_name]
        a["games"] += 1
        a["bombs"] += s["bomb_count"]
        a["passes"] += s["type_counts"].get("PASS", 0)
        a["decisions"] += s["total_decisions"]

    print(f"扫描记录: {len(rows)} 个")
    print()
    print(f"{'player':<14}{'games':>6}{'decisions':>11}{'pass_rate':>11}{'bombs':>8}{'bombs/g':>9}")
    for player, a in sorted(aggregate.items()):
        decs = a["decisions"]
        pr = (a["passes"] / decs * 100) if decs else 0
        bg = a["bombs"] / a["games"] if a["games"] else 0
        print(f"{player:<14}{a['games']:>6}{decs:>11}{pr:>10.1f}%{a['bombs']:>8}{bg:>9.2f}")

    if args.md:
        out_path = Path(args.md)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        render_markdown(rows, out_path)
        print(f"\nMarkdown 报告已写入: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
