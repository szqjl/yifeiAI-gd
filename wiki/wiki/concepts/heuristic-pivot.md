---
type: concept
title: "Heuristic 战略转向 (GUA-071)"
sources:
  - docs/guandan-brain/v7-win-rate-history.md
  - docs/guandan-brain/ITERATIONS.md
tags:
  - v7
  - pivot
  - heuristic
  - GUA-071
  - strategic-shift
status: current
related_gua:
  - GUA-064
  - GUA-071
  - GUA-073
date: 2026-06-20
---

# GUA-071 Heuristic 战略转向

2026-06-17 立项，V7 引擎的 **重大战略转向**：用 `_heuristic_select` 替代 NN argmax。

## 背景

- GUA-064 BC argmax collapse 确证，BC teacher forcing 路线已死
- 累计 18 条批跑记录队胜率 **1/105 = 1.0%**
- 副胜率从 GUA-065 峰值 **25.5%** 跌至 **2.4%**（首批跑严重未达标）

## 转向内容

**Before**（NN 路线）：
```
state → BC Model → argmax → action
```

**After**（Heuristic 路线）：
```
state → 15 Guards (硬排除) → _heuristic_select (软排序) → validate (兜底) → action
```

详见 三层管线架构。

## 关键模块

| 模块 | 职责 |
|------|------|
| `v7_guards.py` | 15 条 Guard 规则（R01-R15） |
| `_heuristic_select` | 软排序（8 优先级） |
| `_model_decision` | validate 兜底（NN 仅作 fallback） |
| `m3_decision_engine.py` | 复用 M3 决策逻辑 |

## 首批跑结果（2026-06-17）

- 副胜率：**2.4%**（vs GUA-065 峰值 25.5%）
- 队胜率：0/9
- **严重未达标**

## 诊断

转向后 KPI 暴跌的可能原因：
1. **过度约束**：15 条 Guard 同时启用可能过度限制出牌选择
2. **Heuristic 优先级不当**：8 优先级排序可能与实战最优不符
3. **失去 NN 兜底**：validate 模块使用频率不足
4. **特征缺失**：heuristic 依赖的人工特征可能漏掉关键信号

## 后续行动

- GUA-072 三引擎 TDD 管线立项（详见 [[three-engine-tdd-pipeline]]）
- GUA-073 Guard-Heuristic 管道架构整理
- 逐条 Guard A/B 测试，识别过激约束

## 教训

- 战略转向不能"一刀切"——需保留 NN 兜底路径
- Heuristic 设计需要 **逐条回归测试**，避免引入新的"过度约束"
- 重大架构变更必须分阶段灰度，不能一次全量切换

## 交叉引用

- [[GUA-071]] — 战略转向缺陷条目
- wiki/concepts/bc-argmax-collapse.md — 转向触发原因
- wiki/concepts/three-layer-pipeline.md — 新架构
- [[GUA-073]] — 管道架构整理
- wiki/concepts/v7-guard-rules.md — 15 Guard 全集
