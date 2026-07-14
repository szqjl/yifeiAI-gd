---
type: source-summary
title: "知识库格式化方案 — 摘要"
sources:
  - docs/knowledge/知识库格式化方案.md
tags:
  - knowledge
  - format-spec
  - naming-convention
  - m3-era
status: current
related_gua: []
date: 2026-06-18
---

# 知识库格式化方案 — 摘要

## 来源

- **原始文件**：`docs/knowledge/知识库格式化方案.md`（20015 字符）
- **覆盖范围**：`docs/knowledge/rules/` 与 `docs/knowledge/skills/` 两大子目录

## 目录结构（17 个知识文件）

### 规则类（rules/）
- `01_basic_rules/` — 基础规则
- `02_competition_rules/` — 竞赛规则
- `03_advanced_rules/` — 高级规则

### 技巧类（skills/）
- `01_foundation/` — 基础技巧
- `02_main_attack/` — 主攻技巧
- `03_assist_attack/` — 助攻技巧
- `04_common_skills/` — 通用技巧
- `05_psychology/` — 心理技巧
- `06_advanced/` — 高级技巧
- `07_opening/` — 开局技巧
- `08_endgame/` — 残局技巧

## 平台标准变量名规范

> ⭐ 文档中存在多次"⭐更正"痕迹，**当前已定稿的命名**如下：

### 牌型（Card Types）

| 变量名 | 含义 | 备注 |
|--------|------|------|
| `Single` | 单张 | |
| `Pair` | 对子 | |
| `Triple` | 三张 | |
| `Bomb` | 炸弹 | |
| `StraightFlush` | 同花顺 | ⭐原"同花顺"已更正 |
| `Tube` | 钢板（三连对）| |
| `Plate` | 钢板（三连张）| |
| `Sequence` | 顺子 | |
| `HR` | 大王花色（红心主牌） | ⭐更新 |
| `SB` | 小王花色（黑桃主牌） | ⭐更新 |

### 位置与玩家

| 变量名 | 含义 | 备注 |
|--------|------|------|
| `curPos` | 当前位置 | |
| `myPos` | 己方位置 | |
| `downPos` | 下家 | `(myPos + 1) % 4` |
| `upPos` | 上家 | `(myPos - 1) % 4` |
| `teammatePos` | 对家 | `(myPos + 2) % 4` |

### 进贡阶段

| 变量名 | 含义 |
|--------|------|
| `tribute` | 进贡动作 |
| `back` | 还贡动作 |
| `PASS` | 不进/不还 |

## 跨域关联

- 命名规范是 [[concept-platform-variable-naming]] 的源材料
- 与 [[source-skills-31-passing-skills-summary]] 等已有 skills summary 一一对应
- 助攻目录对应 [[concept-passing-skills-matrix]]

## 待跟进

- 确认 `HR`/`SB` 命名在最新代码中是否已被采纳
- V7 NN 引擎是否沿用此命名规范作为特征工程输入
