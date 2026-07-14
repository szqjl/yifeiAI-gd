---
type: concept
title: "掼蛋算牌定律 (Calculation Laws)"
sources:
  - docs/knowledge/skills/04_common_skills/04_calculation_skills.md
tags:
  - calculation
  - probability
  - ★重点
status: current
related_gua:
  - GUA-032
  - GUA-063
date: 2026-06-18
---

# 掼蛋算牌定律

> ⚠️ **PRINCIPLES_MAPPING §十四 重点内容**

## 本质

> **掼蛋本质是大概率事件的动态演绎。**

## 三大定律

### 1. 5/10 定律
- **5 出尽无小顺**：5 张牌都出过，则外面无 5 张小顺
- **10 出尽无大顺**：10 张牌都出过，则外面无大顺

### 2. 孤张定律
**始终不见级牌，外面有含级牌顺子。** 级牌（含主级）很少单出，如一直未见，多半被压在顺子里。

### 3. 能打不能收定律
**必有相克轮次。** 队友能跑但收不了，必然有被克牌的轮次。

## 算牌四层次

| 层次 | 输入 | 输出 |
|------|------|------|
| 全手牌算牌 | 起手 27 张 | 大牌、同炸、进贡、概率分布 |
| 已出牌算牌 | 历史出牌 | 大小王位置、排除同炸、孤张 |
| 余牌算牌 | 各家剩余张数 | 各家最可能牌型 |
| 相生相克算牌 | 关系矩阵 | 对手隐藏牌型 |

## 余牌算牌表

| 余牌数 | 主要可能牌型 |
|--------|--------------|
| 1-4 张 | 单/对/三张/4 头炸 |
| 5 张 | 三带二/顺子/同花顺/5 头炸 |
| 6-10 张 | 各有最大概率组合 |

## 引擎映射

- **M3**：❌ 无算牌能力
- **V5+ / V7**：⏳ 需要 probability_reasoning 模块

## 关联

- [[gua-032]] — 记牌技巧
- [[gua-063]] — 算牌定律实施（拟）
- wiki/concepts/card-interactions.md — 相生相克
- wiki/sources/skills-04-calculation-skills-summary.md

---
