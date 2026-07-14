---
type: concept
title: "温度采样（argmax collapse 快速试错）"
sources:
  - docs/guandan-brain/GUA-064-方向调研-温度采样vsBeamSearchvs自对弈.md
tags:
  - sampling
  - argmax-collapse
  - quick-fix
status: current
related_gua:
  - GUA-064
  - GUA-071
date: 2026-06-19
---

# 温度采样（argmax collapse 快速试错）

## 定义

在 NN 输出概率分布上施加温度系数 τ，改变采样分布的"锐度"：
- τ → 0：退化为 argmax
- τ = 1：原始分布
- τ → ∞：均匀分布

## 在 V7 的角色

**快速试错探针**，**不作为生产方案**：
- 验证 argmax collapse 的影响程度
- 5 分钟可实施
- 不解决结构性失败（参 [[gua-074]] §层级二）

## 已被替代

[[gua-071]] heuristic 替代 NN argmax，**温度采样路线已退出主迭代**。

## 关联页面

- [[gua-064]] 方向调研
- [[gua-071]] Guard 规则迭代
- [[gua-074]] V 系列反思
- wiki/concepts/self-play-policy-gradient.md
