---
type: entity-module
title: "残局预处理器 EndgamePreprocessor"
sources:
  - docs/knowledge/skills/07_opening/end position.md
tags:
  - v7
  - endgame
  - module
  - preprocessor
status: current
related_gua:
  - GUA-075
  - GUA-065
date: 2026-06-21
---

# 残局预处理器 EndgamePreprocessor

## 模块定位

V7 引擎残局管线的**核心实现模块**，负责在 `decide()` 主路径中检测残局态势、分派四角色、执行硬排除与降级兜底。

## 所在文件

- 主类：`v7_guards.py`（与 Guard 链同文件）
- 依赖规则：规则引擎的 `BAOSHU_RULE`、`endgame_rule`

## 核心数据结构

### `_endgame_context`

注入到 `decide()` 的上下文对象：

```python
_endgame_context = {
    "self":      {role, hand_size, has_bomb, ...},
    "teammate":  {role, hand_size, has_bomb, ...},
    "enemies":   [{role, hand_size, has_bomb, ...}, ...]  # 0-2 个
}
```

### 角色枚举

| 角色 | 含义 |
|------|------|
| `ENEMY_BLOCK` (Q1) | 敌方封锁路线 |
| `TEAMMATE_ASSIST` (Q2) | 队友助攻路线 |
| `SELF_RUSH` (Q0) | 自己冲刺路线 |
| `NORMAL` (Q3) | 普通（炸弹/常规） |

## 核心方法

### 注入方法
- `inject_endgame_context(state, hand)` → 构建 `_endgame_context` 并挂载到决策上下文

### 硬排除（方案 A）
- `apply_banned_types(action_list, context)` → 在 Guard 运行前对 `actionList` 应用 `banned_types` + `baoshu.never_play` 一刀切

### 四角色处理
- `handle_self_rush(actions, context)` — Q0 冲刺
- `handle_enemy_block(actions, context)` — Q1 封锁
- `handle_teammate_assist(actions, context)` — Q2 助攻
- `handle_normal(actions, context)` — Q3 炸弹/常规

### 辅助方法
- `_map_types(chinese_names)` — 牌型名映射（详见 [[shape-name-to-action-types]]）
- `_three_level_fallback(context)` — 三级降级兜底
- `_count_remaining_suppressors(...)` — 大单张动态阈值
- `_sort_by_danger(actions, context)` — 危险度排序

## 关键决策点

| 决策点 | 当前选择 | 理由 |
|--------|----------|------|
| 注入位置 | `_inject_numofplayers` 之后 | numofplayers 是残局判断的基础 |
| 排除方式 | 方案 A 硬排除 | 实现简单，所有 Guard 自动受益 |
| 敌双残局 | 下家优先 + 并集 | 出牌权威胁更大 |
| Q0 出牌顺序 | 先整后炸（常态） | 保留大牌接队友 |
| R11 退让 | partial | 平衡风险与机会，待批跑验证 |

## 实验性配置

| 配置 | 当前值 | 关联开关 |
|------|--------|----------|
| 残局阈值 | N=10 | 可调 |
| `R11_ENDGAME_MODE` | partial | R11 退让级别 |
| `GUA075_ENDGAME_WEIGHTED` | False | GUA-075 残局加权 |

## 依赖模块

- [[gua-075]] — 推荐引擎（残局管线下一层）
- [[gua-065]] — numofplayers 复用来源
- `MemoryTracker` — 大单张动态阈值复用
- `v7_guards.py` — Guard 链与映射工具

## 关联页面

- [[endgame-pipeline]] — 残局管线主体概念
- [[guandan-guard-retreat]] — Guard 退让规则
- [[shape-name-to-action-types]] — 牌型名映射层
- [[engine-v7]] — V7 引擎主体
- [[batch-evaluation]] — 残局策略验证

## 待补内容

- Q0「出牌权不在我手」场景（文档截断）
- L3 降级「级牌以下最大」具体实现
- Q1/Q2 同牌数冲突最优策略（等记忆管线）
