---
type: concept
title: "V7 出牌类型极化（卡 2 级）"
sources:
  - docs/analysis/archive/level2-root-cause.md
  - docs/analysis/archive/2026-06-18-gua062-batch-eval.md
tags:
  - v7
  - symptom
  - card-type
status: current
related_gua:
  - GUA-059
  - GUA-060
  - GUA-062
date: 2026-06-18
---

# V7 出牌类型极化（卡 2 级）

## 现象描述

V7 引擎在实盘中出牌类型严重偏向 Single，且呈现 2/A 双峰分布。

## 量化指标

| 指标 | 数值 |
|------|------|
| Single 占非 PASS 决策 | 80.5% |
| 双峰 | 2 / A |
| 数据来源 | GUA-062 批跑（9 局 79 副） |

## 根因

- 表层：出牌类型极单一
- 深层：[[concept-bc-argmax-collapse]]

## 修复路径

- 必须先解决 BC 退化根因（[[gua-059]]）
- 再启动组牌质量中间表示（[[gua-054]]）与动作空间二阶段过滤（[[gua-055]]）

## 关联

- [[gua-062]]
- [[gua-059]]
- [[gua-060]]
- [[concept-bc-argmax-collapse]]
