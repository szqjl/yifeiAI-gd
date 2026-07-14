---
type: source-summary
title: "M1 训练修复总结摘要"
sources:
  - docs/guandan-brain/notes/TRAINING_FIXES_SUMMARY.md
tags:
  - m1-training
  - loss-function-tuning
  - stage7
  - historical-lesson
status: current
related_gua:
  - GUA-016
date: 2026-06-18
---

# M1 训练修复总结摘要（GUA-016）

## 文件信息
- **源文件**：`docs/guandan-brain/notes/TRAINING_FIXES_SUMMARY.md`（1007 字符）
- **主题**：GUA-016 训练数据/损失修复的总结

## 修复清单

### 数据层面
- ✅ 过滤空 `action_cards` 样本（PASS 动作）— 避免零标签样本污染训练

### 损失函数层面
- ✅ 阈值范围缩小：`0.00001-0.001`
- ✅ 过度预测惩罚：**平方 → 对数惩罚**
  - 系数：`576650 → 10000`
- ✅ 稀疏性奖励：**指数函数 → 倒数函数**
  - 解决 `exp(-512/10)≈0` 信号消失问题
- ✅ 正样本权重 `alpha`：`降至 0.05`（降低过拟合风险）
- ✅ 学习率：`降至 0.000005`
- ✅ 难样本关注度 `gamma`：`升至 6.0`（增强 Focal Loss 效果）

### 损失函数组件
- **EnhancedFocalLoss** — 增强版 Focal Loss，支持对数惩罚与倒数稀疏奖励

## 修复效果
| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 总损失 | 80,168,580,121 | 4,989.92 |
| 数量级 | 10¹¹ | 10³ |

虽然数量级恢复合理，但 [[TRAINING_EFFECTIVENESS_REPORT-summary]] 显示胜率仍为 0%，说明损失函数修复**未触及根本问题**（过度预测仍存在）。

## 关联
- [[GUA-016]] — 训练数据/损失修复条目
- [[m1-over-prediction-crisis]] — 过度预测危机
