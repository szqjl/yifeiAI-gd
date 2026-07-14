---
type: source-summary
title: "GUA-064 方向调研：温度采样 vs Beam Search vs 自对弈（源摘要）"
sources:
  - docs/guandan-brain/GUA-064-方向调研-温度采样vsBeamSearchvs自对弈.md
tags:
  - gua-064
  - direction-research
  - sampling
  - self-play
status: current
related_gua:
  - GUA-064
  - GUA-071
  - GUA-074
date: 2026-06-19
---

# GUA-064 方向调研：温度采样 vs Beam Search vs 自对弈（源摘要）

## 背景

V7 NN 引擎在 BC v3 训练后出现 **argmax collapse**：2048 维输出层退化为 `PASS + 首候选`（占比 99%），val_acc 不等于实战胜率。需要选定下一步方向。

## 三方向对比

| 方向 | 实施成本 | 治标/治本 | 风险 | 结论 |
|------|---------|-----------|------|------|
| **温度采样** | 5 分钟 | 治标 | 不解决 argmax collapse 根因 | 快速试错用，**不推荐长期** |
| **Beam Search** | 中等 | 治标 | 4 人不完美信息博弈需世界模型，否则搜索空间爆炸 | **不推荐** |
| **自对弈 PG（DMC/PPO）** | 高（需算力） | **治本** | 算力 + 训练稳定性 | **唯一出路** |

## 关键论证

- **温度采样**：仅作为快速验证 argmax collapse 影响程度的探针，不作为生产方案
- **Beam Search 在掼蛋中不可行**：4 人不完美信息 + 108 张牌 + 多轮博弈，分支因子过大，无世界模型则无效
- **自对弈 PG 是终极方案**：参考 wiki/concepts/self-play-policy-gradient.md

## 对照文献

- **DouZero**（快手，ICML 2021）：DMC + 斗地主 → 同思路可迁掼蛋
- **DanZero/DanZero+**（中科大，COG 2022/2023）：DMC+RL 掼蛋成功案例
- **赢麻哒 LSTM+DMC**（麻邻国，2026）：掼蛋实战
- **Posterior BC**（NeurIPS 2025）：BC → RL 过渡方法
- **Big 2 Self-Play**（arXiv 2026.05）：PPO + 熵正则

## 决策结论

1. **短期**：温度采样作为 argmax collapse 的快速试错探针（已完成 GUA-071 替代路线）
2. **中期**：规则记牌 + heuristic + Guard 三层混合架构（参 [[gua-074]]）
3. **长期**：自对弈 PG 重新训 NN，**NN 只做记牌与策略分类**（不做端到端 action 输出）

## 相关页面

- [[gua-064]] 实体页
- [[gua-071]] Guard 规则迭代（heuristic 替代 NN argmax）
- [[gua-074]] V 系列反思（三层混合架构）
- wiki/concepts/temperature-sampling.md
- wiki/concepts/self-play-policy-gradient.md
- synthesis-v7-current-state-2026-06-19
