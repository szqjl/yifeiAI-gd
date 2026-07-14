---
type: source-summary
title: "知识库三层架构（Rules/Strategy/Skills）"
sources:
  - docs/knowledge/STRUCTURE.md
tags:
  - knowledge
  - architecture
  - structure
status: current
related_gua:
  - GUA-032
date: 2026-06-17
---

# 知识库三层架构（Rules/Strategy/Skills）

## 文件位置
- 路径：`docs/knowledge/STRUCTURE.md`

## 三层架构概览

```
┌─────────────────────────────────┐
│ Layer 1: Rules（硬编码）         │  → Python 代码中固定
├─────────────────────────────────┤
│ Layer 2: Strategy（内存加载）    │  → 启动时载入内存
├─────────────────────────────────┤
│ Layer 3: Skills（按需查询）      │  → 决策时调用
└─────────────────────────────────┘
```

### Layer 1: Rules（硬编码）
- 内置规则
- 5 条内置规则（基础牌型识别、合法性检查等）

### Layer 2: Strategy（内存加载）
- 策略库（启动时加载到内存）
- 来源：YAML 文件
- 数量：29 条动态规则
  - card_grouping × 7
  - passing_skills × 7
  - card_language × 7
  - card_interactions × 8

### Layer 3: Skills（按需查询）
- 技巧库（按需查询）
- 包含 §二十一/§二十二 等各章节技巧
- 见 `docs/knowledge/skills/`

## 决策流程

```
1. 关键规则检查 (L1)          ← Rules 层
   ↓
2. 候选动作生成 (L1 + L2)     ← Rules + Strategy 层
   ↓
3. 知识增强评分 (L3)          ← Skills 层
   ↓
4. 选出最优动作
```

## ⚠️ 目录不一致警告

STRUCTURE.md 列出的 `strategy/` 目录：
- 01_main_attack
- 02_assist_attack
- 03_common_strategy
- 04_card_grouping
- 05_fire_matching

实际文件位置：
- `docs/knowledge/strategy/01_core_strategies/01_teammate_protection.md`

**说明**：wiki 索引时以**实际文件路径为准**，并在 index.md 上注明"目录结构为参考，以文件实际路径为准"。

## 跨资料引用
- 配套：[[source-knowledge-yaml-dependency-analysis-summary]]
- 实施：GUA-032（推断层/记忆层鲁棒性）

## 紧张点
- **策略库目录不一致**：见 STRUCTURE.md 与实际路径差异
