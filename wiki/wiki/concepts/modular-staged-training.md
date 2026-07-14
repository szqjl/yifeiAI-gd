---
type: concept
title: "模块化分阶段训练"
sources:
  - docs/guandan-brain/人类掼蛋决策流程完整分析.md
  - docs/guandan-brain/掼蛋AI神经网络训练可行性调研.md
tags:
  - methodology
  - training
  - alpha-go
status: current
related_gua: []
date: 2026-06-18
---

# 模块化分阶段训练

## 概念定义

**模块化分阶段训练**(Modular Staged Training)是 AlphaGo 在 Nature 2016 论文中提出的方法论:**将复杂博弈 AI 拆分为多个独立模块,每个模块单独训练,最后联合微调**。

## AlphaGo 范式

AlphaGo 的三阶段训练:

1. **监督学习阶段**:从人类棋谱学习快速走子网络
2. **强化学习阶段**:自对弈优化策略网络
3. **评估+搜索阶段**:MCTS + 价值网络联合决策

> 每个阶段独立训练、独立评估,降低端到端训练的难度。

## 在掼蛋 AI 中的应用

### 新 V7 的模块化设计

```
GroupingEngine ──┐
Role Assignment ─┼─→ 联合训练层 → 决策输出
MemoryTracker ───┤
DynamicAdjust ───┘
```

每个模块可独立训练:
- **GroupingEngine**:规则 + 搜索(不需要 NN)
- **Role Assignment**:监督学习(从人类对局提取)
- **MemoryTracker**:序列模型(LSTM/Transformer)
- **DynamicAdjust**:强化学习

### 借鉴的其他方法

| 方法 | 出处 | 在掼蛋中的应用 |
|------|------|----------------|
| Curriculum Learning | ICML 2009 | 简单→复杂(单轮→完整对局) |
| 多头监督 | DouMH IJCAI 2024 | 多目标解耦训练 |
| 神经+逻辑混合 | ABL-GD CCFAI 2025 | 可解释决策 |

## 与端到端训练的对比

| 维度 | 端到端 | 模块化分阶段 |
|------|--------|--------------|
| 训练难度 | 极高 | 逐步降低 |
| 可解释性 | 黑盒 | 模块可分析 |
| 调试成本 | 高 | 低(可定位模块) |
| 数据需求 | 巨大 | 中等(可分阶段收集) |
| 上限 | 理论高 | 依赖模块设计 |

## 已知风险

1. **模块间误差累积**:上游模块的误差会传递到下游
2. **联合微调困难**:模块各自最优 ≠ 整体最优
3. **接口设计**:模块间的状态表示需精心设计

## 关联页面

- wiki/concepts/human-like-decision-flow.md — 类人决策五阶段(模块化设计)
- wiki/entities/engine-v7.md — V7 引擎
- [[academic-vs-industrial-guandan]] — 学术 vs 工业
