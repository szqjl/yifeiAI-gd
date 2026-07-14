---
type: concept
title: "平台牌型 JSON 编码"
sources:
  - docs/knowledge/rules/01_basic_rules/04_card_types_guide.md
  - docs/knowledge/rules/01_basic_rules/05_card_distribution.md
tags:
  - rules
  - encoding
  - json
  - m3-core
status: current
related_gua: []
date: 2026-06-18
---

# 平台牌型 JSON 编码

## 核心定义

掼蛋平台出牌/进贡动作的 JSON 编码格式，由 **3 元组** `[type, rank, cards]` 组成。

## 通用 3 元组结构

```json
["<type>", "<rank>", ["<card1>", "<card2>", ...]]
```

| 字段 | 含义 | 示例 |
|------|------|------|
| `type` | 牌型名 | `"Single"`, `"Pair"`, `"Bomb"` |
| `rank` | 级牌标记 | `"R"`=王炸无级牌, `"2"`-`"A"`=级牌 |
| `cards` | 牌面编码列表 | `["HR", "SB"]` |

## 11 种牌型 JSON 对照

| 牌型 | type | rank 示例 | cards 示例 |
|------|------|-----------|------------|
| 单张 | `Single` | `"A"` | `["HA"]` |
| 对子 | `Pair` | `"K"` | `["SK","DK"]` |
| 三张 | `Triple` | `"5"` | `["S5","D5","C5"]` |
| 三带二 | `Triple+Single` | `"7"` | `["H7","S7","D7","D3","S9"]` |
| 顺子 | `Straight` | `"R"` | `["H3","S4","D5","C6","S7"]` |
| 同花顺 | `Flush Straight` | `"R"` | `["H3","H4","H5","H6","H7"]` |
| 三连对 | `Consecutive Pairs` | `"R"` | `["H3","D3","S4","D4","H5","D5"]` |
| 钢板 | `Plate` | `"R"` | `["H3","D3","S3","S4","D4","C4"]` |
| 炸弹 | `Bomb` | `"9"` | `["H9","S9","D9","C9"]` |
| 天王炸 | `Bomb` | `"R"` | `["HR","HR","SB","SB"]` ⚠️ |
| 星级炸弹 | `Bomb` | `"R"` | `["H3","H4","H5","H6","H7"]` |

## ⚠️ 王炸编码特殊性

王炸（4 张王）虽然 type 是 `Bomb`，但 rank 为 `"R"`（**无级牌标记**）：

```json
["Bomb", "R", ["HR", "HR", "SB", "SB"]]
//   ↑       ↑        ↑ 红桃小王 ×2 + 黑色大王 ×2
```

**注意**：
- 王炸不参与级牌比较
- 王炸 ≠ 同花顺 4 星
- 4 张王 = 2 大王（B） + 2 小王（R）

## 牌面编码

| 字符 | 含义 |
|------|------|
| `H` | 红桃（Hearts） |
| `S` | 黑桃（Spades） |
| `D` | 方块（Diamonds） |
| `C` | 梅花（Clubs） |
| `B` | 大王（Big Joker） |
| `R` | 小王（Red Joker / 红色王牌） |
| `2`-`10,J,Q,K,A` | 牌面点数 |

## 进贡/还贡/抗贡 JSON 动作

```json
{ "act": "Tribute", "from": <seat>, "to": <seat>, "card": "S2" }
{ "act": "Back",    "from": <seat>, "to": <seat>, "card": "D7" }
{ "act": "AntiTribute", "player": <seat> }  // 抗贡
```

## M3 引擎注意事项

1. **统一 3 元组**：所有出牌动作遵循 `[type, rank, cards]`
2. **王炸识别**：type=Bomb + cards 全为 B/R + 张数=4
3. **级牌处理**：rank 字段是级牌点数，不是最大点数
4. **逢人配**：H+curRank 在 cards 中需标记（不得与王组牌）

## 关联页面

- 来源：[[source-rules-04-card-types-guide-summary]]、[[source-rules-05-card-distribution-summary]]
- 概念：[[concept-first-lead-rules]]、concept-round-vs-game-multi-level
- 引擎：wiki-minimax/entities/engine-m3.md
- 平台协议：`.cursor/rules/guandan-platform-v1006.mdc`
