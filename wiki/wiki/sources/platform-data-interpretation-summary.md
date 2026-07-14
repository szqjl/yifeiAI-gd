---
type: source-summary
title: "平台数据解读分析摘要"
sources:
  - docs/knowledge/platform-data-interpretation.md
tags:
  - 平台
  - v1006
  - N参数
  - source-summary
status: current
related_gua:
  - GUA-033
date: 2026-06-21
---

# 平台数据解读分析摘要

## 来源
`docs/knowledge/platform-data-interpretation.md`—— 针对 v1006 平台 `N` 参数含义的实测分析报告。

## 核心结论

### N = 局数（不是副数）
- 实测 `target-games 1` → 实际打完 **59 副**
- 1 局从 2 打到 A 双上，平均约 6 副
- 与 [[offline-platform-v1006]] 中的协议说明一致

## 关键证据
- 命令行参数 `target-games` 的实测数据
- v1006 说明书定义对比
- [[局不等于副]] 口径的支撑证据

## 影响
- 所有 KPI 计算必须以**局级**为口径
- 批跑统计（`_count_new_paired_games()`）以局数为单位
- 与 [[batch-evaluation]] 中的 KPI 口径选择一致

## 关联页面
- [[offline-platform-v1006]]：平台协议详情
- [[局不等于副]]：口径定义
- [[batch-evaluation]]：KPI 聚合层级
