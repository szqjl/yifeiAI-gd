---
title: 升级规则
type: rule
category: Rules/Basic
source: .cursor/rules/guandan-knowledge.mdc
platform: 南京邮电大学平台 v1006
version: 3.0
last_updated: 2026-05-29
tags: [规则, 升级, 过A, 基础]
difficulty: 入门
priority: 5
---

# 升级规则

> **真源**：[guandan-knowledge.mdc](../../../../.cursor/rules/guandan-knowledge.mdc) §2、§6、§7 · 平台字段见 [README.md](../../../../README.md)

## 三等级字段

| 变量 | 含义 |
|------|------|
| `curRank` | **当前等级**（本副级牌点数；全场共用） |
| `selfRank` | 我方队伍等级（跨副累积） |
| `oppoRank` | 对方队伍等级（跨副累积） |

- 第一副初始：`curRank = selfRank = oppoRank = 2`
- 仅**本副获胜方**（须有人拿**头游**）按名次升级；落败方 `selfRank`/`oppoRank` 不变
- 下一副 `curRank` = 上副获胜方升级后的级数

## 每副升级（§6，两队独立结算）

以本副最终名次判定**己方**是否升级（对方逻辑相同、独立结算）：

| 本队名次 | 升级 |
|----------|------|
| 头游 + 二游（**双上**） | +3 级 |
| 头游 + 三游 | +2 级 |
| 头游 + 末游 | +1 级 |
| 本队**无人头游** | 不升级 |

级数取值：2、3、4、5、6、7、8、9、10、J、Q、K、A。

## 级牌与逢人配

- **级牌**：与当前 `curRank` 同点数的四花色牌；首副级牌为 2
- **逢人配**：当前级数的**红桃（H）**级牌；可与任意牌组合法牌型；**不得与大王、小王组牌**
- 进贡时须交最大牌，**红桃级牌除外**

牌型与比大小详见 [04_card_types_guide.md](04_card_types_guide.md)。

## 过 A / 赢一局（§7）

**赢一局**须同时满足：

1. 本队等级已为 **A**
2. **本副**（A 级）拿到 **双上**（头游 + 二游）

→ 整局（从 2 打到 A 的闯关）结束。

### A 级未赢局

- A 级**连续 2 副**未能赢一局 → 该队**降回 2 级**重打
- A↔2 循环满 **50 次** → 可判平局

### 易混（A 级本副）

| 本副名次 | 是否按 §6 升级 | 是否赢一局 |
|----------|----------------|------------|
| 头游 + 二游 | +3 | ✅ |
| 头游 + 三游 | +2 | ❌ 继续在 A 打 |
| 头游 + 末游 | +1 | ❌ |
| 无人头游 | 不升 | ❌ |

## 运行示例

```
第一副：curRank=selfRank=oppoRank=2 → 我方双上 → selfRank=5，下一副 curRank=5
第二副：我方头游+三游 → selfRank=7，下一副 curRank=7（oppoRank 仍为 2）
```

## 相关文档

- [08_basic_concepts.md](08_basic_concepts.md) — 术语
- [06_game_flow.md](06_game_flow.md) — 一副结束 `episodeOver`
- [06_game_flow.md](06_game_flow.md) — 进贡与首出
