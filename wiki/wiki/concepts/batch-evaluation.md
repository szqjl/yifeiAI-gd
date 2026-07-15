---
type: concept
title: "批跑评测体系"
sources:
  - docs/guandan-brain/PROMPT_FOR_BATCH_EXECUTOR_COUNTING.md
  - docs/guandan-brain/SCRIPT_INDEX.md
  - docs/guandan-brain/v7-win-rate-history.md
tags:
  - evaluation
  - batch
  - kpi
  - methodology
status: current
related_gua: []
date: 2026-07-15
---

# 批跑评测体系

## 定义

**批跑 (Batch Evaluation)**：在固定算力/时间预算下，让 AI 引擎在历史牌局或生成牌局上**批量对局**，统计胜率/均分等 KPI，作为版本迭代的**唯一真源**。

## 核心要素

| 要素 | 说明 |
|------|------|
| 对手 | lalala、M3 baseline、自博弈 |
| 局数 | 必须足够大以消除方差 |
| 统计单位 | 局 vs 副（见 [[局≠副]]） |
| KPI | 胜率、均分、升级率 |
| 复现性 | 固定 seed + 脚本版本 |

## 原则

1. **批跑是唯一真源**：所有策略改动必须经过离线批跑验证
2. **统一口径**：局/副、对手、牌局集必须固定
3. **可复现**：seed、脚本、模型版本必须锁定

## 关联页面

- [[局≠副]]
- [[engine-v7]]
- [[engine-m3]]
- [[v7-win-rate-history-summary]]
- [[SCRIPT_INDEX-summary]]
