---
type: source-summary
title: "GUA-030 完成定义 - 源文档摘要"
sources:
  - docs/guandan-brain/issues/GUA-030-completion.md
tags:
  - source-summary
  - gua-030
  - principles-mapping
  - closed
status: current
related_gua:
  - GUA-030
  - GUA-029
  - GUA-031
date: 2026-06-17
---

# GUA-030 完成定义 - 源文档摘要

## 文档信息

- **来源文件**：`docs/guandan-brain/issues/GUA-030-completion.md`
- **字符数**：575
- **GUA 状态**：**已关单（2026-05-31）**

## 核心内容

GUA-030 是**原则→代码的映射登记表**，不写具体实现代码，只登记原则 ID、对应源文件、归属引擎。

## 登记的原则体系

| 层级 | 原则 ID | 含义 |
|------|---------|------|
| 基础原则 | **P-C** | 核心原则 |
| 进阶 | **P-J** | 进阶技巧 |
| 牌型 | **P-G** | 牌型相关 |
| 传牌 | **P-F** | 传牌策略 |
| 头游 | **P-H** | 头游策略 |
| 战略层 | **S-PR** | 战略原则 |
| 战略层 | **S-ST** | 战略态势 |
| 战略层 | **S-BS** | 战略基本盘 |
| 残局 | **TT-P10** | 两三带相关 |

## 原则文件来源

- `01_bomb_techniques.md`
- `PRINCIPLES_MAPPING.md`
- `01_passing_skills.md`
- `07_two_trips_skills.md`
- `01_basic_principles.md`
- `02_strategy_overview.md`
- `03_basic_strategy.md`
- `guandan-knowledge.mdc`
- `06_game_flow.md`

## 归属引擎

- **M3**（当前实现）
- **M1**（历史引擎）
- **V5+**（后续挂接）

## 关键澄清

- GUA-030 关单**不阻塞** M3/V 引擎的实现
- 与 GUA-029（GUA-029 写 M3 炸弹执行）、GUA-031（GUA-031 写传牌 guard）**职责正交**
- 实现进度需另建 [[principles-mapping]] 概念页跟踪

## 关联实体

- [[gua-030]] — 完整 GUA 条目
- [[principles-mapping]] — 原则映射体系概念页
- [[gua-029]] — 炸弹执行规则
- [[gua-031]] — 传牌 guard
