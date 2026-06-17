---
title: 游戏流程规则
type: rule
category: Rules/Basic
source: .cursor/rules/guandan-knowledge.mdc, 江苏掼蛋规则.md
platform: 南京邮电大学平台 v1006
version: 4.0
last_updated: 2026-05-29
tags: [规则, 流程, 进贡, 基础]
difficulty: 入门
priority: 5
---

# 游戏流程规则

> **真源**：[guandan-knowledge.mdc](../../../../.cursor/rules/guandan-knowledge.mdc) §1、§5 · 平台 `stage` 见 [guandan-platform-v1006.mdc](../../../../.cursor/rules/guandan-platform-v1006.mdc)

## 一副牌流程（标准）

108 张发完、每人 27 张 →（**第二副起**：进贡 → 还贡，或抗贡）→ 多**圈**出牌 → 四人完牌顺序确定（`episodeOver.order`）→ 升级并决定下副进贡。

**一副 ≠ 一圈 ≠ 比赛一轮 ≠ 一局**（详见 [08_basic_concepts.md](08_basic_concepts.md)）。

## 平台阶段（`stage`）

| stage | 说明 |
|-------|------|
| `beginning` | 发牌完成（首副直接进 play；官方 notify 示例无三等级字段） |
| `tribute` | 进贡（第二副起，见下文） |
| `anti-tribute` | 抗贡广播（双大王免进贡） |
| `back` | 还贡 |
| `play` | 出牌（多圈直至四人名次确定） |
| `episodeOver` | **一副结束**（小局）；`order`、`curRank`、可选 `restCards` |
| `gameOver` | 跑满平台参数 N（**局**，非副数） |
| `gameResult` | 累计 `victoryNum` / `draws` |

平台变量：进贡 `tribute`、还贡 `back`（JSON 动作 `["tribute","tribute",[...]]` / `["back","back",[...]]`）。

## 进贡 / 还贡 / 抗贡（第二副起）

> 与 [guandan-knowledge.mdc](../../../../.cursor/rules/guandan-knowledge.mdc) §5 一致。  
> **易混**：抗贡 = **双大王**，不是「上副双上」；上副对方双上时，本队可能**双进贡**。

### 单下（上副仅末游为对方）

- **进贡**：本副 **末游** 向 **头游** 进全手牌中**牌点最大**的一张（**红桃级牌除外**；平台自动跳过逢人配）
- **还贡**：头游还 **10 点（含）以下** 任意一张；若手牌均大于 10，则还**牌点最小**的一张
- **首圈**：还贡后，通常由**进贡给上游者**首圈领出（实体赛常表述为下游领出；以平台 `act` 为准）

### 双下（上副对方占据头游 + 二游）

- **进贡**：己方 **三游 → 对方头游**，**末游 → 对方二游**
- **还贡**：头游还给三游**牌点较大**的一张；二游还给末游**牌点较小**的一张（仍须满足还贡 ≤10 或最小牌规则）
- **首圈**：还贡后，由**进贡给上游者**（三游）首圈领出

### 抗贡

- 应进贡者（末游，或双下时两人）手中有 **双大王** → **免进贡**
- 平台 `anti-tribute` 广播后，**首圈由上游领出**

### 平台提示

- 进贡 / 还贡阶段 `act` 带 `selfRank` / `oppoRank` / `curRank`
- v1006 由服务器驱动阶段与合法 `actionList`，客户端回 `{"actIndex": N}`

## 一圈出牌

- 一人首发，其余三人逆时针跟压或过牌
- **连续三人过牌** → 本圈结束；最后出牌成功者**接风**，下一圈由其（或队友接风规则下）首发
- 一副内含**多圈**

## 首圈领出（摘要）

| 场景 | 首圈 |
|------|------|
| 第一副 | 平台服务器决定（实体赛：翻牌定首抓者） |
| 第二副起，正常进贡 | 进贡给上游者领出（双下时为三游） |
| 抗贡 | 上游领出 |

## 出牌顺序

- 座位逆时针：0 → 1 → 2 → 3 → 0 …
- 须压当前圈最大牌型或 `PASS`
- 接风时平台常见：`curPos=-1`，`curAction`/`greaterAction` 为 `None`

## 术语（升级 / 牌型见专文）

| 术语 | 含义 |
|------|------|
| 一手牌 | 一次打出的牌组（`actionList` 一项） |
| 一圈牌 | 领出至连续三人过牌 |
| 头游～末游 | 完牌顺序四名 |

## 相关文档

- [05_card_distribution.md](05_card_distribution.md)
- [07_upgrade_rules.md](07_upgrade_rules.md)
- [04_card_types_guide.md](04_card_types_guide.md)
- [08_basic_concepts.md](08_basic_concepts.md)
