---
type: concept
title: "牌型概率分布"
sources:
  - docs/knowledge/skills/01_foundation/02_strategy_overview.md
tags:
  - probability
  - card-types
  - data-foundation
status: current
related_gua: []
date: 2026-06-18
---

# 牌型概率分布

掼蛋牌型出现的**统计概率分布**，是策略权重的**数据基础**。

## 完整分布

| 牌型 | 概率 | 备注 |
|------|------|------|
| 单牌 | **49.55%** | 最高频，几乎占一半 |
| 对子 | **24.77%** | 次高频，开局首选 |
| 炸弹 | **5.13%** | 强压制 |
| 三张 | **8.22%** | 中频 |
| 顺子 | **4.11%** | |
| 连对 | **2.05%** | |
| 同花顺 | **2.05%** | |
| 钢板 | **1.02%** | 最低频常规牌型 |

## 平均手数

- **38.3 手 / 局**
- **9.8 手 / 人**

## 战略含义

### M3 策略权重
- 单牌策略权重最高（近 50%）
- 对子次之
- 钢板/同花顺等低频牌型策略优先级最低

### V7 NN 引擎
牌型概率可作为**训练样本分布参考**或**先验特征**输入。

## 编码基础

概率计算基于 [[concept-card-type-encoding]] 定义的 JSON 牌型编码（13 种基础牌型 + 衍生牌型）。

## 数据口径

- **N 局 ≠ N 副**：所有概率统计均按"局"为单位（详见 concept-round-vs-game-multi-level）

## 关联

- 战略入口：[[source-skills-02-strategy-overview-summary]]
- 策略应用：[[concept-pair-first-strategy]]
