---
type: concept
title: "BC argmax collapse（NN 退化为随机选择器）"
sources:
  - docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md
  - docs/guandan-brain/掼蛋AI技术路径重校-V系列方法论反思.md
tags:
  - bc
  - nn
  - failure-mode
  - collapse
status: current
related_gua:
  - GUA-064
  - GUA-071
date: 2026-07-01
---

# BC argmax collapse

## 现象

V7 BC v3 模型输出层 2048 维：
- **PASS 占比 50.1%**
- **首候选占比 48.9%**
- 两者之和 ≈ 99%，几乎无有意义选择

→ NN 退化为**接近二选一的随机选择器**

## 结构性矛盾

| 维度 | BC 训练目标 | V7 实际可用 |
|------|------------|-------------|
| 输入 | 单局面 + 玩家手牌 | 单局面 + 玩家手牌 + **对手牌型约束** |
| 输出 | 2048 维动作 argmax | 动作空间受组牌候选+过滤规则限制 |
| 信号 | 单步监督 | 多步牌局演化 |

**GAP**：
1. **输入缺失对手手牌**（训练时只能见到自己手牌）
2. **BC 目标 argmax 与可用信息 gap**（可用动作受规则引擎约束）
3. **argmax 在受限空间内无意义**（强约束下 action 列表很短）

## 历史对照：V5 失败

1312 人类数据 BC 训练
