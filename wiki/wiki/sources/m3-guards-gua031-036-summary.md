---
type: source-summary
title: "M3 Guard 系列摘要"
sources:
  - docs/guandan-brain/iterations/m3-guards-gua031-036.md
tags:
  - m3
  - guard
  - kpi
status: current
related_gua:
  - GUA-031
  - GUA-032
  - GUA-034
  - GUA-035
  - GUA-036
date: 2026-06-18
---

# M3 Guard 系列摘要

## 概览

M3 决策引擎 5 个 P0 guard 落地 + S6~S9 KPI 批跑。

## KPI 汇总

| S | GUA | 主题 | 批跑胜率 | 状态 |
|---|-----|------|---------|------|
| S6 | GUA-031 | 传牌 guard（passive_yield / active_feed） | 通过 | closed |
| S7 | GUA-032 | 记牌算牌（sync_remain_cards_classbynum） | 通过 | closed |
| S8 | GUA-034 | 残局拦头游（solo_sprint） | 78.8% | closed |
| S9 | GUA-035 | 对手剩张过滤（solo_opponent_rests） | 78.8% | closed |
| — | GUA-036 | 控权+接风（pick_min_straight_beat） | **52.2%** | **closed-with-regression-flag** |

## 关键张力

> GUA-036 控权 52.2% 显著差于 GUA-035 残局 78.8%（**p=0.009**）
> GUA-036 在多玩家场景引入对称性退化：`[0,3,0,3]` 分布异常
> **GUA-036 不能简单标 closed 待复跑**——需 CALC-M04/M05 修复后回归

## 关联

- M3 Guard 设计模式
- 批跑评测体系（回归对照表）
- [[GUA-036]]（异常回归）
