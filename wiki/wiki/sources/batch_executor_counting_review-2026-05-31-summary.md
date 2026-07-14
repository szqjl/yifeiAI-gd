---
type: source-summary
title: "批跑执行器计数逻辑复盘 2026-05-31"
sources:
  - docs/analysis/batch_executor_counting_review-2026-05-31.md
tags:
  - batch
  - executor
  - counting
  - review
  - root-cause
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# 批跑执行器计数逻辑复盘 2026-05-31

## 文件概况
- 路径：`docs/analysis/batch_executor_counting_review-2026-05-31.md`
- 字符数：~8,424（本次分析集合中体量最大）
- 类型：模块级根因复盘

## 概要
针对 批跑执行器 的计数逻辑进行深度复盘，疑涉及"局 vs 副"的口径问题（参见 局 ≠ 副）。

## 关键内容
- 计数逻辑的代码路径
- 与 批跑评测体系 的对账偏差
- 疑点与可能缺陷
- 修复建议

## 关键概念
- 批跑执行器模块
- 局 ≠ 副
- 对账（reconciliation）
- 计数原子性

## 备注
> ⚠️ 原始分析因 `unmatched braces` 错误未产出结构化实体列表，本页为基于文件元数据的占位摘要。本文件体量较大（8K+），建议后续摄入时重点展开。
