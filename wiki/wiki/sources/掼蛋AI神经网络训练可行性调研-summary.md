---
type: source-summary
title: "掼蛋 AI 神经网络训练可行性调研（摘要）"
sources:
  - docs/guandan-brain/掼蛋AI神经网络训练可行性调研.md
tags:
  - nn-training
  - academic-survey
  - v7-architecture
status: current
related_gua: []
date: 2026-06-18
---

# 掼蛋 AI 神经网络训练可行性调研（摘要）

## 文档定位

本文档调研**掼蛋/斗地主类不完美信息博弈 AI**的神经网络训练可行性,涵盖 4 篇顶会/顶刊论文,并坦诚指出**学术界论文均未落地**的现实问题。

## 调研论文

| 论文 | 出处 | 核心方法 | 落地状态 |
|------|------|----------|----------|
| DanZero | arXiv:2210.17087 (2022) | Self-play + MCTS | 学术原型 |
| GuanZero | arXiv:2402.13582 (2024) | DanZero 改进 | 学术原型 |
| DouZero | ICML 2021 | 纯 MC self-play | 学术原型 |
| DouMH | IJCAI 2024 | 多头监督 | 学术原型 |
| ABL-GD | CCFAI 2025 (南大 LAMDA) | 神经+逻辑混合 | 学术原型 |
| OpenGuanDan | arXiv:2602.00676 (2026) | 公开平台 | 学术原型 |

> ⚠️ 以上论文**均无大规模工业落地案例**。

## 核心结论

### 1. 学术界方法可借鉴但不能照搬

- **可借鉴**:Self-play 范式、Curriculum Learning、多头监督
- **不可照搬**:端到端 BC、纯 RL(在掼蛋复杂度下失效)

### 2. 掼蛋的特殊性

- **状态空间**比斗地主更大(2 副牌、4 人)
- **合作机制**(队友配合)是非线性因素
- **升级机制**引入长程目标

### 3. 推荐方向

> **神经 + 逻辑混合架构**(类 ABL-GD),但需结合 M3 工业界经验

## 关键方法论

| 方法 | 出处 | 价值 |
|------|------|------|
| 模块化分阶段训练 | AlphaGo (Nature 2016) | 降低训练难度 |
| Curriculum Learning | ICML 2009 | 简单→复杂 |
| 多头监督 | DouMH (IJCAI 2024) | 多目标解耦 |
| 神经+逻辑混合 | ABL-GD (CCFAI 2025) | 可解释性 |

## 关联页面

- [[academic-vs-industrial-guandan]] — 学术界 vs 工业界对比
- wiki/concepts/modular-staged-training.md — 模块化分阶段训练概念
- [[v7-failure-postmortem]] — 失败根因分析
