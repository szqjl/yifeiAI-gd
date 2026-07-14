---
type: concept
title: "局 ⊃ 副 (Recursion: Game ⊃ Round)"
sources:
  - docs/guandan-brain/v7-win-rate-history.md
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
tags:
  - recursion
  - data-model
  - l1-l4
status: current
related_gua: []
date: 2026-07-03
---

# 局 ⊃ 副 (Recursion: Game ⊃ Round)

## 核心定音

> **局 ⊃ 副**：1 局掼蛋 = 2 副牌（A 方 vs B 方 × 2 副）
>
> 反过来不成立：副 ⊄ 局（单看一副不能反推整局）

## 数据载体

| 层级 | 载体 | 含义 |
|------|------|------|
| L1 | `game_records/*.json` | 单条 JSON = 1 副（yf1 或 yf2 视角）|
| L2 | yf1 + yf2 配对 | 1 副（双视角）|
| L3 | 2 副组合 | 1 局（升 / 降级结果）|
| L3' | 局级 log | `logs/` 下的批跑日志 |
| L4 | 多次局聚合 | 队胜率 KPI |

## 易错点

1. **副数 = JSON 数 / 2**（每副有 yf1 和 yf2 两条 JSON）
2. **局数 ≠ 副数**：分母不同，不能混用
3. **位次 [0]+[1] 是局级指标**，不是副级

## 已记录的口径偏差

`v7-win-rate-history.md` 末三行出现"队胜率 0/3 vs 副胜 4/28"的口径偏差，需统一为：
- 队胜率：分母为局
- 副胜率：分母为副

## 对账流程

1. L1 → L2：yf_replay.py 配对 yf1/yf2
2. L2 → L3：根据升/降级判定局结果
3. L3 → L3'：与 logs/ 对账
4. L3' → L4：聚合计算 KPI

## 关联

- [[win-rate-kpi]] — 队胜率定义
- [[v7-win-rate-history-summary]] — V7 战 KPI
- [[workflow-decision-trace]] — 决策链路中的副/局区分
