---
type: concept
title: "情况不明对子先行（对子战略）"
sources:
  - docs/knowledge/skills/01_foundation/02_strategy_overview.md
  - docs/knowledge/skills/01_foundation/01_basic_principles.md
tags:
  - pair
  - opening
  - strategy
  - p1
status: current
related_gua:
  - GUA-030
date: 2026-06-18
---

# 情况不明对子先行

掼蛋**开局战略核心**：当牌局信息不充分时，优先选择**出对子**作为首攻牌型。

## 战略依据

### 数据基础
对子出现概率 **24.77%**，是仅次于单牌（49.55%）的高频牌型。
对手持有对子"压制牌"（更大对子）的概率分布有利于**安全先出**。

### 配合价值
- 对子结构清晰，便于队友判断牌力
- 易于升级（对子可演化连对、钢板等）

## 引擎实施

| 引擎 | 状态 | 说明 |
|------|------|------|
| M3 | ✅ 可硬编码 | 逢五出对等 P1 规则 |
| V5+ | 🔜 待实施 | 情况不明对子先行的完整策略 |

## ⚠️ 分类分歧

- [[source-skills-02-strategy-overview-summary]] 将"逢五出对"归 P1（M3 可硬编码）
- [[source-skills-31-passing-skills-summary]] 将同类条目归 P0（无 M3 实现）
- 需核对 `PRINCIPLES_MAPPING.md` 权威分类

## 关联

- 上位原则：[[concept-guandan-principles-pillars]]（一个中心：争头游）
- 引擎映射：[[concept-engine-mapping-principles]]
- GUA：[[gua-030]]
