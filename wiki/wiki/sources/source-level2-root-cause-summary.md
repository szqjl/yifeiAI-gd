---
type: source-summary
title: "卡 2 级根因诊断 - 资料摘要"
sources:
  - docs/analysis/archive/level2-root-cause.md
tags:
  - v7
  - root-cause
  - level-2
status: current
related_gua:
  - GUA-059
  - GUA-060
  - GUA-062
date: 2026-06-18
---

# 卡 2 级根因诊断 - 资料摘要

## 报告定位

V7 卡 2 级（出牌类型极单一）根因分析报告。

## 现象

- Single 占非 PASS 决策 80.5%
- 2/A 双峰分布异常

## 根因链

1. **BC argmax collapse**（理论必然）：训练数据中 Single 最常见 → argmax 总选 Single
2. **组牌引擎 v2 未接入动作选择**：GUA-062 评分算了但决策链仍走 BC argmax
3. **卡 2 级是症状**，根因是 [[concept-bc-argmax-collapse]]

## 结论

- 修复路径：必须先解 [[gua-059]]（BC 退化根因）
- 所有 P1 GUA 硬前置 [[gua-059]]
- 详见 [[gua-059]]、[[gua-060]]、[[gua-062]]
