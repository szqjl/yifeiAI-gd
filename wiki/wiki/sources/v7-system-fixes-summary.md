---
type: source-summary
title: "V7 系统双问题修复摘要（消息格式 + 启动顺序）"
sources:
  - docs/fixes/V7_SYSTEM_FIXES.md
tags:
  - fixes
  - v7
  - communication
  - restart
  - legacy-fix
status: current
related_gua:
  - GUA-061
  - GUA-062
  - GUA-063
date: 2026-06-18
---

# V7 系统双问题修复摘要

## 来源
- **原始文件**：`docs/fixes/V7_SYSTEM_FIXES.md`（3222 字符）
- **时间戳**：2026-01-20（早期 fix，未走 GUA 编号体系；建议补登 GUA-062 / GUA-063）

## 涉及 Fix 总览

| Fix | 标题 | 根因 | 修复点 | 候选 GUA |
|-----|------|------|--------|----------|
| Fix-1 | 消息格式不匹配（KeyError: actionIndex） | yf1_v7 发送 `actionIndex`，server.py 期望 `actIndex`（lalala 标杆） | `src/communication/yf1_v7.py` 改用 `actIndex` | GUA-062 |
| Fix-2 | restart_manager 启动顺序错误 | 客户端名从 `yf1_m1`/`yf2_m1` 迁移到 `yf1_v7`/`yf2_v7`，但 restart_manager 仍按旧名查找 | `batch_executor/restart_manager.py` 增加双检兼容逻辑 | GUA-063 |

## Fix-1 详情：消息格式契约对齐

### 现象
- **报错**：`KeyError: 'actionIndex'`（Tornado `server.py:96` `on_message`）
- **场景**：V7 GUI 启动后，客户端连不上服务，消息被拒

### 根因
- yf1_v7 客户端使用字段名 `actionIndex`（驼峰）
- lalala 客户端与 server.py 协议使用字段名 `actIndex`（缩写）
- 缺乏**全客户端统一消息契约**，是 [[message-protocol-contract]] 缺失的典型表现

### 修复
- `src/communication/yf1_v7.py`：将所有出站消息字段从 `actionIndex` 改为 `actIndex`
- 同步检查 `yf2_v7.py`（已正确使用 `actIndex`）

### 验证
- 启动 V7 GUI，手动打牌，确认消息可达、状态正常
- 与 client3/client4（lalala 系，10s/20s 延迟）联调通过

## Fix-2 详情：客户端启动顺序兼容性

### 现象
- 批跑启动时，V7 客户端未能被 restart_manager 正确拉起
- 日志显示 `client not found: yf1_v7`（按 M1 旧名查表）

### 根因
- `batch_executor/restart_manager.py` 硬编码了 `yf1_m1` / `yf2_m1` 客户端名
- M1 已废弃但仍可能有残留进程；V7 上线后，名称错位

### 修复（向后兼容双检模式）
```python
# 伪代码示意
if client_name in ["yf1_m1", "yf2_m1"]:
    # 旧 M1 客户端
    ...
elif client_name in ["yf1_v7", "yf2_v7"]:
    # 新 V7 客户端
    ...
else:
    # 双检：先按 V7 匹配，失败再按 M1 匹配
    ...
```

### 验证
- 混合场景：先跑 M1 批跑，再跑 V7 批跑，restart_manager 全部识别成功
- 单独 V7 批跑：启动 → 出牌 → 结算，链路通畅

## TENSION 标注

> **TENSION-1**：本文档写作时间早于治理规范（260120），未走 GUA 编号体系；按当前规范应补登 GUA-062 / GUA-063。
> **TENSION-2**：本文档未明确指出"消息契约统一"是系统性原则；读者可能仅当作个别 fix 处理；建议关联 [[message-protocol-contract]] 概念页。

## 关联条目
- v7-gui-path-validation-fix-summary — 同属 V7 fixes 簇，姊妹条目
- [[fixes-cluster-overview]] — fixes 簇总览
- [[gua-061]] — 已有 V7 路径校验 GUA
- wiki/entities/engine-v7.md — V7 引擎实体（待建）
- [[module-restart-manager]] — restart_manager 模块（待建）
- [[message-protocol-contract]] — 消息格式契约概念（待建）
- [[client-startup-sequencing]] — 启动时序方法论（待建）
