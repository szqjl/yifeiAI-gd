---
type: entity-module
title: "BombStrategy (P0-④ 主动炸弹控场增强)"
sources:
  - docs/analysis/agent-sessions/p0_complete_summary.md
  - docs/analysis/agent-sessions/P0_IMPLEMENTATION_COMPLETE_20260528.md
tags:
  - m1-engine
  - p0-④
  - bomb
  - v5-v6-reserved
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# BombStrategy (P0-④ 增强)

## 基本信息

- **文件名**：`bomb_strategy.py`（增强）
- **规模**：原模块 +20 行 / 13889 bytes（增强后总规模）
- **所属引擎**：`M1`（未激活） / `V5` / `V6`（预留）
- **状态**：⚠️ 实现但 **M1 未激活**

## 职责

识别炸弹的**最佳使用时机**，主动控场。

## ⚠️ 重要状态说明

**GUA 体系警示**：
- 文档标记 ✅ 实现
- 但 **M1 未激活**
- 是为 **V5/V6 变体预留**
- Wiki 录入需明确这是"**预留**"而非"**完成**"

## 增强内容（+20 行）

| 增强 | 说明 |
|------|------|
| 炸弹时机评估 | 何时炸最赚（抢分/打断对手/帮队友） |
| 多炸协调 | 多枚炸弹的优先级排序 |
| 风险控制 | 避免浪费（炸空/被反炸） |

## 关联

- wiki/concepts/p0-m1-cooperation-improvements.md — P0 改进设计哲学
- [[engine-m1]] — M1 引擎（未激活）
- V5 / V6 引擎（待 V7 NN 引擎迁移时使用）
