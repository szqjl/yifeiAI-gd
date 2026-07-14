---
type: source-summary
title: "归档：Level 2 卡级根因分析"
sources:
  - docs/analysis/archive/level2-root-cause.md
tags:
  - archive
  - level2
  - bc-argmax
  - root-cause
status: current
related_gua:
  - GUA-062
  - GUA-060
date: 2026-06-29
---

# 归档：卡 2 级根因切片分析

## 切片

V7 末级被压在 2 级的 24 副样本。

## 关键指标

| 指标 | 数值 |
|------|------|
| PASS 占比 | 44.4% |
| 非 PASS 中单张占比 | 80.5% |
| 全局单张占比 | 66.4% |
| 平均炸弹/副 | 1.2 |
| 含炸副占比 | 20/24 (83%) |

## 结论

- **单张主导**：80.5% vs 全局 66.4%，越卡级越走单张
- **末级 2/A 双峰**：12 副 2 + 12 副 A，能爬升但被压回
- **早炸浪费**：炸弹使用在前 12% 位置，炸完无力持续压制
- **主因**：BC argmax collapse（GUA-060）—— 验证 80% 但实战坍缩到 Single 等少数动作

## 关联

- [[gua-060]]
- [[gua-062]]
- [[bc-argmax-collapse]]
- [[archive-gua062-batch-eval-summary]]
