---
type: concept
title: "V7 KPI 护栏"
sources:
  - docs/guandan-brain/v7-win-rate-history.md
tags:
  - v7
  - kpi
  - guardrail
  - evaluation
status: current
related_gua:
  - GUA-039b
date: 2026-06-29
---

# V7 KPI 护栏

## 定义
V7 引擎迭代过程中用于约束「达到何种程度算有效改动」的所有硬性条款，集中记录于 `v7-win-rate-history.md`。

## 核心条款

### 1. 评估次数硬约束
**评估次数 = 0 = 未实施**（明确禁止纸上谈兵护栏）。

### 2. 胜率门槛
- V7 vs Lalala 门槛 ≥30%（GUA-039b）
- 冒烟 ON 触发：50 局 ≥40%

### 3. 批跑数规则
批跑局数必须为 **3 的倍数**（3/9/12…），与平台数据「局≠副」口径一致。

### 4. 数据真源
- `batch_games` 真源 = `current_batch.json`
- `server_vn_raw` 作为 fallback

## 与 M3 线的对比
M3 线无对应 KPI 护栏文件，是治理体系的不对称点。

## 相关页面
- [[batch-evaluation]] - 批跑评测体系
- [[engine-v7]]
- [[v7-win-rate-history-summary]]
