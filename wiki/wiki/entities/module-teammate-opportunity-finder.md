---
type: entity-module
title: "TeammateOpportunityFinder (P0-③ 主动传牌给队友)"
sources:
  - docs/analysis/agent-sessions/p0_complete_summary.md
  - docs/analysis/agent-sessions/P0_IMPLEMENTATION_COMPLETE_20260528.md
tags:
  - m1-engine
  - p0-③
  - cooperation
  - passive-handler
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# TeammateOpportunityFinder (P0-③)

## 基本信息

- **文件名**：`teammate_opportunity_finder.py`
- **规模**：176 行 / 7272 bytes
- **所属引擎**：`M1`
- **状态**：✅ 实现 + 集成（4 个 PassiveHandler）
- **关键 Commit**：`f4de5b7`

## 职责

识别队友可能跑牌的机会，**主动传牌配合**。

## 核心洞察：为什么集成到 Passive？

**传牌本质是协作非攻击**。

- **ActiveHandler（出牌方）**：关心"出哪张最优"
- **PassiveHandler（接牌方）**：关心"是否传牌给队友"

如果队友即将跑牌，接牌方（Passive）应主动垫牌而非自己跑。这种判断逻辑属于"接牌决策"而非"出牌决策"，因此集成到 Passive 是更合理的设计选择。

## 集成点（4 个 PassiveHandler）

| Handler | 集成位置 |
|---------|----------|
| `OpeningPassiveHandler` | L524-547 |
| `MidEarlyPassiveHandler` | L1428-1455 |
| `MidLatePassiveHandler` | L2303-2326 |
| `EndgameEarlyPassiveHandler` | L2940-2963 |

## 核心能力

| 能力 | 说明 |
|------|------|
| 队友牌力估算 | 推断队友剩余牌组成 |
| 跑牌机会识别 | 判断队友是否能一次清完 |
| 传牌路径规划 | 决定传哪张/哪些张给队友 |
| 风险评估 | 避免传牌后被对手打断 |

## 调优参数

- `teammate_remain`：15 → **12**（激进调优，更早识别队友机会）
- `card_power`：4 → **3**（更宽松的传牌触发）

## 关联

- wiki/concepts/p0-m1-cooperation-improvements.md — P0 改进设计哲学
- [[engine-m1]] — M1 引擎
- [[module-history-tracker]] — 历史追踪是传牌判断的基础
