---
type: concept
title: "V7 Guard 体系（R01~R15 全表）"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/ITERATIONS.md
tags:
  - guard
  - rules
  - v7
status: current
related_gua:
  - GUA-066
  - GUA-068
  - GUA-069
  - GUA-070
date: 2026-06-21
---

# V7 Guard 体系

## Guard 角色

Layer1 决策管线的硬排除层（参见 [[three-layer-decision-pipeline]]），由 R01~R15 共 15 条规则组成。

## 已记录规则（部分）

| 规则 | GUA | 状态 | 说明 |
|------|-----|------|------|
| R10 | GUA-066 | ✅ | greaterPos 传参修复 |
| R11 | GUA-068 | ✅ | 全局抑制牌检查 + 节流 |
| 超弱角色 core 保护 | GUA-069 | ✅ | 弱角色额外保护 |
| R12 | GUA-070 | ✅ | 拆对出单禁止 |
| 队友保护 | GUA-065 | ✅ | +18.5pp 副胜提升 |

## 综合批跑表现

- GUA-066/068/069/070 合并批跑：副胜 4/108 (3.7%)
- 对比 GUA-065 单行：25.5%
- 暴跌 14pp，疑似规则叠加过严或 9 局采样方差

## 设计哲学

- 严格 > 宽松（先排除明显非法动作）
- 配合 heuristic 软排序（Layer2）做精细决策
- validate 兜底（Layer3）确保输出可执行

## 关联

- [[three-layer-decision-pipeline]] — 完整架构
- [[gua-065]] — 队友保护（首个显著正向）
