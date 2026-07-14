---
type: entity-module
title: "训练阶段脚本（Stage 5-8）"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
tags:
  - module
  - training
  - stage-5
  - stage-6
  - stage-7
  - stage-8
  - rl
status: current
related_gua: []
date: 2026-06-20
---

# 训练阶段脚本（Stage 5-8）

## 概述

V7 引擎的完整 RL（强化学习）训练流水线，分四阶段渐进迭代。每个阶段均有独立的训练启动器与依赖配置。

## 阶段划分

### Stage 5 — `ultra_optimized`

- **范式**：行为克隆（BC, Behavior Cloning）初版
- **目标**：从人类/规则数据中快速学习基础策略
- **启动器**：`scripts/training/stage5_ultra_optimized.py`
- **状态**：✅ 已完成

### Stage 6 — `game_oriented` / `optimized`

- **范式**：游戏导向的策略优化
- **目标**：在 BC 基础上针对掼蛋规则做定向优化
- **启动器**：`scripts/training/stage6_game_oriented.py` / `stage6_optimized.py`
- **状态**：✅ 已完成

### Stage 7 — `online_rl`

- **范式**：在线强化学习（与批跑对手对抗）
- **目标**：在 wiki-minimax/concepts/batch-evaluation.md 框架下持续自我对弈提升
- **启动器**：`scripts/training/stage7_online_rl.py`
- **快捷方式**：`START_STAGE7_TRAINING.bat`、`INSTALL_STAGE7_DEPENDENCIES.bat`
- **状态**：🚧 进行中（当前主战场）

### Stage 8 — `full_rl`

- **范式**：全量强化学习（多智能体 + 大规模）
- **目标**：突破 Stage 7 的局部最优
- **启动器**：`scripts/training/stage8_full_rl.py`
- **状态**：📋 规划中

## 核心脚本

| 脚本 | 路径 | 用途 |
|------|------|------|
| `train_bc_v7.py` | 根目录 | V7 BC 训练入口 |
| `run_bc_training.py` | `scripts/v7/` | V7 BC 训练启动器 |
| `start_v7_complete.py` | 根目录 | V7 一条龙（BC → 批跑 → GUI） |
| `START_V7_COMPLETE.bat` | 根目录 | V7 一条龙 Windows 快捷方式 |
| `START_SMART_TRAINING.bat` | `scripts/launchers/training/` | 智能训练调度 |
| `START_STRATEGY_TASKS_TRAINING.bat` | `scripts/launchers/training/` | 策略任务训练 |

## 训练 → 评测闭环

```
Stage 5/6 BC 训练
    ↓
train_bc_v7.py 输出 checkpoint
    ↓
run_v7_vs_lalala_games.py 批跑评测（wiki-minimax/concepts/batch-evaluation.md）
    ↓
analyze_v7_rounds.py 副级分析（局不等于副）
    ↓
若胜率达标 → 进入 Stage 7 online_rl
```

## 关联页面

- wiki/entities/engine-v7.md — V7 NN 引擎
- wiki-minimax/concepts/batch-evaluation.md — 批跑评测体系
- [[script-launcher-hierarchy]] — 启动器分层
- wiki/entities/module-batch-executor.md — 批跑执行器
