---
type: concept
title: "局 vs 副 的口径定义"
sources:
  - docs/analysis/agent-sessions/guandan-basic-knowledge.md
  - docs/analysis/agent-sessions/decisions_20260528_batch30.md
tags:
  - terminology
  - tracking
  - critical
status: current
related_gua: []
date: 2026-06-18
---

# 局 vs 副 的口径定义

> ⚠️ **数据解读的核心口径问题，已定音但需持续强调**

## 概览

掼蛋 AI 评测中，"局" 与 "副" 的混淆是数据误读的最高频源头。本概念页明确区分四个相关术语：**局（game）**、**副（round）**、**圈（turn）**、**轮（match）**。

## 四层术语对照

| 术语 | 英文 | 含义 | 典型数量级 |
|------|------|------|-----------|
| **局** | game | 一次完整对局（从开始到决出升级/平局） | N（平台参数） |
| **副** | round | 一副牌的完整过程（从发牌到出完） | 每局包含多副 |
| **圈** | turn | 一手出牌 | 每副包含多圈 |
| **轮** | match | 通常与"局"等价，口语中可能混用 | — |

## 核心区分

### 副 ≠ 局

- **副（round）**：发牌 → 出完一张副的所有牌
- **局（game）**：从开局到决出胜负的完整过程，**包含多副**
- v1006 平台参数 **N = 局数**，**不是副数**

### 升级判定的单位是 **局**

- 升级表（双上 +3 / 头三 +2 / 头末 +1 / 不升级）以 **局** 为单位结算
- 局内所有副的完赛名次共同决定本局升级结果

### 完赛判定的单位是 **副**

- `episodeOver.order = [头游, 二游, 三游, 末游]` 描述的是 **单副** 的完赛名次
- 协议字段 `curRank` / `selfRank` / `oppoRank` 在 **副级** 变化

## 跨副变化判定局边界

- **`curRank` 跨副变化** = 局边界信号
- 一副打完，rank 重置；下一副从新 rank 开始
- 累计升级数达到胜利条件 → 局结束

## 双重追踪架构

- **副级追踪**：每副的完赛名次、决策指标、出牌序列
- **局级追踪**：累计升级数、胜率 KPI、跨副 rank 变化

> 双重架构是 wiki/entities/module-batch-executor.md 的核心数据模型。

## 易错点

1. ❌ 把 N 局跑出的数据当成 N 副 → **指标数量级错误**
2. ❌ 用副级完赛名次直接算胜率 → **错把副当局**
3. ❌ 把 "轮" 当作 "局" → **协议字段误读**
4. ❌ 混淆 PASS 率的统计单位（按圈 vs 按副 vs 按局）

## 关联概念

- [[guandan-rules]]：升级规则以局为单位
- [[v1006-platform-params]]：N=局数 的平台定义
- wiki/entities/module-batch-executor.md：双重追踪架构的实现
- wiki-minimax/entities/engine-m3.md：M3 引擎的局/副状态机

## 参见

- [[guandan-basic-knowledge-summary]]：原始知识库
- [[m1-vs-m2-vs-m3-evolution]]：M 系列如何处理双层状态
