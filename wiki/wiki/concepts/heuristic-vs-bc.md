---
type: concept
title: "heuristic vs BC - V7 决策切换节点"
sources:
  - docs/guandan-brain/v7-win-rate-history.md
tags:
  - v7
  - heuristic
  - bc
  - decision-switch
status: current
related_gua:
  - GUA-064
  - GUA-065
  - GUA-071
date: 2026-06-29
---

# heuristic vs BC - V7 决策切换节点

## 背景
V7 NN 引擎训练出 BC v3（val_acc 80.88%），但实战副胜仅 0/164，巨大脱节迫使团队切换实战策略。

## 决策路径

### 方案 A：BC 模型 argmax
- val_acc 高（80.88%）
- 实战副胜极低（0/164）
- **GUA-064 argmax collapse**

### 方案 B：heuristic_select 四优先级
- 单行副胜 25.5% 巅峰（GUA-065）
- 综合批跑 3.7%
- **GUA-071 NN→heuristic 切换**

## 切换意义
这是从「NN 路线」向「规则兜底」的关键退守，承认 BC 模型在掼蛋场景下的实战化尚未成功。

## 待解问题
- 单行 25.5% 是否可持续？
- BC 路线是否彻底放弃？
- heuristic 方案能否进一步优化？

## 相关页面
- [[engine-v7]]
- [[bc-collapse-pattern]]
- [[gua-071]]
