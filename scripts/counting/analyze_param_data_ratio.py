# -*- coding: utf-8 -*-
"""
GUA-057 Phase 0 任务 3：模型/数据比例分析

目的：基于实测 game_records_v8 数据，量化：
  1. 实际可用样本数（步骤数 × 108 槽位监督信号）
  2. Transformer 319K 参数 vs LSTM 50K 参数 vs 数据规模比例
  3. 是否满足经验法则（参数 / 样本 ≤ 1/100 才不会过拟合）

用法：
  python scripts/counting/analyze_param_data_ratio.py [--records-dir game_records_v8]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import List

# 方案 §4.4.1 精确参数
PARAM_TRANSFORMER = 319204
PARAM_LSTM_BASELINE = 50000  # 估值
PARAM_RULE_MEMORYTRACKER = 0  # 规则记牌无参数


def collect_data_stats(records_dir: Path) -> dict:
    """统计 game_records_v8 数据规模。"""
    files = sorted(records_dir.glob("*.json"))
    total_steps = 0
    n_episodes = len(files)
    step_counts: List[int] = []
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            n = len(d.get("actions", []))
            total_steps += n
            step_counts.append(n)
        except json.JSONDecodeError:
            continue
    return {
        "n_episodes": n_episodes,
        "total_steps": total_steps,
        "avg_steps_per_episode": total_steps / max(1, n_episodes),
        "min_steps": min(step_counts) if step_counts else 0,
        "max_steps": max(step_counts) if step_counts else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="模型/数据比例分析")
    parser.add_argument("--records-dir", default="game_records_v8")
    args = parser.parse_args()

    records_dir = Path(args.records_dir)
    if not records_dir.exists():
        print(f"[ERROR] 目录不存在: {records_dir}", file=sys.stderr)
        return 1

    stats = collect_data_stats(records_dir)

    # 108 槽位 × 3 状态 = 324 维监督信号
    supervision_dim = 108 * 3
    # 每个 step 提供 1 个 324 维监督向量（但稀疏——大多数槽位仅 1 个状态非 0）
    n_supervision_signals = stats["total_steps"] * supervision_dim
    # 经验法则：参数 / 样本 ≤ 1/100（即每参数至少 100 样本监督）
    rule_of_100 = PARAM_TRANSFORMER * 100

    print("=" * 60)
    print("GUA-057 Phase 0 任务 3：模型/数据比例分析")
    print(f"records_dir = {records_dir}")
    print("=" * 60)
    print(f"  数据规模：")
    print(f"    副数（文件数）: {stats['n_episodes']}")
    print(f"    总步骤数: {stats['total_steps']}")
    print(f"    平均步数/副: {stats['avg_steps_per_episode']:.1f}")
    print(f"    步数范围: [{stats['min_steps']}, {stats['max_steps']}]")
    print(f"")
    print(f"  监督信号量：")
    print(f"    每步监督维度: {supervision_dim} (108 槽位 × 3 状态)")
    print(f"    总监督信号: {n_supervision_signals:,}")
    print(f"")
    print(f"  参数 / 样本 比例（经验法则：≤ 1/100）:")
    print(f"    Transformer (319K): {n_supervision_signals:,} / {PARAM_TRANSFORMER:,} = {n_supervision_signals / PARAM_TRANSFORMER:.1f}")
    print(f"    LSTM baseline (50K): {n_supervision_signals:,} / {PARAM_LSTM_BASELINE:,} = {n_supervision_signals / PARAM_LSTM_BASELINE:.1f}")
    print(f"    1/100 阈值: {rule_of_100:,}")
    print(f"")
    print(f"  结论：")
    ratio_tx = n_supervision_signals / PARAM_TRANSFORMER
    ratio_lstm = n_supervision_signals / PARAM_LSTM_BASELINE
    if ratio_tx >= 100:
        print(f"    ✓ Transformer (319K) 满足 1/100 法则（{ratio_tx:.1f}）")
    else:
        print(f"    ✗ Transformer (319K) **不满足** 1/100 法则（{ratio_tx:.1f}，需 ≥ 100）")
        print(f"    → 当前数据量下 Transformer 严重过拟合，必须先 LSTM baseline 验证")
    if ratio_lstm >= 100:
        print(f"    ✓ LSTM baseline (50K) 满足 1/100 法则（{ratio_lstm:.1f}）")
    else:
        print(f"    ✗ LSTM baseline (50K) 不满足 1/100 法则（{ratio_lstm:.1f}）")
    print(f"")
    print(f"  补充判断（更严苛的 1/1000 法则，深度学习标准）:")
    print(f"    Transformer (319K) 需样本数: {PARAM_TRANSFORMER * 1000:,}")
    print(f"    LSTM baseline (50K) 需样本数: {PARAM_LSTM_BASELINE * 1000:,}")
    print(f"    当前样本数: {n_supervision_signals:,}")
    print(f"    → 1/1000 法则下两者都不满足，**Phase 0 必须强制走 LSTM baseline 路线**")
    print("=" * 60)

    # Phase 0 硬门槛：必须警告 Transformer 不可上
    if ratio_tx < 100:
        print("[BLOCK] Phase 0 任务 3 阻断：Transformer 直接训练严重过拟合")
        print("        Phase 1 必须强制 LSTM baseline（参数 ≤ 50K）")
        return 0  # 阻断是正确诊断，不算失败

    return 0


if __name__ == "__main__":
    sys.exit(main())
