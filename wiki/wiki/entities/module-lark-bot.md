---
type: entity-module
title: "飞书 Bot 集成"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
tags:
  - module
  - lark
  - feishu
  - bot
  - gateway
status: current
related_gua: []
date: 2026-06-20
---

# 飞书 Bot 集成

## 概述

`scripts/lark/` 目录实现飞书（Lark）Bot 网关，负责：
1. 接收团队任务派单
2. 推送批跑结果/告警
3. 触发 Qoder Agent 任务

## 核心脚本

| 脚本 | 用途 |
|------|------|
| `start-bot.py` | 启动飞书 Bot 长连接 |
| `start-bot.bat` | Windows 快捷方式 |
| `start-bot.ps1` | PowerShell 快捷方式 |
| `send-message.py` | 主动推送消息 |

## 关联工具

- `scripts/tools/feishu_gateway_auth.py` — 飞书网关鉴权

## 工作流

```
Qoder Agent SDK 完成任务
    ↓
send-message.py 推送结果到飞书群
    ↓
团队成员在飞书收到通知
    ↓
点击链接跳转 wiki/entities/module-batch-executor.md 查看批跑详情
```

## 跨平台入口

- Linux/Mac：`python scripts/lark/start-bot.py`
- Windows CMD：`scripts/lark/start-bot.bat`
- Windows PowerShell：`scripts/lark/start-bot.ps1`

## 关联页面

- [[module-qoder-agent]] — Qoder Agent SDK
- wiki/entities/module-batch-executor.md — 批跑执行器（结果来源）
- wiki-minimax/concepts/batch-evaluation.md — 批跑评测体系
