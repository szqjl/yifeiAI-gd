---
type: source-summary
title: "传牌技巧摘要"
sources:
  - docs/knowledge/skills/03_assist_attack/01_passing_skills.md
tags:
  - passing
  - assist
  - tactics
  - card-count
status: current
related_gua:
  - GUA-031
date: 2026-06-18
---

# 传牌技巧摘要

## 文档定位

`docs/knowledge/skills/03_assist_attack/01_passing_skills.md` 是掼蛋**助攻**子目录的开篇之作，系统整理了**传牌技巧**的全部场景。

## 传牌分类

### 单张传牌
- 高单传牌
- 低单传牌
- 中单传牌
- 卡点传单牌

### 对子传牌
- 配合队友传对子
- 判断队友需要对子

### 三带二与顺子传牌
- 行牌排除法
- 记牌分析法（5/10 核心点）
- 逻辑推演法

## 四大战术

- 砸锅卖铁
- 调虎离山
- 借刀杀人
- 釜底抽薪

## 残牌张数策略矩阵

| 剩余张数 | 策略 |
|----------|------|
| 2 张 | 先中大后小 |
| 3-4 张 | 送单/对/三张通路 |
| 5 张 | 大概率三带二，送三带二或顺子 |
| 6 张 | 5+1 送单，4+2 送对 |
| 7 张 | 有王出单/对子通路 |
| 8 张 | 单/对/三张 |
| 9 张 | 送 5 张牌型（三带二/杂花顺） |
| 10 张 | 三带二 + 杂花顺优先 |

详见 [[concept-passing-skills-matrix]]。

## 引擎实施状态

- **M3 可硬编码 4 条 P1**（基于 `numoffri` / `numofnext` 的 guard 逻辑）
- 其余条目归 V5+ 范畴
- **无 P0 实现**

⚠️ Wiki 中尚未将这 4 条 P1 显式落地，需在 concept-passing-skills-engine-mapping 中列出并跟踪 [[gua-031]]。

## 常见误传

- 刻舟求剑
- 把队友打吐
- 不加防守传牌
- 想当然传牌
- 羊入虎口
- 无意义传牌

## 与 GUA-031 / GUA-030 的关系

- 主要承载 [[gua-031]]「传牌技巧实施跟踪」
- P1 条目也挂 [[gua-030]]「原则→引擎映射」

## ⚠️ 文档内部口径分歧

- 本文档将"逢五出对"类策略归 P0（无 M3 实现）
- 但 [[source-skills-02-strategy-overview-summary]] 将其归 P1（M3 可硬编码）
- 需核对 `PRINCIPLES_MAPPING.md` 的权威分类

## 元信息

- 文件路径：`docs/knowledge/skills/03_assist_attack/01_passing_skills.md`
- 字符数：约 8156
