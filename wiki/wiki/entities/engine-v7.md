---
type: entity-engine
title: "V7 NN 引擎"
sources:
  - docs/guandan-brain/v7-win-rate-history.md
  - docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md
  - docs/guandan-brain/掼蛋AI技术路径重校-V系列方法论反思.md
tags:
  - engine
  - nn
  - v7-dev
status: current
related_gua:
  - GUA-022
  - GUA-061
  - GUA-064
  - GUA-091
date: 2026-07-01
---

# V7 NN 引擎

## 基本信息

- **分支**：`v7-dev`
- **客户端**：`yf1_v7` / `yf2_v7`
- **核心模块**：
  - `ultimate_win_rate_engine_v7.py`
  - `engine_v7.py` / `v7_guards.py`
- **认知架构**：Guard 规则 + NN 策略选择 + Heuristic 回退（混合架构）

## 当前状态（截至 2026-07-01）

| 维度 | 数据 |
|------|------|
| 累计局数 | 138 |
| 累计胜局 | 1 |
| 队胜率 | 0.7% |
| 副胜率峰值 | 25.5%（GUA-065 队友识别） |
| 副胜率谷值 | 2.4%（GUA-071） |
| 硬门槛 | ≥30%（[[gua-039b]]） |

## 已训练模型

| 模型 | val_acc | 状态 |
|------|---------|------|
| `bc_model_v2.pth` | 35.19% | 已弃用 |
| `bc_model_v3.pth` | 80.88% | 当前；存在 [[bc-argmax-collapse]] |
| GLM4-9B-Chat-mix | — | 竞品（9B 参数） |

## 决策链路组件

1. **MemoryTracker** — decide 入口 ①b 记牌
2. **_heuristic_select** — 4 优先级启发式（NN 失败时回退）
3. **_group_consistency_filter** — R16 组牌一致性
4. **_stage_mid_dispatch** — [[gua-091]] 中局入口调度

## 关键缺陷

- [[gua-064]] — BC argmax collapse（NN 退化为随机选择器）
- [[gua-091]] — stage_2 中局入口
- [[gua-097]] — baseline 校准

## 未来方向

→ [[three-layer-hybrid-architecture]]（Guard + 记牌 NN + 策略选择器）

## 跨引用

- [[engine-m3]] — 规则引擎对照
- [[v7-nn-engine-migration]] — M3→V7 迁移路径
- [[synthesis-v7-current-state]] — 综合状态
```

---
