---
type: entity-gua
title: "GUA-037a Context 字段对齐"
sources:
  - docs/guandan-brain/V7-实施方案.md
tags:
  - v7
  - context
  - pass-num
status: current
related_gua:
  - GUA-022
date: 2026-06-18
---

# GUA-037a Context 字段对齐

## 基本信息

- **编号**：GUA-037a
- **标题**：context 字段对齐（pass_num 接线）
- **阶段**：Phase 2 特征与状态
- **状态**：进行中

## 内容

修复 `lalala_adapter.py` 中 `pass_num` 字段的接线缺口，确保 V7 特征空间包含本轮过牌计数。

## 工程意义

`pass_num` 是 V7 188 维特征中的关键维度，缺失会导致「上游已经最大、自己出牌必被压」类误判。

## 关联页面

- [[m1-decision-dimension-gap]]
- [[GUA-022]]
- [[v7-implementation-roadmap]]
