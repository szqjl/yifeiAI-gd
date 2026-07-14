---
type: source-summary
title: "归档：南邮离线平台 actionList 候选缺失观测报告（勘误）"
sources:
  - docs/analysis/archive/南邮离线平台-actionList候选缺失观测报告.md
tags:
  - archive
  - platform
  - actionlist
  - correction
  - guan-rule
status: current
related_gua: []
date: 2026-06-29
---

# 归档：平台 actionList 候选缺失（已勘误）

## ⚠️ 重要：原报告结论已证伪

原报告主张"南邮平台漏算候选"。2026-06-28 独立复现已**证伪**：44 例按 curRank 重算后 0 例可站住。

## 正确结论

`actionList` 中约 26% 仅含 PASS 是**掼蛋 curRank 规则下的正确结果**，**非平台 bug**。

| 样本 | 决策点 | PASS-only 数 | PASS-only 占比 |
|------|--------|--------------|----------------|
| 平台 | 769 | 205 | 26.7% |
| 本地 | 735 | — | 26.1% |

## 复盘法则（重要）

复盘"AI 被迫 PASS"时必须按该步 curRank 比较牌力，**勿用固定 A>J 或四炸压 SF 扫 actionList**。

## 关联

- [[platform-actionlist-pass-only]]
