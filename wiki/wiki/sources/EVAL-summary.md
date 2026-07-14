---
type: source-summary
title: "EVAL.md 结构化摘要"
sources:
  - docs/guandan-brain/EVAL.md
tags:
  - evaluation
  - batch
  - source
status: current
related_gua:
  - GUA-020
  - GUA-026
  - GUA-029
  - GUA-031
  - GUA-034
  - GUA-048
date: 2026-06-17
---

# EVAL.md 结构化摘要

## 来源概述

`docs/guandan-brain/EVAL.md`（5646 字符）是项目批跑评测体系的**核心规范文档**，定义了对局评测的档位、口径、版本说明与 Golden Cases。

## 关键定义

### 1. 批跑局数档位（v1006 · 定音）

| 档位 | 局数 | 用途 |
|------|------|------|
| **标准档** | **12 局** | 默认主交付（3 的倍数） |
| 轻量档 | 3 局 | 冒烟/回归 |
| 中量档 | 9 局 | 快速验证 |
| 对照档 | 10 局 | 仅历史对照，**不再新开** |

> **定音**：10 局样本仅作历史对照，不再新开。所有新批跑使用 3/9/12 档。

### 2. 局 ≠ 副（核心口径）

- **局（game）**：一场完整掼蛋（包含 1～N 副），读 `victoryNum[0]` vs `victoryNum[1]` 判定队胜负
- **副（round）**：一局中的单副牌局，从 `game_records/total_rounds` 读取

⚠️ **KPI 分离**：队胜率（局）≠ 副数胜率（副），评测时必须显式区分。

### 3. M3 vs V7 评估分离

| 引擎 | 评估线 | 默认批跑 |
|------|--------|----------|
| **M3** | 主交付线 | 12 局批跑 |
| **V7** | 实验线 | 仅观测，不混用 KPI |

### 4. 客户端与坐位

```
坐位 0+2：yf1_m3 / yf2_m3  （M3 客户端）
坐位 1+3：run_lalala_client3/4  （对手）
```

### 5. V 系列 GUI 优先级陷阱

`batch_executor_gui.py` 的默认优先级为 **M1 → V6 → V5**，**V4 不在其中**。

- 评测 V4 须手动改优先级，或改用无头 `batch_executor` CLI
- 这是 GUI 入口的已知陷阱，参考 wiki/entities/module-batch-executor.md

## Golden Cases

EVAL.md 引用了 `M1-yf1-yf2` 作为 Golden Cases 参考案例，对应 [[gua-020]]（已 closed，PASS 率差 0.92% 无显著差异）。

## 关联 GUA

- **GUA-020**：yf1_m1 vs yf2_m1 对照（closed）
- **GUA-026**：常态三带二禁拆炸/级牌 trips（active_constraint）
- **GUA-029**：R3/R4/R5 兜底（active_constraint）
- **GUA-031**：solo 时 greater 为对手（active_constraint）
- **GUA-034**：残局拦头游（closed，2026-06-01）
- **GUA-048**：batch_executor dump 延迟（open，P2）

## 跨引用

- wiki-minimax/concepts/batch-evaluation.md — 评测体系概念页
- [[game-vs-round]] — 局/副口径原则
- wiki/entities/module-batch-executor.md — 批跑入口模块
- wiki-minimax/entities/engine-m3.md — M3 决策引擎
- wiki/entities/engine-v7.md — V7 NN 引擎
