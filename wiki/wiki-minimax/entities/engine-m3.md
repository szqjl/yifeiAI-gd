---
type: entity-engine
title: "M3 决策引擎"
sources:
  - docs/guandan-brain/COMMANDER_NOTES.md
tags:
  - engine
  - m3
  - rule-based
  - 4209-lines
status: current
related_gua:
  - GUA-022
  - GUA-014
  - GUA-033
date: 2026-06-17
---

# M3 决策引擎

## 基本信息

| 字段 | 值 |
|------|-----|
| 名称 | M3 决策引擎 |
| 类型 | 硬编码规则引擎 |
| 代码量 | **4209 行**（四核心架构） |
| 状态 | 维护中（瓶颈已现） |
| 分支 | `m-dev` |
| 客户端 | `yf1_m3.py` / `yf2_m3.py` |

## 四核心架构

| 模块 | 职责 |
|------|------|
| `strategy_engine` | 总体策略入口 |
| `phase_handlers` | 各阶段处理（发牌/出牌/结算） |
| `stage_router` | 阶段路由 |
| `rule_based` | 规则匹配核心 |

## 已知缺陷

### GUA-022（已隔离）
- **主题**：`combine_handcards` + `should_protect`
- **结论**：T7/T8/T9 全 0% → **非根因**
- **下一步**：P0 代码改动（choose_bomb/context/combine）

### GUA-014（已完成）
- 拆牌优先级问题，已修复

## 胜率基线

- **历史最差**：「0%(0/88)」COMMANDER_NOTES #5
- **PHASE3 目标**：>90% 队胜率 vs lalala
- **当前状态**：未达目标

## 关联页面
- wiki/entities/engine-v7.md — 下一代 NN 引擎
- [[gua-022]] — 根因隔离
- [[branch-isolation]] — 分支隔离
- wiki-minimax/concepts/batch-evaluation.md — 评测
