---
type: source-summary
title: "PB-002 V7 缺陷发现治理闭环"
sources:
  - docs/guandan-brain/playbooks/PB-002-v7-bug-discovery-governance-loop.md
tags:
  - playbook
  - v7
  - 缺陷发现
  - 治理闭环
  - pb-002
status: current
related_gua:
  - GUA-099
  - GUA-100
  - GUA-101
  - GUA-102
date: 2026-06-29
---

# PB-002 V7 缺陷发现治理闭环

## 核心思想

把回放（replay）从「主力发现手段」**降级为「抽检手段」**，前移到缺陷发现链路前段。

## 四层闭环

```
Layer 1: 静态校验（lint / type / 规则表一致性）
   ↓ 失败即拦下
Layer 2: 参数化测试（矩阵测试 + 边界用例）
   ↓ 失败即拦下
Layer 3: 异常扫描（endgame_anomalies / round_level_stats）
   ↓ 异常预警
Layer 4: WF-12 单步决策链路抽检
   ↓ 抽检定位
```

## 关键规则

- 静态校验失败 → 禁止入批跑
- 参数化测试失败 → 禁止入批跑
- 异常扫描 → 批跑后必跑
- WF-12 → 抽样 10% 局次深挖

## 残局止血规则（GUA-099/100 引入）

- **GUA-099**：endgame 异常扫描默认开启
- **GUA-100**：Q1/Q2/Q3 残局规则集中入口（`endgame_rule` + `BAOSHU_RULE`）

## 落点

- [[pb-002-bug-discovery-loop]] — 概念页
- GUA-099 / GUA-100 — 残局止血规则
- [[decision-trace]] — WF-12 决策可观测
- [[v7-stage-evolution]] — V7 阶段化方案
