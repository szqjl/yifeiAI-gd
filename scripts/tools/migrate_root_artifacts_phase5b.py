#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 5b：根目录散落 md/txt/json/sh 迁入约定目录（见治理方案 §5.6–§5.9）。"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MOVES: list[tuple[str, str]] = [
    ("TRAINING_EFFECTIVENESS_REPORT.md", "docs/guandan-brain/notes/TRAINING_EFFECTIVENESS_REPORT.md"),
    ("TRAINING_FIXES_SUMMARY.md", "docs/guandan-brain/notes/TRAINING_FIXES_SUMMARY.md"),
    ("TRAINING_IMPROVEMENT_REPORT.md", "docs/guandan-brain/notes/TRAINING_IMPROVEMENT_REPORT.md"),
    ("WORKFLOW_MONITORING_GUIDE.md", "docs/guandan-brain/notes/WORKFLOW_MONITORING_GUIDE.md"),
    ("WORKFLOW_RESTART_LOG.md", "docs/guandan-brain/notes/WORKFLOW_RESTART_LOG.md"),
    ("V7_GUI_PATH_VALIDATION_FIX.md", "docs/fixes/V7_GUI_PATH_VALIDATION_FIX.md"),
    ("V7_SYSTEM_FIXES.md", "docs/fixes/V7_SYSTEM_FIXES.md"),
    ("training_effect_summary.txt", "docs/training/archive/training_effect_summary.txt"),
    ("todo.md", "docs/project/todo.md"),
    ("train_m1_optimized.sh", "scripts/shell/train_m1_optimized.sh"),
    ("test_phase4_final_verification_report.json", "data/archive/eval/test_phase4_final_verification_report.json"),
    ("test_t8_results.json", "data/archive/eval/test_t8_results.json"),
    ("test_t9_results.json", "data/archive/eval/test_t9_results.json"),
    ("test_t9_results_backup.json", "data/archive/eval/test_t9_results_backup.json"),
        ("yifeGDBOT-task-card.json", "scripts/tools/feishu/templates/yifeGDBOT-task-card.example.json"),
]

MOVES_BATCH3: list[tuple[str, str]] = [
    ("AUTO_RESTART_SYSTEM_STATUS.md", "docs/guandan-brain/notes/AUTO_RESTART_SYSTEM_STATUS.md"),
    ("AUTO_RESTART_WORKFLOW_GUIDE.md", "docs/guandan-brain/notes/AUTO_RESTART_WORKFLOW_GUIDE.md"),
    ("MONITOR_WORKFLOW.md", "docs/guandan-brain/notes/MONITOR_WORKFLOW.md"),
    ("MODEL_BATTLE_RECORD_REPORT.md", "docs/guandan-brain/notes/MODEL_BATTLE_RECORD_REPORT.md"),
    ("GAME_RECORD_SAVE_FIX.md", "docs/fixes/GAME_RECORD_SAVE_FIX.md"),
    ("GAME_RECORD_VICTORYNUM_CHECK.md", "docs/fixes/GAME_RECORD_VICTORYNUM_CHECK.md"),
    ("EVALUATOR_COMPATIBILITY_REPORT.md", "docs/fixes/EVALUATOR_COMPATIBILITY_REPORT.md"),
    ("INSTALL_DEPENDENCIES.md", "docs/development/INSTALL_DEPENDENCIES.md"),
    ("KANBAN.md", "docs/governance/KANBAN.md"),
    ("KANBAN_CARD_INTEGRATION.md", "docs/governance/KANBAN_CARD_INTEGRATION.md"),
    ("kanban-task-card.json", "scripts/tools/feishu/templates/kanban-task-card.example.json"),
    ("PRACTICAL_RECORDS_TRAINING_GUIDE.md", "docs/training/archive/PRACTICAL_RECORDS_TRAINING_GUIDE.md"),
    ("README_M1_TRAINING.md", "docs/training/archive/README_M1_TRAINING.md"),
    ("README_M1_WORKFLOW.md", "docs/training/archive/README_M1_WORKFLOW.md"),
]

# 第二批：运行时 / 误放目录（仅当仍存在时处理）
RUNTIME_DELETE = ["_batch_log.txt", ".batch_executor.lock", ".cursorrules"]
YFSCORE_SRC = "yfscore/yfscore/yfv4_vs_lalala"
YFSCORE_DST = "data/archive/match-logs/yfv4_vs_lalala_console.txt"

DELETE_IF_EMPTY = ["status"]


def main() -> None:
    for rel in (
        "docs/guandan-brain/notes",
        "docs/training/archive",
        "data/archive/eval",
        "scripts/shell",
        "scripts/tools/feishu/templates",
        "docs/dev",
        "docs/governance",
        "docs/development",
        "docs/fixes",
    ):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)

    for src_rel, dst_rel in MOVES + MOVES_BATCH3:
        src, dst = ROOT / src_rel, ROOT / dst_rel
        if not src.is_file():
            print(f"SKIP missing {src_rel}")
            continue
        if dst.exists():
            print(f"SKIP exists {dst_rel}")
            continue
        shutil.move(str(src), str(dst))
        print(f"OK {src_rel} -> {dst_rel}")

    ws = ROOT / "yifeGDBOT.code-workspace"
    example = ROOT / "docs/dev/yifeGDBOT.code-workspace.example"
    if ws.is_file() and not example.is_file():
        example.write_text(
            '{\n\t"folders": [\n\t\t{\n\t\t\t"path": "."\n\t\t}\n\t],\n\t"settings": {\n\t\t"files.associations": {\n\t\t\t"*.rep": "xml"\n\t\t}\n\t}\n}\n',
            encoding="utf-8",
        )
        ws.unlink()
        print("OK yifeGDBOT.code-workspace -> docs/dev/yifeGDBOT.code-workspace.example (sanitized)")

    for name in DELETE_IF_EMPTY:
        p = ROOT / name
        if p.is_file() and p.stat().st_size == 0:
            p.unlink()
            print(f"DEL empty {name}")


if __name__ == "__main__":
    main()
