---
type: entity-module
title: "trick_state — 场态重算 (GUA-027 修复载体)"
sources:
  - docs/guandan-brain/M3_DIAGNOSIS.md
tags:
  - module
  - m3
  - trick-state
  - gua-027
status: current
related_gua:
  - GUA-027
  - GUA-026
date: 2026-06-18
---

# trick_state — 场态重算

## 基本信息
- **位置**：`src/game_logic/trick_state.py`
- **代际**：M3（实现 GUA-027 修复）
- **状态**：GUA-027 已 closed

## 核心功能
- 用 `beatAction` 重算本圈场态
- 用 `publicInfo[].playArea` 交叉校验服务器 `greater` 字段
- 解决 M3 误用 `curAction[1]` 算 `curVal` 的 BUG6

## 关键概念
- greaterAction 语义：本圈当前最大一手 = 被动出牌要压的目标
- playArea 交叉校验：playArea 是场上真相，兜底服务器可能的 greater 错误

## 关联
- 引擎：wiki-minimax/entities/engine-m3.md
- BUG：M3 七致命 bug 列表见 [[M3_DIAGNOSIS-summary]]
