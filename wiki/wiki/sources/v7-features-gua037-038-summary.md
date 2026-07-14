---
type: source-summary
title: "V7 特征工程与 BC 训练摘要"
sources:
  - docs/guandan-brain/iterations/v7-features-gua037-038.md
tags:
  - v7
  - features
  - bc
  - training
status: current
related_gua:
  - GUA-037a
  - GUA-037b
  - GUA-038
  - GUA-050
  - GUA-052
date: 2026-06-17
---

# V7 特征工程与 BC 训练摘要

## 范围

GUA-037a / GUA-037b / GUA-038 三条核心特征与训练任务，是 V7 端到端 BC 路线的**第一波尝试**。

## 关键 GUA

### GUA-037a — 静态特征
- **实现**：`static_features.py`（[[module-v7-features]]）
- **维度**：124 维（手牌 + 公共牌 + 局势）

### GUA-037b — 动态特征（LSTM）
- **实现**：`dynamic_features.py`
- **维度**：64 维 LSTM 隐状态（最近 8 步出牌序列）

### GUA-038 — BC 热启动训练
- **实现**：`bc_dataset.py` + `bc_trainer.py`（[[gua-038]] 实体页）
- **目标**：以 M3 胜局日志作为监督信号，warm-start V7 网络
- **关键参数**：action_dim 512 → 2048（爆炸式扩参的起点）

## 关键 KPI

| 模型 | val_acc | 备注 |
|------|---------|------|
| `bc_model_v2_PRE_RETRAIN_20260617.pth` | 35.19% | 基线 |
| `bc_model_v2_GUA060_20260617_36pct.pth` | **36.46%** | GUA-060 关闭时产物 |
| `bc_model_v2.pth` | 35.85% | 当前默认 |

- **归一化熵**：0.489（分布严重坍缩，详见 [[argmax-collapse]]）
- **top1 准确率**：35.75%（与 512 action 上随机 1/512=0.2% 相比看似高，但属于全类别坍缩到同一类）

## 重要教训

- **特征堆叠 ≠ 性能提升**：124→188→220 维扩维未带来 val_acc 突破
- **action_dim 爆炸**：从 512 到 2048 使训练难度倍增，触发 argmax collapse
- **val_acc 锁死 36% 区间**：与 GUA-060 [[argmax-collapse]] 理论一致

## 关联

- [[module-v7-features]]
- [[gua-038]]
- [[gua-060]]
- synthesis-v7-bc-failure-map
