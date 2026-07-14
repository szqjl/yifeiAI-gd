---
type: source-summary
title: "三连对技巧 (04_common_skills/09)"
sources:
  - docs/knowledge/skills/04_common_skills/09_three_pair_skills.md
tags:
  - skills
  - three-pair
  - special-formation
  - level:进阶
status: current
related_gua:
  - GUA-030
  - GUA-031
date: 2026-06-18
---

# 三连对技巧 (04_common_skills/09)

## 文档定位

`docs/knowledge/skills/04_common_skills/09_three_pair_skills.md` (3517 chars) — 三连对（ThreePair）运用技巧
原则编号：**§十九 三连对** (PRINCIPLES_MAPPING)

## 核心策略

### 首引不轻易出
- 三连对是高价值牌型（KKK 级）
- 贸然首引可能给对手牌权

### 不接队友木板
- 队友出三连对时不要用更大三连对去接
- 让队友的牌型走完，保留自己的炸弹作为反制

### 可拆可变
- 三连对可拆为：顺子 / 三带二 / 对子互换
- 视手牌结构灵活变换

### 对称原理
- AAABBB 型结构具备对称性
- 残局阶段可作为突袭牌型

### 残局偷袭
- 收官阶段出三连对常能反败为胜
- 对手往往因防炸弹而忽略

## 引擎实现

| 引擎 | 模块 | 状态 |
|------|------|------|
| M3 | `_ThreePair` (三连对检测) | ✅ 已实现 |
| M3 | `rankfour` (牌力评估) | ✅ 已实现 |
| M3 | `R6` (牌力分档) | ✅ 已实现 |

## 同构性

三连对与 §十七 钢板（TwoTrips）**实现路径同构**：
- 同用 `_ThreePair` / `_TwoTrips` 检测
- 同用 `rankfour` / `R6` 分档
- 区别仅在牌型定义（三连对=对子、钢板=三张）

## 牌型概率

- 三连对出现概率：**2.05%**（一手 9.8 张基准）
- 属于低频高价值牌型

## 交叉引用

- [[gua-030]]：原则→引擎映射
- [[gua-031]]：不接队友/送木板
- [[gua-032]]：P-H05 扩展边界
- concept-special-card-formation：特殊牌型同构性
- [[concept-card-type-probability]]：牌型概率分布
