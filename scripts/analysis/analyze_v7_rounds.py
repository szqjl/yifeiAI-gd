#!/usr/bin/env python3
"""V7/V8 批跑局级+副级分析脚本。

从 game_records_v7/ 或 game_records_v8/ 读取所有 JSON 牌谱，自动检测服务器会话边界，
输出局级战果（victoryNum）与副级统计（每副胜负、队分布）。

用法:
    python scripts/analysis/analyze_v7_rounds.py                          # V7 分析今日所有会话
    python scripts/analysis/analyze_v7_rounds.py --dir game_records_v8    # V8 分析（自动检测 platform）
    python scripts/analysis/analyze_v7_rounds.py -s 4                     # 最近 4 个会话
    python scripts/analysis/analyze_v7_rounds.py -w 60                    # 最近 60 分钟
    python scripts/analysis/analyze_v7_rounds.py --json                   # JSON 输出
"""

import json
import re
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RECORDS_DIR = PROJECT_ROOT / "game_records_v7"
GAMES_PER_SESSION = 3  # v1006 固定每会话 3 局；V8 OpenGuanDan 每会话 1 局

# 平台标签：V7 → "V7"，V8 → "V8"（从 --dir 自动推断）
_PLATFORM_TAG = "V7"
_TEAM_A_LABEL = "V7"     # Team A 显示名，V8 vs V8 时改为 V8-TeamA
_TEAM_B_LABEL = "Lalala" # Team B 显示名，V8 vs V8 时改为 V8-TeamB
_PLAYER_PREFIX = "yf1_v7"  # 去重时优先保留的文件名前缀

# 级牌→数值映射（2=1最弱, A=13最强）
LEVEL_ORDER = {"2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6, "8": 7,
               "9": 8, "T": 9, "J": 10, "Q": 11, "K": 12, "A": 13}
LEVEL_NAME = {v: k for k, v in LEVEL_ORDER.items()}

# 末级分布分组标签
FINAL_LEVEL_GROUPS = {
    "2级": (1, 1),
    "≤5级（含2级）": (1, 4),
    "J-K": (10, 12),
    "A": (13, 13),
}


# ── 数据加载 ─────────────────────────────────────────────
_MATCH_KEY_RE = re.compile(
    r"\]-\[(?:opponent_[^\]]+|\d+)\]-\[(\d+)\]-\[([^\]]+)\]\.json$"
)


def match_key_from_filename(fname: str) -> tuple[str, str] | None:
    """从文件名提取 (round, level) 作为副级 match_key（同副 yf1/yf2 共享）。"""
    m = _MATCH_KEY_RE.search(fname)
    if m:
        return (m.group(1), m.group(2))
    return None


def dedupe_session_records(records: list[dict]) -> list[dict]:
    """会话内按 round+level 去重：每副只保留一条，优先 yf1（平台自适应）。"""
    by_key: dict[tuple, dict] = {}
    for rec in records:
        fname = rec.get("_file", "")
        key = match_key_from_filename(fname)
        if key is None:
            key = (fname,)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = rec
        elif _PLAYER_PREFIX in fname:
            by_key[key] = rec
    out = sorted(by_key.values(), key=lambda r: r.get("_file", ""))
    return out


def load_all_records(records_dir: Path) -> list[dict]:
    """加载全部 JSON（含 yf1+yf2 双录；副级去重在 detect_sessions 之后）。"""
    files = sorted(records_dir.glob("*.json"))
    records = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except Exception as e:
            print(f"[WARN] 跳过 {fp.name}: {e}", file=sys.stderr)
            continue
        rec["_file"] = fp.name
        records.append(rec)
    return records


# ── 会话检测 ─────────────────────────────────────────────
def detect_sessions(records: list[dict]) -> list[list[dict]]:
    """按 game_round/game_count 重置 + 时间间隔 >= SESSION_GAP_SEC 检测会话边界。

    规则：game_round（V7）或 result.game_count（V8）不增（新游戏开始）
         且 时间间隔 >= 阈值 → 新会话。

    V8 OpenGuanDan 每批 batch_games=1，每批 = 1 个会话 = 1 局。
    """
    SESSION_GAP_SEC = 5  # 服务器重启 + 客户端重连通常 > 10s
    if not records:
        return []

    # 按文件时间戳排序
    sorted_recs = sorted(records, key=lambda r: r.get("_file", ""))

    sessions = []
    cur_session = []
    prev_gr = -1
    prev_ts_str = ""

    for rec in sorted_recs:
        fname = rec.get("_file", "")
        ts_str = fname.split(" ")[0] if " " in fname else ""
        # V7: top-level game_round; V8: result.game_count
        gr = rec.get("game_round", 0)
        if gr == 0:
            gr = rec.get("result", {}).get("game_count", 0)

        if cur_session:
            gap = (int(ts_str) - int(prev_ts_str)) / 10_000_000 if prev_ts_str else 0
            # V8 (GAMES_PER_SESSION=1): gc 重置即新会话（batch_games=1，每批=1局）
            # V7: gc 重置 + 时间间隔 ≥ 阈值（避免同会话内副间波动误判）
            if _PLATFORM_TAG == "V8":
                if gr <= prev_gr:
                    sessions.append(cur_session)
                    cur_session = []
            else:
                if gr <= prev_gr and gap >= SESSION_GAP_SEC:
                    sessions.append(cur_session)
                    cur_session = []

        cur_session.append(rec)
        prev_gr = gr
        prev_ts_str = ts_str

    if cur_session:
        sessions.append(cur_session)

    return sessions


# ── 副级分析 ─────────────────────────────────────────────
def is_v7_pos(pos: int) -> bool:
    """V7 队友位置：0 (yf1) 和 2 (yf2)。"""
    return pos in (0, 2)


def is_lalala_pos(pos: int) -> bool:
    """Lalala 对手位置：1 和 3。"""
    return pos in (1, 3)


def rank_to_int(rank: str) -> int:
    """级牌→数字，用于排序分布。2=2, 3=3, ..., T=10, J=11, Q=12, K=13, A=14。"""
    rank = rank.upper().strip()
    mapping = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
               "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
    return mapping.get(rank, 0)


def rank_sort_key(r: str) -> int:
    return rank_to_int(r)


def v7_final_level(record: dict) -> str:
    """V7 队末级：pos 0 和 pos 2 中最低的级牌（字符串 key）。"""
    rank_strs = record.get("result", {}).get("curRank", [])
    v7_nums = []
    for pos in (0, 2):
        if pos < len(rank_strs):
            num = LEVEL_ORDER.get(rank_strs[pos].upper(), 0)
            if num > 0:
                v7_nums.append(num)
    if not v7_nums:
        return "?"
    worst = min(v7_nums)  # 最弱级牌
    return LEVEL_NAME.get(worst, str(worst))


def analyze_round(rec: dict) -> dict:
    """分析单副 JSON。"""
    result = rec.get("result", {})
    order = result.get("order", [])  # [第1名, 第2名, 第3名, 第4名]
    rank = result.get("curRank", "?")
    winner = order[0] if order else None  # 本副赢家

    # V7 成员在 order 中的位置
    v7_positions = [i + 1 for i, pos in enumerate(order) if is_v7_pos(pos)]
    lalala_positions = [i + 1 for i, pos in enumerate(order) if is_lalala_pos(pos)]

    return {
        "game_round": rec.get("game_round", 0),
        "rank": rank.upper(),
        "order": order,
        "v7_won": is_v7_pos(winner) if winner is not None else False,
        "v7_finish_positions": v7_positions,
        "lalala_finish_positions": lalala_positions,
        "game_id": rec.get("game_id", ""),
    }


# ── 输出格式化 ───────────────────────────────────────────
def format_dist(dist: dict, sort_by_key: callable = None) -> str:
    """格式化分布字典为字符串。"""
    if sort_by_key:
        items = sorted(dist.items(), key=lambda x: sort_by_key(x[0]))
    else:
        items = sorted(dist.items())
    return ", ".join(f"{k}:{v}" for k, v in items)


def print_session_header(sess_idx: int, records: list[dict], raw_json_count: int | None = None):
    n_rounds = len(records)
    json_note = ""
    if raw_json_count is not None and raw_json_count > n_rounds:
        json_note = f"  ({raw_json_count} JSON)"
    print(f"\n{'='*70}")
    print(f"📦 会话 {sess_idx}  —  {n_rounds} 副{json_note}  ({GAMES_PER_SESSION} 局)")
    # 时间范围
    fnames = [r.get("_file", "") for r in records]
    t1 = fnames[0].split(" ")[0][:14] if fnames else "?"
    t2 = fnames[-1].split(" ")[0][:14] if fnames else "?"
    print(f"   ⏱ {t1} → {t2}")
    print(f"{'='*70}")


def print_victory_table(vn: list, games: int):
    """打印局级战果表。队胜看 vn[0] vs vn[1]（同队 [0]=[2]、[1]=[3]）。"""
    team0_wins = vn[0] if len(vn) > 0 else 0
    team1_wins = vn[1] if len(vn) > 1 else 0
    print(f"  局级: {_TEAM_A_LABEL} {team0_wins}/{games}局胜  {_TEAM_B_LABEL} {team1_wins}/{games}局胜")
    print(f"  victoryNum: {vn}")


def v8_game_result_from_head_dist(head_dist: list[int]) -> tuple[int, int, int]:
    """按一个 OpenGuanDan 会话内的头游副数判定真实局胜。"""
    team_a_heads = head_dist[0] + head_dist[2]
    team_b_heads = head_dist[1] + head_dist[3]
    if team_a_heads > team_b_heads:
        return (1, 0, 0)
    if team_b_heads > team_a_heads:
        return (0, 1, 0)
    return (0, 0, 1)


def print_v8_victory_table(
    vn: list,
    head_dist: list[int],
    game_result: tuple[int, int, int],
) -> None:
    """打印 V8 真实局胜，并保留 victoryNum 作为升级值诊断。"""
    team_a_wins, team_b_wins, draws = game_result
    print(
        f"  局级: {_TEAM_A_LABEL} {team_a_wins}/1局胜  {_TEAM_B_LABEL} {team_b_wins}/1局胜  "
        f"平局 {draws}/1"
    )
    print(
        "  局胜判定: 头游副数 "
        f"TeamA={head_dist[0] + head_dist[2]} "
        f"TeamB={head_dist[1] + head_dist[3]}"
    )
    print(f"  victoryNum（升级值，仅诊断）: {vn}")


def print_round_summary(total_rounds: int, v7_won: int, v7_dist: dict,
                        v7_pos_dist: dict, lalala_achieved_a: int,
                        v7_final_level_dist: dict = None):
    """打印副级汇总。"""
    print(f"  副级: {_TEAM_A_LABEL} 赢 {v7_won}/{total_rounds} ({v7_won/max(1,total_rounds)*100:.1f}%)")
    print(f"  {_TEAM_A_LABEL} 到达级牌分布: {format_dist(v7_dist, sort_by_key=rank_sort_key)}")
    if v7_pos_dist:
        pos_str = format_dist(v7_pos_dist, sort_by_key=lambda k: int(k) if k.isdigit() else k)
        print(f"  {_TEAM_A_LABEL} 名次分布: {pos_str}")
    print(f"  {_TEAM_B_LABEL} 达A: {lalala_achieved_a}副")
    if v7_final_level_dist:
        group_parts = _format_final_level_groups(v7_final_level_dist)
        print(f"  末级分布: {group_parts}")


def _format_final_level_groups(dist: dict) -> str:
    """格式化末级分布（按分组聚合）。"""
    parts = []
    for label, (lo, hi) in FINAL_LEVEL_GROUPS.items():
        count = sum(dist.get(LEVEL_NAME[l], 0) for l in range(lo, hi + 1))
        parts.append(f"{label}:{count}副")
    return "；".join(parts)


def _format_final_level_detail(dist: dict) -> str:
    """格式化末级分布（逐级，用于总计）。"""
    sorted_items = sorted(dist.items(), key=lambda x: LEVEL_ORDER.get(x[0], 99))
    return "；".join(f"{k}级:{v}副" for k, v in sorted_items)


# ── 主分析 ───────────────────────────────────────────────
def analyze_session(session_records: list[dict], sess_idx: int, raw_json_count: int | None = None) -> dict:
    """分析一个会话。"""
    print_session_header(sess_idx, session_records, raw_json_count)

    # 局级：vn 从末副取；V8 的 vn 是升级值，真实局胜稍后按会话头游副数判定。
    vn_raw = session_records[-1].get("result", {}).get("victoryNum", [0, 0, 0, 0])
    vn = list(vn_raw) + [0, 0, 0, 0] if len(vn_raw) < 4 else list(vn_raw)

    # 副级
    total_rounds = len(session_records)
    v7_won = 0
    v7_dist = defaultdict(int)
    v7_pos_dist = defaultdict(int)
    lalala_achieved_a = 0
    v7_final_level_dist = defaultdict(int)
    double_up = 0  # 双上：yf1+yf2 包揽 1st+2nd
    double_down = 0  # 双下：yf1+yf2 包揽 3rd+4th
    head_dist = [0, 0, 0, 0]  # 各席位头游次数

    for rec in session_records:
        ra = analyze_round(rec)
        if ra["v7_won"]:
            v7_won += 1
        v7_dist[ra["rank"]] += 1
        for p in ra["v7_finish_positions"]:
            v7_pos_dist[str(p)] += 1
        if rank_to_int(ra["rank"]) == 14:  # A
            lalala_achieved_a += 1
        v7_final_level_dist[v7_final_level(rec)] += 1
        # 双上/双下/头游
        order = ra["order"]
        if isinstance(order, list) and len(order) >= 4:
            if set(order[:2]) == {0, 2}:
                double_up += 1
            if set(order[2:]) == {0, 2}:
                double_down += 1
            head_pos = int(order[0])
            if 0 <= head_pos < 4:
                head_dist[head_pos] += 1

    if _PLATFORM_TAG == "V8":
        game_result = v8_game_result_from_head_dist(head_dist)
        print_v8_victory_table(vn[:4], head_dist, game_result)
    else:
        game_result = (
            vn[0] if len(vn) > 0 else 0,
            vn[1] if len(vn) > 1 else 0,
            max(0, GAMES_PER_SESSION - sum(vn[:2])),
        )
        print_victory_table(vn[:4], GAMES_PER_SESSION)

    print_round_summary(total_rounds, v7_won, dict(v7_dist),
                        dict(v7_pos_dist), lalala_achieved_a,
                        v7_final_level_dist=dict(v7_final_level_dist))
    # 双上率/头游分布（V8 关键指标）
    if total_rounds > 0:
        print(f"  双上率: {double_up}/{total_rounds} ({double_up/total_rounds*100:.1f}%)")
        print(f"  双下率: {double_down}/{total_rounds} ({double_down/total_rounds*100:.1f}%)")
        team_heads = head_dist[0] + head_dist[2]
        print(f"  队头游率: {team_heads}/{total_rounds} ({team_heads/total_rounds*100:.1f}%)  "
              f"[seat0={head_dist[0]} seat1={head_dist[1]} seat2={head_dist[2]} seat3={head_dist[3]}]")
        yf1_last = sum(1 for r in session_records
                       if isinstance(r.get("result", {}).get("order", []), list)
                       and len(r["result"]["order"]) >= 4
                       and r["result"]["order"][3] == 0)
        yf2_last = sum(1 for r in session_records
                       if isinstance(r.get("result", {}).get("order", []), list)
                       and len(r["result"]["order"]) >= 4
                       and r["result"]["order"][3] == 2)
        print(f"  末游率: yf1={yf1_last}/{total_rounds} ({yf1_last/total_rounds*100:.1f}%)  "
              f"yf2={yf2_last}/{total_rounds} ({yf2_last/total_rounds*100:.1f}%)")

    return {
        "session_idx": sess_idx,
        "games": GAMES_PER_SESSION,
        "rounds": total_rounds,
        "vn": vn,
        "v7_game_wins": game_result[0],
        "lalala_game_wins": game_result[1],
        "draws": game_result[2],
        "v7_rounds_won": v7_won,
        "v7_dist": dict(v7_dist),
        "v7_pos_dist": dict(v7_pos_dist),
        "lalala_achieved_a": lalala_achieved_a,
        "v7_final_level_dist": dict(v7_final_level_dist),
    }


# ── CLI ──────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="V7 批跑局级+副级分析")
    parser.add_argument("--dir", default=str(RECORDS_DIR),
                        help=f"game_records_v7 目录")
    parser.add_argument("--window", "-w", type=int, default=None,
                        help="时间窗口（分钟），如 -w 60 只分析最近 60 分钟")
    parser.add_argument("--sessions", "-s", type=int, default=None,
                        help="只分析最近 N 个会话")
    parser.add_argument("--json", action="store_true",
                        help="输出 JSON")
    parser.add_argument("--all", action="store_true",
                        help="显示全部（默认只显示今日）")
    args = parser.parse_args()

    records_dir = Path(args.dir)
    if not records_dir.is_dir():
        print(f"[ERROR] 目录不存在: {records_dir}", file=sys.stderr)
        sys.exit(1)

    # 平台自动推断：目录名含 v8 → V8 模式
    global _PLATFORM_TAG, _PLAYER_PREFIX, GAMES_PER_SESSION, _TEAM_A_LABEL, _TEAM_B_LABEL
    if "v8" in records_dir.name.lower():
        _PLATFORM_TAG = "V8"
        _TEAM_A_LABEL = "V8"
        _TEAM_B_LABEL = "Lalala"
        _PLAYER_PREFIX = "yf1_v8"
        GAMES_PER_SESSION = 1  # OpenGuanDan batch_games=1
        parser.description = "V8 批跑局级+副级分析"

    records = load_all_records(records_dir)
    if not records:
        print("[ERROR] 无有效 JSON 记录", file=sys.stderr)
        sys.exit(1)

    # V8: 会话检测前过滤为 yf1 文件（yf1/yf2 交错会干扰 gc 序列导致误切分）
    if _PLATFORM_TAG == "V8":
        records = [r for r in records if _PLAYER_PREFIX in r.get("_file", "")]
        # 自动检测对手类型：seat_players 不含 "lalala" → V8 vs V8
        for r in records:
            sp = r.get("seat_players", [])
            if sp and not any("lalala" in str(p).lower() for p in sp):
                _TEAM_A_LABEL = "V8-TeamA"
                _TEAM_B_LABEL = "V8-TeamB"
                break

    # 时间过滤
    if not args.all:
        today = datetime.now().strftime("%Y%m%d")
        records = [r for r in records
                   if r.get("_file", "").startswith(today)]

    if args.window:
        cutoff = datetime.now() - timedelta(minutes=args.window)
        records = [r for r in records
                   if datetime.strptime(r.get("_file", "")[:14], "%Y%m%d%H%M%S") >= cutoff]

    if not records:
        print("[INFO] 无匹配记录", file=sys.stderr)
        sys.exit(0)

    sessions = detect_sessions(records)
    # 副级去重：yf1/yf2 双录 → 每副一条
    deduped: list[tuple[list[dict], int]] = []
    for sess in sessions:
        raw_n = len(sess)
        d = dedupe_session_records(sess)
        deduped.append((d, raw_n))
    sessions = [d for d, _ in deduped]
    raw_counts = [r for _, r in deduped]

    # 限制会话数
    if args.sessions:
        sessions = sessions[-args.sessions:]
        raw_counts = raw_counts[-args.sessions:]

    if not sessions:
        print("[INFO] 未检测到会话", file=sys.stderr)
        sys.exit(0)

    # 分析
    results = []
    for i, sess in enumerate(sessions):
        raw_n = raw_counts[i] if i < len(raw_counts) else None
        r = analyze_session(sess, i + 1, raw_n)
        results.append(r)

    # 总计
    total_games = sum(r["games"] for r in results)
    total_rounds = sum(r["rounds"] for r in results)
    total_vn = [0, 0, 0, 0]
    total_v7_won = 0
    total_v7_game_wins = 0
    total_lalala_game_wins = 0
    total_draws = 0
    total_v7_dist = defaultdict(int)
    total_v7_pos_dist = defaultdict(int)
    total_lalala_a = 0
    total_v7_final_level_dist = defaultdict(int)

    for r in results:
        vn = r["vn"]
        for i in range(4):
            total_vn[i] += vn[i]
        total_v7_game_wins += r["v7_game_wins"]
        total_lalala_game_wins += r["lalala_game_wins"]
        total_draws += r["draws"]
        total_v7_won += r["v7_rounds_won"]
        total_lalala_a += r["lalala_achieved_a"]
        for k, v in r["v7_dist"].items():
            total_v7_dist[k] += v
        for k, v in r["v7_pos_dist"].items():
            total_v7_pos_dist[k] += v
        for k, v in r.get("v7_final_level_dist", {}).items():
            total_v7_final_level_dist[k] += v

    print(f"\n{'='*70}")
    print(f"🏆 总计  ({len(results)} 会话 / {total_games} 局 / {total_rounds} 副)")
    print(f"{'='*70}")
    v7_ttl = total_v7_game_wins
    lalala_ttl = total_lalala_game_wins
    print(f"  队胜: {_TEAM_A_LABEL} {v7_ttl}/{total_games} ({v7_ttl/max(1,total_games)*100:.1f}%)  "
          f"{_TEAM_B_LABEL} {lalala_ttl}/{total_games} ({lalala_ttl/max(1,total_games)*100:.1f}%)  "
          f"平局 {total_draws}/{total_games} ({total_draws/max(1,total_games)*100:.1f}%)")
    print(f"  victoryNum 累加: {total_vn}")
    print(f"  副级: {_TEAM_A_LABEL} 赢 {total_v7_won}/{total_rounds} ({total_v7_won/max(1,total_rounds)*100:.1f}%)")
    print(f"  {_TEAM_A_LABEL} 级牌分布: {format_dist(dict(total_v7_dist), sort_by_key=rank_sort_key)}")
    if total_v7_pos_dist:
        print(f"  {_TEAM_A_LABEL} 名次分布: {format_dist(dict(total_v7_pos_dist), sort_by_key=lambda k: int(k) if k.isdigit() else k)}")
    print(f"  {_TEAM_B_LABEL} 达A副数: {total_lalala_a}")
    if total_v7_final_level_dist:
        print(f"  末级分布: {_format_final_level_groups(dict(total_v7_final_level_dist))}")
        print(f"  (逐级) {_format_final_level_detail(dict(total_v7_final_level_dist))}")

    if args.json:
        output = {
            "total_sessions": len(results),
            "total_games": total_games,
            "total_rounds": total_rounds,
            "victoryNum": total_vn,
            "team_a_label": _TEAM_A_LABEL,
            "team_b_label": _TEAM_B_LABEL,
            "team_a_games_won": v7_ttl,
            "team_b_games_won": lalala_ttl,
            "draws": total_draws,
            "team_a_rounds_won": total_v7_won,
            "team_a_round_win_rate": round(total_v7_won / max(1, total_rounds) * 100, 1),
            "team_a_rank_dist": {k: total_v7_dist[k] for k in sorted(total_v7_dist, key=rank_sort_key)},
            "team_a_pos_dist": dict(sorted(total_v7_pos_dist.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0])),
            "team_b_achieved_a": total_lalala_a,
            "team_a_final_level_dist": dict(sorted(total_v7_final_level_dist.items(), key=lambda x: LEVEL_ORDER.get(x[0], 99))),
            "team_a_final_level_groups": {label: sum(total_v7_final_level_dist.get(LEVEL_NAME[l], 0) for l in range(lo, hi + 1)) for label, (lo, hi) in FINAL_LEVEL_GROUPS.items()},
            "sessions": [
                {
                    "idx": r["session_idx"],
                    "games": r["games"],
                    "rounds": r["rounds"],
                    "vn": r["vn"],
                    "team_a_game_wins": r["v7_game_wins"],
                    "team_b_game_wins": r["lalala_game_wins"],
                    "draws": r["draws"],
                    "team_a_rounds_won": r["v7_rounds_won"],
                    "team_a_dist": {k: r["v7_dist"][k] for k in sorted(r["v7_dist"], key=rank_sort_key)},
                    "team_a_pos_dist": r["v7_pos_dist"],
                    "team_b_achieved_a": r["lalala_achieved_a"],
                }
                for r in results
            ],
        }
        print("\n[JSON]")
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
