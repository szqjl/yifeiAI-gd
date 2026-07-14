---
type: source-summary
title: "相生相克技巧摘要"
sources:
  - docs/knowledge/skills/04_common_skills/03_card_interactions.md
tags:
  - skills
  - card-interactions
  - knowledge-graph
status: current
related_gua:
  - GUA-065
date: 2026-06-18
---

# 相生相克技巧摘要

> 来源：docs/knowledge/skills/04_common_skills/03_card_interactions.md

## 核心原则

**万事万物相生相克，牌型之间也有制约关系。**

## 牌型关系矩阵

| 关系对 | 性质 |
|--------|------|
| 顺子 ↔ 三带二 | 相克 |
| 三张 ↔ 对子 | 相克 |
| 三带二 → 对子 | 一般情况下相克 |
| 顺子 ↔ 对子 | 既相生又相克 |

## 经典口诀

> **能打不能收，必有相克轮次**

## 喂牌策略

### 队友打三带二时
- ✅ 送三张 > 单张 > 对子
- ❌ 忌发顺子

### 队友打顺子时
- ✅ 送单张 > 对子
- ❌ 忌三带二

### 对手打顺子时
- ✅ 出三带二 > 对子
- ❌ 忌小单

## 引擎关联

- **M3**：缺乏牌型关系知识图谱
- **V5+ / V7**：需要 card_relationship_graph 模块
- 关联 `PRINCIPLES_MAPPING.md §十三`
- 关联 `IX-P04 / P05` 喂牌方向原则

## 关联页面

- wiki/concepts/card-interactions.md — 完整相生相克概念
- [[gua-065]] — 相生相克牌型关系图（拟）
- [[gua-031]] — 传牌技巧

---
