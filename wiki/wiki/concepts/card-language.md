---
type: concept
title: "掼蛋牌语 (Card Language / 读牌)"
sources:
  - docs/knowledge/skills/04_common_skills/02_card_language.md
tags:
  - card-language
  - observation
  - intent-recognition
status: current
related_gua:
  - GUA-027
  - GUA-064
date: 2026-06-18
---

# 掼蛋牌语 (Card Language)

## 核心原则

> **鸟有鸟语，牌手出牌传递信息。**

牌手通过出牌的**类型、大小、顺序、组合**传递牌力与意图信息。

## 座位定位

```python
上家 = (myPos - 1) % 4
下家 = (myPos + 1) % 4
队友 = (myPos + 2) % 4
```

> 公式已被 [[gua-027]] 覆盖。

## 首出信号字典

| 首出 | 信号 |
|------|------|
| 小单 | 牌力强 |
| 对子 | 试探 |
| 高单 | 助攻定位 / 交牌权 |
| 小顺 | 有打有收 |
| 木板/钢板 | 中性 |
| 三张 | 弱牌 |

## 牌型组合信号

- **三带二带对大小** → 暗示是否希望队友传三带二
- **相邻炸弹顺序** → 暗示是否还有炸弹
- **33399** → 家里可能有 4-8 顺子
- **4 张同花顺** → 无红心配

## 引擎实施

| 引擎 | 状态 |
|------|------|
| M3 | ❌ 无观察层 |
| V5+ / V7 | ⏳ 需要 `observation_layer` + `intent_recognition` |

## 关联

- [[gua-027]] — 座位公式
- [[gua-064]] — 牌语系统（拟）
- wiki/concepts/card-interactions.md — 相生相克
- wiki/concepts/calculation-laws.md — 算牌定律
- wiki/sources/skills-04-card-language-summary.md

---
