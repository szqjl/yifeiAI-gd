---
type: concept
title: "card_mask Dict 键冲突缺陷"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/analysis/archive/2026-06-21-cardmask-dict-collision.md
tags:
  - bug
  - data-structure
  - card-mask
status: current
related_gua:
  - GUA-072
  - GUA-075
  - GUA-079
date: 2026-06-21
---

# card_mask Dict 键冲突缺陷

## 缺陷描述

`card_mask` 使用 `Dict[str, tuple]` 结构存储牌型 mask，但 **重复牌共用 dict key**，后写覆盖前写，导致：
- 牌型信息丢失
- 组牌引擎输出退化
- 主路径输出崩坏

## 影响范围

- `to_card_mask()` 主路径
- `_basic_classify` 降级路径
- `group_members` multiset 设计错误

## 修复方案

### 已实施（临时保护）

参见 [[gua-072]] 三项保护：
1. 退化诊断
2. handCards 记录
3. 降级炸弹保护（_basic_classify）

### 根本修复（待实施）

将 `group_members` 从 `Dict[str, tuple]` 改为 `Dict[int, List[str]]`（按牌值分组 + multiset 保留重复牌）。

## 触发路径 B

结合 [[gua-075]] 双路径架构，在 card_mask 异常时切到 `_recommend_play() → _quick_guard_validate` 跳过 `_group_consistency_filter`。

## 关联

- [[gua-072]] — 修复实施
- [[gua-075]] — 路径绕开
- [[gua-079]] — 三层根因之数据层
