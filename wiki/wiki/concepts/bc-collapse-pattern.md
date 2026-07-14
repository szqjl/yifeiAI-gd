---
type: concept
title: "BC argmax collapse 通用模式"
sources:
  - docs/guandan-brain/v7-win-rate-history.md
tags:
  - bc
  - collapse
  - pattern
  - nn
status: current
related_gua:
  - GUA-064
date: 2026-06-29
---

# BC argmax collapse 通用模式

## 定义
行为克隆（Behavior Cloning）训练中，模型策略坍缩到单一动作或极少量动作的现象，导致 argmax 输出失去多样性。

## 表现
- val_acc 可达 80%+（看似良好）
- 实战副胜接近 0%
- 决策熵极低

## 根因
掼蛋动作空间巨大但有效动作稀疏，BC 易学到「多数派动作」。

## 应对
- 见 [[heuristic-vs-bc]]
- Guard 叠加过滤（但出现 [[guard-overlap-puzzle]]）

## 相关页面
- [[engine-v7]]
- [[gua-064]]
- [[guard-overlap-puzzle]]
