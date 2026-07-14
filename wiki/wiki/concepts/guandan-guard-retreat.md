---
type: concept
title: "Guard 残局退让机制"
sources:
  - docs/knowledge/skills/07_opening/end position.md
tags:
  - v7
  - endgame
  - guard
  - retreat
status: current
related_gua:
  - GUA-075
date: 2026-06-21
---

# Guard 残局退让机制

## 概念定义

V7 引擎标准 Guard 链（R01-R14）在[[endgame-pipeline|残局管线]]激活时的**退让规则集合**。当残局管线优先级最高时，部分 Guard 需要临时放松阈值或完全失效，以避免与残局决策目标冲突。

## 残局 vs Guard 平等架构的张力

V7 原有架构是 Guard R01-R14 **平等竞争**，每个 Guard 对出牌进行独立评分。残局管线的引入打破了这种平等——残局凌驾于 Guard 之上。

解决方案：**残局激活时 Guard 退让**，不修改 Guard 本身，而是在 [[endgame-pipeline|残局管线]]的 `banned_types` 硬排除层面（方案 A）统一处理。

## 主要退让案例

### R11 抑制炸弹 — 三种退让级别

R11「抑制炸弹」在残局激活时最容易与冲刺/助攻目标冲突，配置开关 `R11_ENDGAME_MODE`：

| 级别 | 行为 | 适用场景 |
|------|------|----------|
| **完全退让**（full_cede） | 不再抑制炸弹 | 冲刺场景，全力出炸 |
| **部分退让**（partial） | 阈值上调但仍抑制 | **当前选择**，平衡风险与机会 |
| **仅节流**（threshold_only） | 仅在张数/段位超过阈值时退让 | 保守场景 |

> 当前为 partial，文档明确"先跑效果、数据说话"，需 [[batch-evaluation]] 验证。

### R08 送队友

Q2 助攻路线下，R08「送队友」可走，但需避开 R11 抑制炸弹——送队友的小牌不应触发炸的抑制。

### R03 被动不 PASS

L2 降级（无炸可出时被动 PASS）可能与 R03「被动不 PASS」冲突。L2 优先级高于 R03。

## 实验性配置

| 开关 | 当前值 | 含义 |
|------|--------|------|
| `R11_ENDGAME_MODE` | partial | R11 退让级别 |
| `GUA075_ENDGAME_WEIGHTED` | False | GUA-075 残局是否加权 |

> `GUA075_ENDGAME_WEIGHTED=False` 的原因：推荐已被 Q1/Q2 消耗，禁止已被一刀切，加权意义不大。

## 关联页面

- [[endgame-pipeline]] — 残局管线主体
- [[module-endgame-preprocessor]] — 实现模块
- [[gua-075]] — GUA-075 残局激活时行为
