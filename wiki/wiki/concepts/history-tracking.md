---
type: concept
title: "历史信息追踪 (history + remain_cards)"
sources:
  - docs/analysis/agent-sessions/07-p0-implementation-verification.md
  - docs/analysis/agent-sessions/04-guandan-mechanics.md
tags:
  - concept
  - Lv2
  - p0
status: current
related_gua:
  - GUA-001
date: 2026-05-28
---

# 历史信息追踪

## 核心思想

维护 **完整出牌历史 + 剩余牌集合**，推断对手手牌结构与可能牌型。

## lalala vs M1 关键差异

- lalala：实时追踪出牌，记忆 remain_cards
- M1/M3：决策时不读历史 → 看不到对手已经少哪些牌

## 实现

- `src/decision/history_tracker.py`（265 行）
- 维护：
  - `played_cards`: 所有已出牌
  - `remaining_cards`: 推算的剩余牌
  - `opponent_estimate`: 对手可能的手牌结构

## 验证

- 20 局 0 触发 → 需排查是否真正接入 stage_router

## 关联页面

- [[gua-001]]
- concepts/strategic-layers
