---
type: concept
title: "V7 三层决策管线"
sources:
  - docs/guandan-brain/ITERATIONS.md
  - docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md
tags:
  - v7
  - architecture
  - guard
  - heuristic
  - pipeline
  - GUA-073
status: current
related_gua:
  - GUA-071
  - GUA-072
  - GUA-073
date: 2026-06-20
---

# V7 三层决策管线架构

V7 引擎决策核心架构：**Layer1 Guard 硬排除 → Layer2 Heuristic 软排序 → Layer3 validate 兜底**。

## 架构图

```
输入: game_state (2048 维)
   ↓
┌─────────────────────────────────┐
│ Layer 1: 15 Guards (硬排除)     │
│ - R01~R15 规则逐条检查          │
│ - 违反规则的 action 被剔除      │
│ - 输出: 候选 action 集          │
└─────────────────────────────────┘
   ↓
┌─────────────────────────────────┐
│ Layer 2: _heuristic_select      │
│ - 8 优先级排序                  │
│ - 软评分（_score_*）            │
│ - 输出: top-K action            │
└─────────────────────────────────┘
   ↓
┌─────────────────────────────────┐
│ Layer 3: validate (兜底)        │
│ - _model_decision (NN fallback) │
│ - 合法性校验                    │
│ - 输出: final action            │
└─────────────────────────────────┘
   ↓
输出: chosen_action
```

## Layer 1: 15 Guards

详见 wiki/concepts/v7-guard-rules.md。

核心 Guard：
- **R10 领出不炸**（GUA-066）
- **R11 全局抑制牌节流**（GUA-068）
- **R12 拆对子出单禁制**（GUA-070）
- **R07/R08/R09 队友保护**（GUA-065）
- **超弱 core 保护**（GUA-069）

## Layer 2: _heuristic_select 8 优先级

1. **PASS**（无牌可出/不出更优）
2. **队友让道**（R07）
3. **队友喂牌**（R08/R09）
4. **牌型最优**（按 _score_power）
5. **灵活性最优**（按 _score_flexibility）
6. **恢复力最优**（按 _score_recovery_static）
7. **组一致性**（按 _group_consistency_filter）
8. **validate fallback**（NN）

## Layer 3: validate

- 合法性校验（牌数、牌型、压制关系）
- NN 兜底（_model_decision）—— **仅在 Layer 1+2 无法决策时启动**
- 超时保护（决策时间 < 100ms）

## 正交架构原则

每次加规则 **不破坏已有规则**——每条 Guard/Heuristic 独立可关停。
配合 **秒级 pytest 反馈**，保证快速迭代。

## 演进时间线

- **2026-06-15**：GUA-073 Guard-Heuristic 管道架构整理（closed）
- **2026-06-17**：GUA-071 heuristic 战略转向（首批跑未达标）
- **2026-06-20**：GUA-072 三引擎 TDD 训练管线立项

## 优劣分析

| 优点 | 缺点 |
|------|------|
| 可解释性强 | 规则维护成本高 |
| 逐条可关停 | 规则间冲突难调试 |
| 兜底 NN 保留 | 副胜率仍依赖规则质量 |
| 决策时间可控 | 难以适应未见局面 |

## 交叉引用

- [[GUA-073]] — 架构整理缺陷条目
- wiki/concepts/v7-guard-rules.md — 15 Guard 全集
- wiki/concepts/heuristic-pivot.md — 战略转向
- wiki/entities/engine-v7.md — V7 引擎整体设计
