---
type: concept
title: "接风禁拆（WIND-P01）"
sources:
  - docs/guandan-brain/issues/GUA-036-completion.md
tags:
  - concept
  - m3
  - wind
  - team-coordination
  - endgame
status: current
related_gua:
  - GUA-036
  - GUA-031
date: 2026-06-17
---

# 接风禁拆（WIND-P01）

## 定义

本方**接风**时，队友**仍在场**的前提下，禁止拆解特定牌型结构去接风，定义于 [[GUA-036]]。

## 禁拆牌型

- `trips`（三张）
- 钢板（连续三张×2）
- 炸弹成员单张

## 触发条件（同时满足）

1. 本方处于接风位（`_active` = 接风）
2. 队友手牌数 > 0（仍在场）
3. 候选动作需要拆解上述结构

## 动作

**跳过**该候选动作，选择其他非拆解动作；若全部候选都涉及拆解，则**保留**评分最高者（fallback）。

## 配套规则

- TEAM-P01（接风让道）：进一步约束——队友是**末手**且手牌为 `Pair`/`Bomb` 时，让道优先

## 适用前提

- 模式：`solo_sprint`（[[solo-sprint]]）
- 引擎：wiki-minimax/entities/engine-m3.md

## 关联

- [[gua-036]] - GUA-036 实体
- [[gua-031]] - 队友让道
- [[m3-endgame-guard]] - 末段博弈综合
