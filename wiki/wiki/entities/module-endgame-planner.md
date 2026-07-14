---
type: entity-module
title: "EndgamePlanner (P0-② 残局两手规划)"
sources:
  - docs/analysis/agent-sessions/p0_complete_summary.md
  - docs/analysis/agent-sessions/P0_IMPLEMENTATION_COMPLETE_20260528.md
tags:
  - m1-engine
  - p0-②
  - endgame
  - planning
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# EndgamePlanner (P0-②)

## 基本信息

- **文件名**：`endgame_planner.py`
- **规模**：229 行 / 7413 bytes
- **所属引擎**：`M1`
- **状态**：✅ 实现 + 集成

## 职责

当自己剩余手数 ≤ 2 时，**提前规划出完顺序**，避免残局翻车。

## 核心能力

| 能力 | 说明 |
|------|------|
| 两手出完检测 | 判断当前是否处于"两手可清"状态 |
| 顺序规划 | 决定先出哪手、后出哪手 |
| 风险评估 | 评估被压/被炸的概率 |
| 接牌适配 | 考虑队友接牌的最佳出法 |

## 集成点

- `EndgameLateActiveHandler`

## 设计背景

**M3 教训**：M3 在 22 副对局中全负，部分原因正是缺此能力——残局时"出大牌后被压死"或"留小牌走不掉"。

## 验证状态

- 第一轮验证：**触发次数=0**（待诊断）
- 与 P0-① 同样的阻塞问题

## 调优参数

- `endgame_threshold`：12 → **10**（激进调优，更早进入残局模式）

## 关联

- wiki/concepts/p0-m1-cooperation-improvements.md — P0 改进设计哲学
- [[engine-m1]] — M1 引擎
- [[module-p0-verification-auto]] — 验证脚本
