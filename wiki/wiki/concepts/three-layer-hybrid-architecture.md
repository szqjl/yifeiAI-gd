---
type: concept
title: "三层混合架构（Guard + 记牌 + 策略选择）"
sources:
  - docs/guandan-brain/掼蛋AI技术路径重校-V系列方法论反思.md
tags:
  - architecture
  - hybrid
  - guard
  - belief
  - strategy
status: current
related_gua:
  - GUA-071
  - GUA-072
  - GUA-074
date: 2026-06-19
---

# 三层混合架构（Guard + 记牌 + 策略选择）

## 定义

[[gua-074]] 提出的 V7 范式转移方案：

```
┌─────────────────────────────┐
│  Layer 1: Guard 规则         │  硬约束（必守/必攻）
├─────────────────────────────┤
│  Layer 2: 记牌信念           │  规则记牌 (GUA-072) → NN 记牌
├─────────────────────────────┤
│  Layer 3: 策略选择           │  heuristic (GUA-071) → NN 分类
└─────────────────────────────┘
```

## 各
