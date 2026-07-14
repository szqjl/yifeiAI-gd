---
type: concept
title: "控权压顺（CTRL-P01/P02）"
sources:
  - docs/guandan-brain/issues/GUA-036-completion.md
tags:
  - concept
  - m3
  - control
  - endgame
status: current
related_gua:
  - GUA-036
  - GUA-031
  - GUA-032
date: 2026-06-17
---

# 控权压顺（CTRL-P01/P02）

## 定义

末段博弈中**被动局面下用最小代价夺回牌权**的策略，定义于 [[GUA-036]]。

## 两条子规则

### CTRL-P01：被动压敌顺

- **触发**：`combine_handcards` 中识别到 `_Straight`，且其 `greaterPos` 属于**对手**
- **动作**：选择**最小够用**的压制牌型
- **关键约束**：**不前置要求** `_Straight` 与 `action[-1]` 严格对齐

这意味着 [[GUA-031]] 的结构对齐边界被延伸——被动压敌顺**不受结构对齐约束**。

### CTRL-P02：降权不阻止夺权

- **触发**：被动局面下 [[GUA-032]] CALC-M03 计算出 5/10 降权
- **动作**：**忽略降权**，完成夺权
- **优先级**：**夺权 > STG-D01（结构保护）**

## 冲突解决

| 冲突 | 优先级 |
|------|--------|
| STG-D01（结构保护） vs CTRL-P01 | **CTRL-P01 优先** |
| CALC-M03 5/10 降权 vs CTRL-P02 | **CTRL-P02 优先** |

## 适用前提

- 模式：`solo_sprint`（[[solo-sprint]]）
- 阶段：末段博弈
- 引擎：wiki-minimax/entities/engine-m3.md

## 关联

- [[gua-036]] - GUA-036 实体
- [[gua-031]] - 队友让道边界
- [[gua-032]] - CALC-M03
- [[m3-endgame-guard]] - 末段博弈综合
