---
type: concept
title: "首圈领出规则"
sources:
  - docs/knowledge/rules/01_basic_rules/06_game_flow.md
tags:
  - rules
  - game-flow
  - lead
status: current
related_gua: []
date: 2026-06-18
---

# 首圈领出规则

## 核心定义

**首圈领出**：每副牌开始时，决定由谁先出第一张牌的规则。

## 规则细则

| 场景 | 领出者 |
|------|--------|
| 第一副 | 服务器决定 |
| 第二副起（普通进贡） | 进贡给上游者（受贡者）领出 |
| 双下情况 | 三游领出（进贡是末游→头游 + 三游→二游） |
| 抗贡情况 | 上游（头游）领出 |
| 无进贡（普通升级） | 上游（头游）领出 |

## 平台 JSON 动作

```json
{
  "act": "PlayCards",
  "stage": "play",
  "player": <seat_id_of_lead>
}
```

平台在 `episodeOver` 之后、下一个 `play` stage 之前，会指明领出者座位。

## ⚠️ 冲突与定音

| 来源 | 描述 |
|------|------|
| 实体赛旧规 | 「下游领出」（指上一副的末游） |
| 平台现行 | 「进贡给上游者领出」 |

**M3 引擎与批跑数据：以平台 act 为准**（即上表「第二副起」规则）。

## 关联页面

- 来源：[[source-rules-06-game-flow-summary]]
- 概念：concept-round-vs-game-multi-level、[[concept-three-rank-fields]]
- 引擎：wiki-minimax/entities/engine-m3.md

## 反例

- 不要假设「第一副永远是某个固定位置出」
- 不要使用「下游领出」描述第二副起的领出规则
