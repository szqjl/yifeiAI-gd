---
type: source-summary
title: "GUA-137 完成定义摘要"
sources:
  - docs/guandan-brain/issues/GUA-137-completion.md
tags:
  - gua-completion
  - sprint-capability-v2
  - grouping-plan-inference
status: current
related_gua:
  - GUA-061
  - GUA-135
  - GUA-136
  - GUA-138
date: 2026-07-16
---

# GUA-137 完成定义摘要

## GUA 元信息

- **标题**：玩家整手结构推断增强
- **状态**：draft（2026-07-08 待登记）
- **优先级**：推断 P1
- **关联**：[GUA-061] grouping_engine / [GUA-135] 双进优先级判定 / [GUA-136] 玩家剩牌估算

## 核心改动

### _estimate_player_grouping_plan 三层降级
```
L1: grouping_engine.enumerate_groupings(hand, cur_rank)
L2: 基于已知出牌 + 剩余牌结构推断
L3: 兜底使用粗粒度统计
```

### 冲刺判定 v2
```python
# GUA-137 升级判定
def is_sprinting(grouping_plan: GroupingPlan) -> bool:
    return (
        grouping_plan.num_rounds <= 2  # 剩余回合数 ≤ 2
        and grouping_plan.has_bomb_family  # 含炸弹家族
    )
```

替代 GUA-136 粗粒度判定：
```python
# GUA-136 旧判定（已废弃）
def is_sprinting_v1(hand_count: int) -> bool:
    return any(count >= 4 for count in hand_count_by_rank.values())
```

### 9 种场景判定表

| 场景 | num_rounds | has_bomb | 判定 | 说明 |
|------|-----------|----------|------|------|
| S1 | 1 | True | sprint | 单手炸弹 |
| S2 | 1 | False | pass | 单手非炸 |
| S3 | 2 | True | sprint | 炸弹 + 单手 |
| S4 | 2 | False | pass | 两手非炸 |
| S5 | 3+ | True | pass | 多手 |
| ... | ... | ... | ... | ... |

### 性能基准
- 每次调用 **< 4ms**
- 1000 次平均 3.8ms
- 由 [GUA-138] LRU 缓存后降至 < 0.1ms

## 关键依赖

- `grouping_engine.enumerate_groupings(hand, cur_rank)` — 整手枚举
- `GroupingPlan.num_rounds` — 回合数
- `GroupingPlan.has_bomb_family` — 炸弹标志

## 下游影响

- [[gua-135]] 双进优先级判定精度提升
- [[gua-138]] LRU 缓存本 GUA 的 grouping_plan 计算

## 风险点

> ⚠️ handoff §关键代码改动没提 V8 迁移是否会引入新的 `grouping_engine` 调用 → 需要确认 V8 不污染 grouping_engine

## 相关 Wiki 页面

- [[gua-137]] — 实体页
- [[gua-061]] — grouping_engine 模块
- [[gua-135]] — 消费者
- [[gua-136]] — 数据源上游
- [[gua-138]] — 性能优化
- [[module-grouping-engine]] — 模块页
