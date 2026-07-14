---
type: concept
title: "V7 末级 2/A 双峰极化"
sources:
  - docs/guandan-brain/v7-win-rate-history.md
  - docs/guandan-brain/ITERATIONS.md
tags:
  - v7
  - polarization
  - structural-issue
  - end-rank
status: current
related_gua:
  - GUA-062
  - GUA-038
date: 2026-06-18
---

# V7 末级 2/A 双峰极化

## 概念定义

V7 模型在批跑对局中反复出现的**末级分布双峰两极化**现象：游戏末级（接近 2/A 级升档点）时，2 级和 A 级的占比异常集中，形成两个峰。

## 量化证据

### GUA-062 v2 批跑
- 12 局批跑
- 末级 2 级比例显著偏高
- A 级比例次峰

### bc_model_v3 批跑（val_acc 80.88%）
- 12 局批跑
- **末级分布与 GUA-062 v2 几乎一致**
- 2/A 双峰稳定重现

## 结构性结论

> 两次批跑（不同模型、不同评分）末级分布几乎一致 → **这是 V7 模型架构的结构性问题**，单纯换 BC 模型不改变分布。

## 与 V7 卡 2 级的关联

这是 [[concept-v7-card-type-polarization]] 在末级的具体表现：

- V7 模型倾向于"守住" → 保守出牌 → 末级堆 2
- 升 A 失败 → 大量对局在 2 级卡死
- 缺乏主动进手/抢级策略

## 治理含义

- **BC 路线无法解决**：分布稳定 = 架构性问题
- **必须自对弈 RL**：GUA-039b 是唯一出路
- 详见 wiki/synthesis/synthesis-v7-current-state.md
