# -*- coding: utf-8 -*-
"""残局异常扫描器。"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_ROOT = os.path.join(REPO_ROOT, "src")
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, SRC_ROOT)

from src.v.nn.endgame.endgame_anomaly_scanner import (  # noqa: E402
    format_anomaly,
    scan_record_file,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="扫描 game_records_v7 中的残局异常样本")
    parser.add_argument("--scan-dir", default="game_records_v7", help="待扫描目录")
    parser.add_argument("--limit", type=int, default=20, help="最多打印多少条异常样本")
    parser.add_argument(
        "--critical-remaining",
        default="1,3",
        help="敌方临门张数集合，逗号分隔；默认 1,3",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scan_dir = Path(args.scan_dir)
    if not scan_dir.exists():
        print(f"错误: 目录不存在 — {scan_dir}")
        return 1

    critical_remaining = tuple(
        int(part.strip()) for part in str(args.critical_remaining).split(",") if part.strip()
    )
    files = sorted(scan_dir.glob("*.json"))
    if not files:
        print(f"错误: {scan_dir} 中没有 JSON 文件")
        return 1

    all_findings = []
    for path in files:
        try:
            all_findings.extend(scan_record_file(path, critical_remaining=critical_remaining))
        except Exception as exc:
            print(f"⚠ 跳过 {path.name}: {exc}")

    print(f"扫描目录: {scan_dir}")
    print(f"记录文件: {len(files)}")
    print(f"异常总数: {len(all_findings)}")
    if not all_findings:
        print("未发现异常样本")
        return 0

    code_counter = Counter(finding["code"] for finding in all_findings)
    print("按 code 统计:")
    for code, count in code_counter.most_common():
        print(f"  {code}: {count}")

    print(f"样本（前 {min(args.limit, len(all_findings))} 条）:")
    for finding in all_findings[: args.limit]:
        print(f"  {format_anomaly(finding)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
