---
type: source-summary
title: "红桃配运用 (04_common_skills/06)"
sources:
  - docs/knowledge/skills/04_common_skills/06_red_heart_usage.md
tags:
  - skills
  - wild-card
  - red-heart
  - level:核心
status: current
related_gua:
  - GUA-026
  - GUA-029
  - GUA-030
date: 2026-06-18
---

# 红桃配运用 (04_common_skills/06)

## 文档定位

`docs/knowledge/skills/04_common_skills/06_red_heart_usage.md` (2788 chars) — 红桃配（逢人配）使用策略
原则编号：**§十六 红桃配** (PRINCIPLES_MAPPING)

## 核心数据

### 配牌用途统计

| 用途 | 比例 |
|------|------|
| 配炸 | **85%** |
| 补缺 | 12% |
| 5 头炸 | 1% |
| 其他 | 2% |

### 优先级排序

| 优先级 | 牌型 | 占比 |
|--------|------|------|
| P0 | 同花顺 | 28% |
| P1 | 4 头炸 | 51% |
| P2 | 6 头炸冲刺 | 5% |
| P3 | 补缺/连牌 | 16% |

## 强牌增效原则

红桃配（H+curRank）作为万能配牌，使用顺序：
1. **同花顺** — 凑出最大牌型（28%）
2. **4 头炸** — 配炸作为主战力（51%）
3. **6 头炸冲刺** — 残局抢控（5%）
4. **补缺** — 单张/对子变三张/连牌（12%）
5. **5 头炸** — 极端场景（1%）

## 引擎实现

| 引擎 | 实现方式 |
|------|----------|
| M3 | `H+curRank` 红心级牌变量（出牌保护） + `_pick_three_with_two` 协同 |
| V7 | wild card 统一接口：`_detect_straight_flushes` / `_detect_straights` / `_upgrade_bombs_with_wilds` |

## 待澄清点（Tensions）

- V7 wild card 在三个检测函数中"统一为填缺 rank"的行为，**与 M3 的 H+curRank 是否完全等价**需要在 [[gua-029]] / wiki/entities/engine-v7.md 页面记录差异点

## 交叉引用

- [[gua-026]]：三带二主战术中的红配保护
- [[gua-029]]：M3 H+curRank 出牌保护
- [[gua-030]]：原则→引擎映射
- concept-wild-card-strategy：红桃配统一概念页
