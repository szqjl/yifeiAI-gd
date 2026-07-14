---
type: concept
title: "平台 actionList PASS-only 复盘法则"
sources:
  - docs/analysis/archive/南邮离线平台-actionList候选缺失观测报告.md
tags:
  - platform
  - actionlist
  - replan-rule
  - guan-rule
status: current
related_gua: []
date: 2026-06-29
---

# 平台 actionList PASS-only 复盘法则

## 现象

离线复盘时常观察到 `actionList` 中**仅含 PASS**，约 26% 决策点。

| 样本 | 决策点 | PASS-only 数 | 占比 |
|------|--------|--------------|------|
| 平台 | 769 | 205 | 26.7% |
| 本地 | 735 | — | 26.1% |

## 错误归因（已证伪）

❌ "南邮平台漏算候选"

## 正确归因

✅ 掼蛋 curRank 规则下"AI 必须 PASS"的正确结果。

## 复盘法则（强约束）

1. **必须按该步 curRank 比较牌力**
2. ❌ 禁止用固定 A>J 比较
3. ❌ 禁止用"四炸压 SF"扫 actionList
4. 若实际可选牌型被遗漏，再判定为 bug

## 引用

- [[archive-platform-actionlist-summary]]
- [[局不等于副]]
