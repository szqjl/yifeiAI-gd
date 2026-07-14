---
type: concept
title: "静默时段机制（0:00-6:00）"
sources:
  - docs/development/DEVELOPMENT_RULES.md
tags:
  - development
  - scheduling
status: current
related_gua: []
date: 2026-06-18
---

# 静默时段机制（0:00-6:00）

## 定义

每日 `0:00-6:00` 为掼蛋 AI 项目的**静默时段**，在此期间：

- ❌ 不执行监控检查
- ❌ 不执行定时任务
- ✅ 定时任务需避开或延后到 6:00 后

## 适用范围

- 批跑评测调度（避开夜间）
- 信息监控检查（间隔 ≥ 6 小时，配合静默时段）
- 自动重启任务
- 日志轮转

## 实现要点

- 时间判断必须调用 `datetime.now()`（参见 [[concept-system-time-rule]]）
- 不可硬编码时间窗口

## 示例

```python
from datetime import datetime

def should_run_check() -> bool:
    hour = datetime.now().hour
    if 0 <= hour < 6:
        return False  # 静默时段
    return True
```

## 关联

- [[concept-system-time-rule]] — 时间判断的底层规则
- DEVELOPMENT_RULES — 第 2 条规则
- wiki/overview — 全局调度策略
