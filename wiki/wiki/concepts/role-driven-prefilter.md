---
type: concept
title: "角色驱动前置过滤 (Role-driven Pre-filtering)"
sources:
  - docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md
  - docs/guandan-brain/人类掼蛋决策流程完整分析.md
tags:
  - v7
  - architecture
  - role-driven
  - pre-filter
status: current
related_gua:
  - GUA-063
date: 2026-06-18
---

# 角色驱动前置过滤 (Role-driven Pre-filtering)

## 概念定义
GUA-063 三层架构的 **Phase 2 核心创新**：在 Guard 后、NN 前引入**角色信号**，根据主攻/助攻身份差异化过滤候选动作。

## 与历史方案的对比

| 阶段 | 方案 | 问题 |
|------|------|------|
| 第一阶段 | 电烙铁焊住（100% 硬约束） | 无灵活性，所有动作都被锁死 |
| 第二阶段 | 适当灵活（无判断标准） | 退化为 BC 现状（90% 拆核心） |
| **第三阶段** | **角色驱动偏置** | **主攻 0.9 / 助攻 0.4，差异化** |

## 主攻 vs 助攻行为对比

| 维度 | 主攻（0.9 权重） | 助攻（0.4 权重） |
|------|------------------|------------------|
| 拆核心牌型 | 硬过滤 ❌ | 全放行 ✅ |
| 接应队友 | 软引导 | 硬过滤 ❌ |
| 抢牌权 | 偏置 +0.3 | 偏置 +0.1 |
| 跑牌/送牌 | 允许 | 鼓励 |

## 安全阀机制
- 助攻全放行避免误伤（不让主攻方案误过滤掉合法动作）
- 主攻硬过滤保证不拆核心（确保牌型完整）
- 角色判断错误时，下游 NN 仍可纠正（不致命）

## 实现位置
```
decide() 流程重写：
  hand_state
    → enumerate_groupings()  [一次跑双产出]
      → best_plan → mask
      → all_plans → features (24 维)
    → v7_guards (合法性)
    → role_detector (主攻/助攻)
    → **role_driven_prefilter** ← 本概念
    → strategy_network (NN)
    → action
```

## 关联页面
- [[gua-063]]：本概念的实施载体
- wiki/concepts/three-stage-human-learning.md：三阶段理论基础
- concept-once-run-dual-output：数据流优化
- concept-card-level-grouping-mask：Phase 1 配合
