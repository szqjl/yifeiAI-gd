---
type: source-summary
title: "GUA-062 批跑结果 Handoff - 资料摘要"
sources:
  - docs/analysis/archive/2026-06-18-gua062-batch-eval.md
tags:
  - handoff
  - v7
  - batch-eval
  - gua-062
status: current
related_gua:
  - GUA-062
  - GUA-059
  - GUA-060
date: 2026-06-18
---

# GUA-062 批跑结果 Handoff - 资料摘要

## Handoff 背景

2026-06-18，组牌引擎 v2（[[gua-062]]）49 单元测试全部通过后的实盘批跑结果交付。

## 关键结果

| 指标 | 数值 | 对比 |
|------|------|------|
| pytest 单元测试 | 49/49 通过 | — |
| 实战批跑局数 | 9 局（vs lalala） | — |
| 实战副数 | 79 副 | — |
| V7 副胜率 | 8/79 = 10.1% | 与 GUA-061 无显著差异 |
| V7 累计队胜率 | 1/42 = 2.4% | — |

## 根因诊断

- 卡 2 级（出牌类型极单一）：Single 占非 PASS 决策 80.5%
- 2/A 双峰分布异常
- 详见 [[concept-v7-card-type-polarization]]、[[level2-root-cause-summary]]

## 关闭决策的张力

- GUA-062 标为 closed（单测通过）
- 但实战副胜率 10.1% 与 GUA-061 无显著差异
- BC 退化根因（[[gua-059]]）仍未解，关闭标准需重审
