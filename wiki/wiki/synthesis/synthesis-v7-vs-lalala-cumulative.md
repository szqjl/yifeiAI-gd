---
type: synthesis
title: "V7 vs lalala 累计战绩合成"
sources:
  - docs/analysis/archive/2026-06-18-gua062-batch-eval.md
  - docs/analysis/archive/level2-root-cause.md
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
tags:
  - synthesis
  - v7-vs-lalala
  - cumulative
  - m3-comparison
status: current
related_gua:
  - GUA-062
  - GUA-060
  - GUA-080
date: 2026-06-29
---

# V7 vs lalala 累计战绩合成

## 核心叙事：M3 vs V7 鸿沟

| 引擎 | 累计局数 | 团队局胜 | 局胜率 | 副胜率 |
|------|----------|----------|--------|--------|
| **M3** | 135+ | 96+ | **~70%**（55%–82% 波动） | — |
| **V7** | 138 | 1 | **0.7%** | 3%–26% |

> 单胜来自 V7-006/007 早期乐观数字，已淹没在后续 137 局零胜中。

## 关键切片：卡 2 级 24 副

| 指标 | 数值 |
|------|------|
| PASS 占比 | 44.4% |
| 单张主导（非 PASS 内） | 80.5% |
| 含炸副占比 | 20/24 (83%) |
| 炸弹使用位置 | 前 12%（早炸浪费） |
| 末级分布 | 12 副 2 + 12 副 A（双峰被压回） |

## 主因定调

**BC argmax collapse**（GUA-060）：
- 验证 80% vs 实战坍缩到 Single
- GUA-062 评分正确但未接入动作选择
- cardmask 缺陷加剧推荐阻塞

## 关单红线

任何 GUA 关闭必须走 [[gua-080]] R-G080-4 零退化批跑，**禁止以 replay 逐步一致为标准**。

## 引用

- [[engine-m3]]
- [[bc-argmax-collapse]]
- [[gua-062]]
- [[gua-060]]
- [[batch-evaluation]]
