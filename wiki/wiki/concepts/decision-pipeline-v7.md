---
type: concept
title: "V7 决策管线 L0~L8"
sources:
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
  - docs/analysis/archive/2026-06-18-gua062-batch-eval.md
tags:
  - v7
  - decision-pipeline
  - nn-engine
  - wf-12
status: current
related_gua:
  - GUA-062
  - GUA-075
  - GUA-078
  - GUA-081
date: 2026-06-28
---

# V7 决策管线 L0~L8

## 概述

V7 决策管线（UltimateWinRateEngineV7）采用**先命中先 return** 的分层架构，从 L0 到 L8 共九层。每一层都是一个独立的回退点，一旦命中即返回决策，不再下传。

## 分层表

| 层 | 名称 | 主要模块 | 命中条件 | 失败行为 |
|----|------|----------|----------|----------|
| L0 | 组牌 | grouping_engine / grouping_engine_v2 | 成功生成候选牌型 | 下传 L0b |
| L0b | 信念 | MemoryTracker / `_belief` | 对手手牌信念满足阈值 | 下传 L1 |
| L1 | 残局 | EndgamePreprocessor (Q0~Q3) | 残局管线激活 | 命中即 return |
| L2 | 决策推荐 | `decide` 主入口 | 模型/启发式产出推荐 | 下传 L2′ |
| L2′ | 组牌保护 | `_group_consistency_filter` | 推荐与组牌一致 | 否则回退 L4 |
| L3 | Guard | `_quick_guard_validate` | guard R-Gxxx 通过 | 下传 L4 |
| L4 | 前置过滤 | `filter_action_list` | 候选经合法性与牌型过滤 | 下传 L5 |
| L5 | 接风判定 | v7_guards.py 接风逻辑 | 我方接风 | 下传 L6 |
| L6 | NN 模型 | `_model_decision` | 模型推理成功 | 下传 L7 |
| L7 | 启发式 | `_heuristic_select` | 启发式产出 | 下传 L8 |
| L8 | 兜底 | `_recommend_play` | 必出兜底 | — |

## 关键洞察

### L1 残局激活时常直接 return
EndgamePreprocessor 在 Q0~Q3 任一阶段激活时直接 return，GUA-078 涉及此层。

### L2′ 保护拦截是设计行为
当推荐命中但被 `_group_consistency_filter` 拦截时，会落入回退路径。这是**设计行为**而非 bug——与 GUA-075（card_mask Dict 键冲突）的修复行为需明确区分。

### L6 vs L7 的塌缩
GUA-062 批跑显示卡2级 Single 决策占 80.5%，即 L7 启发式塌缩回 Single 出牌。这与 BC argmax collapse 共同构成 V7 当前主矛盾。

### L8 兜底缺口
GUA-081 指出 ThreeWithTwo/8 等同型 fallback 缺失，落在 L8 兜底层。

## 与 M3 决策管线的差异

| 维度 | V7 | M3 |
|------|----|----|
| 主入口 | ultimate_win_rate_engine_v7.decide | m3_decision_engine.decide |
| 组牌 | grouping_engine_v2 (multiset) | grouping_engine (原版) |
| 信念 | MemoryTracker + `_belief` | TrickSequenceTracker |
| Guard | `_quick_guard_validate` (R-Gxxx) | guard R-Gxxx (相同规约) |
| NN | `_model_decision` (L6) | 无 NN |
| 残局 | EndgamePreprocessor (L1) | 内联分支 |

## 相关页面

- [[wf-12-decision-trace]] — 本管线的真源工作流
- [[engine-v7]] — V7 引擎整体
- [[engine-m3]] — M3 对比基准
- [[cardmask-multiset-fix]] — L2 组牌层修复
- [[decision-trace-taxonomy]] — 8 类根因标签

## 关联 GUA

- GUA-062：批跑 0/9 局胜、卡2级 80.5% Single 决策（暴露 L7 塌缩）
- GUA-075：card_mask Dict 键冲突已修（L0/L2 组牌层）
- GUA-078：残局管线 L1 行为
- GUA-081：L8 兜底缺 ThreeWithTwo/8 fallback
