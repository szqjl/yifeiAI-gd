---
type: source-summary
title: "根目录脚本清理清单（Phase 3 已完成）"
sources:
  - docs/governance/repo-cleanup-inventory.md
tags:
  - governance
  - cleanup
  - phase-3
  - historical
status: historical
related_gua: []
date: 2026-06-18
---

# 根目录脚本清理清单（Phase 3 已完成）

## 来源

- 源文件：`docs/governance/repo-cleanup-inventory.md`（4883 字符）
- 描述时期：2026-05-28 ~ 2026-05-29 的迁移过程
- 当前状态：**已完成**（历史归档）

## 核心结论

根目录「无 .py 真源」「无 .sh 真源」结论的来源文档。Phase 3 阶段登记了 **7 批迁移记录**，将散落脚本统一收入 `scripts/` 子目录。

## scripts/ 目录布局（Phase 4 收敛结果）

| 子目录 | 用途 | 典型文件 |
|--------|------|----------|
| `scripts/gui/` | GUI 真源 | `batch_executor_gui_m1/m2/m3`, `start_gui` |
| `scripts/shell/` | Shell 真源 | `train_m1_optimized.sh` 等 |
| `scripts/checks/` | 检查/诊断 | `check_*` / `diagnose_*` 共 23 个 |
| `scripts/verify/` | 验证脚本 | `verify_p0_*` 等 7 个 |
| `scripts/analysis/` | 分析脚本 | `analyze_*` 6 个 |
| `scripts/training/` | 训练脚本 | `train_stage5/6/7/8` + view/monitor 等 ~10 个 |
| `scripts/tools/` | 工具集 | `batch_update` / `clean` / `convert` / `download` / `feishu` / `replay` 等 ~13 个 |
| `scripts/workflow/` | 工作流 | `auto_restart_workflow`, `workflow_current_status`, `monitor_workflow_progress` |
| `scripts/v7/` | V7 专用 | `start_v7_complete`, `start_v7_gui` |
| `scripts/clients/` | 客户端 | `client_std_1`, `client_std_3` |
| `scripts/batch_executor.py` | 原根目录 CLI 入口（已迁入） | — |
| `tests/` | 测试文件 | 约 18 个测试已入库 |

## 根目录残留

### 薄 stub（runpy 转发）

- `batch_executor_gui_m1.py`
- `start_gui.py`
- `pre_push_check.bat`

### 根 dotfiles

- `.cursorignore`
- `.editorconfig`
- `.batch_executor.lock`（已改到 `tmp/`）

## 历史意义

本清单是 [[document-governance]] 概念在脚本层的具体实践案例，配合 [[root-artifact-audit-summary]] 共同构成「根目录物理布局」的治理闭环。

## 关联页面

- [[root-artifact-audit-summary]] — Phase 5 散落物审查（同期完成）
- [[script-directory-layout]] — 概念页：scripts/ 目录布局
- [[document-governance]] — 概念页：文档治理
- [[m-v-series-architecture]] — M/V 三系列分层架构
