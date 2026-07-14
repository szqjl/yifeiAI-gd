---
type: concept
title: "专利规避设计原则"
sources:
  - docs/governance/patent-audit-cn113018837a.md
tags:
  - patent
  - legal
  - design-principle
status: current
related_gua:
  - GUA-043
date: 2026-06-18
---

# 专利规避设计原则

## 风险来源

| 项目 | 内容 |
|------|------|
| 专利号 | CN113018837A |
| 专利权人 | 杭州师范大学 |
| 风险公式 | `Ea = E1 + E2`（期望值的线性叠加） |

## 规避策略

### 推荐方案

1. **离散牌型分级**
   - 将连续期望计算改为离散查表
   - 避免解析公式直接落入保护范围

2. **NN win_rate 增量替代**
   - 用神经网络预测 `win_rate` 增量
   - 替代解析的 `Ea = E1 + E2` 公式

3. **重构 grouping 优化器**
   - `dynamic_grouping_optimizer.py` 改为基于**查表 + 启发式**
   - 避免动态期望值叠加

### 禁止做法

- ❌ 任何形式的 `期望 = 子项1期望 + 子项2期望` 公式
- ❌ 对手牌组进行期望值的线性分解

## 安全模块（不涉及风险）

- ✅ 四头网络
- ✅ BC 训练
- ✅ DMC / PPO
- ✅ 特征工程

## 关联页面

- GUA-043 — 专利规避审计 GUA
- [[patent-audit-cn113018837a-summary]] — 审计报告
- wiki/entities/engine-v7.md — V7 引擎
