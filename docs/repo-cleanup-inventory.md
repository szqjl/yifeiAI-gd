# 根目录脚本清理清单（Phase 3）

> 治理方案 Phase 4 再物理迁移；本文件仅分类登记。生成日期：2026-05-28  
> 主开发分支：**m-dev**

## 统计

| 类别 | 数量（约） | 处理建议 |
|------|------------|----------|
| 根目录 `.py` | 64 | 见下表 |
| 目标 | — | 可复用 → `scripts/`；M1 入口保留文档说明 |

## 建议保留在根目录（短期）

| 文件 | 原因 |
|------|------|
| `batch_executor_gui_m1.py` | M1 批跑 GUI 常用入口 |
| `start_gui.py` | GUI 启动 |

## 建议迁入 `scripts/`（Phase 4）

### 检查 / 诊断

`check_*.py`、`diagnose_*.py`、`verify_*.py`、`analyze_*.py`（根目录下多数）

**已迁入 `scripts/checks/`（2026-05-28 第一批，15 个）：**

`check_websocket_config`、`check_workflow_status`、`check_workflow_notification`、`check_auto_restart_status`、`check_training_progress_detailed`、`check_game_record_consistency`、`check_client_positions`、`check_mlflow_runs`、`check_models_before_push`、`check_cuda`、`check_gui_paths`、`check_evaluation_issue`、`diagnose_training_data`、`diagnose_training_issues`、`diagnose_v7_connection`

**根目录 check/diagnose 已全部迁入 `scripts/checks/`（2026-05-28 第二批，8 个）：**

`check_model_loading`、`check_model_optimizations`、`check_training_progress`、`check_stage7_dependencies`、`check_m1_records_for_training`、`check_model_battle_record`、`check_records_for_evaluator`、`check_latest_game_records`

### 训练相关（V 线，非 M 日常）

`train_stage*.py`、`monitor_training.py`、`check_training_progress*.py`

### V7 实验

`start_v7_*.py`、`diagnose_v7_connection.py`

### 批处理 / 工具

`batch_update_*.py`、`clean_*.py`、`convert_rep_to_xml.py`、`download_models.py`

### 测试 / 临时

`_test_*.py`、`debug_test.py` → 删除或 `tests/`

## 已在子目录、根目录可删重复（需 diff 后执行）

| 根目录 | 可能重复位置 |
|--------|----------------|
| `batch_executor.py` | `batch_executor/` 包 |
| `stage6_training_gui*.py` | 考虑 `scripts/training/` |

## 勿提交 Git（已在 .gitignore）

- `models/` 全目录
- `training_logs/`、`logs/`、`game_records/`、`data/artifacts/`

## 下一步（Phase 4 PR）

1. ~~新建 `scripts/checks/`~~ ✅ 已建；**check/diagnose 全部 23 个**已迁入
2. **第三批**：根目录 `verify_*.py` / `analyze_*.py` / 训练脚本 → `scripts/` 子目录
3. 每次 PR 只迁一类（≤15 文件），更新 import 与文档
4. 根目录 README 或 `docs/usage/` 更新启动命令
