---
type: concept
title: "V7 NN 引擎迁移（M3 → V7）"
sources:
  - docs/guandan-brain/handoff/2026-06-04-V7-评审与实施方案就位-Qoder-SDK落地.md
  - docs/analysis/v4v5v6-lessons-2026-06.md
  - docs/analysis/v7-re-eval-2026-06.md
tags:
  - v7
  - migration
  - nn-engine
  - m3-to-v7
status: current
related_gua:
  - GUA-061
date: 2026-06-04
---

# V7 NN 引擎迁移（M3 → V7）

## 核心论点

**V7 是未来方向**：M3 规则引擎已达瓶颈，V7 NN 引擎是突破关键。

## 迁移路径

1. **现状**：M3 决策引擎（规则驱动，已触顶）
2. **过渡**：V4/V5/V6 迭代积累经验（详见 [[v4v5v6-lessons-2026-06-summary]]）
3. **目标**：V7 NN 引擎（神经网络驱动）
4. **工具链**：Qoder SDK（V7 落地的关键工具）

## 关键交付物

- [[2026-06-04-V7-评审与实施方案就位-Qoder-SDK落地-summary]] — 评审与实施方案
- [[v7-re-eval-2026-06-summary]] — V7 重评测
- [[v4v5v6-lessons-2026-06-summary]] — 历史经验复盘

## 验证标准

- **批跑胜率** 必须高于 M3
- **相对 lalala 胜率** 需达到既定 KPI
- 详见 wiki-minimax/concepts/batch-evaluation.md

## 关联实体

- wiki-minimax/entities/engine-m3.md
- wiki/entities/engine-v7.md
- GUA-061（迁移任务追踪）
