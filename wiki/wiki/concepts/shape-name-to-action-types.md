---
type: concept
title: "牌型名映射层（_map_types）"
sources:
  - docs/knowledge/skills/07_opening/end position.md
tags:
  - v7
  - mapping
  - type-bridge
  - endgame
status: current
related_gua: []
date: 2026-06-21
---

# 牌型名映射层（_map_types）

## 概念定义

[[module-endgame-preprocessor|残局预处理器]]中桥接**中文牌型名**与 **V7 ACTION_TYPE 枚举**的 `_map_types` 方法。

## 背景

残局规则引擎（`BAOSHU_RULE`、`endgame_rule`）输出的是**中文牌型名**（如"单张"、"对子"、"三带二"），而 V7 引擎的 `actionList` 和 Guard 链使用 **ACTION_TYPE 枚举**。需要一层映射做转换。

## 映射设计

```python
_map_types(chinese_type_names: list[str]) -> list[ACTION_TYPE]
```

### 复用工具

`_map_types` 复用 `v7_guards.py` 中已有的工具方法，**不新建**：
- `get_action_type(type_name)` — 牌型名 → ACTION_TYPE 枚举
- `get_card_value(card)` — 单张牌的数值
- `CARD_RANK_ORDER` — 牌大小排序常量

### 依赖的中间表

- `_SHAPE_NAME_TO_ACTION_TYPES`：中文牌型名 → ACTION_TYPE 枚举集合
- `_ACTION_TYPE_CARD_COUNT`：ACTION_TYPE → 标准张数

## 设计原则

**不新建 `grouptype_map` / `card_mask`**：
- 避免重复造轮子
- 保持与 `v7_guards.py` 的单一数据源
- 减少维护成本

## 关联页面

- [[module-endgame-preprocessor]] — 使用方
- [[endgame-pipeline]] — 调用上下文
