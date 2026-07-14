---
type: source-summary
title: "2026-06-30 V7 3局净盘批跑 + WF-12 锚点筛选"
sources:
  - docs/guandan-brain/handoff/2026-06-30-V7-3局净盘批跑-WF12锚点筛选.md
tags:
  - handoff
  - v7
  - 净盘批跑
  - wf-12
  - decision-trace
status: current
related_gua:
  - GUA-096
  - GUA-098
date: 2026-06-30
---

# 2026-06-30 V7 3局净盘批跑 + WF-12 锚点筛选

## 核心内容

承接 2026-06-29 阶段化方案，本次执行 3 局净盘批跑并用 WF-12 锚点筛选定位阶段 4 失败根因。

## 批跑数据

- **副胜率**：4/22 ≈ 18%（较前批有结构提升）
- **局胜**：0/3（仍全败）
- **关键问题**：结构优势无法兑现成头游

## WF-12 锚点筛选

通过 [[gua-098|DecisionTracer]] 抓取阶段 4 决策锚点，发现：
- 阶段 4 存在「过牌→失牌→被动升级」的死亡螺旋
- 信念建模缺失导致 V7 无法识别「我方已控牌」的信号
- Q1/Q2/Q3 残局规则分散，无统一中局大脑统一调度

## 落点

- [[gua-096]] — 净盘批跑落盘 hook
- [[gua-098]] — DecisionTracer 决策可观测
- [[batch-evaluation]] — 三批批跑综合对比
- [[v7-stage-evolution]] — 阶段化落地路径进度
