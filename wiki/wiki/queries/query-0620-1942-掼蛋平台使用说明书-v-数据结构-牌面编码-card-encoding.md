---
type: query-answer
title: "掼蛋平台使用说明书 v1006 数据结构 牌面编码 card encoding"
date: 2026-06-20
sources:
  - concepts/concept-card-type-encoding.md
  - entities/module-hand-card-organizer.md
  - sources/source-rules-04-card-types-guide-summary.md
  - concepts/guandan-platform-protocol.md
  - entities/module-grouping-engine.md
  - concepts/card-interactions.md
  - entities/gua-030.md
  - sources/source-rules-05-card-distribution-summary.md
  - concepts/card-language.md
  - concepts/v1006-platform-params.md
---

# 掼蛋平台使用说明书 v1006 数据结构 牌面编码 card encoding

# 掼蛋平台 v1006 牌面编码 (Card Encoding)

## 编码规则

单张牌的编码格式：**花色字符 + 点数字符**，长度固定为 2 位。

| 字符 | 含义 |
|------|------|
| `H` | 红桃（Hearts） |
| `S` | 黑桃（Spades） |
| `D` | 方块（Diamonds） |
| `C` | 梅花（Clubs） |
| `B` | 大王（Big Joker） |
| `R` | 小王（Red Joker） |
| `2`-`10,J,Q,K,A` | 牌面点数 |

## 编码示例

| 编码 | 含义 |
|------|------|
| `HA` | 红桃 A |
| `S7` | 黑桃 7 |
| `D10` | 方块 10 |
| `CJ` | 梅花 J |
| `HR` | 红心小王 |
| `SB` | 黑桃大王 |
| `H2` | 红桃 2（普通牌） |
| `H7` | 红桃 7（当 curRank=7 时即"逢人配"） |

## 关键约束

1. **逢人配**：`H+curRank` 是万能牌（如红桃+当前级牌=7 时，`H7` 可与任意牌组牌），但**不得与王组牌** [{1}][{8}]
2. **王编码**：王无花色概念，统一用 `B`（大王）/ `R`（小王）；**4 张王 = 2 大王(B) + 2 小王(R)** [{1}]
3. **王炸识别**：王炸在出牌 JSON 中是 `["Bomb", "R", ["HR","HR","SB","SB"]]` —— type=Bomb, rank="R"（无级牌）[{1}][{3}]
4. **点数顺序**：`2 < 3 < ... < 10 < J < Q < K < A`（A 最大）

## 在 JSON 协议中的位置

牌面编码出现在 3 元组 `[type, rank, cards]` 的 `cards` 字段中，例如 [{1}][{3}]：

```json
["Pair",   "K", ["SK","DK"]]           // 黑桃K + 方块K
["Straight","R",["H3","S4","D5","C6","S7"]]  // 5-6-7-8-9 顺子
["Bomb",   "9", ["H9","S9","D9","C9"]] // 4 张 9 炸弹
["Bomb",   "R", ["HR","HR","SB","SB"]] // 王炸（rank="R" 无级牌）
```

## 完整编码对应表

```
┌─────────┬──────────────────────────────────────┐
│ 花色    │ H(红桃) S(黑桃) D(方块) C(梅花)       │
│ 大小王  │ B(大王) R(小王)                       │
│ 点数    │ 2-10, J, Q, K, A                      │
│ 逢人配  │ H + 当前级牌 (如 H7 表示 curRank=7)    │
└─────────┴──────────────────────────────────────┘
```

## 关联参考

- [{1}] 牌型 JSON 编码（含王炸特殊性、逢人配约束）
- [{3}] 牌型手册源摘要（11 种合法牌型）
- [{8}] 发牌与牌数源摘要（108 张总数、27 张/手、底牌 8 张）
- [{4}] v1006 平台协议（actIndex 回传、PASS 独立项）
