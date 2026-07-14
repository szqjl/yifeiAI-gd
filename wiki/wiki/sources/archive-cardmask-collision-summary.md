---
type: source-summary
title: "归档：2026-06-21 cardmask Dict 冲突"
sources:
  - docs/analysis/archive/2026-06-21-cardmask-dict-collision.md
tags:
  - archive
  - cardmask
  - gua-075
  - gua-081
  - multiset
status: current
related_gua:
  - GUA-075
  - GUA-081
date: 2026-06-29
---

# 归档：cardmask Dict 冲突分析

## 根因

`to_card_mask` 使用 `Dict[str, tuple]` 表示牌型时，**重复牌共用 key 导致后写覆盖前写**。

例：两张 SQ 共用 `"SQ"` 作为 key，第二张写入后只剩 1 张 SQ，导致 **bombs 日志只显示 3 张 Q** 而非 4 张 Q 炸弹。

## 当前状态

- GUA-075 ~268 行已加拦截段：跳过 `_group_consistency_filter` 保护 Q 炸弹
- ⚠️ **根因仍未解**：`Dict[str, tuple]` 结构缺陷仍在

## 下一步

应改为 `Dict[int, List[str]]`（multiset）以保留重复牌，跨多文件改动需统一追踪。

## 关联

- [[gua-075]]
- [[gua-081]]
- [[cardmask-multiset-fix]]
