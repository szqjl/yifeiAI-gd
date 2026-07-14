---
type: concept
title: "批跑评测体系"
sources:
  - docs/guandan-brain/v7-win-rate-history.md
  - docs/guandan-brain/工作流.md
  - docs/guandan-brain/掼蛋AI技术路径重校-V系列方法论反思.md
tags:
  - evaluation
  - batch
  - kpi
  - workflow
status: current
related_gua:
  - GUA-033
  - GUA-039b
  - GUA-097
date: 2026-07-01
---

# 批跑评测体系

## 核心定义

批跑（Batch Evaluation）是 V7 项目**策略改动的唯一真源验证手段**：所有改动必须经过离线批跑、统计胜率 KPI、与硬门槛对照后才算闭环。

## KPI 层级

### 1. 队胜率（Team Win Rate）
- **定义**：完整升级的局数 / 总批跑局数
- **硬门槛**：≥30%（[[gua-039b]]）
- **当前 V7 状态**：1/138 = 0.7%
- **采集来源**：`completed_games`

### 2. 副胜率（Round Win Rate）
- **定义**：单副胜出的副数 / 总副数
- **峰值**：25.5%（[[gua-065]]）
- **谷值**：2.4%（[[gua-071]]）
- **采集来源**：`game_records`（每 JSON = 1 副）

### 3. 升级数（Upgrade Count）
- **定义**：`victoryNum[0] + victoryNum[1]` = 本局升级数（**非胜局数**）
- **坑点**：见 [[局不等于副]]

## 局 ≠ 副 口径（核心）

> 一局（game）= 8 条 record（4 玩家 × 2 副）

- `game_records` 中每条 JSON = 1 副
- `completed_games` = 局
- `victoryNum[0] + [1]` = 本局总升级数（不是胜局数）
- 解析时务必区分"局"与"副"

详见 [[局不等于副]]。

## 数据校验层级 L1-L4

| 层级 | 来源 | 校验内容 |
|------|------|----------|
| L1 | `latest_victory_num.json` | 当局升级进度 |
| L2 | `logs/` | 决策日志 |
| L3 | `v7_vs_lalala_scores.json` | 累计比分 |
| L4 | `game_records_v7/` | 原始 record（每条=1副） |

**P1 校验**：`[0] + [1] == batch_games` **且** `[0] == [2]` `[1] == [3]`

## 批跑执行流程

见 [[工作流-summary]] WF-04：
1. 检查 baseline 校准（[[gua-097]]）
2. 配置客户端（v7-dev / m-dev）
3. 执行 N 局（默认 100）
4. 收集 L1-L4 四层数据
5. 计算队胜率与副胜率
6. 与硬门槛对照

## Recurrence 排查流程

当队胜率异常波动时：
1. 检查 L1 校验（升级进度异常）
2. 检查 L2 决策链路（WF-12 R-Dxx 标签）
3. 检查 L3 累计比分（历史对比）
4. 检查 L4 原始 record（牌型完整性）
5. 与 [[gua-039b]] ≥30% 硬门槛对照

## 阈值表

| 指标 | 优秀 | 及格 | 不及格 |
|------|------|------|--------|
| 队胜率 | ≥30% | ≥15% | <15% |
| 副胜率 | ≥30% | ≥20% | <20% |
| 与 Lalala 队胜率差 | ≥0 | -10%~0 | <-10% |

## 跨引用

- [[局不等于副]] — 数据口径
- [[synthesis-v7-current-state]] — 当前状态
- synthesis-v-series-failure — 失败方法论
- [[gua-039b]] — 队胜率硬门槛
```

---
