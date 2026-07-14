---
type: entity-module
title: "BC 训练器模块（V7，已判定路径失败）"
sources:
  - docs/guandan-brain/MOCs/V7-Development.md
tags:
  - module
  - v7
  - bc
  - dead-end
status: current
related_gua:
  - GUA-059
  - GUA-060
date: 2026-06-18
---

# BC 训练器模块

## 模块身份
- **类型**：模仿学习训练器
- **引擎**：wiki/entities/engine-v7.md
- **状态**：🚫 路径已死（GUA-060 关闭）

## 文件清单
- `src/v/nn/training/bc_dataset.py` — 数据集
- `src/v/nn/training/bc_trainer.py` — 训练器

## ⚠️ 关闭原因
- BC argmax collapse（见 wiki/concepts/bc-argmax-collapse.md）
- 理论必然，非工程问题

## 关联页面
- [[gua-060]]
- wiki/concepts/bc-argmax-collapse.md
- [[modular-architecture-gua061]]（替代方向）
