---
type: concept
title: "工作流 WF-12 · yf 决策链路分析"
sources:
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
tags:
  - workflow
  - wf-12
  - decision-trace
  - root-cause
status: current
related_gua:
  - GUA-062
  - GUA-075
  - GUA-078
  - GUA-081
date: 2026-06-28
---

# 工作流 WF-12 · yf 决策链路分析

## 概述

WF-12 是 [[yf1_m3]] 主导的**单步微观决策**分析工作流。它与 [[wf-04-batch-kpi]]（批量胜率 KPI）形成互补：WF-04 看结果，WF-12 看过程。

## 核心方法

### §1 触发条件
- WF-04 批跑胜率异常（如 GUA-062 0/9 局胜）
- 单局复盘发现决策可疑
- GUA 缺陷涉及决策链路

### §2 关单标准
- **禁止** 以 replay 逐步一致作为通过标准（见 [[batch-evaluation]]）
- 必须用 [[decision-pipeline-v7]] 标注失败层
- 必须套用 [[decision-trace-taxonomy]] 至少一个 R-Dxx 标签

### §3 决策管线还原表
输出 [[decision-pipeline-v7]] L0~L8 的命中层、return 点、失败层。

### §4 根因诊断
套用 R-D01~R-D08 标签 + 关联 GUA + 修复建议。

## 与其他工作流的关系

| 工作流 | 视角 | 输出 |
|--------|------|------|
| [[wf-04-batch-kpi]] | 宏观 KPI | 胜率、退化率、末级分布 |
| WF-06 | 叙事复盘 | 单局/单副故事线 |
| **WF-12** | **微观决策链路** | **决策层表 + R-Dxx 标签** |
| [[wf-10-guard-rule]] | 规则规约 | guard R-Gxxx 编号 |

## 历史产出

- GUA-062 卡2级 24 副 44.4% PASS 率诊断
- GUA-075 card_mask Dict 键冲突定位（L2 组牌层）
- GUA-078 残局管线 L1 行为记录
- GUA-081 L8 兜底 fallback 缺失

## 团队归属

- **yf1_m3**：主导工作流设计与执行
- **yf2_m3**：批跑验证、case 抽样

## 相关页面

- [[decision-pipeline-v7]] — 决策层表
- [[decision-trace-taxonomy]] — 根因标签
- [[gua062-batch-eval-summary]] — 典型产出
- [[cardmask-multiset-fix]] — 典型产出
