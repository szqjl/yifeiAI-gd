---
title: 牌张分配规则
type: rule
category: Rules/Basic
source: .cursor/rules/guandan-knowledge.mdc
platform: 南京邮电大学平台 v1006
version: 2.0
last_updated: 2026-05-29
tags: [规则, 牌张, 基础]
difficulty: 入门
priority: 5
---

# 牌张分配规则

> **真源**：[guandan-knowledge.mdc](../../../../.cursor/rules/guandan-knowledge.mdc) §1.2

## 数量

- **全副牌**：108 张（两副扑克）
- **每位牌手**：27 张
- **无底牌**：108 张全部分配

## 组成

- 普通牌：A、2–9、T(10)、J、Q、K，每种 4 张 × 2 副 = 104 张
- 王牌：大王 `HR`、小王 `SB` 各 2 张 = 4 张

## 发牌

- 按座位逆时针抓牌或发牌，每人 27 张
- 平台 `beginning` 阶段下发 `handCards`

## 相关文档

- [06_game_flow.md](06_game_flow.md)
- [04_card_types_guide.md](04_card_types_guide.md) — 卡牌编码
