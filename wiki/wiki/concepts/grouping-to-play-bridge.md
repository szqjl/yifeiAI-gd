---
type: concept
title: "组牌→出牌衔接三阶段"
sources:
  - docs/guandan-brain/ISSUES.md
tags:
  - v7
  - bridging
status: current
related_gua:
  - GUA-063
date: 2026-06-19
---

# 组牌→出牌衔接

## 三阶段

### 阶段 1：card_mask 传递
`GroupingPlan.to_card_mask()` 输出牌级 mask，core 牌型受保护。

### 阶段 2：角色过滤
`_group_consistency_filter` 按角色约束过滤非法组牌。

### 阶段 3：中局重分组
中局阶段允许重新分组（受限于 [[GUA-091]] `_stage_mid_dispatch` 入口）。

## 职责边界
- **组牌阶段**：决定牌型结构（[[GUA-062]] 评分）
- **衔接阶段**：保证牌级 mask 与角色约束一致
- **出牌阶段**：从已确认的 mask 中选择具体出牌

## 关联
- [[gua-063]] — GUA-063 实体
- [[gua-062]] — 上游组牌
- [[gua-091]] — 中局入口
