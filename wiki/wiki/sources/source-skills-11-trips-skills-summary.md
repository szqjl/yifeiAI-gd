---
type: source-summary
title: "三张技巧（§二十一）"
sources:
  - docs/knowledge/skills/04_common_skills/11_trips_skills.md
tags:
  - skills
  - trips
  - section-21
  - common-skills
status: current
related_gua:
  - GUA-026
  - GUA-029
  - GUA-031
date: 2026-06-17
---

# 三张技巧（§二十一）

## 文件位置
- 路径：`docs/knowledge/skills/04_common_skills/11_trips_skills.md`
- 章节：§二十一 三张（Trips）

## 核心内容

### 牌型定义
- **三张（Trips）**：三张同点数的牌
- 引擎变量名：`Trips`（与代码一致）
- 与 gua-026 拆 trips 边界 强相关

### 三张的特点（牌路）
- **暴露牌路**：出现三张的牌局往往呈现"无顺子/对少/炸少/单多"特征
- **灵活性强**：可带对子、可配炸、可参顺
- **形成冲刺**：连续三张（如 333444）易造成冲刺局面

### 关键技巧

| 技巧 | 编号 | 说明 |
|------|------|------|
| 示弱送夯 | P-J03 | 见 [[concept-passing-skills-matrix]] |
| 拆三张组顺送队友 | - | 与 GUA-026 拆 trips 边界 |
| 三张+配+单=夯 / 三张+配+对=三带二 | - | 灵活变形 |
| 骗炸、顶大牌拦截、判三炸四 | - | 进阶技巧 |

### 概率数据（来自本文件）
- **三张**：8.22%
- **三带二**：7 手/局
- **炸弹**：8.5 手/局（含同花顺与天王炸）

## 引擎映射

### M3 引擎
- 已有牌型处理：`_Trips` / `rankthree`
- 详见 wiki-minimax/entities/engine-m3.md

### 与其他 skills 的联动
- gua-029 钢板：钢板+三张形成大组合
- gua-031 传牌技巧实施跟踪：送三张/三带二/示弱送夯

## 跨资料引用
- 上游原则：P-J03（示弱送夯）
- 下游实施：GUA-026 / GUA-029 / GUA-031

## 相关页面
- [[gua-026]]
- [[gua-029]]
- [[gua-031]]
- [[concept-passing-skills-matrix]]
- [[concept-card-type-probability]]
