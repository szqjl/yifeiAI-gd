#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7 副级等级分析工具 — 输出每副等级进度表

用途：批跑后分析 V7 vs lalala 每副的等级变化，
     回答「V7 赢了几副」「谁先双上过 A」「V7 离双上还差几步」。

用法：
  python scripts/tools/analyze_v7_round_levels.py                    # 分析全部 V7 game_records
  python scripts/tools/analyze_v7_round_levels.py --game-id 20260617113035277252
  python scripts/tools/analyze_v7_round_levels.py --player yf1_v7

输出：
  - 每副等级表（game_id / round / 起始级 / V7-curRank / 赢家 / lalala推断级）
  - 每局汇总（game_id / V7赢副数 / lalala赢副数 / V7最高达级）
  - 全局汇总（总局数 / V7赢副 / lalala赢副 / V7达A级副数）
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GAME_RECORDS = REPO / "game_records_v7"  # V7批跑数据目录

# 级牌点值
RANK_VAL = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
            "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}


def norm_rank(s):
    s = str(s or "2").strip().upper()
    if s in ("10", "T"):
        return "T"
    if s == "1":
        return "A"
    return s


def rank_val(s):
    return RANK_VAL.get(norm_rank(s), 0)


def parse_filename(fname):
    m = re.match(
        r"^(\d+)\s+\[([^\]]+)\]-\[([^\]]+)\]-\[(\d+)\]-\[([^\]]*)\]\.json$",
        fname
    )
    if not m:
        return None
    game_id, player, opponent, rnd, start_lvl = m.groups()
    return {
        "game_id": game_id,
        "player": player,
        "opponent": opponent,
        "round": int(rnd),
        "start_level": norm_rank(start_lvl) if start_lvl else "2",
    }


def load_records(pattern="v7", game_id=None):
    files = sorted(GAME_RECORDS.glob("*.json"))
    records = defaultdict(dict)  # (game_id, round) -> {player -> entry}

    for f in files:
        fname = f.name
        if pattern.lower() not in fname.lower():
            continue
        info = parse_filename(fname)
        if not info:
            continue
        if game_id and info["game_id"] != game_id:
            continue
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
        except Exception:
            continue

        key = (info["game_id"], info["round"])
        records[key][info["player"]] = {
            "data": data,
            "start_level": info["start_level"],
            "fname": fname,
        }

    return records


def infer_lalala_level(v7_start, v7_cur, v7_won):
    """推断 lalala 方在副末的等级（紧邻等级差假设，仅供参考）"""
    v7_sv = rank_val(v7_start)
    v7_cv = rank_val(v7_cur)
    gained = max(0, v7_cv - v7_sv) if v7_won else max(0, v7_sv - v7_cv)
    lala_sv = v7_sv
    if v7_won:
        lala_cv = max(2, lala_sv - gained)
    else:
        lala_cv = min(14, lala_sv + gained)
    # 转回等级字符串
    for rk, rv in RANK_VAL.items():
        if rv == int(round(lala_cv)):
            return rk
    return "2"


def val_to_rank(v):
    v = max(2, min(14, int(round(v))))
    for rk, rv in RANK_VAL.items():
        if rv == v:
            return rk
    return "2"


def determine_winner(entries_by_player):
    """
    判断一副谁赢（谁最后跑光牌）。

    V7 占位置 0(yf1_v7) 和 2(yf2_v7)。
    order = [w,x,y,z] = 出牌顺序（w 先出完，z 最后出完）
    order[0] = 赢家，order[3] = 末家（最后出完）

    判断逻辑：
    - 找 yf1_v7 文件的 order，取 order[0] = 胜者位置
    - 若 order[0] ∈ {0, 2} → V7 赢
    - 若 order[0] ∈ {1, 3} → lalala 赢
    """
    # 优先用 yf1_v7（yf1 通常在位置 0）
    yf1_key = None
    for k in entries_by_player:
        if "yf1_v7" in k:
            yf1_key = k
            break

    if not yf1_key:
        for k in entries_by_player:
            if "yf2_v7" in k:
                yf1_key = k
                break

    if not yf1_key:
        return "?"

    data = entries_by_player[yf1_key].get("data", {})
    order = data.get("result", {}).get("order", [])
    if not order:
        return "?"

    winner_pos = order[0]  # 出牌顺序第一个 = 赢家
    # V7 占 0 和 2
    if winner_pos in (0, 2):
        return "V7"
    else:
        return "lalala"


def analyze_round_entry(entries_by_player):
    """分析单副数据"""
    if not entries_by_player:
        return None

    # 找任一 V7 方
    v7_key = next(
        (k for k in entries_by_player if "yf1_v7" in k or "yf2_v7" in k),
        None
    )
    if not v7_key:
        return None

    vd = entries_by_player[v7_key]
    data = vd.get("data", {})
    result = data.get("result", {})
    v7_cur = norm_rank(result.get("curRank", "2"))
    start_level = vd.get("start_level", "2")
    winner = determine_winner(entries_by_player)
    v7_won = (winner == "V7")
    lalala_cur = infer_lalala_level(start_level, v7_cur, v7_won)
    order = result.get("order", [])
    rest_cards = result.get("restCards", [])
    # 剩余牌数
    rest_str = _format_rest(rest_cards, v7_key, entries_by_player)

    return {
        "start_level": start_level,
        "v7_cur": v7_cur,
        "lalala_cur": lalala_cur,
        "winner": winner,
        "v7_won": v7_won,
        "order": order,
        "rest_str": rest_str,
    }


def _format_rest(rest_cards, v7_key, entries_by_player):
    """格式化剩余牌数"""
    if not rest_cards:
        return "[]"
    parts = []
    for r in rest_cards:
        if isinstance(r, list) and len(r) >= 2:
            pos = r[0]
            cards = r[1] if isinstance(r[1], list) else []
            label = f"pos{pos}({len(cards)})"
            parts.append(label)
    return " ".join(parts)


def analyze_game(game_recs):
    """分析单个 game_id"""
    rows = []
    v7_wins = 0
    lalala_wins = 0
    v7_max_rank = "2"
    gid = ""
    total = 0

    for (g, rnd), entries in sorted(game_recs.items(), key=lambda x: x[0][1]):
        gid = g
        total += 1
        info = analyze_round_entry(entries)
        if not info:
            continue
        if info["v7_won"]:
            v7_wins += 1
        else:
            lalala_wins += 1
        if rank_val(info["v7_cur"]) > rank_val(v7_max_rank):
            v7_max_rank = info["v7_cur"]
        rows.append((rnd, info))

    rows.sort(key=lambda x: x[0])
    return {
        "game_id": gid,
        "total_rounds": total,
        "v7_wins": v7_wins,
        "lalala_wins": lalala_wins,
        "v7_max_rank": v7_max_rank,
        "rows": rows,
    }


def print_report(records, verbose=False):
    game_ids = sorted(set(k[0] for k in records.keys()))
    all_v7_wins = 0
    all_lala_wins = 0
    all_v7_a_rounds = 0
    game_summaries = []

    print("=" * 70)
    print("V7 副级等级分析报告")
    print("=" * 70)
    print()

    for gid in game_ids:
        game_recs = {k: v for k, v in records.items() if k[0] == gid}
        result = analyze_game(game_recs)
        game_summaries.append(result)
        all_v7_wins += result["v7_wins"]
        all_lala_wins += result["lalala_wins"]

        print(f"--- game_id: {gid} | V7 {result['v7_wins']}/{result['total_rounds']} 副胜 | "
              f"V7 最高达: {result['v7_max_rank']} ---")
        print(f"{'副':>4}  {'起始':>4}  {'V7末级':>6}  {'lalala':>6}  {'赢家':>5}  "
              f"{'剩余牌数':>16}  {'出牌顺序':>12}")
        print("-" * 65)
        for rnd, info in result["rows"]:
            winner_mark = "*" if info["v7_won"] else " "
            if info["v7_cur"] == "A":
                all_v7_a_rounds += 1
            print(f"  {rnd:>3}  {info['start_level']:>4}  "
                  f"{info['v7_cur']:>6}  {info['lalala_cur']:>6}  "
                  f"{winner_mark}{info['winner']:>4}  "
                  f"{info['rest_str']:>16}  {str(info['order']):>12}")

        if verbose:
            print()

    total_rounds_all = all_v7_wins + all_lala_wins
    print("=" * 70)
    print("全局汇总")
    print("=" * 70)
    print(f"  局数:            {len(game_ids)}")
    print(f"  总副数:          {total_rounds_all}")
    print(f"  V7 赢副:         {all_v7_wins} ({100*all_v7_wins/total_rounds_all:.1f}%)")
    print(f"  lalala 赢副:    {all_lala_wins} ({100*all_lala_wins/total_rounds_all:.1f}%)")
    print(f"  V7 达 A 级副数: {all_v7_a_rounds}")
    print()
    print("每局汇总:")
    print(f"  {'game_id':<20}  {'V7赢副':>6}  {'lalala':>6}  {'V7最高级':>8}")
    print("  " + "-" * 46)
    for g in game_summaries:
        print(f"  {g['game_id']:<20}  {g['v7_wins']:>5}副  {g['lalala_wins']:>5}副  {g['v7_max_rank']:>8}")
    print()
    print("说明: * = V7 赢副；lalala 推断等级 = 紧邻等级差假设（V7 升 N 则 lalala 降 N），")
    print("      仅供方向参考，受贡还牌数量影响与真实值有偏差。")
    print("      出牌顺序 [w,x,y,z]: w=赢家(先跑完), x=第二, y=第三, z=末家(最后跑完)。")


def main():
    parser = argparse.ArgumentParser(description="V7 副级等级分析工具")
    parser.add_argument("--game-id", dest="game_id", default=None,
                        help="仅分析指定 game_id")
    parser.add_argument("--player", dest="player", default="v7",
                        help="玩家过滤关键字（默认: v7）")
    parser.add_argument("-v", dest="verbose", action="store_true",
                        help="详细输出（每局间空行）")
    args = parser.parse_args()

    records = load_records(pattern=args.player, game_id=args.game_id)
    if not records:
        print(f"未找到匹配的 game_records（pattern={args.player}）")
        print(f"提示: game_records 目录: {GAME_RECORDS}")
        return

    print_report(records, verbose=args.verbose)


if __name__ == "__main__":
    main()
