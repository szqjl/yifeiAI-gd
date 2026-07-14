---
type: entity-module
title: "module-v7-guard-pipeline · V7 Guard 管道"
sources:
  - docs/guandan-brain/ISSUES.md
  - src/v/nn/guards/v7_guards.py
  - docs/guandan-brain/V7-实施方案.md
tags:
  - module
  - v7
  - guard
  - pipeline
status: current
related_gua:
  - GUA-045
  - GUA-065
  - GUA-068
date: 2026-06-30
---

# module-v7-guard-pipeline · V7 Guard 管道

V7 原生 Guard 管道，由 `src/v/nn/guards/v7_guards.py` 实现，不 import M3。

## 规则集

- R01 〜 R12 + R14（13 条可用，R13 待实现）
- 阶段调度：STAGE_RULE_MAP 按 stage_0_1 / stage_2 / stage_3 依次启用不同子集（GUA-089）

## 实现原则

- Layer 3 决策不读 `actions` 历史（避免 M3 GUA-036 堆叠崩）
- 查询对手剩余走 Layer 1 → Layer 2

## 关联

- GUA-045：V7 Guard 壳定义
- GUA-065：队友识别与保护（R07-R09）
- GUA-068：R11 全局抑制牌检查
- GUA-089：阶段调度器（与 Guard 管道协同）
