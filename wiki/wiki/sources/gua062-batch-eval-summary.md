---
type: source-summary
title: "GUA-062 批跑验证归档"
sources:
  - docs/analysis/archive/2026-06-18-gua062-batch-eval.md
  - docs/analysis/archive/level2-root-cause.md
tags:
  - gua-062
  - batch-eval
  - closed
  - root-cause
status: current
related_gua:
  - GUA-062
date: 2026-06-28
---

# GUA-062 批跑验证归档

## 来源

- `docs/analysis/archive/2026-06-18-gua062-batch-eval.md` (1691 chars)
- `docs/analysis/archive/level2-root-cause.md` (1206 chars)
- 日期：2026-06-18

## 关键数据

| 指标 | 数值 |
|------|------|
| 局胜 | **0 / 9**（0%） |
| 副胜 | 8 / 79（10.1%） |
| 卡2级副数 | 24 副 |
| 卡2级 PASS 率 | 44.4% |
| 全局 PASS 率 | 46.1% |
| 卡2级 Single 决策占比 | **80.5%** |

## 根因诊断

### 主因：BC argmax collapse
卡2级（轮到我方出牌且场上最大牌级别 ≤ 2）的 24 副样本中，**Single 决策占 80.5%**。模型在级牌压制规则下塌缩到最大单张。

### 辅因：知识未接入
- 级牌压制规则（curRank > 点数）未生效
- 同花顺压四/五星炸规则未生效

## 关单结论

GUA-062 已 **closed**，但**关闭 ≠ 实战可用**：
- pytest 49 用例全过
- 9 局实战 0 胜
- 决策链 V7 主路径仍未接入

## 修复方向（后续 GUA）

- GUA-072 / GUA-073：card_mask 修复（→ GUA-075 落地）
- GUA-078：残局管线
- GUA-079：启发式优化
- GUA-081：L8 兜底 fallback

## 批跑脚本

- `scripts/launchers/v7/run_v7_vs_lalala_games`
- `v7_batch_output.txt`
- `v7_vs_lalala_scores.json`

## 关联

- [[gua-062]] — 缺陷条目
- [[batch-evaluation]] — 评测体系
- [[v7-current-state]] — V7 当前状态
- [[decision-trace-taxonomy]] — R-D05 / R-D08 标签
- [[局不等于副]] — 局胜 vs 副胜口径分离
