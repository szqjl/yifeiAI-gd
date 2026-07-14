---
type: concept
title: "结构化记忆"
sources:
  - docs/guandan-brain/人类掼蛋决策流程完整分析.md
tags:
  - memory
  - stage-3
  - v7-architecture
status: current
related_gua: []
date: 2026-06-18
---

# 结构化记忆

## 概念定义

**结构化记忆**(Structured Memory)是人类玩家在掼蛋对局中**维护的心理模型**:对已出牌、剩余牌、信号牌的分类整理与持续追踪。

## 人类的记忆机制

### 1. 物理重排序(Hand Reordering)

人类会将手牌**按区域分组**摆放:
- 炸弹区
- 顺子区
- 三张/对子区
- 单张区

这**不是装饰**,而是**工作记忆的物理扩展**——通过空间位置减少认知负荷。

### 2. 区域索引(Area Indexing)

类似"用手指分组",人类玩家对已出牌的分类:
- **已炸弹**:记录大小、花色
- **已三张**:记录关键牌型
- **已控制牌**:记录谁打出了哪些关键牌
- **剩余估算**:推断每家可能的牌型

### 3. 信号牌追踪

人类会记住"上一轮谁打的什么",作为:
- 队友信号的来源
- 对手牌型的推断
- 升级进度的判断

## AI 实现挑战

### 挑战 1:状态表示

- **序列表示**:LSTM/Transformer
- **图表示**:已出牌 = 节点,关联 = 边
- **符号表示**:规则可读的牌型列表

### 挑战 2:记忆容量

- 完整对局:80+ 轮 × 4 家 = 320+ 次出牌
- 需选择性记忆(关键牌/信号牌)

### 挑战 3:记忆刷新

- 队友换人/重开局:记忆清空
- 长程目标(升级):记忆需跨局保留

## 对应模块

- MemoryTracker — 记忆追踪器
- HandCardOrganizer — 手牌整理器
- DynamicAdjustment — 动态调整(依赖记忆)

## 关联页面

- wiki/concepts/human-like-decision-flow.md — 类人决策的阶段 3-4
- wiki/concepts/power-contention.md — 牌权争夺(依赖记忆推断)
