---
type: source-summary
title: "V7-dev 换机交接摘要"
sources:
  - docs/guandan-brain/handoff/2026-06-16-v7-dev.md
tags:
  - v7
  - handoff
  - nn
  - source
status: current
related_gua:
  - GUA-037a
  - GUA-037b
  - GUA-038
  - GUA-050
  - GUA-051
  - GUA-052
date: 2026-06-17
---

# V7-dev 换机交接摘要（2026-06-16）

## 来源概述

`docs/guandan-brain/handoff/2026-06-16-v7-dev.md`（3516 字符）记录 V7 实验线在换机节点的工作交接，明确当前已实现项、待办 GUA 与下轮优先级。

## V7 引擎状态

- **类型**：NN 引擎（`v-nn-v7` → `ultimate_win_rate_engine_v7`）
- **模型**：188 维 BC 模型（Static 124 + Dynamic 64）
- **val_acc**：88.44%
- **队胜率**：1/21（**4.8%**）
- **状态**：实验线，**不进入 M3 主交付 KPI**

## 已实现项

### GUA-050 局面信念向量 8 维（2026-06-16）

位置 **188-195**，特征利用率 **38.3%**。8 维定义见 [[belief-vector]]。

```python
# static_features.py
BELIEF_DIM = 8
extract_state_belief()  # 拼接至 188-195
```

### GUA-037a / GUA-037b 特征切片

- **GUA-037a**：Static 特征 0-123（124 维）
- **GUA-037b**：Dynamic LSTM 特征 124-187（64 维）

## 开放 GUA 与下轮优先级

| 优先级 | GUA | 描述 | 状态 |
|--------|------|------|------|
| **#1** | GUA-051 | 稠密 Reward 信号 9 种 | open, P1 |
| **#2** | GUA-052 | 108 张牌全量追踪 + 排除法推断 | open, P1 |
| **#3** | GUA-038 | BC 模型重训（用 M3 胜利局 game_records） | open, next |
| P2 | GUA-039a | 自对弈 | open |
| P2 | GUA-039b | PPO | open |
| P1 | GUA-040 | 模型权重管理（COS） | open |
| P2 | GUA-053 | 对手池多样性 | open |

## 待建模块

- `memory_tracker.py`（GUA-052）
- `reward.py`（GUA-051）

## 关键结论

1. V7 仍在实验线，队胜率 4.8% 远低于 M3 70-80%，**不混用 KPI**
2. GUA-050 已实施但 belief 信号在 BC 模型中未激活，**待 GUA-038 重训**
3. 下轮 priority #1 是 GUA-051（reward），#2 是 GUA-052（memory），#3 是 GUA-038（重训）

## 跨引用

- wiki/entities/engine-v7.md — V7 引擎实体页
- [[gua-050]] — 信念向量 GUA
- [[belief-vector]] — 信念向量概念
- wiki/synthesis/synthesis-v7-current-state.md — V7 现状综合
