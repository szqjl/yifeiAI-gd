---
type: entity-engine
title: "M1 决策引擎"
status: frozen
sources:
  - docs/guandan-brain/iterations/m1-strategy-gua022.md
  - docs/guandan-brain/iterations/m1-pass-gua020-021.md
related_gua:
  - GUA-020
  - GUA-021
  - GUA-022
tags:
  - m1
  - rule-engine
  - frozen
date: 2026-06-18
---

# M1 决策引擎

## 状态

> **frozen / 非交付线**
> KPI 已迁 M3，P0 guard 改至 `m3_decision_engine`

## 关键文件

- `rule_based_decision_engine_m1.py`
- `yf1_m1.py` / `yf2_m1.py`
- `stage_router.py` / `phase_handlers.py`（共用层）
- `intelligent_router.py`

## 已知缺陷

- 0/12 队胜率同机对照（GUA-022）
- 规则引擎能力瓶颈，复杂场景无法突破

## 历史 KPI

- yf1 vs yf2 PASS率：扩样复测 ≈ 一致（GUA-020）
- 问题 PASS：共用层收紧后清零（GUA-021）
- 队胜率：0/12（GUA-022，frozen 原因）

## 关联

- m1-vs-m3-handoff
- M1 frozen 迁 M3 决策路径
- wiki-minimax/entities/engine-m3.md
