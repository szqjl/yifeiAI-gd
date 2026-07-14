---
type: entity-module
title: "COS 云端存储脚本"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
tags:
  - module
  - cos
  - artifact-storage
  - sync
status: current
related_gua: []
date: 2026-06-20
---

# COS 云端存储脚本

## 概述

项目使用**腾讯云 COS（Cloud Object Storage）**作为训练产物、回放文件、评测日志的云端 artifact 仓库。`scripts/cos/` 目录承担双向同步职责。

## 核心脚本

| 脚本 | 用途 |
|------|------|
| `cos_client.py` | COS 客户端封装（上传/下载/列表/删除） |
| `batch_upload_regression.py` | 回归测试 artifact 批量上传 |
| `sync_pull_all.py` | 全量拉取同步 |

## 上行同步（本地 → COS）

```bash
# 单文件上传
python scripts/cos/cos_client.py upload <local_path> <cos_key>

# 批量上传回归产物
python scripts/cos/batch_upload_regression.py --src ./artifacts/regression/
```

## 下行同步（COS → 本地）

```bash
# 全量拉取
python scripts/cos/sync_pull_all.py --target ./artifacts/

# 指定 key 下载
python scripts/cos/cos_client.py download <cos_key> <local_path>
```

## Artifact 分类

| 类别 | COS 路径前缀 | 典型内容 |
|------|-------------|----------|
| 训练 checkpoint | `v7/checkpoints/` | Stage 5-8 模型权重 |
| 批跑日志 | `v7/batch-logs/` | `run_v7_vs_lalala_games.py` 输出 |
| 回放文件 | `replays/` | yf_replay 导出 |
| 回归报告 | `regression/` | `batch_upload_regression.py` 打包 |

## 关联页面

- [[artifact-storage-strategy]] — 制品存储策略概念
- wiki/entities/module-batch-executor.md — 批跑执行器（产物来源）
- [[module-training-stages]] — 训练阶段（checkpoint 来源）
