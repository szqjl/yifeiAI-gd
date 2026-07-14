---
type: concept
title: "V7 模块化架构（GUA-061 方向）"
sources:
  - docs/guandan-brain/MOCs/V7-Development.md
tags:
  - methodology
  - v7
  - p0
  - current-direction
status: current
related_gua:
  - GUA-061
  - GUA-060
date: 2026-06-18
---

# V7 模块化架构（GUA-061 方向）

## 背景
BC 模仿学习路径已死（见 wiki/concepts/bc-argmax-collapse.md），V7 必须转向**模块化架构**以突破 3.0% 队胜率。

## 核心五阶段路径
```
组牌 → 角色定位 → 记忆追踪 → 动态调整 → 动作选择
```

### 阶段说明
| 阶段 | 功能 | 候选模块 |
|------|------|---------|
| 1. 组牌 | 当前手牌的最佳牌型组合 | `static_features.py` |
| 2. 角色定位 | 己方在同桌中的角色（主攻/辅助/控场） | 待实现 |
| 3. 记忆追踪 | 追踪已出牌与剩余牌分布 | `memory_tracker.py` (24 维) |
| 4. 动态调整 | 根据记忆与角色调整策略 | `dynamic_features.py` (LSTM 64 维) |
| 5. 动作选择 | 输出最终动作 | `v7_guards.py` (R01~R06) 做硬约束 |

## 优势（vs 端到端 BC）
- 每个阶段可独立训练、调试、验证
- 减少单点坍缩风险
- Guard 壳策略保证规则合规

## 风险
- 模块间接口设计复杂
- 误差在各阶段累积
- 阶段 2（角色定位）当前缺乏成熟方案

## 关联页面
- [[gua-061]]
- wiki/entities/engine-v7.md
- [[module-v7-features]]
- [[module-v7-guards]]
- wiki/concepts/bc-argmax-collapse.md
