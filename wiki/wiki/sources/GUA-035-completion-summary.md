---
type: source-summary
title: "GUA-035 completion · END-M02+ solo 接风对手剩张过滤"
sources:
  - docs/guandan-brain/issues/GUA-035-completion.md
tags:
  - source-summary
  - gua-035
  - m3
  - solo
  - 接风
status: current
related_gua:
  - GUA-035
  - GUA-034
  - GUA-026
  - GUA-029
  - GUA-031
date: 2026-06-17
---

# GUA-035 completion · END-M02+ solo 接风对手剩张过滤

## 摘要

GUA-035 是 M3 续切片系列的接风对手剩张过滤条目，覆盖 solo 模式下接风对手持 1/2/5 张等关键阈值时的过滤逻辑。

## 完成 ID

- END-M02+-01
- END-M02+-02
- END-M02+-03
- END-M02+-04

## 范围排除（明确划出本轮）

- 两手规划 → V5+
- 可回收单张完整评分 → V5+

## 关联 GUA

- [[gua-034]] — 前置讨论/方案评审
- [[gua-026]] — 接风禁拆
- [[gua-029]] — solo 路径分流
- [[gua-031]] — 队友让道 PASS

## 测试

`tests/test_m3_gua035.py` 覆盖四组 case。

## 入册日期

2026-06-01
