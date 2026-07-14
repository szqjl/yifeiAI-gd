---
type: synthesis
title: "掼蛋对手牌型判断方法论"
sources:
  - docs/knowledge/skills/04_common_skills/02_card_language.md
  - docs/knowledge/skills/04_common_skills/03_card_interactions.md
  - docs/knowledge/skills/04_common_skills/04_calculation_skills.md
tags:
  - synthesis
  - judgment
  - methodology
status: current
related_gua:
  - GUA-032
  - GUA-063
  - GUA-064
  - GUA-065
date: 2026-06-18
---

# 掼蛋对手牌型判断方法论

## 三位一体方法

```
   ┌──────────────┐
   │   算 牌       │ ← 数据层
   │ （概率推理）   │
   └──────┬───────┘
          │
   ┌──────┴───────┐
   │   相生相克    │ ← 关系层
   │ （牌型约束）  │
   └──────┬───────┘
          │
   ┌──────┴───────┐
   │   牌  语      │ ← 信号层
   │ （意图识别）  │
   └──────────────┘
```

## 各层职责

### 算牌层
- 全手牌概率分布
- 已出牌排除
- 余牌推断
- 三定律（5/10、孤张、能打不能收）

### 相生相克层
- 牌型关系矩阵
- 喂牌方向
- 隐藏牌型反推

### 牌语层
- 首出信号
- 组合信号
- 队友/对手意图识别

## 推断链示例

**观察**：对手出 `33399`

**推断 1（牌语）**：家里可能有 4-8 顺子

**推断 2（算牌）**：4-8 顺子需要 5 张连续牌，余牌结构为"三带二 + 顺子"

**推断 3（相生相克）**：若我方打顺子，对手可能用三带二反击；应避免送小单

## 引擎实施

- **M3**：完全缺乏此判断体系
- **V5+ / V7**：需要三模块协同（probability + relationship + observation）

## 关联

- wiki/concepts/calculation-laws.md
- wiki/concepts/card-interactions.md
- wiki/concepts/card-language.md

---
