---
type: concept
title: "solo sprint（残局 solo 冲刺）"
sources:
  - docs/guandan-brain/iterations/m3-guards-gua031-036.md
tags:
  - 概念
  - 残局
  - solo
status: current
related_gua:
  - GUA-034
  - GUA-035
date: 2026-07-15
---

# solo sprint（残局 solo 冲刺）

## 定义

当本方仅剩 1 名玩家（队友已升级或被关）且进入收官阶段时，激活的高强度残局策略模式。

## 触发判定 `_is_solo_sprint`

- 本方存活玩家数 == 1
- 本人手牌 ≤ 5 张
- 对手 ≥ 2 名玩家进入收官

## 方向选择

| 方向 | 含义 | 状态 |
|------|------|------|
| A | 优先拦对手头游 | 当前实施（[[gua-034]]） |
| B | 优先自己冲头游 | 未实施 |

## 配合模块

- [[gua-035]]：对手剩张过滤（1/2/5 张差异化）
- [[gua-031]]：传牌 guard（solo 模式可放宽）

## 关联

- 实体：[[gua-034]]
- 引擎：[[engine-m3-strategy-bundle]]

## C 情形示例（结构性稳定解·2026-07-24 v8-sf-endgame-c-scenario-correction）

> **场景**：本方 68/91 步剩 4 张（SB + J 炸 + SF A-5 + Q），对手 @3 剩 8 张（如 SF 9-K + 单 K + 对 8）。

### 常见误判

- 把 "opp 持 SF 9-K" 机械等同为 opp 必胜。
- 误判 "Option B（@3 PASS）→ yf2 后续任意出牌被 SF 9-K 吃 → opp 头游"。

### 正确反制链（Option B 路径）

| 步 | yf2 | @3 | yf1 | @1 | 牌面 |
|---|---|---|---|---|---|
| 68 | **SB** | PASS | PASS | PASS / 大王 / 炸 | 4 - 1 = 3 张 |
| 69 | **J 炸** 或 **SF A-5** 反压制回收 | — | — | — | 2 张 |
| 70 | **Q** | — | — | — | 1 张 |
| 71 | **SF A-5** 或 **J 炸** 收官 | — | — | — | 0 张 |

**结果**：yf2 头游，@3 的 8 张整局锁死。

### Option A 反制（@3 出 SF 9-K 吃 SB）

- @3 出手后剩 K + 对 8 = 3 张 → yf2 出 K → @3 对 8 → yf2 J 炸回收。
- **@3 主动升级反而败得更快**。

### 关键隐性约束

- **SF 不可拆**：opp 持 SF 9-K 时，K 不可单独出（被 yf2 SB 抢出牌权）。
- **双重反压制通道**：yf2 的 SB 反压制 + J 炸回收，两条通道任一条成立即 yf2 头游。
- **SF 越强越不敢出**：SF 9-K 越强，opp 越不敢出（出就被炸回收），opp 越不出，yf2 越安全清场。

### 引擎策略

- **68/91 应当 SB 领出**，而非 SF 5 张同花顺 lead-1（属于 GUA-159「同型可压时禁炸弹 lead-1」/ GUA-160「队友冲刺期散单优先」框架）。
- **不必新增 `_has_dominating_sprint` 拦截**（过度防御，C 情形结构性稳定解已通过现有规则覆盖）。
- **不属于本 wiki 触发的 solo-sprint 模式**（5 张约束 + 队友存活数约束），但策略同源。

### 锚点

- `game_records_v8/20260724070916808898 [yf2_v8]-[opponent_1_3]-[8]-[2].json` 步 68/91

### 关联

- ITERATIONS: `v8-sf-endgame-c-scenario-correction`（GUA-161-post observation）
- GUA-159（同型可压禁炸弹 lead-1）
- GUA-160（队友冲刺散单优先）
- GUA-161（同牌 multiset Straight→StraightFlush 强声明）
