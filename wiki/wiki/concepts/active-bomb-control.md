---
type: concept
title: "主动炸弹控场"
sources:
  - docs/analysis/agent-sessions/07-p0-implementation-verification.md
tags:
  - concept
  - bomb
  - Lv2
status: current
related_gua:
  - GUA-004
date: 2026-05-28
---

# 主动炸弹控场

## 核心思想

炸弹 = **控场牌**，不是 **防守牌**。在关键回合主动炸开，抢回牌权。

## lalala vs M1 关键差异

- lalala：每局炸弹数中高，主动用
- M3/M1：pass_num ≥ 5 才考虑 → 几乎主动不用

## 实现

- `src/decision/bomb_strategy.py`（新增 4 条规则）
- **M1 未激活**，V5/V6 才会激活

## 关联页面

- [[gua-004]]
- concepts/strategic-layers
