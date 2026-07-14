---
type: source-summary
title: "DEVELOPMENT_RULES 摘要"
sources:
  - docs/development/DEVELOPMENT_RULES.md
tags:
  - development
  - rules
  - source
status: current
related_gua: []
date: 2026-06-18
---

# DEVELOPMENT_RULES 摘要

> 来源：`docs/development/DEVELOPMENT_RULES.md`（约 5017 字符，含部分乱码，正文已解码）

## 概述

掼蛋 AI 项目的核心开发规则手册，覆盖 5 条强制规则 + 代码/测试/日志规范 + 检查清单。

## 5 条核心开发规则

### 1. 系统时间强制规则
- **强制要求**：所有涉及当前/实时时间的场景必须调用 `datetime.now()`
- **禁止**：硬编码时间字符串、固定时间戳
- **工具类**：推荐使用统一的 `TimeUtils`（位置未指定，跨项目复用）

### 2. 静默时段机制
- **时段定义**：每日 `0:00-6:00` 为静默时段
- **适用范围**：监控检查、定时任务
- **要求**：定时任务需避开静默时段或延后到 6:00 后执行

### 3. 组队规则（座位对位）
- **规则**：第 1/3 个连接的 AI 为队友，第 2/4 个连接的 AI 为队友
- **不可更改**：连接时固定，整个会话期间不变

### 4. 响应时间 SLA
- **建议值**：决策响应时间 `< 1秒`
- **目的**：避免超时判负

### 5. 信息监控检查间隔
- **最小间隔**：`≥ 6小时`
- **配套**：使用系统时间判断静默时段

## 代码规范

- **文档编写**：先列提纲再填充，每 3 分钟保存一次（避免长文档生成超时）
- **代码风格**：详见文档（略）

## 关联概念

- [[concept-system-time-rule]] — 系统时间强制规范
- [[concept-quiet-hours]] — 静默时段机制
- [[concept-seat-sync-and-diagnosis]] — 座位同步（组队规则相关）

## 备注

- 原文存在乱码（疑似 UTF-8 误解码），本摘要已还原为可读中文
- 知识图谱中不携带乱码字符
