---
type: source-summary
title: "V7 IP 规则 ablation log (GUA-097)"
sources:
  - docs/guandan-brain/iterations/v7-gua097-ablation-log.md
tags:
  - v7
  - ablation
  - ip-rule
status: current
related_gua:
  - GUA-097
  - GUA-091
date: 2026-06-19
---

# V7 IP 规则 ablation log

## 概述
GUA-097 IP 规则对照批跑 helper 的 ablation log 起点。

## 首个 ablation 目标
**GUA-091**: `stage_2` 中局入口 `_stage_mid_dispatch`

## 当前结果
| 配置 | 队胜率 | 副胜率 |
|------|--------|--------|
| baseline | 0/3 (0%) | TBD |
| enable | 0/3 (0%) | TBD |

**结论**：队胜率未变 (0%→0%)，暂无 delta 基线。需后续更多 ablation 才有意义。

## 范式
**Baseline + Enable + Delta** — 防"加规则不测"，是 V7 后续迭代的标配验证流程。

## 关联
- [[gua-097]] — GUA-097 实体页
- [[gua-091]] — GUA-091 实体页（ablation 目标）
- [[ip-rule-ablation]] — 概念页
