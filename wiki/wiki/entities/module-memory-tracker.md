---
type: entity-module
title: "MemoryTracker 记忆追踪器"
sources:
  - docs/guandan-brain/人类掼蛋决策流程完整分析.md
tags:
  - module
  - memory
  - stage-3
  - v7-architecture
status: current
related_gua: []
date: 2026-06-18
---

# MemoryTracker 记忆追踪器

## 模块定义

**MemoryTracker** 是新 V7 架构中**结构化记忆**的核心实现:追踪对局中所有玩家的出牌历史,并组织为**人类可理解的结构**(已炸弹、已三张、信号牌、剩余估算)。

## 核心职责

| 职责 | 说明 |
|------|------|
| 出牌记录 | 记录每轮每家出的牌 |
| 牌型分类 | 将已出牌按牌型分类(炸弹/三张/对子/单张) |
| 关键牌标记 | 标记关键牌(2、王、A)的归属 |
| 信号追踪 | 识别队友的"信号牌" |
| 剩余估算 | 推断每家可能的剩余牌型 |

## 数据结构

```python
class MemoryState:
    played_history: List[PlayedRound]  # 完整出牌历史
    bombs_played: List[Bomb]           # 已出炸弹
    triples_played: List[Triple]       # 已出三张
    pairs_played: List[Pair]           # 已出对子
    singles_played: List[Single]       # 已出单张
    
    # 关键牌追踪
    jokers_played: List[int]           # 大小王归属
    twos_played: List[Tuple[int, Suit]] # 2 的归属
