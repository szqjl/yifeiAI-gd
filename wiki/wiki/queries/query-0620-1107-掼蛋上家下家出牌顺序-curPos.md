---
type: query-answer
title: "掼蛋上家下家出牌顺序 curPos"
date: 2026-06-20
sources:
  - concepts/concept-platform-variable-naming.md
  - sources/source-knowledge-format-spec-summary.md
  - sources/source-skills-01-basic-principles-summary.md
---

# 掼蛋上家下家出牌顺序 curPos

# 掼蛋上家下家出牌顺序与 `curPos`

## 核心结论

按平台标准变量名规范，**上家、下家的位置关系是相对于 `myPos`（己方位置）计算的**，`curPos` 是当前出牌者的位置，而非固定指向某一方。 [{1}][{2}]

## 位置关系公式（顺时针）

```
downPos = (myPos + 1) % 4   // 下家
upPos   = (myPos - 1) % 4   // 上家
teammatePos = (myPos + 2) % 4  // 对家
```

**出牌顺序**：掼蛋是 4 人游戏、2v2 配对制。按 `curPos` 视角，下一轮接牌方 = `(curPos + 1) % 4`（即下家先接）。 [{1}]

## 关键变量

| 变量 | 含义 |
|------|------|
| `myPos` | 己方位置（固定锚点） |
| `curPos` | 当前位置（当前出牌方，随轮次推进） |
| `downPos` | 下家 |
| `upPos` | 上家 |
| `teammatePos` | 对家 |

## ⚠️ 命名一致性提醒

在 `01_basic_principles.md` 文档中，牌型命名用的是旧版（`Trips` / `Straight` / `ThreePair` / `TwoTrips` / `ThreeWithTwo`），而平台最新定稿用的是 `Triple` / `Sequence` / `Tube` / `Plate`。 [{2}][{3}]

**位置命名一致**：`myPos` / `curPos` 在新旧文档中保持一致，没有歧义。

## 参考页面
- [{1}] 平台标准变量名规范
- [{2}] 知识库格式化方案 — 摘要
- [{3}] 掼蛋原则体系摘要
