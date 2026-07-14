---
type: concept
title: "队伍联动（主动传牌 / 接风 / 压制对手）"
sources:
  - docs/analysis/agent-sessions/04-guandan-mechanics.md
  - docs/analysis/agent-sessions/07-p0-implementation-verification.md
tags:
  - concept
  - Lv2
  - team
status: current
related_gua:
  - GUA-003
date: 2026-05-28
---

# 队伍联动

## 核心思想

掼蛋是 2v2 游戏，**单牌最优 ≠ 双上**。需主动与队友配合：
- 主动传牌给队友（让队友上手）
- 接风判主动（队友打完一轮，自己接风成主动）
- 压制对手（阻止对手成主动）

## lalala vs M1 关键差异

- lalala：22 副对局 100% 双上 → 队友配合完美
- M1/M3：22 副对局 0% 双上 → 几乎没有队友意识

## 实现

- `src/decision/teammate_opportunity_finder.py`（176 行）
- 集成到 4 个 PassiveHandler
- 评估：队友是否需要这张牌 / 队友能否成主动

## 验证

- 20 局 0 触发 → 高度怀疑 dead code 或条件过严

## 关联页面

- [[gua-003]]
- concepts/strategic-layers
- concepts/double-up-mechanic
