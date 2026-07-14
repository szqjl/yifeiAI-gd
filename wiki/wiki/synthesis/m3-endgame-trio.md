---
type: synthesis
title: "M3 末段博弈三件套（GUA-034/035/036）"
sources:
  - docs/guandan-brain/issues/GUA-035-completion.md
  - docs/guandan-brain/issues/GUA-036-completion.md
tags:
  - synthesis
  - m3
  - endgame
  - trio
status: current
related_gua:
  - GUA-034
  - GUA-035
  - GUA-036
date: 2026-06-17
---

# M3 末段博弈三件套（GUA-034/035/036）

## 概述

[[GUA-034]] / [[GUA-035]] / [[GUA-036]] 三个 GUA 构成 M3 末段博弈的**递进式三件套**，按"拦头 → 末段过滤 → 控权+接风"的顺序解决末段决策问题。

## 演进结构

```
GUA-034  拦头（基础层）
   ↓
GUA-035  末段对手剩张过滤（END-M02+，solo_sprint 模式）
   ↓
GUA-036  控权压顺 + 接风配合（同级扩展，batch7 round38 驱动）
```

## 各阶段职责

| 阶段 | GUA | 解决的核心问题 |
|------|-----|----------------|
| 1. 拦头 | [[GUA-034]] | 末段开局抢牌权 |
| 2. 末段过滤 | [[GUA-035]] | 对手剩 1/2/5 张时的送牌过滤 |
| 3. 控权+接风 | [[GUA-036]] | 被动压敌顺、接风禁拆、接风让道 |

## 共同关单口径

> **pytest 构造态 + 回归通过即可关单**；不绑定具体 game_id

这与早期"末段要让道让赢"的类目标形成**明确区分**——本批 GUA 是**机制定义**，不承诺具体局面的最优结果。

## 推迟到 V5+ 的内容

- 整手组牌
- 可回收单张完整评分
- 两手规划

> M3 末段博弈的天花板已被本三件套**钉死**，V5+ 是必要跃迁。

## 依赖与回归

### GUA-035 回归集合
- `test_m3_gua034`
- `test_m3_gua026`
- `test_m3_gua029`
- `test_m3_gua031`

### GUA-036 完整依赖
- `GUA-026`、`GUA-029`、`GUA-031`、`GUA-032`、`GUA-034`、`GUA-035`

### GUA-036 关联回放
- `batch7 round38`（驱动来源）

## 与 V7 主迭代的衔接

- **V7 是未来方向**：M3 规则引擎已达瓶颈
- **V5+ 是中间过渡**：本三件套的未实现部分将由 V5+ 承载
- **V7 NN 引擎**：长期目标

## 关联

- [[m3-endgame-guard]] - 末段博弈综合（待更新为三件套视角）
- [[gua-034]] - 拦头
- [[gua-035]] - 末段过滤
- [[gua-036]] - 控权+接风
- wiki-minimax/entities/engine-m3.md - M3 引擎
- wiki/synthesis/synthesis-v7-current-state.md - V7 当前状态（需协调叙事）
