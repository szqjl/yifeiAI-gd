---
type: source-summary
title: "AUTO_RESTART_SYSTEM_STATUS 摘要"
sources:
  - docs/guandan-brain/notes/AUTO_RESTART_SYSTEM_STATUS.md
tags:
  - auto-restart
  - m1
  - stage7
  - infrastructure
status: current
related_gua: []
date: 2026-06-18
---

# AUTO_RESTART_SYSTEM_STATUS 摘要

## 概述
M1 旧管线（stage7）的自动重启系统状态记录，**注意：M1 ≠ M3 ≠ V7**，本文档属于历史管线，与 V7 主线存在 5 个月代差。

## 关键数据
- 文档日期：2026-01-12（V7/M3 MOC 日期为 2026-06-17，相隔 5 个月）
- M1 目标胜率：> 50%
- M1 当前胜率：0%（evaluation_failed）
- M1 状态：**评估器失效**，非模型能力为 0

## 已知问题
- M1 过度预测：512/512 卡牌，355.37 倍
- M1 评估器失效：game_info 无 game_result 字段
- M1 高损失值：191,825.22 / 958,804.55

## ⚠️ 重要澄清
- **M1 (stage7 旧管线) ≠ M3 (现役决策引擎) ≠ V7 (NN 引擎)**
- 文档命名"M1"易与"M3"混淆，引用时需明确上下文

## 关联页面
- [[auto-restart-workflow]]
- [[synthesis-m1-evaluation-failure]]
- wiki/entities/engine-v7.md
