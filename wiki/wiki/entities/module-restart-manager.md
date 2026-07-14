---
type: entity-module
title: "batch_executor/restart_manager.py"
sources:
  - docs/fixes/V7_SYSTEM_FIXES.md
tags:
  - module
  - batch-executor
  - restart
  - client-lifecycle
status: current
related_gua:
  - GUA-063
date: 2026-06-18
---

# batch_executor/restart_manager.py

## 模块职责
负责批跑过程中客户端进程的**生命周期管理**：
- 启动各客户端进程
- 监控客户端存活
- 崩溃后自动重启
- 跨引擎兼容（M1 / V7 共存场景）

## 关键设计：向后兼容双检模式

```python
# 伪代码示意
KNOWN_CLIENTS = ["yf1_v7", "yf2_v7", "yf1_m1", "yf2_m1"]

def identify_client(process_name):
    # 主匹配
    if process_name in ["yf1_v7", "yf2_v7"]:
        return "v7"
    # 兜底匹配
    if process_name in ["yf1_m1", "yf2_m1"]:
        return "m1"
    return None
```

## 启动时序
- 等待时间 = 各客户端 `DELAY_BEFORE_CONNECT` + 1s 缓冲
- 详见 [[client-startup-sequencing]]

## 关联 GUA
- [[gua-063-candidate]] — 启动顺序兼容性 fix 来源

## 关联条目
- wiki/entities/engine-v7.md — V7 引擎
- [[client-startup-sequencing]] — 启动方法论
