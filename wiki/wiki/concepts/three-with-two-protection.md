---
type: concept
title: "三带二拆牌保护"
sources:
  - docs/guandan-brain/iterations/m3-strategy-gua026-029.md
related_gua:
  - GUA-026
tags:
  - m3
  - three-with-two
  - bomb
  - reuse-pattern
date: 2026-06-18
---

# 三带二拆牌保护

## 概览

M3 阶段三带二拆牌 / 炸弹保护的复用范式，由 [[GUA-026]] 落地批跑 11/12（91.7%）验证。

## 关键函数

- `_uses_level_rank_cards`：检测当前出牌是否使用级牌
- `_three_with_two_protect_ok`：三带二拆牌保护校验

## 触发条件

- 三带二 + 含级牌 + 队友可接
- 炸弹 R1–R6 规则包未冲突

## 复用范式

```python
if _uses_level_rank_cards(action) and _three_with_two_protect_ok(hand, ctx):
    return _protect_split(...)
```

## 关联

- [[GUA-026]] / [[GUA-029]]
- M3 Guard 设计模式
