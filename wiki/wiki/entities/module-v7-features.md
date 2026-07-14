---
type: entity-module
title: "V7 特征工程模块"
sources:
  - docs/guandan-brain/MOCs/V7-Development.md
tags:
  - module
  - v7
  - features
status: current
related_gua:
  - GUA-037
  - GUA-038
date: 2026-06-18
---

# V7 特征工程模块

## 模块身份
- **类型**：NN 特征提取
- **引擎**：wiki/entities/engine-v7.md

## 文件清单
| 文件 | 输出维度 | 类型 |
|------|---------|------|
| `src/v/nn/features/static_features.py` | 124 | 静态特征 |
| `src/v/nn/features/dynamic_features.py` | 64 | LSTM 动态特征 |
| `src/v/nn/features/memory_tracker.py` | 24 | 记忆追踪 |

## 关联页面
- wiki/entities/engine-v7.md
- [[module-v7-guards]]
- [[modular-architecture-gua061]]
