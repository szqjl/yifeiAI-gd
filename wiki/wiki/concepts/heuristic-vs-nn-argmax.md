---
type: concept
title: "Heuristic vs NN argmax 选择"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/ITERATIONS.md
tags:
  - v7
  - nn
  - heuristic
  - strategic-pivot
status: current
related_gua:
  - GUA-064
  - GUA-071
date: 2026-06-19
---

# Heuristic vs NN argmax 选择

## 概念
V7 NN 引擎在决策时面临的两种动作选择路径对比。

## NN argmax
- **机制**：BC 模型前向，取 logits 最大索引
- **优点**：理论上能学到复杂策略
- **致命缺陷**：见 [[GUA-064]] — 2048 维输出仅用 2 维（99.1% 集中在 actIndex 0/1）

## Heuristic Select
- **机制**：基于规则 + 启发式评分（如 [[GUA-062]] 五维评分）
- **优点**：可解释、可控、当前副胜率虽低但稳定
- **缺点**：上限低，无法学到复杂模式

## 当前决策
**Heuristic + Guard 暂替 NN argmax**（2026-06-19 战略转向）
- BC 权重保留但不作为决策路径
- 关单条件：heuristic 副胜率 ≥ 15%（[[GUA-071]]）

## 未来路径
需 [[GUA-072]] 三引擎 TDD 训练管线完成后，才能重新评估 NN argmax 路径。

## 关联
- [[gua-064]] — BC argmax collapse 根因
- [[gua-071]] — heuristic 关单条件
- [[engine-v7]] — V7 引擎状态
- synthesis-v7-strategic-pivot-2026-06-19 — 战略转向
