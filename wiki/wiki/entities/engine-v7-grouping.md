---
type: entity-engine
title: "V7 组牌引擎"
sources:
  - docs/knowledge/skills/07_opening/04_card_grouping_skills.md
tags:
  - entity-engine
  - v7
  - card-grouping
  - nn
status: current
related_gua:
  - GUA-030
  - GUA-032
date: 2026-06-18
---

# V7 组牌引擎

V7 引擎的**组牌子系统**，实现开局的牌型组合与牌力评分。

## 核心组件

| 组件 | 路径 | 功能 |
|------|------|------|
| 主模块 | `src/v/nn/features/grouping_engine.py` | 组牌主逻辑 |
| 评分函数 | `_score_power()` | 5 维牌力评分 |
| 枚举函数 | `enumerate_groupings()` | 枚举所有可能组法 |

详见 wiki/entities/module-grouping-engine.md。

## 处理流程

```
输入：手牌 + main_rank + 局况
    ↓
1. SF_FIRST：识别同花顺苗子
    ↓
2. BOMB_FIRST：识别炸弹（4/5/6 头）
    ↓
3. enumerate_groupings()：枚举所有组法
    ↓
4. _score_power()：5 维评分
    ↓
5. 选择 power_score 最高的组法
    ↓
输出：最优组法 + 牌力分
```

## 5 维评分权重

| 维度 | 权重 |
|------|------|
| 炸弹 | 0.3 |
| 手数 | 0.3 |
| 回收 | 0.1 |
| 灵活 | 0.1 |
| 去单化 | 0.2 |

详见 [[concept-power-scoring]]。

## 与代际引擎对比

| 代际 | 组牌路径 | 牌力分 |
|------|---------|--------|
| M3 | `combine_handcards` 单路径 + CG-G01/B03/B05 可选 P2 | 无量化 |
| V5+ | `enumerate_groupings` + 牌力分 | CG-R01–R07 |
| V7 | `enumerate_groupings` + 5 维 _score_power | CG-R01–R08 |

## 多策略并行

V7 引擎并行评估三种策略：
- **NO_STRAIGHTS**：无顺子策略
- **BALANCED**：平衡策略
- **ROUND_OPTIMAL**：轮次最优策略

最终选择 power_score 最高的策略。

## 已知限制

- **首发 +1 分未实现**：口诀建议但未纳入 V7
- **配 5 头炸策略冲突**：未显式惩罚
- **孤张定律/A 下放**：未量化

## 关联

- 上游：[[concept-card-grouping-principles]]、[[concept-power-scoring]]
- 模块：wiki/entities/module-grouping-engine.md
- 引擎映射：[[gua-030]]、[[concept-engine-mapping-principles]]
- V7 总览：wiki/entities/engine-v7.md
