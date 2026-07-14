---
type: source-summary
title: "workflows/README 摘要 - WF-12 yf 决策轨迹工作流"
sources:
  - docs/guandan-brain/workflows/README.md
tags:
  - workflows
  - wf-12
  - yf-decision-trace
status: current
related_gua:
  - GUA-085
date: 2026-06-29
---

# workflows/README 摘要

## 工作流概览

文档位置：`docs/guandan-brain/workflows/README.md`

## WF-12-yf-decision-trace

**主题**：yf 决策轨迹工作流

**关联缺陷**：
- [[gua-085]] 回退 NN actIndex 错位 + 领出保 SF/炸核

**用途**：
- 追踪 yf 玩家（yf1 / yf2）的决策轨迹
- 验证回退 NN 路径的 actIndex 正确性
- 支撑领出阶段保 SF/炸核的回归测试

## 工作流定位

WF-12 是 [[gua-085]] 修复验证的**核心工作流**：
- 记录每次决策的 actIndex 与实际出牌张数
- 对比 enumerate_groupings 输出与领出实际行为
- 在 pytest 构造态中作为断言依据

## 关联

- [[gua-085]] P0 缺陷
- [[no-pseudo-closure]] 禁止伪关单原则
