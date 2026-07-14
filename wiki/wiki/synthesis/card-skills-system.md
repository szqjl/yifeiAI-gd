---
type: synthesis
title: "掼蛋牌型技巧体系"
sources:
  - docs/knowledge/skills/04_common_skills/01_pair_skills.md
  - docs/knowledge/skills/04_common_skills/01_single_card_skills.md
  - docs/knowledge/skills/04_common_skills/02_card_language.md
  - docs/knowledge/skills/04_common_skills/03_card_interactions.md
  - docs/knowledge/skills/04_common_skills/04_calculation_skills.md
tags:
  - synthesis
  - card-skills
  - system
status: current
related_gua:
  - GUA-031
  - GUA-062
  - GUA-063
  - GUA-064
  - GUA-065
date: 2026-06-18
---

# 掼蛋牌型技巧体系

## 体系结构

五个 skills 文档形成**完整的"判断→策略"闭环**：

```
┌─────────────────────────────────────────┐
│  算牌（数据层）                          │
│  → 概率分布、大小王、5/10 定律           │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  相生相克（关系层）                      │
│  → 牌型关系矩阵、喂牌方向                │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  牌语（信号层）                          │
│  → 首出信号、组合信号、意图识别           │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  对子 / 单张（执行层）                   │
│  → 具体牌型的组/顺/顶/让/封/逼/送/抢/拆  │
└─────────────────────────────────────────┘
```

## 牌型概率统计（五个文档一致）

| 牌型 | 占比 |
|------|------|
| 单牌 | 49.55% |
| 对子 | 24.77% |
| 三张 | 8.22% |
| 顺子 | 4.11% |
| 连对 | 2.05% |
| 钢板 | 1.02% |
| 炸弹 | 5.13% |
| 同花顺 | 2.05% |

> ✅ **跨文档一致性已确认**

## 引擎映射全景

| 原则 | M3 | V5+ / V7 |
|------|-----|----------|
| 对子技巧 §十 | 部分 | 完整 |
| 单张技巧 §十一 | 阈值可实施（GUA-062） | 完整 |
| 牌语 §十二 | ❌ | ⏳ GUA-064 |
| 相生相克 §十三 | ❌ | ⏳ GUA-065 |
| 算牌 §十四 | ❌ | ⏳ GUA-063 |

## 关键洞察

> M3 对这 5 个新 skill 文档**几乎无新增 P0/P1 实施**，全部 deferred 到 V5+。
>
> 这印证了 **V7 NN 引擎的必要性**——规则引擎难以表达 4 人合作博弈中的策略意图传递。

## 关联

- wiki/concepts/role-conversion.md
- [[concept-pair-first-strategy]]
- wiki/concepts/card-language.md
- wiki/concepts/card-interactions.md
- wiki/concepts/calculation-laws.md

---
