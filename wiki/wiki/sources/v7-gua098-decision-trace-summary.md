---
type: source-summary
title: "GUA-098 决策追踪摘要"
sources:
  - docs/guandan-brain/iterations/v7-gua098-decision-trace.md
tags:
  - v7
  - decision-trace
  - debugging
status: current
related_gua:
  - GUA-098
date: 2026-06-30
---

# GUA-098 决策追踪摘要

## 来源
`docs/guandan-brain/iterations/v7-gua098-decision-trace.md`

## 概述
GUA-098 为 V7 NN 引擎引入决策追踪（decision trace）能力，记录每一手出牌的网络前向传播、中间特征、最终选择，便于调试与归因。

## 关键内容
- Decision trace 的采集字段
- 存储格式与回放工具
- 用于诊断 [[engine-m3]] 已知缺陷的可迁移性

## 关联
- [[gua-098]]
- [[engine-v7]]
- [[engine-m3]]
