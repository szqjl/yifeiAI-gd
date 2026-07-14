---
type: concept
title: "M3 引擎历史债务"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/analysis/archive/2026-06-18-gua062-batch-eval.md
tags:
  - m3
  - debt
  - historical
status: current
related_gua:
  - GUA-027
  - GUA-060
  - GUA-061
date: 2026-06-28
---

# M3 引擎历史债务

## M3 的价值

- vs lalala ~70% 局胜（135+ 局累计 96+ 胜）
- 作为 V7 追赶的基准
- 决策管线稳定（guard R-Gxxx 校验）

## 决策管线差异

| 维度 | M3 | V7 |
|------|----|----|
| 主入口 | `m3_decision_engine.decide` | `ultimate_win_rate_engine_v7.decide` |
| 组牌 | `grouping_engine` | `grouping_engine_v2` (multiset) |
| 序列追踪 | `TrickSequenceTracker` | `MemoryTracker` / `_belief` |
| Guard | R-Gxxx | R-Gxxx（相同规约） |
| NN | 无 | `_model_decision` (L6) |

## 已知债务（GUA）

| GUA | 描述 | 状态 |
|-----|------|------|
| GUA-027 | 历史规则缺口 | 修复中 |
| GUA-060 | 边界 case | closed |
| GUA-061 | 历史债务汇总 | 持续跟踪 |
| GUA-065 ~ GUA-070 | M3 子模块债务 | mixed |
| GUA-067 | TrickSequenceTracker 边界 | 观察 |

## M3 vs V7 战略定位

- **M3**：当前可用版本，lalala 战主力
- **V7**：未来方向，但当前不可用（[[v7-current-state]]）
- **M3 债务**：在新 GUA 编号下持续跟踪，但优先级低于 V7 主矛盾

## 关联

- [[engine-m3]] — M3 引擎实体
- [[engine-v7]] — V7 引擎实体
- [[v7-current-state]] — V7 当前状态
- [[decision-pipeline-v7]] — V7 决策管线
