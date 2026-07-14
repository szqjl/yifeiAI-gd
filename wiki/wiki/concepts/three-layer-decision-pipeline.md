---
type: concept
title: "三层决策管线（Layer1 Guard / Layer2 Heuristic / Layer3 validate）"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/ITERATIONS.md
tags:
  - architecture
  - pipeline
  - guard
  - heuristic
status: current
related_gua:
  - GUA-073
  - GUA-075
date: 2026-06-21
---

# 三层决策管线

## 架构

```
┌─────────────────────────────────────────┐
│ Layer 1: Guard 硬排除 (v7_guards.py)    │
│   - R01 ~ R15 规则集                     │
│   - 合法动作过滤                         │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ Layer 2: Heuristic 软排序                │
│   - grouping_engine.py                   │
│   - 5 维评分（炸弹0.3/手数0.3/回收0.1/  │
│     灵活0.1/去单化0.2）                  │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ Layer 3: validate 兜底                   │
│   - _quick_guard_validate                │
│   - 确保输出可执行                       │
└─────────────────────────────────────────┘
```

## 双路径变体（[[gua-075]]）

### 路径 A：排除法
`decide() → _group_consistency_filter → Layer1 → Layer2 → Layer3`

### 路径 B：推荐法
`decide() → _recommend_play() → _quick_guard_validate`
- 跳过 `_group_consistency_filter`
- 用于 card_mask 退化场景

## 5 维评分权重

| 维度 | 权重 | 说明 |
|------|------|------|
| 炸弹 | 0.3 | 控炸能力 |
| 手数 | 0.3 | 出牌手数最优 |
| 回收 | 0.1 | 后续轮次可用牌 |
| 灵活 | 0.1 | 应变能力 |
| 去单化 | 0.2 | 减少单只残留 |

## 关联

- [[gua-073]] — 架构整理 GUA
- [[gua-075]] — 双路径改造
- [[v7-guard-architecture]] — R01~R15 规则全表
