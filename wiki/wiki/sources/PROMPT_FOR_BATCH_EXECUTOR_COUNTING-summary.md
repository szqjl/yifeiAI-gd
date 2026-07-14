---
type: source-summary
title: "PROMPT_FOR_BATCH_EXECUTOR_COUNTING.md 资料摘要"
sources:
  - docs/guandan-brain/PROMPT_FOR_BATCH_EXECUTOR_COUNTING.md
tags:
  - batch-executor
  - counting
  - prompt
status: current
related_gua:
  - GUA-033
date: 2026-06-30
---

# 批跑执行器记数 Prompt 摘要

## 概述

该文档定义了批跑执行器（Batch Executor）在对局记数环节的 Prompt 规范，用于离线对局数据的统计与核验。

## 已知信息

- 文件大小：约 3,470 字符（短文档）
- 聚焦单一主题：批跑记数逻辑
- 与"局 ≠ 副"口径问题直接相关

## 核心内容（待确认）

- 批跑过程中"局"（Round）与"副"（Pair）的统计规则
- 如何区分一次完整对局（2 局）与单局结果
- KPI 计算时的分母选择

## 关联

- [[batch-evaluation]] — 批跑评测体系
- [[局不等于副]] — 核心口径概念
- [[ISSUES-summary]] — 缺陷追踪
