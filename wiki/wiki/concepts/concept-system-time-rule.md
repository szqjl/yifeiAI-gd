---
type: concept
title: "系统时间强制规范（TimeUtils）"
sources:
  - docs/development/DEVELOPMENT_RULES.md
tags:
  - development
  - time
  - core-rule
status: current
related_gua: []
date: 2026-06-18
---

# 系统时间强制规范（TimeUtils）

## 定义

掼蛋 AI 项目的**第一强制规则**：所有涉及当前/实时时间的场景必须调用 `datetime.now()`，**禁止硬编码时间字符串或固定时间戳**。

## 适用范围

- 监控检查时间判断
- 静默时段判定（依赖此规则）
- 定时任务调度
- 对局时间戳记录
- 日志时间字段

## 推荐实现

统一使用 `TimeUtils` 工具类（位置未指定，跨项目复用），封装：

```python
from datetime import datetime

class TimeUtils:
    @staticmethod
    def now() -> datetime:
        return datetime.now()
    
    @staticmethod
    def is_quiet_hours() -> bool:
        hour = datetime.now().hour
        return 0 <= hour < 6
```

## 反例（禁止）

```python
# ❌ 硬编码时间戳
timestamp = "2026-06-18 03:00:00"

# ❌ 固定时间字符串
if current_time == "00:00":
    skip_check()
```

## 正例

```python
# ✅ 调用系统时间
from datetime import datetime
now = datetime.now()
if now.hour < 6:
    skip_check()
```

## 关联

- [[concept-quiet-hours]] — 静默时段机制（基于此规则实现）
- [[source-development-rules-summary]] — 核心规则出处
- DEVELOPMENT_RULES — 第 1 条规则
