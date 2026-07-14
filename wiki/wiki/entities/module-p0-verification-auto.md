---
type: entity-module
title: "P0自动验证脚本"
sources:
  - docs/analysis/agent-sessions/p0_verification_status_20260528.md
  - docs/analysis/agent-sessions/p0_complete_summary.md
tags:
  - m1-engine
  - verification
  - automation
  - blocker
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# P0 自动验证脚本

## 基本信息

- **主脚本**：`p0_verification_auto.py`（438 行）
- **辅助脚本**：
  - `test_p0_single_game.py`
  - `test_p0_correct.py`
  - `verify_p0_improvements.py` / `v2` / `final` / `implementation`
  - `p0_quick_tune.sh`

## 职责

自动化验证 P0 改进的代码完整性与触发行为。

## 验证维度

| 维度 | 检查项 |
|------|--------|
| 代码完整性 | 4 个 P0 模块是否被引用 |
| 模块加载 | 模块能否成功 import |
| 触发统计 | 各 Handler 调用 P0 模块的次数 |
| 集成验证 | PassiveHandler 是否包含 P0-③ 调用 |

## 当前状态

**第一轮验证结果**：
- P0-① `HistoryTracker`：触发次数 = 0
- P0-② `EndgamePlanner`：触发次数 = 0
- P0-③ `TeammateOpportunityFinder`：集成已确认（4 个 PassiveHandler）
- P0-④ `BombStrategy`：未激活（M1 范围外）

## ⚠️ 关键阻塞

**离线平台端口问题**：
- 平台：`guandan_offline_v1006.exe`（端口 23456）
- 占用：PID 13788 顽固占用
- 启动脚本未等待 "Ready for connect." 信号
- 影响：无法运行真实对局验证

**结论**：代码已实施，但胜率验证被平台阻塞，无法证明 P0 有效性。

## 关联

- [[concept-batch-evaluation]] — 验证方法论
- wiki/concepts/p0-m1-cooperation-improvements.md — 被验证对象
- wiki-minimax/entities/gua-033.md — 批跑评测 GUA
- wiki/entities/module-batch-executor.md — 批跑执行器（待批跑验证使用）
