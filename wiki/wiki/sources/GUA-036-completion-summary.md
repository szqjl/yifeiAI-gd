---
type: source-summary
title: "GUA-036 完成定义摘要 · 控权压顺 + 接风配合（M3 guard）"
sources:
  - docs/guandan-brain/issues/GUA-036-completion.md
tags:
  - gua
  - m3
  - endgame
  - control
  - team-coordination
  - wind
status: current
related_gua:
  - GUA-036
  - GUA-031
  - GUA-032
  - GUA-034
  - GUA-035
date: 2026-06-17
---

# GUA-036 完成定义摘要

## 概述

GUA-036 是 M3 末段博弈的**同级扩展**（与 [[GUA-035]] 并列），由 **batch7 round38 复盘**驱动。包含 4 个子规则：

## 子规则详解

### CTRL-P01：被动压敌顺

- **触发**：`_Straight` `greaterPos` 属于对手
- **动作**：用最小够用的牌压住对手的顺子
- **关键约束**：**不前置要求** `combine_handcards['Straight']` 与 `action[-1]` 严格对齐
- **影响**：延伸了 [[GUA-031]] 的边界——被动压敌顺不受结构对齐约束

### CTRL-P02：被动夺权优先于 STG-D01

- **触发**：被动局面遇到 [[GUA-032]] CALC-M03 的 5/10 降权
- **动作**：**降权不阻止被动夺权**
- **原则**：夺权优先于 STG-D01（结构保护）
- **影响**：[[GUA-032]] 的 CALC-M03 需要标注此例外

### WIND-P01：接风禁拆

- **触发**：本方接风 + 队友仍在场
- **动作**：**禁止**拆 `trips` / 钢板 / 炸弹的成员单张去接风
- **目的**：保结构、保队友

### TEAM-P01：接风让道

- **触发**：本方接风 + 队友是**末手**且手牌为 `Pair` / `Bomb`
- **动作**：**优先不出**拆结构的对子
- **目的**：让队友收官

## 冲突解决

| 冲突点 | 优先级 |
|--------|--------|
| STG-D01（结构保护） vs CTRL-P01（夺权） | **夺权优先** |
| WIND-P01（禁拆） vs 评分最高 | **禁拆优先** |
| TEAM-P01（让道） vs 评分最高 | **让道优先**（仅限末手队友） |

## 依赖关系

- **依赖 GUAs**：`GUA-026`、`GUA-029`、`GUA-031`、`GUA-032`、`GUA-034`、`GUA-035`
- **关联回放**：`batch7 round38`

## 关单口径

> **pytest 构造态 + 回归通过即可关单**；不绑定具体 game_id

## 关联页面

- [[gua-036]] - GUA-036 实体页
- [[gua-031]] - 队友让道边界（被延伸）
- [[gua-032]] - CALC-M03（被标注例外）
- [[gua-035]] - 同级扩展
- [[control-press-straight]] - 控权压顺概念
- [[wind-banned-dismantle]] - 接风禁拆概念
- [[m3-endgame-guard]] - M3 末段博弈综合
