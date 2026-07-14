---
type: entity-module
title: "batch_executor 进程管理与自启动"
sources:
  - docs/guandan-brain/COMMANDER_NOTES.md
tags:
  - tool
  - batch
  - process
  - executor
status: current
related_gua: []
date: 2026-06-17
---

# batch_executor 进程管理与自启动

## 模块定义
`executor.py` — 批量对局执行器，负责启动/管理多个客户端进程完成离线批跑。

## 关键机制

### 1. TrackedClientProcess（2026-05-22 修复）
- **作用**：跟踪每个客户端子进程的生命周期
- **修复内容**：进程异常退出检测 + 自动重启
- **修复前 bug**：客户端崩溃后 executor 沉默等待，批跑卡死

### 2. 单实例锁
- **作用**：防止多个 executor 同时跑同一批任务
- **机制**：基于 pid 文件 + 端口占用检查

### 3. 宽限期（Grace Period）
- **作用**：客户端启动后给一定时间初始化
- **默认值**：30s
- **可调**：通过命令行参数

### 4. 熔断机制（Circuit Breaker）
- **触发条件**：连续 N 次客户端崩溃
- **动作**：停止当前批跑并报警
- **目的**：避免无效消耗 + 快速失败

## 关联命令

```bash
# 启动批跑
python -m src.batch.executor --target-games 12 --vs lalala

# 进程状态查询
ps aux | grep yf

# 日志路径
logs/batch_executor/
```

## 关联页面
- [[branch-isolation]] — M3/V7 分支对应不同执行
- wiki-minimax/concepts/batch-evaluation.md — 评测体系
- [[v7-current-state]] — V7 状态
