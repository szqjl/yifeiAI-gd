---
type: source-summary
title: "card_mask Dict 键冲突 multiset 修复"
sources:
  - docs/analysis/archive/2026-06-21-cardmask-dict-collision.md
tags:
  - cardmask
  - multiset
  - gua-075
  - in-progress
status: current
related_gua:
  - GUA-075
date: 2026-06-28
---

# card_mask Dict 键冲突 multiset 修复

## 来源

- `docs/analysis/archive/2026-06-21-cardmask-dict-collision.md` (2001 chars)
- 日期：2026-06-21

## 问题描述

`card_mask` 在 `to_card_mask` 函数中以 `Dict[int, List[str]]` 编码，但**重复牌会被同 key 覆盖**。这导致 `group_members` 字段在 multiset 场景下丢失部分成员，进而影响 `_basic_classify` 与下游推荐。

## 命中路径

- `src/v/nn/ultimate_win_rate_engine_v7.py:268` 附近
- `_group_consistency_filter` 调用 `card_mask` 时

## 已知症状

- Q 炸弹（4 张 Q）被拆成 4 张单 Q
- 同牌型（如 555）只保留一个 group_members 条目

## 修复方案（进行中）

1. 将 `group_members` 从 `Dict` 改为 `List`（保留所有成员）
2. `_basic_classify` 接收 multiset 形式的 group
3. 加诊断日志：命中 GUA-075 路径时打印 card_mask 与 group_members 对照
4. pytest 用例：4 张 Q、5 个 5 等 multiset 牌型

## 状态

| 项 | 状态 |
|----|------|
| 保护拦截（`GUA-075 跳过 _group_consistency_filter`） | **已加**（2026-06-21） |
| multiset 数据结构迁移 | **待做** |
| 诊断日志 | **待做** |
| pytest | **待做** |

## 注意事项

- handoff 明示「**不要再改同一段代码**」
- 保护拦截是**设计行为**（推荐命中但被 mask 挡 → 掉进回退），与 GUA-075 bug 修复行为需区分

## 关联

- [[gua-075]] — 缺陷条目
- [[decision-pipeline-v7]] — L2′ 保护拦截层
- [[decision-trace-taxonomy]] — R-D01 典型案例
- [[v7-current-state]] — 当前状态
