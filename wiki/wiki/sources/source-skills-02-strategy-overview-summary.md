---
type: source-summary
title: "对子战略+牌型概率摘要"
sources:
  - docs/knowledge/skills/01_foundation/02_strategy_overview.md
tags:
  - strategy
  - pair
  - probability
  - card-types
status: current
related_gua:
  - GUA-030
date: 2026-06-18
---

# 对子战略 + 牌型概率摘要

## 文档定位

`docs/knowledge/skills/01_foundation/02_strategy_overview.md` 提供掼蛋**开局战略总览**，由两部分组成：
1. **对子先行**战略（开局首选牌型）
2. **牌型概率分布**（出牌决策的数据基础）

## 核心战略：对子先行

- **情况不明对子先行** → M3 硬编码 / V5+ 实施
- **P1 原则「逢五出对」** → M3 可硬编码
- 详见 [[concept-pair-first-strategy]]

## 牌型概率分布

| 牌型 | 概率 |
|------|------|
| 单牌 | 49.55% |
| 对子 | 24.77% |
| 三张 | 8.22% |
| 顺子 | 4.11% |
| 连对 | 2.05% |
| 钢板 | 1.02% |
| 炸弹 | 5.13% |
| 同花顺 | 2.05% |

**平均手数**：38.3 手 / 9.8 手每人

详见 [[concept-card-type-probability]]。

## 与编码体系的关系

牌型概率的计算基于 [[concept-card-type-encoding]] 中定义的 JSON 牌型编码（13 种基础牌型 + 衍生牌型）。

## 与 GUA-030 的关系

本文是 [[gua-030]]「原则→引擎映射」的承载文档之一。P1「逢五出对」被归入 M3 硬编码范畴，但 [[source-skills-31-passing-skills-summary]] 将同类条目归入 P0（无 M3 实现）—— **存在分类分歧**，需核对 `PRINCIPLES_MAPPING.md`。
