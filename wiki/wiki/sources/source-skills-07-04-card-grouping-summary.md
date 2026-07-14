---
type: source-summary
title: "组牌技巧摘要 (skills/07/04)"
sources:
  - docs/knowledge/skills/07_opening/04_card_grouping_skills.md
tags:
  - source-summary
  - skills
  - card-grouping
  - opening
status: current
related_gua:
  - GUA-026
  - GUA-030
  - GUA-031
  - GUA-032
date: 2026-06-18
---

# 组牌技巧摘要 (skills/07_opening/04)

## 概述

掼蛋组牌技巧的系统化文档，覆盖**组牌总纲**、**牌力计算法**、**主攻/助攻定位**、**多策略并行**、**配牌（逢人配）**、**去单化**、**炸弹取舍**等核心方法论。文档既包含口诀级别的实战口诀，也包含可被 V7 引擎直接落地的评分规则表。

## 关键结构

### 1. 组牌总纲（P-G01）
- **三大总目标**：去单化 + 最小轮次 + 牌型变化余地（活牌）
- **组牌顺序优先级**：同花顺 → 炸弹 → 整牌（钢板/三带二/三连对/顺子/连对）→ 配牌
- **变化余地原则**：能组三带二不组三连对（留变化）

### 2. 牌力计算法（V7 _score_power）
- **5 维评分公式**（V7 引擎）：
  - 炸弹权重 0.3
  - 手数权重 0.3
  - 回收权重 0.1
  - 灵活权重 0.1
  - 去单化权重 0.2
- **4 级牌力分级**：
  - 超强牌 ≥8 分
  - 强牌 5-7 分
  - 中弱牌 2-4 分
  - 超弱牌 <2 分
- **主攻/助攻临界**：4-5 分

### 3. 角色定位
- **主攻组牌**：全面组牌，奔最大化（>5 分）
- **助攻组牌**：精简配火，保留变化（<4 分）
- **超弱牌组牌**：配火优先，过渡为主（<2 分）
- **角色转换**：主攻转助攻（残牌兜底）

### 4. 多策略并行
- NO_STRAIGHTS（无顺子）
- BALANCED（平衡）
- ROUND_OPTIMAL（轮次最优）

### 5. 配牌（逢人配）6 策略
- 配炸弹（保留其他牌型）
- 补缺（如 2-3-4-5-6 配 H 变同花顺）
- 配顺子
- 配木板（三连带）
- 配三带二
- 预留策略

### 6. 炸弹取舍
- 一炸保两单（拆炸要兜底）
- 破二炸弹不能搭（拆二炸得不偿失）
- 配 5/6 头炸取舍（忌配 5 头炸）
- 宜配中小不配大

### 7. 去单化与赘牌消除
- 顺子吸收单张
- 夯吸收对子
- 封顶策略（拆王、拆级牌）

### 8. 孤张定律 & A 下放原则
- 孤张不打
- A 必下放（避免 A 死压）

## 与现有 Wiki 的关联

- 上游原则：[[concept-guandan-principles-pillars]]、[[concept-card-type-probability]]
- 引擎映射：[[gua-030]]、[[concept-engine-mapping-principles]]
- 传牌技巧：[[gua-031]]、[[concept-passing-skills-matrix]]
- 行牌 guard：[[gua-026]]、[[gua-032]]

## 下游概念页（已生成）

- [[concept-card-grouping-principles]] — 组牌三大总纲
- [[concept-power-scoring]] — 牌力计算法
- [[concept-role-positioning]] — 主攻/助攻定位
- [[concept-wild-card-usage]] — 逢人配使用策略
- [[concept-bomb-vs-straightflush]] — 炸弹与同花顺取舍
- [[concept-singles-reduction]] — 去单化与赘牌消除

## 引擎映射

| 引擎 | 组牌路径 | 牌力分 |
|------|---------|--------|
| M3 | `combine_handcards` 单路径 + CG-G01/B03/B05 可选 P2 | 无量化 |
| V5+ | `enumerate_groupings` + 牌力分 | CG-R01–R07 |
| V7 | `enumerate_groupings` + 5 维 _score_power | CG-R01–R08（5 维权重） |

## 已知限制

- **"首发 +1 分"**：口诀建议但 V7 引擎暂未实现，待后续 GUA
- **配 5 头炸**：口诀建议"忌配"，但 V7 牌力分表 5 头炸 +3/个 与 4 头普通炸 +2/个 并列——是否惩罚待确认
- **孤张定律/A 下放**：尚未在 V7 评分中量化
