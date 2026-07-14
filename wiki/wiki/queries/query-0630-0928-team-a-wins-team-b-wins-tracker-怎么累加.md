---
type: query-answer
title: "team_a_wins team_b_wins tracker 怎么累加"
date: 2026-06-30
sources:
---

# team_a_wins team_b_wins tracker 怎么累加

# 不知道

Wiki 中没有 `team_a_wins` / `team_b_wins` tracker 的累加逻辑或实现位置。

当前检索覆盖的相关页面（残局管线、决策管线、MemoryTracker、组牌引擎、M3 引擎债务、历史追踪等）均**未涉及**队胜计数字段的累加规则。

## 可能的线索方向（未在 Wiki 中确认）

如果你要查的是：

1. **离线批跑评测的局胜累计** → 查 [[batch-evaluation]] 相关页面（本次未命中）
2. **MemoryTracker 的 hand_counts 累加**（每个玩家剩余手牌数）→ 见 [[gua-078]] / `end-position-design-summary.md` §五（残局管线入口）— 这是**手牌数累加**，不是"队胜"累加
3. **v7-win-rate-history** 里的累计胜率 → 见 [[gua-052]] 提及的 `v7-win-rate-history.md`（累计队胜 100% 那一段），但这是**统计结果**而非累加代码

## 建议

请补充：
- 这是**哪条管线 / 哪个模块**的字段？（v7 引擎 / 批跑框架 / 复盘脚本？）
- 是在**对局过程中累加**还是**复盘统计时累加**？
- 是否能指一个文件路径或 GUA 编号？

否则 Wiki 里没有足够信息可以回答。
