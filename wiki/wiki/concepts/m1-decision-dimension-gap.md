---
type: concept
title: "M1 决策维度缺口清单"
sources:
  - docs/guandan-brain/reviews/M1_vs_lalala_TECHNIQUE_cursor.md
tags:
  - m1
  - context
  - feature-gap
status: current
related_gua:
  - GUA-037a
  - GUA-022
date: 2026-06-18
---

# M1 决策维度缺口清单

## 概念定义

M1 决策引擎决策时**缺失的关键上下文字段**，是 M1 胜率持续 0% 的核心根因之一。

## 缺口字段

| 字段 | 含义 | 影响 |
|------|------|------|
| `pass_num` | 本轮过牌计数 | 无法判断本轮是否已被压制 |
| `numofnext` | 下游玩家剩余牌数 | 无法评估送牌风险 |
| `numofgreaterPos` | 上游可压制位数量 | 无法判断出牌安全性 |

## 接线现状

- **lalala_adapter.py**：lalala → M1 适配层，存在 `pass_num` 接线缺口
- **context 字段对齐**：GUA-037a 修复中

## 与决策质量的关系

### 缺 `pass_num`
- 无法判断「上游已经最大，自己出牌必被压」场景
- 导致 M1 在被压制场景仍出牌（GUA-061 over-prediction 表象）

### 缺 `numofnext`
- 无法判断「下游剩余 1 张牌，送牌风险极高」场景
- 导致 M1 给下游队友送牌

### 缺 `numofgreaterPos`
- 无法判断「上游还有 2 个玩家能压我」场景
- 导致 M1 顶张选择不当

## V7 的对应处理

V7 特征工程将上述字段全部纳入 **188 维特征空间**（124 静态 + 64 动态 LSTM），从架构上消除维度缺口。

## 关联页面

- [[engine-m1]]
- wiki/entities/engine-v7.md
- [[GUA-037a]]
- [[stagerouter-forced-nonpass-fallback]]
