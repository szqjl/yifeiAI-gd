---
type: concept
title: "残局两手规划 (≤12 张)"
sources:
  - docs/analysis/agent-sessions/07-p0-implementation-verification.md
tags:
  - concept
  - endgame
  - Lv1-Lv2
status: current
related_gua:
  - GUA-002
date: 2026-05-28
---

# 残局两手规划 (≤12 张)

## 核心思想

手牌 ≤ 12 张时，枚举所有两手配对，**先手/控场**最优。

## 为什么是关键

- 掼蛋残局胜负常在 2-3 回合决定
- 漏掉最优两手组合 = 错失头游 / 二游
- lalala 在 22 副对局中 100% 双上，残局两手分析是基础

## 实现

- `src/decision/endgame_planner.py`（229 行）
- 触发条件：`len(hand) <= 12`
- 输出：两手组合 + 预期先手

## 验证

- 20 局触发 8 次（4/4 对称，0.8% 决策占比）
- 与 3 局基线（6/0）不一致 → 样本量方差

## 关联页面

- [[gua-002]]
- concepts/strategic-layers
