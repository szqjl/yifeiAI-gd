---
type: concept
title: "StageRouter 强制非 PASS 兜底机制"
sources:
  - docs/guandan-brain/reviews/M1_vs_lalala_TECHNIQUE_cursor.md
tags:
  - m1
  - stage-router
  - fallback
  - over-prediction
status: current
related_gua:
  - GUA-061
date: 2026-06-18
---

# StageRouter 强制非 PASS 兜底机制

## 机制定义

M1 决策引擎中 `stage_router.py` 的**兜底逻辑**：当所有合法动作评估后无可出牌时，强制选择一个非 PASS 动作以避免直接弃权。

## 设计初衷

- **避免弃权失控**：防止连续 PASS 导致队友误判
- **保持出牌节奏**：宁可出小牌也不全 PASS

## 问题诊断

### 与 GUA-061 的关系
Cursor 评审认为此机制与 GUA-061（m1 over-prediction，P0 缺陷）**可能是同一根因的不同表述**：
- GUA-061 表象：M1 频繁出过大的牌
- 兜底机制根因：宁可乱出也不 PASS，导致过牌选择偏离最优

### 实际表现
1. **过牌过大**：在末游位仍出炸弹等高代价牌型
2. **忽略队友**：未考虑队友是否需要过牌
3. **战术失衡**：强制出牌导致手牌结构破坏

## 修复方向

### 候选方案 A：删除兜底
- 完全允许 PASS
- **风险**：可能出现连续 PASS 导致送局

### 候选方案 B：智能兜底
- 兜底时优先选择最小代价牌型
- 关联：M1 中已有的 `choose_bomb 最小代价炸弹选择` 逻辑可复用

### 候选方案 C：学习 lalala
- 让模型学会「合理 PASS」语义
- V7 路线：通过 PPO 奖励信号让网络学会 PASS 决策

## 关联页面

- [[engine-m1]]
- [[GUA-061]]
- [[m1-vs-lalala-paradigm]]
