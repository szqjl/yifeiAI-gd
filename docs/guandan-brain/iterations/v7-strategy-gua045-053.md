---
tags: [V7, strategy, GUA-045, GUA-051, GUA-052, GUA-053, guards]
created: 2026-06-07
updated: 2026-06-17
topic: V7 Guard 壳与策略增补
related: [[V7-Development]], [[v7-features-gua037-038]]
---

# V7 Guard 壳与策略增补（GUA-045 / GUA-051~053）

> 来源：[[ITERATIONS]] 2026-06-07 ~ 2026-06-17

## GUA-045：V7 P0 Guard 壳

| 日期 | 迭代 | 内容 |
|------|------|------|
| 2026-06-07 | 落地 | V7-R01~R06：不炸单张、最小炸弹、被动不 PASS、单张必出、不压队友、不拆结构对子；pytest **24/24 passed** ✅ |
| 2026-06-07 | 回归 | 48 passed（含其他测试）；**GUA-045 closed** ✅ |

**涉及文件**：
- `src/v/nn/guards/v7_guards.py`
- `src/decision/ultimate_win_rate_engine_v7.py`（decide() 集成 guard）
- `tests/test_v7_gua045.py`

## GUA-051：稠密 Reward（9 种）

- `src/v/nn/training/reward.py`：play_success/wind_catch/guan_dan/level_control/coordination/feed_partner/bomb±/self_upgrade/opponent_upgrade + RewardAccumulator
- `tests/test_v7_reward_gua051.py` **12 passed**；**GUA-051 closed** ✅

## GUA-052：全量记牌 MemoryTracker

- `src/v/nn/features/memory_tracker.py`：108 张牌全量追踪 + 排除法推断 + 24 维 state_vector + 性能风险管控
- `tests/test_v7_memory_tracker_gua052.py` **10 passed**；**GUA-052 closed** ✅

## GUA-053：方案增补套路登记

- 仅文档：[`ISSUES.md`](ISSUES.md) 登记 GUA-050~053（V7 方案增补 4 套路）
- 目的：在原 V7 方案上增补「信念+配合+多样化」三要素
- 随机应变覆盖度目标：~25% → ~70%
