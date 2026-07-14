---
type: concept
title: "IP 规则对照批跑范式"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/iterations/v7-gua097-ablation-log.md
tags:
  - v7
  - ablation
  - ip-rule
status: current
related_gua:
  - GUA-097
  - GUA-091
date: 2026-06-19
---

# IP 规则对照批跑范式

## 概念
V7 战略转向后，每条新规则必须经过 IP（In-Play）规则对照批跑验证才能合入。

## 三步范式
1. **Baseline 批跑**：关闭新规则，记录基线胜率
2. **Enable 批跑**：启用新规则，记录胜率
3. **Delta 分析**：计算胜率变化，若无正向变化则需重审设计

## 当前 ablation log
[[gua-091]] 是首个 ablation 目标：
- baseline: 0/3 (0%)
- enable: 0/3 (0%)
- 暂无 delta 意义，需更多样本

## 价值
**防"加规则
