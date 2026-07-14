---
type: entity-module
title: "Qoder Agent SDK 集成"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
tags:
  - module
  - qoder
  - agent-sdk
  - ai-orchestration
status: current
related_gua: []
date: 2026-06-20
---

# Qoder Agent SDK 集成

## 概述

项目集成了 **Qoder Agent SDK**（`scripts/sdk/`），用于 AI 自动化派单、代码评审、冒烟测试。这是项目独有的 AI Agent 协作机制。

## 核心脚本

| 脚本 | 路径 | 用途 |
|------|------|------|
| `qoder_smoke.py` | `scripts/sdk/` | Agent 冒烟测试（验证 SDK 可用性） |
| `qoder_review_template.py` | `scripts/sdk/` | Agent 代码评审模板 |

## 工作流

```
任务派发（飞书/Lark）
    ↓
Qoder Agent SDK 接收
    ↓
qoder_smoke.py 冒烟验证
    ↓
qoder_review_template.py 代码评审
    ↓
pre_push_validate.py 推送前检查
    ↓
合并入库
```

## 关联页面

- [[module-lark-bot]] — 飞书 Bot 网关（任务来源）
- [[pre-push-check]] — 推送前检查
- wiki/entities/module-batch-executor.md — 批跑执行器（Agent 可调用）
