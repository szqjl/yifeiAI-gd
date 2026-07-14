---
type: concept
title: "多方案组牌"
sources:
  - docs/guandan-brain/人类掼蛋决策流程完整分析.md
tags:
  - grouping
  - stage-0
  - v7-architecture
status: current
related_gua: []
date: 2026-06-18
---

# 多方案组牌

## 概念定义

**多方案组牌**(Multi-Plan Card Grouping)是类人决策的**阶段 0**:对一手牌,枚举**所有合法组牌方案**,为后续决策提供候选空间。

## 为什么需要"多方案"?

### 1. 组牌是非平凡问题

掼蛋一手 27 张牌,合法组牌方案数:
- 简单情况:5-10 种
- 复杂情况:**20-50 种**
- 极端情况(炸弹多):100+ 种

### 2. 单一最优组牌 ≠ 决策最优

- 短期最优组牌可能锁死后续出牌
- 需保留**多种备选方案**应对局势变化
- 这就是"组牌缓存"的必要性

## 方案表示

每种组牌方案包含:

```yaml
plan:
  bomb: [♠A♠A, ♥K♥K]      # 炸弹
  straight_flush: [...]     # 同花顺
  sequences: [...]          # 顺子
  triples: [...]            # 三张
  pairs: [...]              # 对子
  singles: [...]            # 单张
  remaining: 0              # 剩余张数
  score: 0.85               # 方案评分
```

## 实现模块

- GroupingEngine — 组牌引擎核心
- GroupingPlanCache — 方案缓存
- HandCardOrganizer — 手牌物理重排序(人类记忆机制)

## 与传统组牌的区别

| 维度 | 传统组牌 | 多方案组牌 |
|------|----------|------------|
| 输出 | 单一方案 | 多种方案 |
| 评价 | 最优分数 | 多种分数 + 风险评估 |
| 缓存 | 无 | 复用历史方案 |
| 决策耦合 | 紧耦合 | 解耦(先枚举,后选择) |

## 关联页面

- wiki/concepts/human-like-decision-flow.md — 类人决策的阶段 0
- wiki/entities/module-grouping-engine.md — 组牌引擎模块
- wiki/concepts/structured-memory.md — 结构化记忆
