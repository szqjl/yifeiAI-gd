---
type: source-summary
title: "GUA-097 IP 消融运行器摘要"
sources:
  - docs/guandan-brain/iterations/v7-gua097-ip-ablation-runner.md
tags:
  - v7
  - ablation
  - ip
  - runner
status: current
related_gua:
  - GUA-097
date: 2026-06-30
---

# GUA-097 IP 消融运行器摘要

## 来源
`docs/guandan-brain/iterations/v7-gua097-ip-ablation-runner.md`

## 概述
GUA-097 下的 IP（Inference Profile / Interaction Policy）消融运行器实现说明，用于在 V7 NN 引擎上做策略组件的消融实验。

## 关键内容
- IP 消融的运行器架构
- 消融维度（哪些 IP 组件可被屏蔽/替换）
- 与 [[batch-executor]] 的调用关系
- 产出至 [[v7-gua097-ablation-log-summary]] 的日志格式

## 关联
- [[gua-097]]
- [[engine-v7]]
- [[batch-executor]]
