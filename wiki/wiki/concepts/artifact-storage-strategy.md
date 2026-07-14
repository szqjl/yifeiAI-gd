---
type: concept
title: "制品存储策略"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
tags:
  - concept
  - artifact-storage
  - cos
  - sync
  - retention
status: current
related_gua: []
date: 2026-06-20
---

# 制品存储策略

## 概述

项目使用**腾讯云 COS**作为训练产物、回放文件、评测日志的统一存储仓库。`scripts/cos/` 实现双向同步与生命周期管理。

## 制品分类

| 类别 | COS 路径前缀 | 典型内容 | 保留期 |
|------|-------------|----------|--------|
| **训练 checkpoint** | `v7/checkpoints/` | Stage 5-8 模型权重 | 长期 |
| **批跑日志** | `v7/batch-logs/` |
