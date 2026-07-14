---
type: concept
title: "Guard 叠加过滤悖论"
sources:
  - docs/guandan-brain/v7-win-rate-history.md
tags:
  - guard
  - puzzle
  - v7
status: current
related_gua:
  - GUA-064
  - GUA-071
date: 2026-06-29
---

# Guard 叠加过滤悖论

## 定义
V7 引入多护栏（R07~R16）叠加过滤后，副胜率不升反降的悖论。

## 现象
- 单护栏独立看均合理
- 叠加后过滤掉所有候选动作
- 副胜率反降

## 解释方向
1. 护栏假设相互独立，实际强耦合
2. 护栏设计基于 M3 经验，未适配 V7 BC 模型的输出分布

## 当前处置
叠加护栏方案暂停，转向 heuristic_select（GUA-071）。

## 相关页面
- [[engine-v7]]
- [[bc-collapse-pattern]]
