---
type: concept
title: "M1 过度预测危机"
sources:
  - docs/guandan-brain/notes/TRAINING_EFFECTIVENESS_REPORT.md
  - docs/guandan-brain/notes/TRAINING_FIXES_SUMMARY.md
tags:
  - m1-training
  - over-prediction
  - bc-learning
  - failure-pattern
  - historical-lesson
status: current
related_gua:
  - GUA-016
date: 2026-06-18
---

# M1 过度预测危机

## 概念定义
**过度预测（Over-Prediction）** 指 BC 模仿学习模型在卡牌多标签分类任务中，预测输出远多于真实标签数量的现象。M1 训练中表现为预测全部 512 张卡牌。

## 失败模式

### 现象
- **预测卡牌数**：512/512（即输出全 1 向量）
- **真实卡牌数均值**：0.79 → 1.44（修复后）
- **预测比例**：644.51 倍 → 355.37 倍（修复后）

### 根因分析

#### 1. 数据分布不平衡
掼蛋游戏中：
- **PASS 动作**占大量样本（真实卡牌数 = 0）
- **过牌/小牌组合**的真实卡牌数远小于 512

#### 2. 损失函数设计缺陷
- **平方惩罚**对预测过量的梯度信号过强
  - `576650 × (pred - target)²` 在 pred=512 时梯度爆炸
- **指数稀疏奖励** `exp(-|pred|/10)` 在 pred=512 时≈0
  - 奖励信号完全消失，无法引导模型收敛

#### 3. 模型容量问题
M1 的 BC 模型可能容量不足，无法学习"何时不出牌"的精细决策。

## 修复尝试（均未根治）

| 维度 | 修复 | 效果 |
|------|------|------|
| 数据 | 过滤 PASS 样本 | ✅ 损失数量级恢复 |
| 损失函数 | 平方 → 对数惩罚 | ✅ 损失稳定 |
| 奖励 | 指数 → 倒数 | ✅ 信号恢复 |
| 超参 | lr↓, alpha↓, gamma↑ | ⚠️ 边际改善 |
| **胜率** | — | ❌ 仍为 0% |

## 教训

### 对 M1 的结论
M1 BC 模仿学习**不适合掼蛋的复杂动作空间**，应转向：
- 序列决策（每次出一手牌作为一个完整决策）
- 或直接进入 NN 强化学习（V7 方向）

### 对 V7 的启示
V7 NN 引擎设计时应规避：
- 多标签分类输出（避免过度预测的诱因）
- 平方形式惩罚（梯度爆炸风险）
- 稀疏性奖励的指数衰减形式

## 关联
- wiki/concepts/bc-argmax-collapse.md — BC 训练的 argmax 坍缩（已关闭 GUA-060，但同源问题）
- [[GUA-016]] — 数据/损失修复
- [[synthesis-m1-training-failure]] — M1 失败综合分析
- wiki-minimax/entities/engine-m3.md — 取代 M1 的现役引擎
- wiki/entities/engine-v7.md — 未来方向
