---
type: source-summary
title: "V7 决策架构改造：从排除法到推荐法"
sources:
  - docs/guandan-brain/V7-决策架构改造-从排除法到推荐法.md
tags:
  - v7
  - decision-architecture
  - refactor
  - paradigm-shift
status: current
related_gua: []
date: 2026-07-15
---

# V7 决策架构改造：从排除法到推荐法

## 概述

`V7-决策架构改造-从排除法到推荐法.md` 描述了 V7 NN 引擎的**核心决策范式转变**：从 M3 时代的"排除法"（Elimination）转向 NN 驱动的"推荐法"（Recommendation）。

## 范式对比

| 维度 | 排除法 (M3 时代) | 推荐法 (V7 时代) |
|------|----------------|----------------|
| 决策起点 | 候选动作全集 | 上下文状态编码 |
| 决策方式 | 逐个排除非法/低分动作 | 直接输出动作分布/最优动作 |
| 知识来源 | 硬编码规则 | NN 学习 |
| 泛化能力 | 弱 | 强 |

## 关键论点

1. **M3 规则引擎已达瓶颈**：硬编码规则难以覆盖复杂局面
2. **NN 引擎是突破关键**：学习到的策略可超越人工规则
3. **批跑是唯一验证标准**：所有架构改造必须经过离线批跑

## 关联页面

- [[engine-v7]] — V7 引擎
- [[engine-m3]] — M3 引擎（对比基线）
- [[v7-win-rate-history-summary]] — 改造后的胜率验证
- [[V7-Development-summary]] — V7 主索引

## 备注

- 源文件较大（13367 字符），是 V7 架构演进的核心文献
- 与 [[GUA]] 体系中的 M3 缺陷条目形成对照
