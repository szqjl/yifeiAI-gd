---
type: source-summary
title: "V7 Guard 壳与策略增补摘要"
sources:
  - docs/guandan-brain/iterations/v7-strategy-gua045-053.md
tags:
  - v7
  - strategy
  - guards
  - reward
  - memory
status: current
related_gua:
  - GUA-045
  - GUA-051
  - GUA-052
  - GUA-053
date: 2026-06-17
---

# V7 Guard 壳与策略增补摘要

## 范围

GUA-045 ~ GUA-053，覆盖 V7 引擎的**策略层**与**可解释性增强**：Guard 壳、稠密 Reward、全量记牌、辅助决策信号。

## 关键 GUA

### GUA-045 — P0 Guard 壳 V7-R01~R06
- **实现**：`v7_guards.py`（[[module-v7-guards]]）
- **六道防线**：
  - R01 牌型合法性
  - R02 接风规则
  - R03 炸弹时序
  - R04 队友保护
  - R05 升级阈值
  - R06 终局保护
- **状态**：CLOSED（已合入 V7 主线）
- **详细**：见 [[gua-045]] 实体页

### GUA-051 — 稠密 Reward 9 种
- **实现**：`reward.py`
- **设计**：每步给出稠密反馈（出牌节省、控牌、压制、配合等 9 个维度）
- **状态**：CLOSED

### GUA-052 — 全量记牌 MemoryTracker
- **实现**：`memory_tracker.py`（[[module-v7-features]] 关联）
- **维度**：24 维（每种花色点数剩余）
- **状态**：CLOSED

### GUA-053 — 辅助决策信号
- 配合 GUA-045 Guard 壳的次级信号层

## 关键 KPI

- **V7 队胜 366/366 (100%)**：Guard 壳保护下 NN 几乎不决策失误
- **V7 副胜 0/236**：Guard 壳保护的是「不出错」，不是「赢」，体现纯 NN 决策能力仍为 0

## 重要教训

- **Guard 壳 ≠ 智能**：100% 队胜但 0% 副胜证明 Guard 只能保证不犯蠢，不能赢得比赛
- **Reward 稠密 ≠ RL 起效**：见 synthesis-v7-bc-failure-map 进一步分析

## 关联

- [[gua-045]]
- [[module-v7-guards]]
- wiki/entities/engine-v7.md
- wiki/synthesis/synthesis-v7-current-state.md
