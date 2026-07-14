---
type: source-summary
title: "规则摘要：05 发牌与牌数"
sources:
  - docs/knowledge/rules/01_basic_rules/05_card_distribution.md
tags:
  - rules
  - card-distribution
status: current
related_gua: []
date: 2026-06-18
---

# 规则摘要：05 发牌与牌数

## 来源

- 原始文件：`docs/knowledge/rules/01_basic_rules/05_card_distribution.md`（627 字符）

## 核心内容

### 牌数规格

- **总牌数**：108 张（两副标准扑克合用，每副 54 张）
- **每手牌数**：27 张（108 ÷ 4 = 27）
- **底牌**：8 张（剩余 108 - 27×4 = 8，作为进贡/底牌池）

### 牌面编码

- **数字牌**：2-10（10 张）
- **字母牌**：J / Q / K / A（4 张）
- **大小王**：大王 B / 小王 R（每副各 2 张，共 4 张）
- **花色**：H（红桃）/ S（黑桃）/ D（方块）/ C（梅花）

### 逢人配机制

- 标识：`H+curRank`（红桃 + 当前级牌）
- 作用：可与任意牌组成合法牌型
- 约束：不得与王组牌

## 与其他页面的关系

- 上游：[[source-rules-04-card-types-guide-summary]]
- 下游：[[source-rules-06-game-flow-summary]]
- 相关概念：[[concept-card-type-encoding]]
