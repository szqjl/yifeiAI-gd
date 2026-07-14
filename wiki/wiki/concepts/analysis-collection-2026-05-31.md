---
type: concept
title: "分析资料集合：2026-05-31 批跑复盘日"
sources:
  - docs/analysis/batch-warnings-comparison-2026-05-31.md
  - docs/analysis/batch_executor_counting_review-2026-05-31.md
tags:
  - batch
  - retrospective
  - 2026-05-31
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# 2026-05-31 批跑复盘日分析集合

## 概念说明
2026-05-31 是一日集中产出批跑相关分析的日期，至少包含两份核心文档：
- 告警对比分析
- 执行器计数复盘

## 共性主题
1. **批跑结果可信度**：告警与计数偏差直接影响 批跑评测 的胜率 KPI 解读
2. **局 ≠ 副 口径**：计数的多源对账是核心痛点（参见 局 ≠ 副）
3. **M3 引擎稳定性**：批跑异常往往与 M3 引擎 的规则边界处理相关

## 关联实体
- 批跑执行器模块
- GUA-033 缺陷（批跑相关）
- M3 引擎

## 后续行动
- 将计数逻辑缺陷升级为独立 GUA
- 在 本地评测 checklist 中新增计数对账步骤
