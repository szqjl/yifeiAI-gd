---
type: source-summary
title: "GUA-032 完成定义摘要"
sources:
  - docs/guandan-brain/issues/GUA-032-completion.md
tags:
  - gua
  - m3
  - calculation
  - memory
status: current
related_gua:
  - GUA-032
  - GUA-027
  - GUA-028
  - GUA-029
  - GUA-031
date: 2026-06-17
---

# GUA-032 完成定义摘要

## GUA 元信息

| 字段 | 值 |
|------|-----|
| 编号 | GUA-032 |
| 标题 | 记牌 + 算牌 · M3 |
| 类型 | calculation / memory |
| 状态 | open |
| 范围 | M3 |
| 依赖 | GUA-027、GUA-028、GUA-029、GUA-031（回归测试） |

## 关键条目

- **MEM-M02**：记炸——每 pos 维护 `has_bomb` / `max_bomb_rank`，扫 `history.send`
- **MEM-M03**：（详见原文档）
- **MEM-M04**：（详见原文档）
- **CALC-M01**：排除四炸——某点数外剩 ≤3 张 → 被动不回该点 Bomb
- **CALC-M02**：进贡无级牌——进贡无级牌对手 + `numofnext==1` → `_active` 禁过小单，可合并 P-H01
- **CALC-M03**：5/10 关键张——点十外剩 0 → 降权大顺；点五外剩 0 → 降权小顺

## 关联概念

- 2468 计数法：基础算牌基建，`remain_cards_classbynum` 与 `remain_cards` 一致即可派生
- 记炸（MEM-M02）
- 排除四炸（CALC-M01）
- 进贡无级牌（CALC-M02，可与 P-H01 合并关单）
- 5/10 关键张（CALC-M03）

## 跨 GUA 依赖

- **回归测试依赖**：GUA-027/028/029/031
- **合并机会**：CALC-M02 可与 P-H01 迭代合并关单

## 备注

完整 998 字符完成定义，条目编号完整（M01~M04 / M02-M04），需要进一步细化实现时再展开。
