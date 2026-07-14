---
type: source-summary
title: "根目录散落物审查（Phase 5 已完成）"
sources:
  - docs/governance/ROOT_ARTIFACT_AUDIT.md
tags:
  - governance
  - cleanup
  - phase-5
  - historical
status: historical
related_gua:
  - GUA-008
  - GUA-016
  - GUA-017
date: 2026-06-18
---

# 根目录散落物审查（Phase 5 已完成）

## 来源

- 源文件：`docs/governance/ROOT_ARTIFACT_AUDIT.md`（4896 字符）
- 描述时期：2026-05-29 的三批处置
- 当前状态：**已完成**（历史归档）

## 核心处置（三批）

### 第一批：无效文件清理

- `status`（空文件）→ 删除
- `_batch_log.txt`（空）→ 删除
- `.cursorrules`（冗余）→ 删除（已迁入 `.cursor/rules/`）

### 第二批：工具配置

- `docs/dev/yifeGDBOT.code-workspace.example` 替换原 `.code-workspace`（本机专用）

### 第三批：剩余 .md 归档

- `docs/archive/` ← 原 `docs/rules/` + `docs/skill/`（根留 README stub）
- `docs/analysis/agent-sessions/` ← 原 `docs/claude-analysis/`
- `reference/lalala/` ← 原 `lalala_src/*.py`
- `docs/fixes/` ← 多个修复文档（含 V7 相关）
- `docs/guandan-brain/notes/` ← 训练/工作流笔记
- `docs/training/archive/` ← 训练归档
- `docs/governance/` ← KANBAN 相关
- `docs/development/` ← INSTALL_DEPENDENCIES
- `docs/project/todo.md` ← 原 `todo.md`
- `data/archive/eval/` ← 历史评测结果
- `data/archive/match-logs/yfv4_vs_lalala_console.txt` ← 原 `yfscore/` 误放内容
- `scripts/shell/train_m1_optimized.sh` ← 原根目录 shell
- `scripts/tools/feishu/templates/` ← 飞书模板

## 文档迁移清单中的 GUA 关联

| 文档 | 关联 GUA | 迁入位置 |
|------|----------|----------|
| `GAME_RECORD_SAVE_FIX.md` | **GUA-008** | `docs/fixes/` |
| `TRAINING_FIXES_SUMMARY.md` | **GUA-016** | `docs/guandan-brain/notes/` |
| `TRAINING_EFFECTIVENESS_REPORT.md` / `WORKFLOW_RESTART_LOG.md` | **GUA-017** | `docs/guandan-brain/notes/` |
| `GAME_RECORD_VICTORYNUM_CHECK.md` | — | `docs/fixes/` |
| `EVALUATOR_COMPATIBILITY_REPORT.md` | — | `docs/fixes/` |
| `V7_GUI_PATH_VALIDATION_FIX.md` | — | `docs/fixes/` |
| `V7_SYSTEM_FIXES.md` | — | `docs/fixes/` |

## 已知悬置项

- `yf_replay.py` 暂留根目录（第六批说明），但收尾批又写「yf_replay → scripts/gui/ / scripts/tools/」存在**描述矛盾**
- `stage6_training_gui*.py` 与 `scripts/training/` 存在潜在重复（待 diff）
- `batch_executor/` 包 vs `scripts/batch_executor.py` 关系未明
- `DOCUMENT_AUDIT.md` 被 推送前检查指南 引用，但归档后路径可能在 `docs/development/`

## 关联页面

- [[repo-cleanup-inventory-summary]] — Phase 3 脚本迁移
- [[gua-008]] — GAME_RECORD_SAVE_FIX
- [[gua-016]] — TRAINING_FIXES_SUMMARY
- [[gua-017]] — TRAINING_EFFECTIVENESS_REPORT / WORKFLOW_RESTART_LOG
- wiki/entities/engine-v7.md — V7_SYSTEM_FIXES 已迁入 docs/fixes/
- [[document-governance]] — 概念页
