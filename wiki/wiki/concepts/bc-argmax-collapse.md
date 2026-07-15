```markdown
---
type: concept
title: "BC argmax collapse（行为克隆输出坍缩）"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - bc
  - collapse
  - blocker
  - v7
status: current
related_gua:
  - GUA-064
  - GUA-039b
date: 2026-07-15
---

# BC argmax collapse

## 现象
V7 BC 模型的 2048 维输出空间**仅使用 2 维**：
- PASS：50%
- 首候选：48.9%

模型坍缩为二元分类，**完全丧失掼蛋出牌的多样性**。

## 根因
- BC 训练数据中 PASS 和首选项占绝对多数
- Softmax + cross-entropy 在不平衡标签下退化为 argmax
- 深层网络无 belief 输入，无法利用牌局信息

## 证据
- 5 次批跑（GUA-059/060/062/063/064）一致 0/12
- 不可通过学习率/正则化修复

## 结论
**V7 BC 路线已死**，唯一解是 [[GUA-039b]] 自对弈（RL）：
- 自对弈可探索非首选项
- 奖励信号直接优化胜率
- 配合 [[belief-input-rule-engine]] 打破零信念

## 关联
- [[gua-064]] — 主 GUA
- [[module-bc-trainer]] — 训练器
- [[belief-input-rule-engine]] — 信念输入
```

---
