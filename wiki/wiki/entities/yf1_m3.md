---
type: entity-engine
title: "yf1_m3 · M3 队友客户端"
sources:
  - src/communication/yf1_m3.py
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
tags:
  - entity
  - engine
  - m3
  - yf
status: current
related_gua:
  - GUA-031
  - GUA-062
date: 2026-06-30
---

# yf1_m3 · M3 队友客户端

M3 决策引擎的 yf1 客户端实现（队友位），与 yf2_m3 合起组成一个完整队。

## 与 V7 的区别

- **M3**：以 `IDecisionProvider` 运行，70+ if-then 硬规则，无独立记忆模块
- **V7**：`yf1_v7` / `yf2_v7` + `UltimateWinRateEngineV7`，三层架构 + 阶段调度

## 关联

- GUA-031：M3 队友保护已建
- GUA-062：M3 组牌逻辑提取到 V7 GroupingEngine
