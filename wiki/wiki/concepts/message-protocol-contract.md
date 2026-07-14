---
type: concept
title: "消息格式契约（protocol contract）"
sources:
  - docs/fixes/V7_SYSTEM_FIXES.md
tags:
  - concept
  - protocol
  - contract
  - systemic-risk
status: current
related_gua:
  - GUA-062
date: 2026-06-18
---

# 消息格式契约（protocol contract）

## 概念定义
所有 AI 客户端（V7 / M1 / lalala / client3 / client4）与 Tornado server 之间通信的**统一字段命名规范**。

## 关键字段
| 字段 | 含义 | 来源 |
|------|------|------|
| `actIndex` | 出牌动作索引 | **lalala 标杆**，全客户端必须一致 |
| ~~`actionIndex`~~ | （错误）驼峰命名 | 已被 GUA-062 fix 弃用 |

## 为什么重要
- 字段名不一致 → server 端 `KeyError` → 客户端失联
- 任何新客户端接入都必须遵循此契约
- **缺乏契约 = 系统性风险**（TENSION-5）

## 当前状态
- ✅ `actIndex` 已成为事实标准
- ⚠️ **未文档化为正式协议**——只有 fix 记录，无 RFC 级规范
- 建议：建立 `docs/protocol/CLIENT_SERVER_PROTOCOL.md` 正式契约文档

## 暴露的 fix
- [[gua-062-candidate]] — V7 actionIndex / actIndex 不匹配

## 关联条目
- wiki/entities/engine-v7.md — 当前主迭代引擎
- gua-dan-ai-dev-guide-summary — lalala 协议标杆来源
- evaluator-compatibility-report-summary — 同类 fix 簇
