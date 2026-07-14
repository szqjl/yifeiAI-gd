---
type: source-summary
title: "M3 三带二与炸弹规则摘要"
sources:
  - docs/guandan-brain/iterations/m3-strategy-gua026-029.md
tags:
  - m3
  - strategy
  - bomb-rules
  - three-with-two
status: current
related_gua:
  - GUA-026
  - GUA-029
date: 2026-06-18
---

# M3 三带二与炸弹规则摘要

## 概览

M3 策略规则包落地，2 条 GUA 关键结论。

## 关键 KPI

| GUA | 主题 | 批跑成绩 | 状态 |
|-----|------|---------|------|
| GUA-026 | 三带二拆牌/炸弹保护 | **11/12（91.7%）** | closed |
| GUA-029 | 炸弹可执行规则包 R1–R6 | 全过 | closed |

## 关键机制

- `_uses_level_rank_cards` / `_three_with_two_protect_ok`：三带二拆牌保护
- 炸弹 R1–R6 规则包：频次限制、点控时机、配合信号
- `resolve_effective_greater` + `TrickSequenceTracker`

## 演进叙事

`m3-integration-gua024-028 → m3-strategy-gua026-029 → m3-guards-gua031-036`

## 关联

- 三带二拆牌保护
- M3 Guard 设计模式
