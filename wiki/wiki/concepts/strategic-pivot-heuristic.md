---
type: concept
title: "2026-06-19 战略转向：heuristic 优先"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/ITERATIONS.md
tags:
  - strategic-decision
  - heuristic
  - milestone
status: current
related_gua:
  - GUA-064
  - GUA-071
  - GUA-073
  - GUA-075
date: 2026-06-21
---

# 2026-06-19 战略转向：heuristic 优先

## 节点意义

V7 引擎的**关键战略拐点**。鉴于 BC argmax collapse 已确证（GUA-064），决定将 V7 主迭代路径从 NN argmax 全面转向 heuristic 优先。

## 决策内容

| 维度 | 决策 |
|------|------|
| 短期策略 | heuristic 优先（复用组牌引擎 TDD 迭代模式） |
| 中期策略 | NN 权重保留 |
| 长期策略 | 待 GUA-039b 自对弈 RL 就绪后重新启用 NN |

## 首跑结果（2026-06-19）

- 副胜：**4/168 (2.4%)**
- 远低于 GUA-065 baseline 25.5%
- 暴露 heuristic 缺牌力评估/剩余牌数/炸数估计等 Guard 级智能

## 后续动作

- [[gua-073]] — Guard-Heuristic 管道架构整理
- [[gua-075]] — 双路径决策架构
- [[gua-072]] — card_mask 退化保护

## 关联

- [[v7-current-state]] — 当前状态汇总
- [[gua-064]] — 触发事件
