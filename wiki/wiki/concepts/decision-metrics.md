---
type: concept
title: "决策模式指标体系"
sources:
  - docs/analysis/agent-sessions/decisions_20260528_batch30.md
tags:
  - metrics
  - decision
  - evaluation
status: current
related_gua: []
date: 2026-06-18
---

# 决策模式指标体系

## 概述

本概念页沉淀掼蛋 AI 决策模式的量化指标体系，是 wiki-minimax/concepts/batch-evaluation.md 的重要组成。

## 核心指标

### 决策频次类

| 指标 | 含义 | 单位 |
|------|------|------|
| **PASS 率** | 决策频次中 "不出" 的比例 | % |

> PASS 率反映保守程度。PASS 率高 = 倾向让队友出头游 / 避免抢风。

### 进攻意愿类

| 指标 | 含义 | 用途 |
|------|------|------|
| **首炸@** | 第几手首次使用炸弹 | 早期进攻信号 |
| **炸弹使用次数** | 单副炸弹总数 | 资源投入度 |

> 首炸@数值越小 = 越早投入炸弹 = 进攻意愿越强。

### 牌型分布类

| 牌型 | 协议字段 | 决策含义 |
|------|---------|---------|
| Single | 单张 | 散牌处理能力 |
| Pair | 对子 | 中小牌组合 |
| Trips | 三张 | 中大牌 |
| **Bomb** | 炸弹 | 关键进攻/防守 |
| **ThreeWithTwo** | 三带二 | 主要得分牌型 |
| **ThreePair** | 三连对 | 牌型优化 |
| **tribute** | 贡牌 | 进贡/还贡策略 |
| **back** | 抗贡/回手 | 防守策略 |

## 应用场景

- **离线批跑画像**：每个 agent 出一份指标分布（见 [[decisions_20260528_batch30-summary]]）
- **版本对比**：M1 vs M2 vs M3 的决策风格迁移
- **异常检测**：PASS 率异常 / 牌型分布突变

## 统计单位注意

- PASS 率：可按 **圈** / **副** / **局** 三种粒度统计
- 首炸@：按 **副** 粒度（每副首个炸弹手数）
- 牌型分布：通常按 **圈** 统计出牌类型

> 详见 [[round-vs-game]] 的口径定义。

## 关联概念

- wiki-minimax/concepts/batch-evaluation.md：批跑评测体系
- wiki-minimax/entities/engine-m3.md：M3 引擎的指标埋点
- wiki/entities/module-batch-executor.md：批跑执行器的指标聚合

## 参见

- [[guandan-rules]]：牌型规则背景
- [[m1-vs-m2-vs-m3-evolution]]：指标随引擎代的迁移
