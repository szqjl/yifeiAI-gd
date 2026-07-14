---
type: source-summary
title: "模型文件管理方案"
sources:
  - docs/governance/模型文件管理方案.md
tags:
  - governance
  - model-management
  - cos
  - artifact
  - active
status: current
related_gua: []
date: 2026-06-18
---

# 模型文件管理方案

## 来源

- 源文件：`docs/governance/模型文件管理方案.md`（4584 字符）
- 状态：**current**——当前模型分发方式的来源文档

## 背景

模型文件（NN 权重）通常为数百 MB 到数 GB，**不适合直接进 Git**。需要一套明确的模型分发/同步机制。

## 四方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **云存储 + 脚本** | 大文件友好、版本可控 | 需维护脚本 | ⭐⭐⭐⭐⭐ **推荐** |
| 仅推脚本本地生成 | Git 极简 | 首次拉取耗时长 | ⭐⭐⭐ |
| 清单 + 手动下载 | 透明 | 易遗漏 | ⭐⭐ |
| Git submodule | 版本可锁定 | 仓库臃肿 | ⭐ |

## 推荐方案：云存储 + 脚本

### 核心组件

- **COS bucket** 分区：
  - `replays/` — 离线对局回放
  - `models/` — 训练产物（按版本号/日期组织）
  - `eval/` — 评测结果快照
- **`download_models.py`** — 拉取脚本（按 `models_manifest.yaml` 清单）
- **`models_manifest.yaml`** — 模型清单（文件名、版本、SHA256、来源 URL）

### 工作流

1. 训练完成 → 上传到 COS 对应分区
2. 更新 `models_manifest.yaml` 追加新条目
3. 提交 `models_manifest.yaml` 到 Git
4. 其他设备/Agent 运行 `download_models.py` 按需拉取

## 关联页面

- [[artifact-storage-strategy]] — 产物存储策略概念
- [[handoff-protocol]] — Handoff 接续协议（云存储是 handoff 的数据载体之一）
- wiki/entities/engine-v7.md — V7 引擎的训练产物走此通道
