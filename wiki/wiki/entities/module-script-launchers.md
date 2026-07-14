---
type: entity-module
title: "scripts/launchers/ 启动器分层"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
tags:
  - module
  - launchers
  - phase-5
  - script-organization
status: current
related_gua: []
date: 2026-06-20
---

# scripts/launchers/ 启动器分层

## 概述

`scripts/launchers/` 是 Phase 5 目录迁移的**核心落地**，承担项目所有引擎、训练、分析工具的**启动器入口**职责。根目录下的 `.bat` 和 `.py` 多为 stub，真源在此。

## 五大子目录

### 1. `scripts/launchers/v7/` — V7 NN 引擎

**职责**：V7 神经网络引擎的 GUI/CLI 启动入口

**核心脚本**：
- `batch_executor_gui_v7.py` — V7 批跑 GUI（对应 wiki/entities/module-batch-executor.md）

**关联**：wiki/entities/engine-v7.md 是当前主迭代方向

### 2. `scripts/launchers/v-learn/` — V4-V6 学习引擎

**职责**：V4、V5、V6 实验性学习引擎的启动入口

**核心脚本**：
- `START_V4_GUI.bat`、`START_V5_GUI.bat`、`START_V6_GUI.bat`

**关联**：V4-V6 是 V7 的过渡实验版本

### 3. `scripts/launchers/m/` — M 系列规则引擎

**职责**：M1、M2、M3 规则引擎的 GUI 启动入口

**核心脚本**：
- `START_M1_GUI.bat`、`START_M2_GUI.bat`、`START_M3_GUI.bat`
- `START_M1_TRAINING.bat` — M1 训练启动
- `START_M1_WORKFLOW_FULL.bat` — M1 完整工作流

**关联**：wiki-minimax/entities/engine-m3.md 是当前生产主力，但入口覆盖度低于 V7

### 4. `scripts/launchers/training/` — 训练流水线

**职责**：Stage 5-8 训练流水线启动器

**核心脚本**：
- `START_SMART_TRAINING.bat` — 智能训练调度
- `START_STAGE7_TRAINING.bat` — Stage 7 专项
- `START_STRATEGY_TASKS_TRAINING.bat` — 策略任务训练
- `INSTALL_STAGE7_DEPENDENCIES.bat` — Stage 7 依赖安装
- `run_bc_training.py` — BC 训练启动器

**关联**：[[module-training-stages]] 完整描述 Stage 5-8

### 5. `scripts/launchers/tools/` — 辅助工具

**职责**：replay、encoding、git 历史、argv 探测、飞书网关、Phase 5 迁移等辅助工具

**核心脚本**：
- `YF_REPLAY.bat` — 回放工具
- `batch_convert_replays.bat` — 批量转换回放
- `pre_push_check.bat` — 推送前检查

## 根目录 Stub 映射表

| 根目录 Stub | 真源位置 |
|-------------|----------|
| `START_V7_GUI.bat` | `scripts/launchers/v7/batch_executor_gui_v7.py` |
| `START_V4_GUI.bat` | `scripts/launchers/v-learn/START_V4_GUI.bat` |
| `START_M3_GUI.bat` | `scripts/launchers/m/START_M3_GUI.bat` |
| `START_M1_TRAINING.bat` | `scripts/launchers/training/` |

## 维护规则

1. **新增脚本**：必须放置到对应的 `scripts/launchers/` 子目录
2. **删除脚本**：同步更新 [[SCRIPT_INDEX-summary]]
3. **跨平台兼容**：根目录 stub 保留 Windows `.bat` 与 Linux `.py` 双入口
4. **真源优先**：所有文档、GUA、Wiki 引用应指向 `scripts/launchers/` 真源

## 关联页面

- [[SCRIPT_INDEX-summary]] — 完整脚本索引
- [[script-launcher-hierarchy]] — 启动器分层概念
- [[script-directory-layout]] — 脚本目录布局
- [[m-v-series-architecture]] — M/V 三系列架构
