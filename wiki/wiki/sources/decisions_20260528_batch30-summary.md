---
type: source-summary
title: "decisions_20260528_batch30 批跑数据摘要"
sources:
  - docs/analysis/agent-sessions/decisions_20260528_batch30.md
tags:
  - batch-run
  - decisions
  - batch30
  - m1
status: current
related_gua: []
date: 2026-06-18
---

# decisions_20260528_batch30 批跑数据摘要

## 来源信息

- **原始文件**：`docs/analysis/agent-sessions/decisions_20260528_batch30.md`
- **字符数**：3985
- **生成日期**：2026-06-18

## 概述

本文件记录了 2026-05-28 进行的 batch30 批跑中各玩家的决策模式指标。参与对象为 `yf1_m1`（0 号位，队长）和 `yf2_m1`（2 号位，队友），属于同一队伍（座位规则：0+2 / 1+3 配对）。平台为 `guandan_offline_v1006`。

## 关键实体

### 参与玩家

| 玩家标识 | 座位 | 队伍角色 | 引擎版本（推测） |
|---------|------|---------|----------------|
| `yf1_m1` | 0 号位 | 队长 | M1 |
| `yf2_m1` | 2 号位 | 队友 | M1 |

> ⚠️ **命名歧义**：`yf1_m1` 中的 `m1` 可能指代 **M1 引擎代际** 或 **agent 文件版本后缀**。需结合 wiki-minimax/entities/engine-m3.md 与 [[module-yf1-v5-client]] 的迭代脉络综合判定。

### 数据文件关联

- 输出文件：`decisions_20260528_batch30`（与源文件同名）
- 历史数据：`game_scores_m2.json`（M2 阶段遗留分数数据）

## 决策模式指标

| 指标 | 含义 | 用途 |
|------|------|------|
| PASS 率 | 决策频次中 "不出" 的比例 | 衡量保守程度 |
| 首炸@ | 第几手首次使用炸弹 | 反映早期进攻意愿 |
| 炸弹使用次数 | 单副炸弹总数 | 资源投入度 |
| 主要牌型分布 | Single / Pair / Trips / Bomb / ThreeWithTwo / ThreePair / tribute / back | 决策风格画像 |

## 关键概念引用

- [[round-vs-game]]：副/局/圈/轮的区分
- [[v1006-platform-params]]：平台 N=局数 参数含义
- [[decision-metrics]]：决策指标体系
- [[guandan-rules]]：掼蛋基本规则

## 关联页面

- wiki-minimax/entities/engine-m3.md：M 系列决策引擎主条目
- wiki/entities/module-batch-executor.md：批跑执行器
- [[m1-vs-m2-vs-m3-evolution]]：M 系列迭代脉络综合分析

## 开放问题

1. `yf1_m1` / `yf2_m1` 是 M1 引擎实例，还是 agent 文件后缀？
2. batch30 是 M1 阶段数据还是回测数据？
3. 与 `game_scores_m2.json` 的关系是版本切换还是并存？
