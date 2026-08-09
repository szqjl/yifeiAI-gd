# -*- coding: utf-8 -*-
"""
GUA-223 / 第 2 项验证脚本 — Botzone post-GUA-216 数据质量

> 关联：GUA-223 / GUA-216（KEEP_RUNNING 增量模式扣牌双扣修复）
> 数据源：logs/v8_vs_botzone_*.log（重启监听后新生成）
> 输出：warnings_per_match 表 + 关单条件 (warning 样本数 == 0)

> ⚠️ **本脚本必须在用户本地跑** —— 需要在线 Botzone 监听 + 30 分钟生成新 log。
> Agent 不能直接跑（没有真实 Botzone 在线账号）。

用法：
  1. WF-14 重启 Botzone 监听（杀旧 PID + 根目录 nohup run_v8_vs_botzone.py）
  2. 等 30+ 分钟累计 ≥1 场完整对局
  3. python scripts/checks/check_botzone_post_gua216.py
  4. 期望输出：warning 样本数 == 0（之前 GUA-216 修复前有 4 个）

关单条件：
  - 新生成日志样本数 >= 10（验证有数据）
  - warning 样本数 == 0
  - 5 项硬门槛 ① 手算对账 PASS
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.etl.botzone_to_counting_dataset import (
    iter_clean_samples,
    parse_log_file,
    summarize_dataset,
)


def check_new_logs(log_dir: Path, baseline_marker_path: Path) -> Dict[str, any]:
    """扫描 log_dir 所有 v8_vs_botzone_*.log，找出"基线之后"的新 log。

    Args:
        log_dir: 日志目录（默认 logs/）
        baseline_marker_path: 标记文件，记录"GUA-216 修复后"开始时间。
                              第一次运行自动创建；之后只检查新文件。

    Returns:
        {
          "new_files": [...],  # 新日志文件列表
          "total_samples": N,
          "warning_samples": W,
          "warnings_per_match": {match_id: count},
          "pass": bool,
        }
    """
    # 找新文件
    all_logs = sorted(log_dir.glob("v8_vs_botzone_*.log"))
    new_logs = [p for p in all_logs if "_err" not in p.name and "_nohup" not in p.name]

    if not new_logs:
        return {"new_files": [], "total_samples": 0, "warning_samples": 0,
                "warnings_per_match": {}, "pass": False, "reason": "无 v8_vs_botzone_*.log"}

    # baseline marker：简单实现——记录最新日志文件的 mtime
    if not baseline_marker_path.exists():
        # 首次运行：把所有现有 log 当作 baseline，pass=False 提示
        baseline_marker_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_marker_path.write_text(
            json.dumps({"baseline_time": "now", "note": "首次运行；请在 GUA-216 修复+重启监听后再次运行"}),
            encoding="utf-8",
        )
        return {"new_files": [], "total_samples": 0, "warning_samples": 0,
                "warnings_per_match": {}, "pass": False,
                "reason": "首次运行；已创建 baseline marker，请 GUA-216 修复+重启监听后再跑"}

    # 加载 baseline
    marker = json.loads(baseline_marker_path.read_text(encoding="utf-8"))
    if "latest_log_mtime" in marker:
        baseline_mtime = marker["latest_log_mtime"]
        new_files = [p for p in new_logs if p.stat().st_mtime > baseline_mtime]
    else:
        new_files = new_logs  # fallback

    if not new_files:
        return {"new_files": [], "total_samples": 0, "warning_samples": 0,
                "warnings_per_match": {}, "pass": False,
                "reason": "无新日志（GUA-216 修复后未生成新对局）"}

    # 解析所有新 log
    total_samples = 0
    total_warnings = 0
    warnings_per_match: Dict[str, int] = {}
    samples_per_match: Dict[str, int] = {}
    for log_path in new_files:
        matches = parse_log_file(log_path)
        for mid, data in matches.items():
            # ETL 一次（用 in-memory parse，不写盘）
            from scripts.etl.botzone_to_counting_dataset import (
                compute_hand_at_step,
                compute_played_at_step,
                compute_ground_truth,
            )
            n_warn_match = 0
            n_step_match = 0
            for i, step in enumerate(data["steps"]):
                if step.get("stage") != "play":
                    continue
                if "history_raw" not in step:
                    continue
                _, w = compute_hand_at_step(data, i)
                if w:
                    n_warn_match += 1
                n_step_match += 1
            total_samples += n_step_match
            total_warnings += n_warn_match
            warnings_per_match[mid] = n_warn_match
            samples_per_match[mid] = n_step_match

    # 更新 baseline mtime
    latest_mtime = max(p.stat().st_mtime for p in new_logs)
    baseline_marker_path.write_text(
        json.dumps({"latest_log_mtime": latest_mtime, "total_samples_so_far": total_samples}),
        encoding="utf-8",
    )

    return {
        "new_files": [str(p.name) for p in new_files],
        "total_samples": total_samples,
        "warning_samples": total_warnings,
        "warnings_per_match": warnings_per_match,
        "samples_per_match": samples_per_match,
        "pass": (total_samples >= 10 and total_warnings == 0),
    }


def main():
    parser = argparse.ArgumentParser(description="Botzone post-GUA-216 数据质量验证")
    parser.add_argument("--log-dir", type=Path, default=Path("logs"))
    parser.add_argument("--baseline-marker", type=Path,
                        default=Path("data/training/card_counting_v1/.post_gua216_baseline.json"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("check_botzone_post_gua216")

    result = check_new_logs(args.log_dir, args.baseline_marker)

    logger.info("=" * 60)
    logger.info("Botzone post-GUA-216 数据质量验证")
    logger.info("=" * 60)
    logger.info("新日志文件数: %d", len(result["new_files"]))
    for f in result["new_files"]:
        logger.info("  - %s", f)
    logger.info("新样本总数: %d", result["total_samples"])
    logger.info("warning 样本数: %d", result["warning_samples"])
    if result["warnings_per_match"]:
        logger.info("warnings per match:")
        for mid, n in result["warnings_per_match"].items():
            logger.info("  %s: %d warnings", mid, n)
    if "reason" in result:
        logger.info("⚠️ 原因: %s", result["reason"])

    logger.info("=" * 60)
    if result["pass"]:
        logger.info("✅ PASS：GUA-216 修复生效，新对局无扣牌不一致")
        sys.exit(0)
    else:
        logger.info("❌ FAIL：warning != 0 或样本不足")
        sys.exit(1)


if __name__ == "__main__":
    main()