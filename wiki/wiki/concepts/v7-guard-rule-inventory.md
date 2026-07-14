---
type: concept
title: "V7 Guard 规则总览（R01-R14）"
sources:
  - docs/guandan-brain/ISSUES.md
  - src/v/nn/guards/v7_guards.py
  - docs/guandan-brain/PRINCIPLES_MAPPING.md
tags:
  - concept
  - v7
  - guard
  - inventory
status: current
related_gua:
  - GUA-065
  - GUA-068
  - GUA-089
date: 2026-06-30
---

# V7 Guard 规则总览（R01-R14）

V7 原生 Guard 规则的完整总览，是 GUA-089 阶段调度的依据。

## 规则表

| 编号 | 名称 | 阶段启用 | 主要职责 |
|------|------|----------|----------|
| R01 | 不用炸弹压单 | 2 | 节省炸弹 |
| R02 | 最小炸弹 | 2 | 选最小损耗 |
| R03 | 被动不 PASS | 2 | 避免无貓 PASS |
| R04 | 单牌 B 不 PASS | 2 | 防守不止 |
| R05 | 队友不炸 | 2 | 保护队友 |
| R06 | 不拆对子结构 | 2 | 结构保护 |
| R07 | 队友让道 | 2 | 让牌权 |
| R08 | 队友剩 1 张送最小单 | 2/3 | 残局送完 |
| R09 | 队友剩 5 张送 | 2 | 中期投喂 |
| R10 | 领出不炸 | 0+1/2 | 防供献炸 |
| R11 | 全局抑制牌节流 | 0+1/2/3 | 避免浪费炸 |
| R12 | 三带二不拆对 | 2 | 三带二保护 |
| R13 | 平台炸弹合法性 | 待实现 | 防御性 |
| R14 | 领出不拆天然牌型 | 0+1/2/3 | 领出保护 |

## 阶段启用（GUA-089）

- **stage_0_1**（21-27 张）：R10 / R11 / R14
- **stage_2**（6-20 张）：R01-R09 除 R13 外 + R10-R12 + R14
- **stage_3**（0-5 张）：R08 / R11 / R14

## 参考

- ISSUES.md 主表完整列表
- `src/v/nn/guards/v7_guards.py` 实现
