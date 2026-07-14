---
type: concept
title: "组牌核心原则"
sources:
  - docs/knowledge/skills/07_opening/04_card_grouping_skills.md
tags:
  - concept
  - card-grouping
  - principles
  - P-G01
status: current
related_gua:
  - GUA-030
  - GUA-031
date: 2026-06-18
---

# 组牌核心原则

掼蛋组牌的**三大总纲**与**顺序优先级**，对应 PRINCIPLES_MAPPING.md §二十二（★）的 P-G01 组牌总纲。

## 三大总目标

### 1. 去单化
- **定义**：消除单张牌，使手牌尽量由 2 张以上的牌型组成
- **手段**：
  - 顺子吸收单张
  - 夯/三带二吸收对子
  - 配牌（逢人配）补缺
- **贯穿始终**：从首攻到终局均适用

### 2. 最小轮次
- **定义**：用最少的出牌轮次打完所有手牌
- **衡量**：牌力分中的"手数"维度（V7 权重 0.3）
- **口诀**："组顺生两单，肯定没眼光"（顺子不应制造单张）

### 3. 牌型变化余地（活牌）
- **定义**：保持手牌对对手牌型的多向应变能力
- **手段**：
  - 优先组三带二而非三连对（保变化）
  - 保留 A 为下放手段
  - 配火保留主灵活度
- **口诀**："孤张定律"（不打孤张）

## 组牌顺序优先级

```
1. 同花顺 (SF_FIRST)        ← 最强吸收
2. 炸弹 (BOMB_FIRST)        ← 拆炸/配炸决策
3. 整牌组合：
   - 钢板 (TwoTrips)
   - 三带二 (ThreeWithTwo)
   - 三连对 (ThreePair)
   - 顺子 (Straight)
   - 连对 (Pair)
4. 配牌 (Wild Card)         ← 逢人配补缺
5. 单张 (Single)            ← 兜底
```

## 变化余地原则（细节）

- **能组三带二不组三连对**：三连对死板，三带二可拆出三张作单
- **A 下放原则**：A 必下放（避免 A 死压）
- **孤张定律**：孤张不打（保灵活）

## 与引擎映射

| 引擎 | 实现 | 引用 |
|------|------|------|
| M3 | `combine_handcards` + CG-G01/B03/B05 | 单路径，可选 P2 |
| V5+ | `enumerate_groupings` + CG-R01–R07 | 枚举所有可能 |
| V7 | `enumerate_groupings` + 5 维 _score_power | 见 [[concept-power-scoring]] |

## 关联

- 上游：[[concept-guandan-principles-pillars]]
- 下游：[[concept-power-scoring]]、[[concept-singles-reduction]]
- 实施：[[gua-030]]、[[gua-031]]、[[engine-v7-grouping]]
