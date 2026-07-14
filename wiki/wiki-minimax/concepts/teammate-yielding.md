---
type: concept
title: "队友让道与传牌策略"
sources:
  - docs/guandan-brain/issues/GUA-031-completion.md
  - docs/guandan-brain/principles/01_passing_skills.md
tags:
  - concept
  - teammate-yielding
  - passing
  - cooperation
status: current
related_gua:
  - GUA-031
  - GUA-029
  - GUA-026
date: 2026-06-17
---

# 队友让道与传牌策略

## 定义

掼蛋作为 2v2 团队游戏，M3 决策引擎在主动/被动场景下**主动让队友接牌 / 不抢队友牌权**的策略集合，由 GUA-031 定义为 PASS-P01~P04 四原则。

## 四原则总览

| 原则 | 场景 | 动作 | 置信度 |
|------|------|------|--------|
| **PASS-P01** | 主动 | 送小单让队友接牌 | high |
| **PASS-P02** | 主动 | 防送炸（不主动给队友出炸机会） | high |
| **PASS-P03** | 被动 | `_is_teammate_greater` 时 `return 0` 让道 | high |
| **PASS-P04** | 主动 | 逢五喂队友 | **low** |

## 主动场景（`_active` 分支）

### PASS-P01 — 送小单

- **触发**：检测到队友可能接牌（如队友已出单张、我方有更小单张）
- **动作**：出最小单张，让队友接牌继续牌权
- **目的**：保持队友牌权、避免抢队友牌型

### PASS-P02 — 防送炸

- **触发**：我方有炸弹、队友可能接牌
- **动作**：**不主动出炸弹**（即使牌型允许）
- **目的**：避免给队友制造"必须压炸弹"的局面

### PASS-P04 — 逢五喂队友（弱推断）

- **触发**：当前出牌点数为 5（如 5 张单 / 5 张连）
- **动作**：故意出小牌喂队友
- **置信度**：**low**（弱推断，来源于 `01_passing_skills.md` 描述性原则）
- **验证需求**：需更多批跑数据验证胜率提升

## 被动场景（`_passive` 分支）

### PASS-P03 — 让道

- **触发**：`_is_teammate_greater(teammate, me) == True`
- **动作**：`return 0`（不出牌，让队友接管）
- **目的**：队友牌力更强时主动让道

## 关键辅助函数

### `_is_teammate_greater(teammate_cards, my_cards)`

判断队友当前手牌是否大于我方：

- 比较剩余手牌数量
- 比较最大牌点数
- 比较牌型强度

## 决策优先级

```
_active 分支:
  1. 检测队友冲刺意图 → PASS-P01（送小单）
  2. 若我方有炸弹 → PASS-P02（防送炸）
  3. 若点数 = 5 → PASS-P04（逢五喂队友，flag 控制）

_passive 分支:
  1. _is_teammate_greater → PASS-P03（return 0）
  2. 否则按正常被动逻辑出牌
```

## 边界澄清

| 相关 GUA | 关系 |
|----------|------|
| **GUA-026** | GUA-031 不放宽其"三带二禁拆炸弹/耗级牌"保护 |
| **GUA-029** | GUA-031 不放宽 R5"不压队友"原则 |

## 不确定性管理

### PASS-P04 的 confidence=low 标注

- **来源**：`01_passing_skills.md` 的描述性原则，未经过严格的批跑验证
- **风险**：可能引入负向优化（喂队友反而导致牌权流失）
- **缓解措施**：
  1. 实现时以 flag 控制默认开关
  2. 净盘 M3 批跑中对比启用/不启用 PASS-P04 的胜率
  3. 若胜率提升则默认启用，否则保持关闭

## 实现位置

- `m3_utils._is_teammate_greater` — 辅助函数
- `m3_utils._active` — PASS-P01/P02/P04
- `m3_utils._passive` — PASS-P03
- `m3_utils.one_hand` — 决策入口

## 验证标准

- 单元测试：`test_m3_gua031.py` 覆盖 PASS-P01~P04
- 批跑验证：wiki-minimax/concepts/batch-evaluation.md 净盘 M3 批跑
  - 观察主动场景送牌率
  - 观察被动场景让道率
  - PASS-P04 启用 vs 不启用胜率对比

## 关联页面

- [[gua-031]] — GUA 完整条目
- [[gua-029]] — 炸弹执行规则（边界）
- [[gua-026]] — 拆牌保护（边界）
- [[bomb-execution-rules]] — 炸弹可执行规则
- wiki-minimax/entities/engine-m3.md — M3 决策引擎
- wiki-minimax/concepts/batch-evaluation.md — 批跑评测体系
