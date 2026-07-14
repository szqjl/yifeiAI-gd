---
type: source-summary
title: "M1 队胜率策略攻关摘要"
sources:
  - docs/guandan-brain/iterations/m1-strategy-gua022.md
tags:
  - m1
  - team-win-rate
  - frozen
status: current
related_gua:
  - GUA-022
date: 2026-06-18
---

# M1 队胜率策略攻关摘要

## 概览

M1 队胜率策略攻关，10 条迭代横跨 40 天（详见原始文件）。本批次的关键决策：**M1 frozen 定音，KPI 迁 M3**。

## 关键结论

- GUA-022（队胜率）经多轮策略调整仍 0/12 同机对照
- 决定：M1 = frozen / 非交付线
- KPI 迁 M3，P0 guard 改至 `m3_decision_engine`

## 重要声明

> M1 0/12 与 M3 7/10 同机对照已排除口径误差
> M1 frozen 原因：规则引擎能力瓶颈

## 演进叙事

`m1-pass-gua020-021 → m1-strategy-gua022（frozen）→ m3-integration-gua024-028`

## 关联

- m1-vs-m3-handoff
- [[GUA-022]]（closed-frozen）
- M1 frozen 迁 M3 决策路径
