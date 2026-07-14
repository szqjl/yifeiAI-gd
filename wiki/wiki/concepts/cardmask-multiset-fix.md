---
type: concept
title: "card_mask multiset 修复"
sources:
  - docs/analysis/archive/2026-06-21-cardmask-dict-collision.md
tags:
  - cardmask
  - multiset
  - refactor
  - cross-cutting
status: current
related_gua:
  - GUA-075
  - GUA-081
date: 2026-06-29
---

# card_mask multiset 修复

## 现状（缺陷）

`to_card_mask` 内部使用 `Dict[str, tuple]`：

```python
# ❌ 缺陷写法
masks: Dict[str, tuple] = {}
masks["SQ"] = (...)  # 第二张 SQ 写入时覆盖前一次
```

→ 两张 SQ 共用 `"SQ"` key，**后写覆盖前写**，导致 4 张 Q 炸弹的日志只显示 3 张 Q。

## 目标（修复）

替换为 multiset 表示：

```python
# ✅ 目标写法
masks: Dict[int, List[str]] = {}
masks[11].append("SQ")  # 重复牌可累积
```

## 跨文件影响范围

- `src/v/nn/ultimate_win_rate_engine_v7.py`
- `src/v/nn/guards/v7_guards.py`
- `src/v/nn/endgame/*`
- `src/communication/v7_game_recorder.py`（日志输出端）

## 当前进度

- ✅ GUA-075 ~268 行已加拦截段（表面修复）
- ⏳ **根因修复（数据结构替换）待启动**

## 引用

- [[gua-075]]
- [[gua-081]]
- [[archive-cardmask-collision-summary]]
