---
type: source-summary
title: "单张技巧摘要"
sources:
  - docs/knowledge/skills/04_common_skills/01_single_card_skills.md
tags:
  - skills
  - single-card
  - pseudo-code
status: current
related_gua:
  - GUA-031
  - GUA-062
date: 2026-06-18
---

# 单张技巧摘要

> 来源：docs/knowledge/skills/04_common_skills/01_single_card_skills.md

## 核心策略

**先单张 → 后对子 → 然后三二和顺子**

## 单张数量阈值判定（GUA-062 候选）

| 单张数 | 占比 | 判定 |
|--------|------|------|
| 0-2 张 | 0-7% | 牌型整齐 |
| 2-4 张 | 7-15% | 正常 |
| 5-6 张 | 19-22% | 单张较多，需优先处理 |
| >7 张 | >26% | 单张太多，组牌有问题 |

## 子技巧集

- **顺上家**：上家单牌对自己有利
- **控下家**：首用 Q，次用 JK，卡下家小单
- **让对家**：不要越级打大牌拦对家
- **高/中/低单选择**：根据牌力优势决定
- **卡点出单**：精确送牌给队友过单

## 伪代码（Wiki 首个含代码的 skills 文档）

文档末尾包含：
- `should_play_single()` 函数
- `choose_single_card()` 函数

**可作为其他 skills 文档代码化的模板。**

## 双贡慎单原则（P-H01）

双进贡情况下，对单张的选择要特别谨慎。

## 引擎关联

- **M3**：可实施单张阈值判定（GUA-062 P0 候选）
- **V5+ / V7**：需要完整单张选择策略
- 关联 `PRINCIPLES_MAPPING.md §十一`

## 关联页面

- wiki/concepts/single-card-quantitative.md — 单张数量阈值
- [[gua-062]] — 单张数量阈值判定（拟）

---
