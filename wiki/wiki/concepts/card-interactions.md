---
type: concept
title: "掼蛋相生相克 (Card Interactions)"
sources:
  - docs/knowledge/skills/04_common_skills/03_card_interactions.md
tags:
  - card-interactions
  - knowledge-graph
  - feeding
status: current
related_gua:
  - GUA-065
  - GUA-031
date: 2026-06-18
---

# 掼蛋相生相克 (Card Interactions)

## 核心原则

> **万事万物相生相克，牌型之间也有制约关系。**
>
> **能打不能收，必有相克轮次。**

## 牌型关系图

```
顺子 ←→ 三带二   (相克)
  ↑       ↓
对子 ←→ 三张      (相克)
  ↕
三带二 → 对子     (相克)
```

| 关系对 | 性质 |
|--------|------|
| 顺子 ↔ 三带二 | 相克 |
| 三张 ↔ 对子 | 相克 |
| 三带二 → 对子 | 相克 |
| 顺子 ↔ 对子 | 既相生又相克 |

## 喂牌矩阵

### 队友视角

| 队友打 | 送 | 忌 |
|--------|----|----|
| 三带二 | 三张 > 单张 > 对子 | 顺子 |
| 顺子 | 单张 > 对子 | 三带二 |

### 对手视角

| 对手打 | 我出 |
|--------|------|
| 顺子 | 三带二 > 对子（忌小单） |

## 引擎映射

- **M3**：无牌型关系图
- **V5+ / V7**：需要 `card_relationship_graph` 模块
- 关联原则 IX-P04 / P05

## 关联

- [[gua-065]] — 牌型关系图（拟）
- [[gua-031]] — 传牌技巧
- wiki/concepts/card-language.md — 牌语读牌
- wiki/sources/skills-04-card-interactions-summary.md

---
