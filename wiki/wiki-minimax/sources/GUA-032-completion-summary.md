---
type: source-summary
title: "GUA-032 记牌+算牌（M3）完工记录摘要"
sources:
  - docs/guandan-brain/issues/GUA-032-completion.md
tags:
  - gua-032
  - m3-engine
  - card-counting
  - open
status: current
related_gua:
  - GUA-032
  - GUA-027
  - GUA-028
date: 2026-06-17
---

# GUA-032 记牌 + 算牌（M3）完工记录摘要

## 概览

| 字段 | 值 |
|------|----|
| GUA 编号 | GUA-032 |
| 标题 | 记牌 + 算牌（M3） |
| 类型 | feature |
| 状态 | open |
| 引擎 | M3 |
| 关联原理 | PRINCIPLES_MAPPING.md §14 / §15 / §22 |

## 子项清单

| 子项 | 模块 | 职责 |
|------|------|------|
| MEM-M02 | 记牌 | 扫 `history.send` 维护 `has_bomb` / `max_bomb_rank` |
| CALC-M01 | 算牌 | 排炸推理（依赖 MEM-M02 产出） |
| CALC-M03 | 算牌 | 大顺/小顺在点五/点十外剩 0 时降权 |
| CALC-M02 | 算牌 | 进贡无级牌对手 + `numofnext==1` 触发 `_active` 禁过小单 |

## 关键概念

- **2468 计数法**：`remain_cards_classbynum` 与 `remain_cards` 一致性的派生源
- **记炸 / 排炸**：MEM-M02 / CALC-M01 串联产出对方剩余炸弹上限
- **5/10 关键张降权**：CALC-M03，控制顺子的爆裂风险
- **进贡无级牌**：CALC-M02，进贡者出牌权利与级牌缺失的对手处理

## 关联与边界

- **回归不失败**：GUA-027 / GUA-028 旧决策行为未被破坏
- **可与 P-H01 合并关单**：CALC-M02 实现与 P-H01 迭代节奏一致

## 约束

> GUA-032 明确**不要求队胜率达标**，以 M3 批跑观测为准

## 交叉引用

- [[gua-032]] — 实体页
- [[card-counting-and-calc]] — 记牌算牌体系概念页
- wiki-minimax/entities/engine-m3.md — M3 引擎
