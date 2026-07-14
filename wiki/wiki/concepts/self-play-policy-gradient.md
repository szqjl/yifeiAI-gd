---
type: concept
title: "自对弈 Policy Gradient（DMC/PPO）路线"
sources:
  - docs/guandan-brain/GUA-064-方向调研-温度采样vsBeamSearchvs自对弈.md
  - docs/guandan-brain/掼蛋AI技术路径重校-V系列方法论反思.md
tags:
  - self-play
  - policy-gradient
  - dmc
  - ppo
  - long-term
status: current
related_gua:
  - GUA-064
  - GUA-074
date: 2026-06-19
---

# 自对弈 Policy Gradient（DMC/PPO）路线

## 定义

让多个智能体副本互相对弈，用对弈结果作为 reward 信号，通过策略梯度方法更新网络参数。

## 代表算法

- **DMC**（Deep Monte Carlo，参考 AlphaZero/DouZero）
- **PPO**（Proximal Policy Optimization）

## 在掼蛋的可行性

**唯一出路**（[[gua-064]] 结论）：
- 端到端 BC 结构性失败（V5 阶段 5/6、1312 真实人类数据）
- 规则补全路线有上限（[[gua-074]] §层级三）
- 唯有自对弈能让策略"自我进化"

## 关键约束

- **算力**：DMC/PPO 需大量自对弈样本
- **稳定性**：4 人博弈的 reward 信号比 2 人稀疏
- **V7 范围收窄**：NN 只做记牌+策略分类，**不做端到端 action 输出**（参 [[gua-074]] §层级六）

## 对照文献

- **DouZero**（ICML 2021）：斗地主 DMC
- **DanZero/DanZero+**（COG 2022/2023）：掼蛋 DMC+RL 成功
- **赢麻哒 LSTM+DMC**（麻邻国 2026）：掼蛋实战
- **Big 2 Self-Play**（arXiv 2026.05）：PPO + 熵正则

## 关联页面

- [[gua-064]] 方向调研
- [[gua-074]] V 系列反思
- wiki/concepts/three-layer-hybrid-architecture.md
- synthesis-v7-current-state-2026-06-19
