---
type: source-summary
title: "GUA-036 completion · 控权压顺 + 接风配合 M3 guard"
sources:
  - docs/guandan-brain/issues/GUA-036-completion.md
tags:
  - source-summary
  - gua-036
  - m3
  - guard
  - 控权
  - 接风
status: current
related_gua:
  - GUA-036
  - GUA-026
  - GUA-029
  - GUA-031
  - GUA-032
  - GUA-034
  - GUA-035
date: 2026-06-17
---

# GUA-036 completion · 控权压顺 + 接风配合 M3 guard

## 摘要

GUA-036 是 M3 guard 系列条目，来源 batch7 round38 复盘。它是 P-F02（队友配合）的扩展切片，包含四项子规则。

## 完成 ID

- CTRL-P01 — 控权压敌顺的最小够用原则
- CTRL-P02 — 阶段路由的夺权优先（与 STG-D01 协作）
- WIND-P01 — 接风禁拆 trips / 钢板 / 炸弹成员
- TEAM-P01 — 接风让道（与 GUA-031 PASS 边界耦合）

## 范围排除

- 整手组牌 → V5+-01/02
- combine_handcards 重写
- batch7 replay 逐步一致

## 关联 GUA

- [[gua-026]] [[gua-029]] [[gua-031]] [[gua-032]] [[gua-034]] [[gua-035]]

## 引用的原则

P-F02 / P-G01 / P-G02 / P-H04 / P-H06 / CG-T06 / STG-D01 / CALC-M03 / PASS-P02

## 备注

本条目是 M3 guard 范式文档化的候选模板，建议在 [[engine-m3]] 页面作为典型示例引用。

## 测试

`tests/test_m3_gua036.py`

## 入册日期

2026-06-01
