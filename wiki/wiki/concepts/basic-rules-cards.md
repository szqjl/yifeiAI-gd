---
type: concept
title: "掼蛋基本规则：牌张（108/27/副/手/圈）"
sources:
  - docs/analysis/掼蛋AI对基本规则_牌张_的体现.md
tags:
  - rules
  - cards
  - foundational
status: current
related_gua: []
date: 2026-06-18
---

# 掼蛋基本规则：牌张（108/27/副/手/圈）

## 概述

本文档沉淀掼蛋游戏最基础的概念口径：牌张总数、单人牌数、「副」、「手」、「圈」的精确定义。这些是所有上层策略、组牌引擎、出牌逻辑的语义基石。

## 关键定义

| 概念 | 定义 | AI 实现含义 |
|------|------|-------------|
| **108 张** | 一副完整掼蛋牌的总张数（2 副扑克去 3 鬼去大小王） | `guandan_constants.py` 中常量基数 |
| **27 张** | 单个玩家持牌数（108 ÷ 4） | 状态空间大小、特征维度依据 |
| **一副** | 108 张的集合单位（出牌上下文） | M3 `play_one_round` 输入 |
| **一手** | 一名玩家出的一组牌型（单张/对子/三带/炸弹/顺子等） | M3 `play_hand`、V7 GroupingEngine 拆分单位 |
| **一圈** | 四名玩家各出一次手（4 手构成一圈） | 一级决策节奏 |

## 与 AI 决策的对接

- **M3 规则引擎**：以「手」为最小决策单元，`play_hand()` 处理单手牌型判定
- **V7 GroupingEngine**：以「手」为拆分单位，将 27 张拆分为多组手牌方案
- **评测体系**：每局（不是每副！）含若干圈，每圈 4 手

## 边界与争议

- 「局 ≠ 副」口径已定音：文档/日志中"局"统一指一局完整比赛（包含升级、过牌、再打）
- "圈"在不同实现里有时被误称为"轮"，需在 wiki/entities/module-batch-executor.md 与 [[concept-batch-evaluation]] 中保持术语一致

## 关联实体

- wiki-minimax/entities/engine-m3.md — 规则引擎实现消费这些常量
- wiki/entities/engine-v7.md — NN 引擎特征层消费牌张/手牌结构
- module-guandan-constants（若存在）— 常量定义模块
