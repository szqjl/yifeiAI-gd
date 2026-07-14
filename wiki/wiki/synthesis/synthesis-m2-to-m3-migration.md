---
type: synthesis
title: "M2 → M3 迁移：系列架构缺陷 vs 具体 Bug"
sources:
  - docs/guandan-brain/M2_OPTIMIZATION.md
  - docs/guandan-brain/M3_DIAGNOSIS.md
  - docs/guandan-brain/MOCs/GUA-Index.md
tags:
  - synthesis
  - migration
  - m2
  - m3
  - architecture
status: current
related_gua:
  - GUA-020
  - GUA-027
  - GUA-021
date: 2026-06-18
---

# M2 → M3 迁移：系列架构缺陷 vs 具体 Bug

## 核心论断
M2 的 60% PASS 极端被动与 M3 的连续 PASS×10+ 行为**高度相似**——两者都是"读了场态但没主动进攻路线规划"。这可能不是孤立的 Bug，而是 **M 系列规则引擎的系列架构缺陷**。

## 跨代际对比

| 维度 | M2 | M3 |
|------|----|----|
| 队胜率 | 0% (0/N) | 0 胜（22 副） |
| PASS 比例 | **60%** | 连续 PASS×10+ |
| 主动进攻 | 几乎无 | 几乎无 |
| 拆牌/引诱/送队友 | 不会 | 不会 |
| 场态理解 | 弱 | 强（GUA-027 修复后） |
| 残局两手组合 | 有 Bug | 缺失（BUG2） |

## 共同根因
1. **规则引擎天花板**：硬编码规则难以覆盖"主动进攻路线规划"
2. **缺少队友协作意识**：M2 无、M3 BUG4 也无
3. **炸弹策略空白**：M2 仅 10%、M3 BUG5 消极

## 具体 Bug（必须修的）
- M3 BUG1（下标）、BUG2（残局）、BUG4（协作）、BUG5（炸弹）
- GUA-027 场态重算已修，是**唯一已关闭的关键 bug**

## 迁移学到的教训
- **不能直抄 lalala**：lalala `action.py:1117-1127` 残局两手组合本身含 Bug
- **异常静默是排查大敌**：`yf1_m3.py` 的 `except` 吞日志
- **队胜率口径必须严守**：victoryNum 口径、局≠副

## 走向 V7 的必然性
M 系列规则引擎的天花板已被两次证明（70+ 局 0%、22 副 0 胜）：
- 即使修完 M3 七 Bug，可能仍受限于"规则表达力"
- V7 NN 引擎是**架构层面的跃迁**，不是修补
- 详见 wiki/synthesis/synthesis-v7-current-state.md

## 关联
- 引擎：[[engine-m2]]、wiki-minimax/entities/engine-m3.md、wiki/entities/engine-v7.md
- 源：[[M2_OPTIMIZATION-summary]]、[[M3_DIAGNOSIS-summary]]
- 概念：M2 极端被动根因（待建）
