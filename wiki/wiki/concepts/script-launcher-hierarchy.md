---
type: concept
title: "脚本启动器分层"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
tags:
  - concept
  - launchers
  - hierarchy
  - engine-family
status: current
related_gua: []
date: 2026-06-20
---

# 脚本启动器分层

## 概述

`scripts/launchers/` 采用**两级分层**：第一级按**引擎族**划分，第二级按**功能域**细分。这种设计支持多引擎并行演进，避免启动器命名冲突。

## 分层结构

```
scripts/launchers/
├── v7/                    # 第一级：V7 NN 引擎族
│   └── batch_executor_gui_v7.py
│
├── v-learn/               # 第一级：V4-V6 学习引擎族
│   ├── START_V4_GUI.bat
│   ├── START_V5_GUI.bat
│   └── START_V6_GUI.bat
│
├── m/                     # 第一级：M 系列规则引擎族
│   ├── START_M1_GUI.bat
│   ├── START_M2_GUI.bat
│   ├── START_M3_GUI.bat
│   ├── START_M1_TRAINING.bat
│   └── START_M1_WORKFLOW_FULL.bat
│
├── training/              # 第一级：训练流水线（跨引擎）
│   ├── run_bc_training.py
│   ├── START_SMART_TRAINING.bat
│   ├── START_STAGE7_TRAINING.bat
│   ├── START_STRATEGY_TASKS_TRAINING.bat
│   └── INSTALL_STAGE7_DEPENDENCIES.bat
│
└── tools/                 # 第一级：辅助工具（跨引擎）
    ├── YF_REPLAY.bat
    ├── batch_convert_replays.bat
    └── pre_push_check.bat
```

## 根目录 Stub 完整映射表

| 根目录 Stub | 真源（scripts/launchers/） |
|-------------|---------------------------|
| `START_V7_GUI.bat` | `v7/batch_executor_gui_v7.py` |
| `START_V7_CLIENTS.bat` | `v7/` 下客户端启动器 |
| `START_V7_COMPLETE.bat` | `v7/` 一条龙脚本 |
| `START_V7_AUTO.bat` | `v7/` 自动模式 |
| `RUN_V7_VS_LALALA.bat` | 根目录 `run_v7_vs_lalala_games.py` |
| `START_V4_GUI.bat` | `v-learn/START_V4_GUI.bat` |
| `START_V5_GUI.bat` | `v-learn/START_V5_GUI.bat` |
| `START_V6_GUI.bat` | `v-learn/START_V6_GUI.bat` |
| `START_M1_GUI.bat` | `m/START_M1_GUI.bat` |
| `START_M2_GUI.bat` | `m/START_M2_GUI.bat` |
| `START_M3_GUI.bat` | `m/START_M3_GUI.bat` |
| `START_M1_TRAINING.bat` | `m/` 或 `training/` |
| `START_M1_WORKFLOW_FULL.bat` | `m/` |
| `START_SMART_TRAINING.bat` | `training/START_SMART_TRAINING.bat` |
| `START_STAGE7_TRAINING.bat` | `training/START_STAGE7_TRAINING.bat` |
| `START_STRATEGY_TASKS_TRAINING.bat` | `training/START_STRATEGY_TASKS_TRAINING.bat` |
| `INSTALL_STAGE7_DEPENDENCIES.bat` | `training/INSTALL_STAGE7_DEPENDENCIES.bat` |
| `YF_REPLAY.bat` | `tools/YF_REPLAY.bat` |
| `batch_convert_replays.bat` | `tools/batch_convert_replays.bat` |
| `pre_push_check.bat` | `tools/pre_push_check.bat` |

## 命名约定

- **批处理（.bat）**：`START_<功能>_<引擎>.bat` 或 `<功能>.bat`
- **Python（.py）**：`<功能>_<引擎>.py`（如 `batch_executor_gui_v7.py`）
- **PowerShell（.ps1）**：`<功能>.ps1`（如 `start-bot.ps1`）

## 入口分裂风险

V7 当前存在 8+ 个入口（GUI/CLI/Windows/Linux），存在认知分裂风险。建议：
1. 在 [[SCRIPT_INDEX-summary]] 中标注**主入口**与**辅助入口**
2. 所有新文档统一引用主入口
3. 辅助入口逐步合并或标注 deprecated

## 关联页面

- [[SCRIPT_INDEX-summary]] — 完整脚本索引
- [[module-script-launchers]] — 启动器分层模块
- [[m-v-series-architecture]] — M/V 三系列架构
- [[script-directory-layout]] — 脚本目录布局
