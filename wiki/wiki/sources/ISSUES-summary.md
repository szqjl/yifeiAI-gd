---
type: source-summary
title: "ISSUES 摘要"
sources:
  - docs/guandan-brain/ISSUES.md
tags:
  - source-summary
  - issues
  - gua-registry
status: current
related_gua:
  - GUA-057
  - GUA-072
  - GUA-079
  - GUA-091
  - GUA-135
  - GUA-136
  - GUA-137
  - GUA-138
  - GUA-142
  - GUA-143
  - GUA-144
  - GUA-145
  - GUA-146
  - GUA-147
  - GUA-148
  - GUA-150
date: 2026-07-19
---

# ISSUES 摘要

> 来源：`docs/guandan-brain/ISSUES.md`（约 20K 字符）

## 用途

**GUA 编号体系的总账**：所有缺陷、迭代、分析都挂在这里。是 Wiki 的脊柱。

## 当前 GUA 状态盘点

### P0 Open 🔴

| GUA | 简述 | 状态备注 |
|-----|------|----------|
| GUA-057 | NN 记牌模块 | Phase 1 启动不依赖关单 |
| GUA-072 | 规则层兜底 | 代码 100% / 批跑验证 pending |
| GUA-079 | 组牌引擎三层根因 | ①②互锁、③静默 |
| GUA-091 | intent 体系迁移出口 | GUA-150 已激活 |
| GUA-135 | self_sprint 让道规则 | 被 GUA-150 修复 |
| GUA-136~138 | 残局决策族 | — |
| GUA-142~148 | 批跑观察族 | — |

### 最近关闭 ✅

| GUA | 简述 | 关闭方式 |
|-----|------|----------|
| GUA-150 | R-D09 self_sprint 让道误判 | 实施完成（commit ad52a50） |

### 候选 ⏸️

| GUA | 简述 | 决策 |
|-----|------|------|
| GUA-151 | Q0 跟压场景下 SB 解敌控 | 暂搁置，待 12 局观察 |

## 三层根因（GUA-079 范式）

> 范式：单点症状 → 三层根因拆解

- **层 ①**：单牌倒置（组牌逻辑）
- **层 ②**：拆炸凑压（组牌引擎临时借调 API）
- **层 ③**：残局静默（管线兜底无明确败招）

## 编号体系规则

- GUA-001 ~ GUA-061：V7 引擎迁移期老缺陷
- GUA-057 起：NN 引擎新方向
- GUA-091 起：intent 体系时代
- GUA-135 起：V8 残局族
- GUA-142~148：批跑观察族

## 交叉引用

- [[gua-072]] — 状态审计
- [[gua-079]] — 三层根因范式
- [[gua-150]] — 最近关闭
- [[synthesis-v7-current-state]] — V7 综合
