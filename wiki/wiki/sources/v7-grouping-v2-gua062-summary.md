---
type: source-summary
title: "V7 组牌引擎 v2 (GUA-062 实施)"
sources:
  - docs/guandan-brain/iterations/v7-grouping-v2-gua062.md
tags:
  - v7
  - grouping
  - iteration
status: current
related_gua:
  - GUA-062
  - GUA-063
date: 2026-06-19
---

# V7 组牌引擎 v2 迭代记录

## 概述
GUA-062 完整实施记录，2026-06-18 closed，49 pytest pass。

## 评分公式
五维加权评分：
- 炸弹：0.3
- 手数：0.3
- 回收：0.1
- 灵活：0.1
- 去单化：0.2

## 关键设计

### 静态回收评估 `_score_recovery_static`
组牌阶段评估兜底大牌，避免出牌阶段无牌可救。

### 角色阈值
按队友角色（主攻/超弱/助攻）调整各维度权重。

## 配套 GUA
- GUA-063（组牌→出牌衔接三阶段）已 closed
- GUA-072（规则记牌引擎）P0 open，是下一步

## 关联
- [[gua-062]] — GUA-062 实体页
- [[gua-063]] — GUA-063 实体页
- [[grouping-engine-v2-scoring]] — 评分公式概念页
- [[grouping-to-play-bridge]] — 衔接概念页
