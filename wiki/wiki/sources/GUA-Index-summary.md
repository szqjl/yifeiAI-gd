---
type: source-summary
title: "GUA 编号索引 (GUA-Index)"
sources:
  - docs/guandan-brain/MOCs/GUA-Index.md
tags:
  - source-summary
  - gua
  - index
  - moc
status: current
related_gua:
  - GUA-001
  - GUA-061
date: 2026-06-18
---

# GUA 编号索引 (GUA-Index)

## 文件定位
GUA-Index.md 是 GUA 编号体系的**全量索引**（1~61 + V7-xxx 辅助编号）。是 GUA 编号体系 概念页的补充数据。

## 当前 Open P0（4 个）
- **GUA-054**：V7 组牌中间表示（grouping_scanner 9 维）
- **GUA-055**：V7 动作空间二阶段过滤
- **GUA-059**：BC v2 退化根因定位
- **GUA-061**：模块化架构（GroupingEngine）—— **当前焦点**

## 当前 Open P1（3 个）
- GUA-056
- GUA-057
- GUA-058

## 当前 Open P2/Unscoped（3 个）
- GUA-048
- GUA-050
- GUA-053

## 已 Closed（30 个）
GUA-020, 021, 022, 024, 025, 026, 027, 028, 029, 030, 031, 032, 033, 034, 035, 036, 037a, 037b, 038, 041, 042, 043, 044, 045, 047, 049, 051, 052, 060, 014

## V7-xxx 辅助编号
- **V7-006**：端到端决策链路 — closed
- **V7-007**：胜率基线测试 — open
- **V7-010**：服务器 exe 迁出仓库 — closed

## 迭代阶段一览
- phase5-infra
- batch-executor
- governance-docs
- m1-pass-gua020-021
- m1-strategy-gua022
- m3-integration-gua024-028
- m3-strategy-gua026-029
- m3-guards-gua031-036
- m3-skills-mapping-gua030
- v7-features-gua037-038
- v7-infra-gua041-049
- v7-strategy-gua045-053
- v7-bc-training-gua059-061
- V7-Development

## ⚠️ 数据质量问题
- **GUA-039 / 040 / 046 缺失**：可能是跳号或遗漏，需在 log 中标注待核实
- 跳号常见原因：被合并/被废弃/录入遗漏

## 关联
- 上位概念：GUA 编号体系
- 当前 P0 焦点：[[gua-061]]
- V7 阶段：[[V7-Development]]
