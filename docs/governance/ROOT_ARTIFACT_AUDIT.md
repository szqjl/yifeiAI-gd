# 根目录散落物审查（2026-05-29）

> 依据 [M-V-Series-治理方案.md](./M-V-Series-治理方案.md) §5.6、§5.9、Phase 5。  
> 迁移脚本：`scripts/tools/migrate_root_artifacts_phase5b.py`

## 审查结论总表

| 文件 | 有效性 | 处置 | 新路径 / 说明 |
|------|--------|------|----------------|
| `status` | **无效**（空文件） | 已删除 | — |
| `test_phase4_final_verification_report.json` | **归档**（2026-05-25，Phase4 未达标） | 已迁入 | `data/archive/eval/` |
| `test_t8_results.json` | **归档**（0 局样本） | 已迁入 | `data/archive/eval/` |
| `test_t9_results.json` | **归档**（16 局 0 胜） | 已迁入 | `data/archive/eval/`；新跑见 `data/eval/` |
| `test_t9_results_backup.json` | **归档** | 已迁入 | `data/archive/eval/` |
| `todo.md` | **半过时**（早期计划，部分已完成） | 已迁入 | `docs/project/todo.md` |
| `train_m1_optimized.sh` | **有效**（≈ `START_M1_TRAINING.bat`） | 已迁入 | `scripts/shell/train_m1_optimized.sh` |
| `training_effect_summary.txt` | **归档**（2025-12-13 策略任务总结） | 已迁入 | `docs/training/archive/` |
| `TRAINING_EFFECTIVENESS_REPORT.md` | **有效·历史**（GUA-017 上下文） | 已迁入 | `docs/guandan-brain/notes/` |
| `TRAINING_FIXES_SUMMARY.md` | **有效·历史**（GUA-016） | 已迁入 | `docs/guandan-brain/notes/` |
| `TRAINING_IMPROVEMENT_REPORT.md` | **有效·历史** | 已迁入 | `docs/guandan-brain/notes/` |
| `V7_GUI_PATH_VALIDATION_FIX.md` | **有效·历史**（GUI 路径校验修复说明） | 已迁入 | `docs/fixes/` |
| `V7_SYSTEM_FIXES.md` | **有效·历史**（V7 actIndex/连接） | 已迁入 | `docs/fixes/` |
| `WORKFLOW_MONITORING_GUIDE.md` | **有效·历史** | 已迁入 | `docs/guandan-brain/notes/` |
| `WORKFLOW_RESTART_LOG.md` | **有效·历史**（ISSUES GUA-017/019） | 已迁入 | `docs/guandan-brain/notes/` |
| `YF_REPLAY.bat` | **有效** | **保留根 stub** | 真源 `scripts/launchers/tools/YF_REPLAY.bat`（Phase 5） |
| `yifeGDBOT-task-card.json` | **有效·示例** | 已迁入 | `scripts/tools/feishu/templates/yifeGDBOT-task-card.example.json` |
| `yifeGDBOT.code-workspace` | **本机专用**（含他人 Obsidian 路径） | 已替换 | `docs/dev/yifeGDBOT.code-workspace.example`（仅本仓库根） |

## 第二批（2026-05-29）：工具配置与运行时残留

| 文件 | 有效性 | 处置 | 说明 |
|------|--------|------|------|
| `_batch_log.txt` | **无效**（空、无引用） | 已删除 + `.gitignore` | 批跑临时日志，不应进 Git |
| `.batch_executor.lock` | **运行时** | 锁文件改到 `tmp/.batch_executor.lock` | `batch_executor/executor.py`；根目录残留可删 |
| `.cursorignore` | **有效** | **保留根目录** | Cursor 约定；已补充 `yfscore/`、`_batch_log.txt` |
| `.cursorrules` | **冗余**（且指向不存在的 `docs/planning/`） | 已删除 | 内容迁入 `.cursor/rules/game-objective.mdc`、`planning-handoff.mdc` |
| `.editorconfig` | **有效** | **保留根目录** | 编辑器统一 UTF-8 / 缩进 |
| `yfscore/` | **误放**（V4 vs lalala 控制台文本 ~354KB） | 已迁入 | `data/archive/match-logs/yfv4_vs_lalala_console.txt`；目录已删 |

## 第三批（2026-05-29）：根目录剩余 `.md`

| 文件 | 处置 | 新路径 |
|------|------|--------|
| `AUTO_RESTART_SYSTEM_STATUS.md` | 已迁入 | `docs/guandan-brain/notes/` |
| `AUTO_RESTART_WORKFLOW_GUIDE.md` | 已迁入 | `docs/guandan-brain/notes/` |
| `MONITOR_WORKFLOW.md` | 已迁入 | `docs/guandan-brain/notes/` |
| `MODEL_BATTLE_RECORD_REPORT.md` | 已迁入 | `docs/guandan-brain/notes/` |
| `GAME_RECORD_SAVE_FIX.md` | 已迁入 | `docs/fixes/`（GUA-008） |
| `GAME_RECORD_VICTORYNUM_CHECK.md` | 已迁入 | `docs/fixes/` |
| `EVALUATOR_COMPATIBILITY_REPORT.md` | 已迁入 | `docs/fixes/` |
| `INSTALL_DEPENDENCIES.md` | 已迁入 | `docs/development/` |
| `KANBAN.md` | 已迁入 | `docs/governance/` |
| `KANBAN_CARD_INTEGRATION.md` | 已迁入 | `docs/governance/` |
| `kanban-task-card.json` | 已迁入 | `scripts/tools/feishu/templates/kanban-task-card.example.json` |
| `PRACTICAL_RECORDS_TRAINING_GUIDE.md` | 已迁入 | `docs/training/archive/` |
| `README_M1_TRAINING.md` | 已迁入 | `docs/training/archive/` |
| `README_M1_WORKFLOW.md` | 已迁入 | `docs/training/archive/` |

**根目录保留 `.md`**：仅 `README.md`、`CLAUDE.md`。

## 代码引用已更新

| 引用方 | 变更 |
|--------|------|
| `scripts/tools/run_t9_direct.py` | 输出 → `data/eval/test_t9_results.json` |
| `scripts/launchers/tools/run_new_test.bat` | 去掉 `C:\yifeGDBOT`，改用 `%REPO_ROOT%` + `scripts/batch_executor.py` |
| `docs/guandan-brain/ISSUES.md` | 工作流/训练纪要链至 `notes/` |
| `scripts/shell/train_m1_optimized.sh` | 启动时 `cd` 仓库根 |
| `batch_executor/executor.py` | 单实例锁 → `tmp/.batch_executor.lock`（自动清理根目录旧锁） |
| `scripts/gui/batch_executor_gui_m1.py` | `REPO_ROOT = parents[2]` |
| `scripts/launchers/m/START_M1_GUI.bat` | `python scripts/gui/batch_executor_gui_m1.py` |
| `scripts/shell/*.sh` | 头部 `cd` 仓库根；`run_new_test.sh` 对齐 `run_new_test.bat` |

## Phase 5 GUI / shell（2026-05-29 已完成）

| 原根目录 | 新路径 | 根目录 stub |
|----------|--------|-------------|
| `batch_executor_gui_m1.py` | `scripts/gui/batch_executor_gui_m1.py` | 是（`runpy`） |
| `start_gui.py` | `scripts/gui/start_gui.py` | 是 |
| `auto_clean_large_files.sh` 等 4 个 `.sh` | `scripts/shell/` | 否 |

根目录 **无** `.sh` 真源；`.py` GUI 入口仅保留薄 stub。

## Phase 5f docs 归档（2026-05-29）

| 迁移 | 目标 |
|------|------|
| `docs/rules/`、`docs/skill/` | `docs/archive/`（根留 README stub） |
| `docs/claude-analysis/` | `docs/analysis/agent-sessions/` |
| `lalala_src/*.py` | `reference/lalala/` |

## 个人工作区

若需多根工作区，复制 `docs/dev/yifeGDBOT.code-workspace.example` 到本机并自行添加 Obsidian 等路径；**勿将本机绝对路径提交进 Git**。
