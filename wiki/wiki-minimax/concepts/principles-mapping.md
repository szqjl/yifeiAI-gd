---
type: concept
title: "原则→代码映射体系（P-C/J/G/F/H）"
sources:
  - docs/guandan-brain/issues/GUA-030-completion.md
  - docs/guandan-brain/principles/PRINCIPLES_MAPPING.md
tags:
  - concept
  - principles-mapping
  - methodology
status: current
related_gua:
  - GUA-030
  - GUA-029
  - GUA-031
date: 2026-06-17
---

# 原则→代码映射体系（P-C/J/G/F/H）

## 定义

掼蛋原则文档（`01_bomb_techniques.md`、`01_passing_skills.md` 等）与 M3/M1/V5+ 引擎代码之间的**索引层映射体系**，由 GUA-030 登记。

## 原则 ID 体系

### 基础原则层

| ID | 含义 | 典型源文件 |
|----|------|------------|
| **P-C** | 核心原则 | `01_basic_principles.md`、`guandan-knowledge.mdc` |
| **P-J** | 进阶技巧 | `01_basic_principles.md` |
| **P-G** | 牌型相关 | `01_bomb_techniques.md` |
| **P-F** | 传牌策略 | `01_passing_skills.md` |
| **P-F02** | 传牌子原则 | `01_passing_skills.md` |
| **P-H** | 头游策略 | `01_basic_principles.md` |

### 战略层

| ID | 含义 | 典型源文件 |
|----|------|------------|
| **S-PR** | 战略原则 | `02_strategy_overview.md` |
| **S-ST** | 战略态势 | `02_strategy_overview.md` |
| **S-BS** | 战略基本盘 | `03_basic_strategy.md` |

### 残局/特殊

| ID | 含义 | 典型源文件 |
|----|------|------------|
| **TT-P10** | 两三带相关 | `07_two_trips_skills.md` |
| **PASS-P01** | 送小单 | `01_passing_skills.md` |
| **PASS-P02** | 防送炸 | `01_passing_skills.md` |
| **PASS-P03** | 让道 | `01_passing_skills.md` |
| **PASS-P04** | 逢五喂队友 | `01_passing_skills.md` |

## 归属引擎矩阵

| 原则 ID | M1 | M3 | V5+ |
|---------|----|----|-----|
| P-C | ✓ | ✓ | 待挂接 |
| P-J | ✓ | ✓ | 待挂接 |
| P-G | ✓ | ✓ (GUA-029) | 待挂接 |
| P-F | ✓ | ✓ (GUA-031) | 待挂接 |
| P-F02 | ✓ | ✓ (GUA-031) | 待挂接 |
| P-H | ✓ | ✓ (GUA-029 R6) | 待挂接 |
| S-PR | ✓ | ✓ | 待挂接 |
| S-ST | ✓ | ✓ | 待挂接 |
| S-BS | ✓ | ✓ | 待挂接 |
| TT-P10 | ✓ | ✓ | 待挂接 |
| PASS-P01~P03 | ✓ | ✓ (GUA-031) | 待挂接 |
| PASS-P04 | ✓ | ✓ (GUA-031, flag) | 待挂接 |

## 映射方法

### 1. 原则提取

从 markdown 原则文档中提取可执行规则，赋予 ID：
- 基础原则：P-{字母}
- 战略原则：S-{字母}
- 子原则：父 ID + 数字后缀（P-F02、PASS-P04 等）

### 2. 归属引擎

按实现状态打标：
- M1：历史引擎已实现
- M3：当前主迭代引擎
- V5+：后续挂接

### 3. 实现进度跟踪

本概念页持续更新 M3/V5+ 的实现状态，作为 [[iteration-tracking]] 的子视图。

## 当前实现状态

| GUA | 关联原则 | 状态 | 备注 |
|-----|----------|------|------|
| **GUA-029** | P-G、P-H | P0 完成定义，待实现 | R1–R6 规则包 |
| **GUA-031** | P-F、P-F02、PASS-P01~P04 | P0 完成定义，待实现 | PASS-P04 flag 控制 |
| **GUA-030** | 全量原则 | **closed 2026-05-31** | 登记完成 |

## 后续工作

- V5 引擎挂接时，按本表逐条对齐
- 新增原则时，先在 PRINCIPLES_MAPPING.md 登记，再创建/更新 GUA
- 批跑验证：见 wiki-minimax/concepts/batch-evaluation.md

## 关联页面

- [[gua-030]] — 原则映射登记 GUA
- [[gua-029]] — 炸弹执行
- [[gua-031]] — 传牌 guard
- [[bomb-execution-rules]] — 炸弹可执行规则
- [[
