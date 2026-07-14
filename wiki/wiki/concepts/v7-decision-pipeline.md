---
type: concept
title: "V7 决策管线 L0–L8"
sources:
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
  - docs/analysis/archive/level2-root-cause.md
tags:
  - v7
  - decision-pipeline
  - architecture
status: current
related_gua:
  - GUA-075
  - GUA-072
  - GUA-073
  - GUA-067
date: 2026-06-29
---

# V7 决策管线 L0–L8

## 8 层管线（自上而下）

| 层 | 模块 | 责任 |
|----|------|------|
| **L0** | `grouping_engine` / `_basic_classify` | 组牌生成 |
| **L1** | `endgame/` (`EndgamePreprocessor`) | 残局判定 |
| **L2** | `_recommend_play` | 主推荐（含 GUA-075 四场景） |
| **L2'** | `_group_consistency_filter`（GUA-075 命中跳过） | 组牌保护拦截 |
| **L3** | `guards/v7_guards.py` / `_quick_guard_validate` | Guard 规则校验 |
| **L4** | `_get_broken_core_type` / `_action_breaks_core` | 接风/拆核前置过滤 |
| **L5** | `MemoryTracker` / `TrickSequenceTracker` | 接风投喂 |
| **L6** | `_model_decision` | NN（BC v2 / BC v3） |
| **L7** | `_heuristic_select` | Heuristic 兜底（含 GUA-071/079） |
| **L8** | fallback | 兜底 |

## 关键行为

- **first_hit_returns**：L2 命中即返回（不进入下游）
- **L2' 跳过**：GUA-075 命中路径**跳过** `_group_consistency_filter`（曾导致 Q 炸弹被拆，已在 ~268 行修复表面症状）

## 当前性能瓶颈

- **L6 BC argmax collapse**：验证 80% 但实战坍缩到 Single（见 [[bc-argmax-collapse]]）
- **L7 heuristic 兜底过频**：因 L6 输出不可用，频繁落到 L7，导致 BC 模型实际参与决策比例偏低

## 引用

- [[wf-12-decision-trace]]
- [[gua-075]] / [[gua-072]] / [[gua-073]] / [[gua-067]]
- [[bc-argmax-collapse]]
