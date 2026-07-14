---
type: concept
title: "card_mask Dict 键冲突缺陷"
sources:
  - docs/analysis/archive/2026-06-21-cardmask-dict-collision.md
  - src/v/nn/ultimate_win_rate_engine_v7.py
  - src/v/nn/features/grouping_engine.py
tags:
  - cardmask
  - multiset
  - data-loss
  - v7
  - defect
status: current
related_gua:
  - GUA-075
  - GUA-072
date: 2026-06-29
---

# card_mask Dict 键冲突缺陷

## 概述

V7 多处代码使用 `Dict[str, tuple]` 存储 card_mask（如 `_card_mask` / `_basic_classify` / `to_card_mask`），由于 Python dict key 唯一性，**重复牌（如双 SQ、双 HA）共用 key 后写覆盖前写**，导致数据丢失。

## 缺陷分布

| 代码位置 | 函数 | 状态 | 影响 |
|----------|------|------|------|
| `src/v/nn/ultimate_win_rate_engine_v7.py` 行 268-287 | `_card_mask` | **已修**（GUA-075） | 保护拦截输入正确 |
| `src/v/nn/ultimate_win_rate_engine_v7.py` 行 699 | `_basic_classify` | **未修** | 降级路径 card_mask 丢失 |
| `src/v/nn/features/grouping_engine.py` 行 130-202 | `to_card_mask` | **未修** | 组牌引擎 v2 评分输入丢牌 |
| `src/m/m3/...` `TrickSequenceTracker` | — | **未修** | M3 路径同型问题 |

## 典型症状

### 案例 1：双 SQ 丢失

```python
# 错误示例（dict 冲突）
card_mask = {"SQ": (12, 4, 0)}  # 后写覆盖前写
# 实际手牌：SQSQHA → 期望 mask {"SQ": (12, 4, 1), "HA": (14, 1, 0)}
# 实际得到：mask {"SQ": (12, 4, 0), "HA": (14, 1, 0)}  # SQ 重复标志丢失
```

### 案例 2：炸弹日志丢一张

```
手牌：QQQQ
日志输出：bombs [Q, Q, Q]  # 仅 3 张
group_size=4 / count=4  # 内部状态正确
```

**根因**：日志显式时遍历 dict 遇到 SQ key 只取 1 张，内部 group 计数正确但日志丢一张。

## 修复方案

### Multiset 改造

将 `Dict[str, tuple]` 改为 `Counter` 或带重复计数的 list：

```python
# 正确示例
from collections import Counter
card_mask = Counter(["SQ", "SQ", "HA"])  # Counter({"SQ": 2, "HA": 1})
```

### 进行中（2026-06-29）

- `to_card_mask`（grouping_engine.py L130-202）：multiset 改造 PR 待合
- `_basic_classify`（行 699）：未启动
- `TrickSequenceTracker`（M3）：未启动

## 关联缺陷

- **GUA-075 命中路径**：行 268 已修，但下游 `_basic_classify` 行 699 未修
- **GUA-062 组牌引擎 v2**：评分函数输入丢牌 → 评分不准
- **GUA-072 MemoryTracker 降级**：降级路径经过 `_basic_classify` 触发

## 关联页面

- [[gua075-recommendation-pipeline]]
- [[gua-075]]
- [[gua-062]]
- [[gua-072]]
- [[module-grouping-engine]]
