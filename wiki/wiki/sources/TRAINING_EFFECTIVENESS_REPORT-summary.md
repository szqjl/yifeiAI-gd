---
type: source-summary
title: "M1 训练效果报告摘要"
sources:
  - docs/guandan-brain/notes/TRAINING_EFFECTIVENESS_REPORT.md
tags:
  - m1-training
  - over-prediction
  - stage7
  - historical-lesson
  - failure-analysis
status: current
related_gua:
  - GUA-016
  - GUA-017
  - GUA-019
date: 2026-06-18
---

# M1 训练效果报告摘要

## 文件信息
- **源文件**：`docs/guandan-brain/notes/TRAINING_EFFECTIVENESS_REPORT.md`（2293 字符）
- **主题**：M1 BC 模仿学习训练的 10 次迭代效果评估

## 核心结论
**M1 战胜 client 胜率 0%**（10 次迭代全部失败），M1 训练实验已确认无法达到实用水平。

## 失败模式
### 1. 过度预测危机
- 模型预测输出 **512/512 张卡牌**（整副牌）
- 实际真实卡牌数均值仅 0.79 → 1.44
- 预测比例高达 **644 倍**（后期降至 355 倍仍过高）

### 2. 损失函数爆炸
- 总损失达到 **80,168,580,121**（800 亿级别）
- 平方惩罚系数过大（576650）导致梯度爆炸

### 3. 稀疏性奖励失效
- 原设计：`exp(-512/10) ≈ 0`
- 过度预测时奖励信号完全消失，无法引导模型收敛

## 关键指标演进

| 指标 | 初始值 | 修复后期 | 状态 |
|------|--------|----------|------|
| 总损失 | 80,168,580,121 | 4,989.92 | ✅ 已修复 |
| 真实卡牌数 | 0.79 | 1.44 | ✅ 已提升 |
| 预测卡牌数 | 512 | 待验证 | ⚠️ 未确认 |
| 预测比例 | 644.51 | 355.37 | ⚠️ 仍过高 |
| 评估胜率 | 0% | 0% | ❌ 未改善 |

## 关联概念
- [[m1-over-prediction-crisis]] — 过度预测危机的完整概念页
- [[synthesis-m1-training-failure]] — 跨文档综合分析
- wiki/concepts/bc-argmax-collapse.md — BC 训练的 argmax 坍缩问题（已关闭 GUA-060）

## 教训
M1 训练投入产出比极低，资源应转向 V7 NN 引擎开发。
