---
type: source-summary
title: "GUA-136 完成定义摘要"
sources:
  - docs/guandan-brain/issues/GUA-136-completion.md
tags:
  - gua-completion
  - sprint-capability
  - memory-tracker
status: current
related_gua:
  - GUA-052
  - GUA-135
  - GUA-137
  - GUA-138
date: 2026-07-16
---

# GUA-136 完成定义摘要

## GUA 元信息

- **标题**：玩家剩牌估算增强
- **状态**：draft（2026-07-08 待登记）
- **优先级**：推断 P1（sprint 评估升级链）
- **关联**：[GUA-052] MemoryTracker / [GUA-135] 双进优先级判定

## 核心改动

### MemoryTracker.get_hand_count 优先级
```
优先级链：手牌记录 → 已出牌记录 → _estimate_player_remaining
```
- 第一优先级：对手主动报手牌（极少数情况）
- 第二优先级：从 play_history 反推
- 第三优先级：调用 `_estimate_player_remaining`（增强点）

### _estimate_player_remaining 增强
- 基于 `card_state` 108 张牌全量追踪
- 排除法推断对手手牌
- **三层降级推断算法**：
  1. L1: 直接从 card_state 减去已出牌
  2. L2: 基于对手历史出牌模式估算
  3. L3: 兜底使用统计先验

### 关单条件（7 项）
1. `card_state` 完整（108 张无丢失）
2. `play_history` 完整记录
3. `_estimate_player_remaining` 三层降级覆盖所有场景
4. 单测覆盖 8 种典型牌局
5. `MemoryTracker.get_hand_count` 优先级测试通过
6. 不破坏 V7 引擎兼容性（handoff §V7 链路保护）
7. 性能：调用耗时 < 1ms

## 数据源

- `src/v/nn/features/memory_tracker.py`
- `card_state` (108 张)
- `play_history` (历史出牌)

## 下游影响

- [[gua-137]] 依赖本 GUA 的 `_estimate_player_remaining` 输出
- [[gua-135]] 双进优先级判定的数据源升级链起点

## 相关 Wiki 页面

- [[gua-136]] — 实体页
- [[gua-052]] — MemoryTracker 模块
- [[gua-135]] — 双进优先级判定（消费者）
- [[gua-137]] — 下一阶段升级
- [[module-memory-tracker]] — 模块页
- [[sprint-precision-upgrade-chain]] — 升级链综合
