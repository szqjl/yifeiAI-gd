---
type: source-summary
title: "2026-06-29 V7 阶段化方案设计 + GUA-096/097/098 治理护栏落地"
sources:
  - docs/guandan-brain/handoff/2026-06-29-V7-阶段化方案设计-GUA-096-097-098治理护栏落地.md
tags:
  - handoff
  - v7
  - 阶段化
  - 治理护栏
  - gua-096
  - gua-097
  - gua-098
status: current
related_gua:
  - GUA-096
  - GUA-097
  - GUA-098
  - GUA-075
  - GUA-078
date: 2026-06-29
---

# 2026-06-29 V7 阶段化方案设计 + GUA-096/097/098 治理护栏落地

## 核心内容

本次 handoff 是 2026-06-29 的主轴定音文档，同时完成两件事：
1. **V7 阶段化方案设计**：把 V7 引擎落地路径拆为 A/B/C 三阶段
2. **三条治理护栏落地**：GUA-096（净盘落盘 hook）、GUA-097（IP 规则对照批跑器）、GUA-098（DecisionTracer 决策可观测）

## V7 阶段化方案

| 阶段 | 范围 | 目标 | 杠杆点 |
|------|------|------|--------|
| **阶段 A** | 补丁主脑 | 已有规则的 V7 移植 + 端到端跑通 | 净盘批跑胜率归零可解释化 |
| **阶段 B** | 统一中局大脑 | 信念建模（IP-01~IP-21）+ Q1/Q2/Q3 残局分散治理 | 阶段 4 副胜率从 0% → 30%（带动整体 0% → 3-5%） |
| **阶段 C** | 候选统一评分器 | NN 评分头 | 长线方向 |

## 三条治理护栏

- **GUA-096 post_batch_log**：批跑落盘 hook，强制落 `v7_vs_lalala_scores.json` + `v7_vs_lalala_state.json` + 净盘标记
- **GUA-097 ip_ablation_runner**：IP 规则对照批跑（baseline / enable / diff / list 四模式）
- **GUA-098 DecisionTracer**：单步决策链路深挖，落到 `game_decision_traces/` 可回放

均已 commit + push + pytest 7/7 PASS。

## 关键认知修正

- 之前归因为「GUA-064 BC argmax collapse」是错的
- **V 系列失败真根因**：无 KPI 循环 + 静默失败 + 知识库用死
- **信念建模非 P2**——而是阶段 B 核心

## 落点

- [[V7-架构演进与新增规则准入治理-summary]] — 阶段化方案的完整治理延伸
- [[pb-002-bug-discovery-loop]] — 缺陷发现 4 层闭环
- [[engine-v7]] — V7 引擎实体页
- [[gua-096]] / [[gua-097]] / [[gua-098]] — 治理护栏条目

## 严格遵守

- 局≠副（GUA-033 定音）
- victoryNum [0]=[2] / [1]=[3] 镜像校验
- WF-04 三口径对账
- WF-12 单步决策链路深挖
