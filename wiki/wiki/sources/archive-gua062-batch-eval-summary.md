---
type: source-summary
title: "归档：2026-06-18 GUA-062 批跑评测"
sources:
  - docs/analysis/archive/2026-06-18-gua062-batch-eval.md
tags:
  - archive
  - gua-062
  - batch-eval
  - v7-vs-lalala
status: current
related_gua:
  - GUA-062
date: 2026-06-29
---

# 归档：GUA-062 分组引擎 v2 批跑评测

## 摘要

V7 (含 GUA-062 分组引擎 v2) vs lalala 的离线批跑结果，于 2026-06-18 入档。

## 关键数据

| 指标 | 数值 |
|------|------|
| 团队局胜 | 0 / 9 (0%) |
| 副胜率 | 8 / 79 (10.1%) |
| lalala 副胜率 | 71 / 79 (89.9%) |
| A 级别副数 | 12 / 79 (15.2%) |
| 双升 2 副数 | 12 |
| victory_num | [0,3,0,3] |

## 结论（闭环但有遗留债务）

- ✅ **闭环**：49 pytest 全过 + 评分正确输出
- ⚠️ **债务**：评分输出**未接入动作选择链路**，V7 decide() 仍走 BC argmax，导致 10.1% 副胜未转化为局胜

## 关联

- [[gua-062]]
- [[bc-argmax-collapse]]（实战败北主因）
- [[level2-root-cause-summary]]（卡 2 级 24 副切片互为证据）
- [[synthesis-v7-vs-lalala-cumulative]]
