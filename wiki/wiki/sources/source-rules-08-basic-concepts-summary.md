---
type: source-summary
title: "规则摘要：08 基础概念词典"
sources:
  - docs/knowledge/rules/01_basic_rules/08_basic_concepts.md
tags:
  - rules
  - glossary
  - terminology
status: current
related_gua: []
date: 2026-06-18
---

# 规则摘要：08 基础概念词典

## 来源

- 原始文件：`docs/knowledge/rules/01_basic_rules/08_basic_concepts.md`（2154 字符）

## 核心内容

### 嵌套结构术语

| 术语 | 定义 | 结束标志 |
|------|------|----------|
| **圈**（Round） | 一次跟牌循环 | 所有玩家 Pass 一次 |
| **副**（Episode） | 发牌 → 多圈 → 升级 | `episodeOver` 事件 |
| **局**（Game） | 2 打到 A 且 A 双上 | `gameOver` 事件 |
| **比赛一场/一轮** | 编排用语 | ≠ 圈/副 |

⚠️ **口径冲突**：
- 平台 `gameOver` 触发 N **局**（非 N 副）
- 批跑脚本若按副计数会误判（见 concept-round-vs-game-multi-level）

### 角色与方位

- **头游 / 二游 / 三游 / 末游**：本副前 4 名
- **上游 / 下游**：头游 vs 末游
- **对家**：固定对角的两人（同队）
- **队友 / 敌家**：固定

### 名次判定

- **双上**：对家分别获头游 + 二游（最有利）
- **双下**：对家分别获末游 + 三游（最不利，需进贡）
- **平上 / 平下**：对家各获一胜一负

### 关键平台字段

- `victoryNum`：升级数（+3/+2/+1/-1/0）
- `curRank`：本副级牌
- `selfRank` / `oppoRank`：队伍等级
- `gameOver`：局结束标志
- `episodeOver`：副结束标志

## 与其他页面的关系

- 上游：[[source-rules-07-upgrade-rules-summary]]
- 下游：[[source-rules-01-game-introduction-summary]]（闭环）
- 相关概念：concept-round-vs-game-multi-level、[[concept-three-rank-fields]]、[[concept-first-lead-rules]]

## 平台字段引用真源

- 平台协议：`.cursor/rules/guandan-platform-v1006.mdc`
- 详细 JSON 动作见 [[concept-card-type-encoding]]
