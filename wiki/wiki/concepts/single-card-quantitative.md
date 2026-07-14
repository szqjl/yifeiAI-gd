---
type: concept
title: "单张数量阈值判定"
sources:
  - docs/knowledge/skills/04_common_skills/01_single_card_skills.md
tags:
  - single-card
  - threshold
  - diagnostic
status: current
related_gua:
  - GUA-062
date: 2026-06-18
---

# 单张数量阈值判定

## 阈值表

| 单张数 | 占比 | 判定 | 行动 |
|--------|------|------|------|
| 0-2 张 | 0-7% | 牌型整齐 | 正常出牌 |
| 2-4 张 | 7-15% | 正常 | 正常出牌 |
| 5-6 张 | 19-22% | 单张较多 | 优先处理单张 |
| >7 张 | >26% | 组牌有问题 | 重新考虑组牌策略 |

## 判定意义

- **诊断牌型结构**：单张过多说明组牌阶段策略有问题
- **指导出牌顺序**：单张多时优先出单张
- **早期预警**：5-6 张是警戒线

## 引擎实施

- **M3**：✅ 可立即实施（简单阈值判定，GUA-062 P0 候选）
- **V5+ / V7**：保留为启发式规则之一

## 关联

- [[gua-062]] — 单张数量阈值判定（拟）
- [[concept-pair-first-strategy]] — 对子先行
- [[concept-card-type-probability]] — 牌型概率
- wiki/sources/skills-04-single-card-skills-summary.md

---
