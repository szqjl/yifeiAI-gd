---
type: entity-gua
title: "GUA-063（候选）restart_manager 客户端启动顺序兼容性"
sources:
  - docs/fixes/V7_SYSTEM_FIXES.md
tags:
  - v7
  - batch-executor
  - restart
  - backward-compat
  - candidate
status: draft
related_gua:
  - GUA-062
date: 2026-06-18
---

# GUA-063（候选）restart_manager 客户端启动顺序兼容性

> ⚠️ **状态**：候选 GUA，尚未正式编号入册。
> 来源：早期 fix 文档 `V7_SYSTEM_FIXES.md`（2026-01-20）未走 GUA 体系，建议补登。

## 缺陷描述
批跑启动时，`batch_executor/restart_manager.py` 仍按 M1 客户端名（`yf1_m1` / `yf2_m1`）查找进程，V7 客户端（`yf1_v7` / `yf2_v7`）启动后被判定为"未知客户端"，拉起失败。

## 触发条件
- 任何 V7 批跑
- 混合场景（M1 残留 + V7 启动）尤甚

## 根因
restart_manager 硬编码了旧客户端名清单，未做迁移兼容。

## 修复
引入**向后兼容双检模式**：
- 主匹配：按当前 V7 名称
- 兜底匹配：旧 M1 名称
- 双检通过即视为合法客户端

## 关联
- [[gua-062-candidate]] — 同期修复
- [[module-restart-manager]] — 模块说明（待建）
- [[client-startup-sequencing]] — 客户端启动时序方法论（待建）
- wiki/entities/engine-v7.md — V7 引擎

## 设计启发
M1 → V7 的命名迁移是**破坏性变更**；所有引用客户端名的代码都需双检。  
此 fix 可作为后续引擎迁移（如未来 V8）的参考模板。

## 优先级建议
**P1**（已修复，待正式入册）
