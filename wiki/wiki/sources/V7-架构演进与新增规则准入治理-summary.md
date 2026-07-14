---
type: source-summary
title: "V7 架构演进与新增规则准入治理"
sources:
  - docs/guandan-brain/V7-架构演进与新增规则准入治理.md
tags:
  - v7
  - 架构演进
  - 规则准入
  - 治理
status: current
related_gua:
  - GUA-096
  - GUA-097
  - GUA-098
  - GUA-108
  - GUA-110
  - GUA-111
date: 2026-06-29
---

# V7 架构演进与新增规则准入治理

## 三层架构

| Layer | 职责 | 当前实现 |
|-------|------|----------|
| **Layer 1 记忆** | MemoryTracker 状态记录 | `MemoryTracker` |
| **Layer 2 推断** | 信念建模（IP-01~IP-21） | `_inference_phase_relation` / `_phase_relation` / `_belief` |
| **Layer 3 决策** | 候选统一评分器 | `ultimate_win_rate_engine_v7.py` + 阶段 C NN 评分头 |

## V7 阶段化方案（落地路径）

### 阶段 A：补丁主脑
- 范围：M3 规则 → V7 移植
- 目标：净盘批跑胜率归零但可解释
- 落点：`scripts/launchers/v7/run_v7_vs_lalala_games.py`

### 阶段 B：统一中局大脑
- 范围：信念建模 + 残局分散治理
- 目标：阶段 4 副胜率 0% → 30%（带动整体 0% → 3-5%）
- 落点：IP-01~IP-21 + `endgame_rule` + `BAOSHU_RULE`

### 阶段 C：候选统一评分器
- 范围：NN 评分头
- 目标：长线方向
- 落点：DanZero+ 论文同构

## 新增规则 5 问准入审查表

| # | 审查问题 | 不通过则 |
|---|----------|----------|
| 1 | 是否能用现有规则覆盖？ | 禁止新增 |
| 2 | 是否有可观测的胜率提升？ | 禁止入批跑 |
| 3 | 是否破坏 victoryNum 镜像？ | 禁止 merge |
| 4 | 是否有 WF-12 决策可观测？ | 禁止 merge |
| 5 | 是否有 PB-002 四层闭环测试？ | 禁止 merge |

## 落点矩阵

| 阶段 | 净盘 | 信念 | 决策 | 残局 | 评分 |
|------|------|------|------|------|------|
| A | GUA-096 | — | 规则移植 | — | 规则 |
| B | — | IP-01~21 | 中局大脑 | GUA-099/100 | 规则 |
| C | — | — | NN 评分头 | — | NN |

## 落点

- [[engine-v7]] — V7 引擎实体页
- [[v7-stage-evolution]] — 概念页
- [[three-layer-pipeline]] — 三层架构
- [[ip-rule-ablation]] — IP 规则登记
- [[pb-002-bug-discovery-loop]] — 4 层闭环
