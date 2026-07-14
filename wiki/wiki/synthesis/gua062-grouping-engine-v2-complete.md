---
type: synthesis
title: "GUA-062 组牌引擎 v2 完整演进综合分析"
sources:
  - docs/guandan-brain/ITERATIONS.md
  - docs/guandan-brain/v7-win-rate-history.md
  - docs/guandan-brain/ISSUES.md
tags:
  - synthesis
  - gua-062
  - grouping-engine
  - v2
status: current
related_gua:
  - GUA-062
  - GUA-061
  - GUA-059
  - GUA-038
date: 2026-06-18
---

# GUA-062 组牌引擎 v2 完整演进综合分析

## 概述

GUA-062 "组牌引擎 v2 演进" 在 2026-06-18 单日完成 **6 次迭代**，是 V7 战役中信息密度最高的 GUA 之一。本综合分析跨多文件还原完整演进链路。

## 6 次迭代时间线

### 迭代 1：基础 v2 评分上线
- 24 维评分框架
- 五维权重：炸弹0.3 + 手数0.3 + 回收0.1 + 灵活0.1 + 去单化0.2
- 单元测试通过

### 迭代 2：流水线接通
- 与 V7 主决策链路打通
- 单元测试 + 冒烟 ON

### 迭代 3：12 局批跑
- 队胜率 0/12
- 末级 2/A 双峰首次观测

### 迭代 4：三连对优化
- 修复三连对的特殊处理
- 提升特定牌型评分

### 迭代 5：去单化循环
- SF_FIRST 多 pass 迭代
- 单张从 8 → 4

### 迭代 6：角色定论 + 权重调优 + A→2 包接
- **角色定论**：组牌只做特征提取，不参与决策
- A→2 包接：A 下放当 1
- 权重再调优

## 关键成果

| 指标 | v1 | v2 | 提升 |
|------|----|----|------|
| 评分维度 | 9 | 24 | +166% |
| SF_FIRST 评分 | 0.2750 | 0.4067 | +47.9% |
| 单张数（测试用例） | 8 | 4 | -50% |
| 队胜率 | 0% | 0% | **0** |

## 核心张力

### 张力 1：单元测试 vs 实战
- 单元测试大幅提升 → 实战仍 0%
- **结论**：组牌优化无法弥补决策层缺陷

### 张力 2：角色定论 vs v2 设计
- 角色定论"只做特征提取"
- v2 投入大量精力在硬约束/软引导/纯特征三路径
- **冲突**：v2 部分实现可能尝试了硬约束路径

### 张力 3：末级分布稳定
- 两次批跑末级分布几乎一致
- **结论**：V7 架构性问题，非组牌可解

## 关键资产

- `grouping_engine.py` v2 升级
- `grouping_scanner` 9 维 → 24 维
- `ultimate_win_rate_engine_v7.py` 集成
- 详见 wiki/concepts/grouping-engine-v2-five-dim-scoring.md

## 后续影响

- **GUA-061**（V7 模块化架构）追加 v7-pipeline-connect-fix
- **GUA-059** 退化为观测（BC 路线已死）
- **GUA-039b** 自对弈成为唯一出路

详见 wiki/synthesis/synthesis-v7-current-state.md。
