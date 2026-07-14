---
type: source-summary
title: "知识库目录结构摘要（三级架构）"
sources:
  - docs/knowledge/README.md
tags:
  - knowledge-base
  - three-tier
  - rules
  - strategy
  - skills
status: current
related_gua: []
date: 2026-06-18
---

# 知识库目录结构摘要

> 原文件：`docs/knowledge/README.md`（2,701 字）

## 三级知识库架构

| 层级 | 名称 | 加载方式 | 性能 | 内容 |
|------|------|----------|------|------|
| L1 | **Rules** | 硬编码（O(1)） | 最快 | 01_basic_rules（含 `06_game_flow.md` 进贡流程） |
| L2 | **Strategy** | 内存加载（O(1)） | 快 | 5 个子目录：核心/角色/牌型/阶段/通用 |
| L3 | **Skills** | 按需查询+缓存 | 较慢 | 01_foundation~08_endgame 8 个子目录 |

详见 concept-knowledge-three-tier-architecture

## Strategy 子目录

- `01_core_strategies` — 核心策略
- `02_role_strategies` — 角色策略（主牌/跟牌/进贡/还贡）
- `03_card_strategies` — 牌型策略（炸弹/顺子/连对/三带）
- `04_phase_strategies` — 阶段策略（开局/中局/残局）
- `05_common_strategy` — 通用策略

## Skills 子目录

按需加载，8 个子目录（01_foundation~08_endgame），含 39 条动态生成规则。

## 性能特征

- **L1 Rules**：硬编码，零 IO 延迟
- **L2 Strategy**：启动时一次性加载到内存
- **L3 Skills**：按需查询+缓存（lazy init 加速 GUI 启动）

## 关联

- concept-knowledge-three-tier-architecture — 三级架构详细说明
- [[entity-knowledge-base]] — 44 条规则统计
- [[engine-hybrid-decision-v4]] — 决策流程中调用 L1/L2/L3
