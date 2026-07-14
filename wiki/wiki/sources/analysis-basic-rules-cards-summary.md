---
type: source-summary
title: "掼蛋 AI 对基本规则（牌张）的体现摘要"
sources:
  - docs/analysis/掼蛋AI对基本规则_牌张_的体现.md
tags:
  - rules
  - foundational
  - analysis
status: current
related_gua: []
date: 2026-06-18
---

# 掼蛋 AI 对基本规则（牌张）的体现摘要

## 核心定义

- **108 张**：一副完整掼蛋牌
- **27 张**：单个玩家持牌数（108 ÷ 4）
- **副**：108 张的集合单位
- **手**：一名玩家出的一组牌型
- **圈**：四名玩家各出一次手（4 手构成一圈）

## AI 决策层映射

| 概念 | M3 规则引擎 | V7 NN 引擎 |
|------|-------------|------------|
| 27 张 | `Hand.cards` 状态空间 | GroupingEngine 输入 |
| 手 | `play_hand()` | 6 策略枚举输出 |
| 圈 | 一级决策节奏 | memory_tracker 步长 |

## 口径定音

- **局 ≠ 副**：文档/日志中"局"统一指一局完整比赛
- "圈"在实现中应避免被误称为"轮"

## 关联实体

- wiki/concepts/basic-rules-cards.md — 详细概念页
- wiki-minimax/entities/engine-m3.md / wiki/entities/engine-v7.md
