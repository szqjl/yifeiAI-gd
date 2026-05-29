# 启动脚本（Launchers）

> Phase 5（2026-05-29）：根目录 `START_*.bat` 等真源迁入此目录；仓库根仅保留 **薄 stub**（双击旧文件名仍可用）。  
> 治理说明：[M-V-Series-治理方案.md](../../docs/governance/M-V-Series-治理方案.md) §5.5–§5.7。

## 使用方式

| 方式 | 说明 |
|------|------|
| **习惯路径** | 仍在仓库根双击 `START_M1_GUI.bat` 等（自动 `call` 到本目录） |
| **直接调用** | `scripts\launchers\m\START_M1_GUI.bat` |
| **工作目录** | 各脚本通过 `_env.bat` 将 `cd` 设为仓库根（`%REPO_ROOT%`） |

## 目录结构

| 子目录 | 系列/用途 | 脚本 |
|--------|-----------|------|
| `m/` | M1/M2/M3 GUI、M1 训练与工作流 | `START_M1_GUI.bat`、`START_M2_GUI.bat`、`START_M3_GUI.bat`、`START_M1_TRAINING.bat`、`START_M1_WORKFLOW_FULL.bat` |
| `v-learn/` | V4–V6（deprecated 客户端仍可通过 GUI 批跑） | `START_V4_GUI.bat`、`START_V5_GUI.bat`、`START_V6_GUI.bat`、`START_V5_CLIENTS.bat` |
| `v-nn/` | V7 | `START_V7_GUI.bat`、`START_V7_COMPLETE.bat`、`START_V7_AUTO.bat`、`START_V7_CLIENTS.bat` |
| `training/` | 阶段训练 / 智能训练 | `START_STAGE7_TRAINING.bat`、`START_SMART_TRAINING.bat`、`START_STRATEGY_TASKS_TRAINING.bat`、`QUICK_START_STAGE7*.bat`、`INSTALL_STAGE7_DEPENDENCIES.bat`、`run_stage6_training_gui.bat` |
| `workflow/` | 工作流自动重启 | `START_AUTO_RESTART_WORKFLOW.bat` |
| `tools/` | 回放、批转换、测试 | `YF_REPLAY.bat`、`batch_convert_replays.bat`、`run_new_test.bat` |
| `checks/` | 记录一致性 | `CHECK_RECORD_CONSISTENCY.bat` |

## 根目录 GUI 入口（薄 stub）

| 文件 | 真源 |
|------|------|
| `batch_executor_gui_m1.py` | `scripts/gui/batch_executor_gui_m1.py` |
| `start_gui.py` | `scripts/gui/start_gui.py` |

日常启动：`scripts/launchers/m/START_M1_GUI.bat` → `python scripts/gui/batch_executor_gui_m1.py`。

## 维护约定

1. **新增启动器**：只在本目录对应子文件夹添加 `.bat`；根目录增加 3 行 stub（见 `START_M1_GUI.bat`）。
2. **路径**：脚本内使用 `%REPO_ROOT%` 或相对仓库根路径；禁止写死 `D:\...`（V7 GUI 中 lalala 路径待配置化）。
3. **Python**：M1 GUI 使用 `python.exe`（非 `py`），见 `m/START_M1_GUI.bat` 注释。
4. **分支**：日常开发分支为 **`m-dev`**（非 `m1-dev`）。

## 迁移工具

```bash
python scripts/tools/migrate_launchers_phase5.py
```

重新生成 launchers 正文与根 stub（修改映射表后使用）。
