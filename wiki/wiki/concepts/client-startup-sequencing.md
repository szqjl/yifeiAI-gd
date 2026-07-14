---
type: concept
title: "客户端启动时序方法论"
sources:
  - docs/fixes/V7_SYSTEM_FIXES.md
tags:
  - concept
  - startup
  - timing
  - batch-executor
status: current
related_gua:
  - GUA-063
date: 2026-06-18
---

# 客户端启动时序方法论

## 核心公式

```
wait_time = max(client.DELAY_BEFORE_CONNECT) + 1s buffer
```

## 为什么需要缓冲
- 客户端进程冷启动到 WebSocket 握手完成有数百 ms 抖动
- 1s 缓冲是经验值，平衡"等够"与"不浪费"

## 各客户端 DELAY 参数

| 客户端 | DELAY_BEFORE_CONNECT | 备注 |
|--------|---------------------|------|
| yf1_v7 / yf2_v7 | 3s / 9s | V7 默认 |
| yf1_m1 / yf2_m1 | (历史值) | M1 残留 |
| client3 / client4 | 10s / 20s | lalala 系固定延迟 |

## 双检启动模式
详见 [[module-restart-manager]]：
1. 主匹配 V7 名称
2. 兜底匹配 M1 名称
3. 全部失败才报错

## 关联条目
- [[module-restart-manager]] — 启动模块
- wiki/entities/engine-v7.md — V7 引擎
- [[gua-063-candidate]] — 兼容性 fix
