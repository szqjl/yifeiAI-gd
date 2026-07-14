---
type: entity-module
title: "HistoryTracker (P0-① 历史信息追踪)"
sources:
  - docs/analysis/agent-sessions/p0_complete_summary.md
  - docs/analysis/agent-sessions/P0_IMPLEMENTATION_COMPLETE_20260528.md
tags:
  - m1-engine
  - p0-①
  - history
  - cooperation
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# HistoryTracker (P0-①)

## 基本信息

- **文件名**：`history_tracker.py`
- **规模**：265 行 / 6991 bytes
- **所属引擎**：`M1`
- **状态**：✅ 实现 + 集成

## 职责

追踪已出牌历史，**推断剩余牌组成**。

## 核心能力

| 能力 | 说明 |
|------|------|
| 出牌记录 | 记录每回合每位玩家出的牌型 |
| 牌型统计 | 推断剩余牌中各牌型的概率分布 |
| 关键牌标记 | 标记已确认出完的牌（如王炸、级牌等） |
| 配合决策 | 为 Lv1 决策提供"对手可能有什么"的信息 |

## 验证状态

- 第一轮验证：**触发次数=0**（待诊断）
- 原因可能：配置路径、模块未真正被调用、或端口阻塞导致无真实对局

## 关联

- wiki/concepts/p0-m1-cooperation-improvements.md — P0 改进设计哲学
- [[engine-m1]] — M1 引擎
- [[module-p0-verification-auto]] — 验证脚本
