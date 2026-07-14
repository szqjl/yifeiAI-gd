---
type: concept
title: "批跑评测与运维观察"
sources:
  - docs/analysis/archive/批跑cmd窗口观察.md
  - docs/analysis/regression-diff-2026-05-31.md
  - docs/analysis/v7-re-eval-2026-06.md
tags:
  - batch
  - evaluation
  - ops
  - kpi
status: current
related_gua: []
date: 2026-06-01
---

# 批跑评测与运维观察

## 核心论点

**批跑是唯一真源**：所有策略改动必须经过离线批跑验证。

## 评测维度

1. **胜率 KPI** — 相对各对手（尤其是 lalala）的胜率
2. **回归测试** — 同一引擎不同版本的对比（详见 [[regression-diff-2026-05-31-summary]]）
3. **重评测** — 引擎大版本变更后的全面评测（详见 [[v7-re-eval-2026-06-summary]]）

## 运维观察

批跑过程中的 CMD 窗口观察记录（详见 [[批跑cmd窗口观察-summary]]）是发现：
- 启动异常
- 性能瓶颈
- 日志错误
的重要手段。

## 关键警示

> **局 ≠ 副**：数据解读的核心口径问题，已定音但需持续强调。
