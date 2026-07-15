---
type: entity-module
title: "batch_executor — 批跑执行器"
sources:
  - docs/guandan-brain/V8-新平台对接方案.md
tags:
  - module
  - batch
  - v8
status: current
related_gua:
  - GUA-131
  - GUA-132
  - GUA-133
date: 2026-07-08
---

# batch_executor — 批跑执行器

## 路径

`batch_executor/`

## 子模块

- `executor.py` — 新平台启动适配（V8 高风险改动）
- `restart_manager.py` — 客户端启动顺序（yf1 建房→其他加房）

## V8 改造点

- 启动流程对接 OpenGuanDan 新平台
- 启动顺序调整避免竞态

## 风险

详见 [v8-platform-migration]。

## 延伸阅读

- [v8-openguandan-protocol]
- [batch-evaluation]
