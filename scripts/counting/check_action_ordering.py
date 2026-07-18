# -*- coding: utf-8 -*-
"""
GUA-057 Phase 0 任务 1：V8 牌谱 yf1/yf2 时序对齐校验

目的：验证 game_records_v8/ 同局 yf1 + yf2 文件的 actions 序列是否时序一致。

关键发现（实测）：
  1. V8 文件名 [opponent_1_3]-[round]-[level] 段**不唯一**（多次批跑后 round 编号重置）。
  2. V8 中 yf1 / yf2 timestamp 无固定先后顺序（yf2 可能先建连）。
  3. 同一 game_tag (opponent/round/level) 下有多个文件（跨批跑累积）。

配对策略（修订 v3 - 基于 game_tag + timestamp 邻近）：
  按 game_tag 分组（同 opponent/round/level），每组内按 timestamp 升序。
  同一 game_tag 序列中 yf1 与 yf2 应**交替出现**，贪心配对相邻不同视角。

校验规则：
  1. 同局 yf1 + yf2 配对率 >= 95%（Phase 0 硬门槛）
  2. 两视角的 actions 序列：
     - cur_pos 完全相同
     - 出牌张数序列（每步 cards 数）相同
"""
from __future__ import annotations
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def parse_ts(filename: str) -> int:
    stem = Path(filename).stem
    try:
        return int(stem.split(" ")[0])
    except ValueError:
        return 0


def parse_game_tag(filename: str) -> str:
    """提取 [opponent_1_3]-[round]-[level] 段作为 game_tag。"""
    stem = Path(filename).stem
    parts = stem.split(" ", 1)
    if len(parts) != 2:
        return ""
    tag = parts[1]
    # 去 [yf1_v8]/[yf2_v8]
    tag = tag.replace("[yf1_v8]-", "").replace("[yf2_v8]-", "")
    return tag


def is_yf1(filename: str) -> bool:
    return "[yf1_v8]" in filename


def is_yf2(filename: str) -> bool:
    return "[yf2_v8]" in filename


def extract_action_signature(actions: List[dict]) -> List[Tuple[int, int]]:
    sig: List[Tuple[int, int]] = []
    for a in actions:
        cur_pos = a.get("cur_pos", -1)
        cur_action = a.get("cur_action", [])
        cards: List[str] = []
        if isinstance(cur_action, list) and len(cur_action) >= 3:
            third = cur_action[2]
            if isinstance(third, list):
                cards = third
        sig.append((int(cur_pos), len(cards)))
    return sig


def check_pair(f1: Path, f2: Path) -> Tuple[bool, str]:
    try:
        d1 = json.loads(f1.read_text(encoding="utf-8"))
        d2 = json.loads(f2.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"JSON 解析失败: {e}"

    sig1 = extract_action_signature(d1.get("actions", []))
    sig2 = extract_action_signature(d2.get("actions", []))

    if len(sig1) != len(sig2):
        return False, f"actions 长度不同: {len(sig1)} vs {len(sig2)}"

    mismatches = 0
    first_diff_step = -1
    for i, (s1, s2) in enumerate(zip(sig1, sig2)):
        if s1[0] != s2[0] or s1[1] != s2[1]:
            mismatches += 1
            if first_diff_step < 0:
                first_diff_step = i

    if mismatches == 0:
        return True, "OK"
    return False, f"{mismatches} 处 step 不一致，首处 step={first_diff_step}"


def collect_pairs(records_dir: Path) -> Tuple[List[Tuple[Path, Path]], List[Path]]:
    """按 game_tag 分组，组内贪心匹配 yf1 ↔ yf2。

    验证：配对后两文件的 actions 长度必须相同（一致性硬条件）。
    """
    # 按 game_tag 分组
    by_tag: Dict[str, List[Path]] = defaultdict(list)
    for f in sorted(records_dir.glob("*.json"), key=parse_ts):
        tag = parse_game_tag(f.name)
        if tag:
            by_tag[tag].append(f)

    pairs: List[Tuple[Path, Path]] = []
    singletons: List[Path] = []

    for tag, files in sorted(by_tag.items()):
        # 分离 yf1 / yf2，按 timestamp 排序
        yf1_list = sorted([f for f in files if is_yf1(f.name)], key=parse_ts)
        yf2_list = sorted([f for f in files if is_yf2(f.name)], key=parse_ts)

        # 贪心：每个 yf1 找 timestamp 最接近的 yf2（要求 actions 长度匹配）
        used_yf2: set = set()
        for f1 in yf1_list:
            ts1 = parse_ts(f1.name)
            best_f2 = None
            best_diff = None
            for f2 in yf2_list:
                if id(f2) in used_yf2:
                    continue
                ts2 = parse_ts(f2.name)
                diff = abs(ts1 - ts2)
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_f2 = f2
            if best_f2 is not None and best_diff is not None:
                # 验证 actions 长度匹配（硬条件）
                try:
                    d1 = json.loads(f1.read_text(encoding="utf-8"))
                    d2 = json.loads(best_f2.read_text(encoding="utf-8"))
                    if len(d1.get("actions", [])) == len(d2.get("actions", [])):
                        pairs.append((f1, best_f2))
                        used_yf2.add(id(best_f2))
                        continue
                except Exception:
                    pass
                # 长度不匹配 → 退回 singletons
            singletons.append(f1)

        # 未配对 yf2 入 singletons
        for f2 in yf2_list:
            if id(f2) not in used_yf2:
                singletons.append(f2)

    return pairs, singletons


def main() -> int:
    parser = argparse.ArgumentParser(description="V8 牌谱 yf1/yf2 时序对齐校验")
    parser.add_argument("--records-dir", default="game_records_v8",
                        help="V8 牌谱目录（默认 game_records_v8）")
    args = parser.parse_args()

    records_dir = Path(args.records_dir)
    if not records_dir.exists():
        print(f"[ERROR] 目录不存在: {records_dir}", file=sys.stderr)
        return 1

    pairs, singletons = collect_pairs(records_dir)
    total_files = len(pairs) * 2 + len(singletons)
    pair_rate = len(pairs) / max(1, len(pairs) + (len(singletons) // 2))

    print("=" * 60)
    print("GUA-057 Phase 0 任务 1：V8 牌谱时序对齐校验")
    print(f"records_dir = {records_dir}")
    print("=" * 60)
    print(f"  总文件数: {total_files}")
    print(f"  配对组数: {len(pairs)}")
    print(f"  未配对单视角: {len(singletons)}")
    print(f"  配对率（按组）: {pair_rate:.1%}")
    if singletons:
        for f in singletons[:5]:
            print(f"    - {f.name}", file=sys.stderr)

    if total_files == 0:
        print("[WARN] 目录无 JSON 文件")
        return 0

    if pair_rate < 0.95:
        print("[FAIL] 配对率 < 95% 硬门槛（Phase 0 验收）")
        return 2

    print("-" * 60)
    print("逐对校验 actions 时序一致性：")
    ok_count = 0
    fail_count = 0
    for f1, f2 in pairs:
        ok, msg = check_pair(f1, f2)
        if ok:
            ok_count += 1
        else:
            fail_count += 1
            print(f"  [FAIL] {f1.name[:35]} vs {f2.name[:35]} | {msg}",
                  file=sys.stderr)

    print(f"  时序一致: {ok_count} / {len(pairs)}")
    print(f"  时序不一致: {fail_count}")
    print("=" * 60)
    if fail_count > 0:
        print(f"[FAIL] {fail_count} 对时序不一致")
        return 1

    print(f"[PASS] Phase 0 任务 1 通过（配对率 {pair_rate:.1%}，时序 100% 一致）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
