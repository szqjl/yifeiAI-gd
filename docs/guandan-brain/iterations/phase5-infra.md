---
tags: [infrastructure, Phase5, governance, docs]
created: 2026-05-29
topic: Phase 5 仓库治理与基础设施整理
related: [[Infrastructure]], [[governance-docs]]
---

# Phase 5 仓库治理与基础设施整理

> 来源：[[ITERATIONS]] 2026-05-29（10 条迭代）

## Phase 5a–5g 全流程

| 步骤 | 内容 | 关键产出 |
|------|------|----------|
| 5a | `scripts/launchers/` 创建 + 根目录 25 bat stub | `migrate_launchers_phase5.py` |
| 5b | 根目录散落物（md/json/sh）迁入 `notes/` `fixes/` `data/archive/` | `ROOT_ARTIFACT_AUDIT.md` |
| 5c | 运行时/工具配置：锁→`tmp/`，`.cursorrules`→`.cursor/rules/*.mdc` | 规则模块化 |
| 5d | 根目录 md 清仓（KANBAN、AUTO_RESTART_* 等 14 篇） | 全部迁入子目录 |
| 5e | GUI + shell 收尾：`batch_executor_gui_m1.py`→`scripts/gui/` | 4 个 `.sh`→`scripts/shell/` |
| 5f | docs 归档 + lalala 源码→`reference/lalala/` | `check_doc_paths.py` pass |
| 5g | `docs/implementation/`→`docs/archive/implementation/` | 归档完成 |
| 结案 | Phase 0–5 归档完成；提交 `72b117c`/`6505778` | 治理 §9 标「仓库整理已结案」 |

## M2/M3 物理迁入

- 11 个 M1 模块 → `src/m/m1/`
- M2/M3 → `src/m/m2/`、`src/m/m3/`
- 4 个 V 引擎 → `src/v/`
- 契约 + GUA 回归 **33 passed**

## 后续

- GitHub 镜像 push-only 同步（`sync_github_mirror.ps1`）
- develop 分支清理
