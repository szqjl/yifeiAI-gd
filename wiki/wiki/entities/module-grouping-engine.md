---
type: entity-module
title: "grouping_engine 组牌引擎 v2"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
  - docs/guandan-brain/v7-win-rate-history.md
tags:
  - module
  - grouping
  - card-type
  - v2
status: current
related_gua:
  - GUA-070
date: 2026-06-29
---

# grouping_engine 组牌引擎 v2

## 身份

- **规模**：v2 共 **1461 行**
- **唯一验收入口**：`check_grouping_engine.py`
- **职责**：将一手牌枚举为所有合法牌型组合，按 4 维加权+6 方案枚举最优

## 核心特性

| 特性 | 描述 |
|------|------|
| **SF_FIRST 全候选枚举** | 先枚举所有同花顺（Straight Flush）候选，再枚举其他牌型 |
| **NO_STRAIGHTS 双变体** | 两套无顺子方案（处理 A→2 包接 ×3） |
| **A→2 包接** | A→2 视作 5 张顺子，×3 重复计数（接顺/接对/接三） |
| **ThreePair 子结构拆分** | 三对拆解（影响 GUA-070 单行胜率） |
| **SteelPlate 子结构拆分** | 钢板（双三）拆解 |
| **4 维加权** | 权重 = (长度, 强度, 灵活性, 控场) |
| **6 方案枚举** | 6 种枚举策略选最优 |

## 关键 GUA

- **GUA-070**：ThreePair/SteelPlate 拆分影响单行胜率（17.7%）

## 链接

- 脚本索引：[[SCRIPT_INDEX-summary]]
- V7 引擎：[[engine-v7]]
- 守卫悖论：[[guard-overlap-puzzle]]
