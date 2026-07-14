---
type: source-summary
title: "GAME_RECORD_VICTORYNUM_CHECK - 摘要"
sources:
  - docs/fixes/GAME_RECORD_VICTORYNUM_CHECK.md
tags:
  - fix-report
  - game-record
  - validation
status: current
related_gua: []
date: 2026-06-18
---

# GAME_RECORD_VICTORYNUM_CHECK - 摘要

## 概述

增强对局记录中"胜局数"（VictoryNum）字段的校验逻辑。

## 关键主题

- **Bug 现象**：VictoryNum 字段在异常情况下出现非预期值
- **根因**：升级/双升判定逻辑不严谨
- **修复方案**：增加字段范围校验、与升级状态交叉验证
- **影响范围**：胜率统计、KP[^1]I 计算

## 与其他资料的关系

- 与 game-record-save-fix 属于同一系列修复
- 直接影响 wiki-minimax/concepts/batch-evaluation.md 中胜率计算的准确性
- 体现"局 ≠ 副"的口径问题（见 gua-ju-vs-fu 概念）

## 备注

[^1]: KPI 应为 Key Performance Indicator，原文笔误
