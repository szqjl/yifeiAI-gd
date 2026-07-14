---
type: concept
title: "副级决策分析"
sources:
  - docs/analysis/agent-sessions/M1 vs lalala 逐副深度分析脚本.md
tags:
  - concept
  - analysis
  - round-level
  - decision-quality
status: current
date: 2026-06-18
---

# 副级决策分析（Round-Level Decision Analysis）

## 概念定义

**副级决策分析**是一种以"单副（round）"为最小分析粒度的方法论，通过拆解每副牌局中的玩家决策序列（action、is_pass 等），将**决策质量**与**最终胜负**建立关联，从而在批跑 KPI 之外提供下钻诊断能力。

## 核心方法

### 1. 配对（Pairing）
按 `(game_id, round_num)` 配对己方两名玩家（如 `yf1_m1` + `yf2_m1`）的副级记录，分析"双 M1 协同表现"。

### 2. 决策序列提取
从 `my_decisions` 字段抽取：
- `action`：具体出牌动作
- `is_pass`：是否过牌
- 决策详情（具体字段待补全）

### 3. 胜负归因
基于 `episodeOver/order` 判定单副胜负，与决策序列对齐，定位**关键决策点**（winning/losing move）。

### 4. 统计指标
- **pass_rate**：决策中 Pass 占比
- **problem_passes**：问题 Pass 次数（判定逻辑待补全）
- **m1_victories / lalala_victories**：单副胜场数

## 适用场景

| 场景 | 价值 |
|------|------|
| 批跑 KPI 异常下钻 | 当整体胜率下降时，按副级定位异常副 |
| 引擎 A/B 对比 | 在 (game_id, round_num) 维度对比 M1 vs lalala |
| 决策质量审计 | 统计 problem_passes、关键牌型失误 |
| 协同表现分析 | 双 M1 配对的协作模式 |

## 与局级分析的区别

- **局级分析**：以一整局（上下两副+双副升级）胜负为单位
- **副级分析**：以单副（round）为单位，颗粒度更细

> ⚠️ 注意 **局 ≠ 副** 的核心口径（参见 [[concept-batch-evaluation]]）。

## 推广到 V7 引擎

该方法论不依赖具体引擎，可直接套用到 V7 NN 引擎的副级决策分析，是评测 V7 当前状态 的重要下钻工具。

## 关联页面

- [[module-m1-vs-lalala-rounds-analyzer]]：方法论的脚本实现
- [[engine-m1]]：M1 引擎（首个应用对象）
- entity-opponent-lalala：lalala 对手
- [[concept-batch-evaluation]]：批跑评测体系（上游数据源）
- wiki/synthesis/synthesis-v7-current-state.md：V7 当前状态（潜在应用场景）
