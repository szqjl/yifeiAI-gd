---
type: entity-gua
title: "GUA-062（候选）V7 消息字段名不匹配 KeyError"
sources:
  - docs/fixes/V7_SYSTEM_FIXES.md
tags:
  - v7
  - communication
  - protocol
  - candidate
status: draft
related_gua:
  - GUA-061
  - GUA-063
date: 2026-06-18
---

# GUA-062（候选）V7 消息字段名不匹配 KeyError

> ⚠️ **状态**：候选 GUA，尚未正式编号入册。
> 来源：早期 fix 文档 `V7_SYSTEM_FIXES.md`（2026-01-20）未走 GUA 体系，建议补登。

## 缺陷描述
V7 客户端向 Tornado server 发送出牌消息时，server 抛出 `KeyError: 'actionIndex'`，连接被拒。

## 触发条件
- 启动 V7 GUI
- 客户端首次出牌

## 根因
yf1_v7 出站消息字段名为 `actionIndex`（驼峰），与 lalala 系客户端及 server.py 协议期望的 `actIndex`（缩写）不一致。

## 影响
- V7 客户端**完全无法**与 server 通信
- 所有 V7 批跑 / 联调全部失败

## 修复
- `src/communication/yf1_v7.py`：字段名从 `actionIndex` 改为 `actIndex`
- 同步核查 `yf2_v7.py`（已正确）

## 关联
- [[gua-063-candidate]] — 同期发现的 restart_manager 启动顺序问题
- [[message-protocol-contract]] — 暴露的系统性问题（缺乏统一消息契约）
- wiki/entities/engine-v7.md — V7 引擎实体

## 优先级建议
**P0**（已修复，待正式入册）
