---
type: concept
title: "原则→引擎映射（P0→M3 / P1+→V5+ / 传牌→GUA-031）"
sources:
  - docs/knowledge/skills/01_foundation/01_basic_principles.md
  - docs/knowledge/skills/01_foundation/02_strategy_overview.md
  - docs/knowledge/skills/01_foundation/03_basic_strategy.md
  - docs/knowledge/skills/03_assist_attack/01_passing_skills.md
tags:
  - engine-mapping
  - meta
  - principles
  - m3
  - v5
  - v7
status: current
related_gua:
  - GUA-030
  - GUA-031
date: 2026-06-18
---

# 原则→引擎映射

连接**人类策略原则**与**AI 引擎实现**的元规则集。

## 核心映射规则

| 策略级别 | 落点引擎 | 实施方式 |
|----------|----------|----------|
| **P0**（核心规则） | wiki-minimax/entities/engine-m3.md | 硬编码策略池 |
| **P1**（可编码规则） | wiki-minimax/entities/engine-m3.md | 硬编码（带 guard 逻辑） |
| **P2+**（复杂策略） | V5+ / wiki/entities/engine-v7.md | 神经网络或规则引擎扩展 |

## 分类详解

### P0 → M3
**一个中心**（争头游）、**两个基本点**（判断/记牌）等最核心原则。

### P1 → M3
- 情况不明对子先行
- 逢五出对
- 4 条传牌 guard（基于 `numoffri` / `numofnext`）

### P2+ → V5+ / V7
- 主攻 / 助攻三阶段
- 完整传牌矩阵（2-10 张）
- 残局精细化策略

## 文档口径分歧 ⚠️

| 条目 | 在 02 中归类 | 在 31 中归类 | 建议 |
|------|--------------|--------------|------|
| 逢五出对 | P1（M3 可硬编码） | P0（无 M3 实现） | 核对 `PRINCIPLES_MAPPING.md` |

## 承载 GUA

- [[gua-030]]：原则→引擎映射的**主承载 GUA**
- [[gua-031]]：传牌专项实施跟踪

## 关联概念

- 上游：[[concept-guandan-principles-pillars]]
- 下游（策略点）：
  - [[concept-pair-first-strategy]]
  - [[concept-passing-skills-matrix]]
  - [[concept-card-type-probability]]
- 引擎落点：wiki-minimax/entities/engine-m3.md、V5+、V7

## 维护责任

- 任何原则文档变更 → 必须更新本概念页
- 任何引擎版本变更 → 必须回流检查 P0/P1 边界
