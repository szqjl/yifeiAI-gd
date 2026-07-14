---
type: source-summary
title: "顺子技巧 (04_common_skills/08)"
sources:
  - docs/knowledge/skills/04_common_skills/08_straight_skills.md
tags:
  - skills
  - straight
  - formation
  - level:核心
status: current
related_gua:
  - GUA-030
  - GUA-031
  - GUA-032
date: 2026-06-18
---

# 顺子技巧 (04_common_skills/08)

## 文档定位

`docs/knowledge/skills/04_common_skills/08_straight_skills.md` (6318 chars) — 顺子（Straight）运用技巧
原则编号：**§十八 顺子** (PRINCIPLES_MAPPING)

## 核心策略

### 5/10 法则（CALC-M03）
- 顺子长度 ≥ 5 张为有效组牌
- 10 张法则：手牌 ≥ 10 张时优先尝试组 5+ 张顺子

### 三大原则

| 原则 | 含义 |
|------|------|
| **组顺生两单没眼光** | 为组顺子而拆散两单，破坏牌型多样性 |
| **小顺往前凑大顺殿后** | 优先出小顺保留大顺作为终局牌 |
| **谁打谁收** | 自己组的顺子自己收尾，避免给对手牌权 |

### 相生相克
- 顺子克单牌/对子
- 被炸弹/钢板克制
- 出顺时机需考虑对手可能的反制牌型

## 引擎实现

| 引擎 | 模块 | 状态 |
|------|------|------|
| M3 | `_Straight` (顺子检测) | ✅ 已实现 |
| M3 | `_active` / `is_inStraight` | ✅ 已实现 |
| V5+ | 牌力分时优化 | 🔄 进行中 |
| V7 | `_detect_straights` (顺子+wild) | 🔄 NN 引擎迁移中 |

## 慎始发原则（P-H05）

- P-H05 慎始发 = 首引不轻易出大顺
- **归属问题待澄清**：§十八 称 P-H05 属于既有 P0/GUA-032，但 §十九 三连对称"P-H05 可扩"
- 见 [[concept-engine-mapping-principles]] 的 tensions 区

## 牌型概率

- 顺子出现概率：**4.11%**（一手 9.8 张基准）
- 属于中高频牌型

## 交叉引用

- [[gua-030]]：原则→引擎映射
- [[gua-031]]：送顺/不接队友
- [[gua-032]]：P-H05 + CALC-M03 归属
- concept-tempo-and-feed：谁打谁收/相生相克
- [[concept-card-type-probability]]：牌型概率分布
