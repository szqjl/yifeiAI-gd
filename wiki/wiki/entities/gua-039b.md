---
type: entity-gua
title: "GUA-039b 自对弈路线"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/v7-win-rate-history.md
tags:
  - p0
  - open
  - self-play
  - long-term
status: current
related_gua:
  - GUA-039a
  - GUA-060
  - GUA-063
date: 2026-06-18
---

# GUA-039b 自对弈路线（PPO/DMC）

## 基本信息
- **编号**：GUA-039b
- **状态**：P0 open
- **路线**：PPO / DMC 自对弈
- **优先级**：长期

## 目标
绕开 BC argmax collapse，通过自对弈产生**超出人类专家分布**的策略。

## 验收标准
- **30 局 ≥ 30%** 队胜率
- 当前累计 **1/54 = 1.9%**，远低于门槛

## 与 GUA-063 的关系
- GUA-063 是**短期可落地的硬约束方案**
- GUA-039b 是**长期根本性突破**
- 两者并行：GUA-063 提升近期胜率，GUA-039b 解决根本问题

## 关联页面
- [[gua-039a]]：短中期子路线
- [[gua-060]]：BC 路线终止（催生本 GUA）
- [[gua-063]]：并行短期方案
- [[concept-batch-evaluation]]：胜率验证
