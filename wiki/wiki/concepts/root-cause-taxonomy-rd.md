---
type: concept
title: "R-Dxx 根因分类法"
sources:
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
tags:
  - r-d-taxonomy
  - wf-12
  - root-cause
status: current
related_gua:
  - GUA-081
  - GUA-071
  - GUA-079
  - GUA-078
date: 2026-06-29
---

# R-Dxx 根因分类法

WF-12 的**输出语言**。8 类标签覆盖 V7 决策失败的常见模式。

## 分类

| 标签 | 含义 | 对应 GUA / 模块 |
|------|------|-----------------|
| **R-D01** | 推荐被 mask 挡 | [[gua-081]]（三带二 builder 同型 fallback） |
| **R-D02** | 推荐缺失 | — |
| **R-D03** | 残局未命中 | [[gua-078]]（Q0–Q3） |
| **R-D04** | 组牌锁死 | [[gua-075]] + cardmask 缺陷 |
| **R-D05** | 启发式 NN 劣选 | [[gua-071]] / [[gua-079]] |
| **R-D06** | 场态误读 | — |
| **R-D07** | 记录/贡献 | [[gua-067]]（recorder） |
| **R-D08** | 知识未接入 | [[gua-073]]（常识→guard 映射） |

## 使用约束

- 单局禁止写特例代码（WF-12 §2）
- 同一 R-D 类问题累计 ≥3 例应升级为独立 GUA
- 修复必须通过 R-G080-4 零退化批跑验收

## 关联

- [[wf-12-decision-trace]]
- [[v7-decision-pipeline]]
