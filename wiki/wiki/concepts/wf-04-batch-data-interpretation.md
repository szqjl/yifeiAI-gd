---
type: concept
title: "WF-04 批跑数据解读 SOP"
sources:
  - docs/guandan-brain/工作流.md
tags:
  - workflow
  - wf-04
  - batch
  - interpretation
  - sop
status: current
related_gua:
  - GUA-033
  - GUA-062
  - GUA-096
date: 2026-06-30
---

# WF-04 批跑数据解读 SOP（标准操作流程）

> **真源**：本文件 = wiki 侧的真源；docs/guandan-brain/工作流.md §2.3 = 工作流侧简版。
> 任何冲突以本文件为准。

## 0. 一句话总结

> **别自己推**——ictoryNum 是本局升级数不是胜局数；completed_games 不等于真打局数；跑 nalyze_v7_rounds.py 后以工具输出为真源。

## 1. Step 1：明确口径（必走）

| 术语 | 严格定义 | 数据来源 |
|------|----------|----------|
| **副**（round） | 108 张发完到 4 人完牌 → order 确定 | 
ounds[] |
| **局**（game） | 从 2 打到 A 并在 A 级双上过关 | games[] |
| **关系** | 1 局 ≈ 6 副（实测 v1006 	arget-games 1 → **59 副**） | — |

**关键**：
- ictoryNum 是**本局升级数**（0/1/2/3），**不是胜局数**。
- 队胜判定：**本局双上**（vn≥2 且过 A）才算 A 队本局胜。
- 累计队胜率 = A 队累计升级数 / 总局数（按 v7-win-rate-history 公式）。

## 2. Step 2：跑分析工具（**别自己推**）

| 粒度 | 工具命令 | 用途 |
|------|----------|------|
| 局级 + 副级 | python scripts/analysis/analyze_v7_rounds.py --all | 胜率、victoryNum 末级分布、名次分布 |
| 副级 curRank 分组 | python scripts/analysis/analyze_v7_round_levels.py | 调试升级路径、≤5/JK/A 双峰 |

**工具输出包含**：会话 N = X 局 Y 副；队胜 X/N；副胜 Y/N；末级分布。
**直接以工具输出为真源**——不要自己再算。

## 3. Step 3：写 7-win-rate-history.md

按其「记录格式」一行，公式：
- V7 队胜率 = [0]+[1] vs 总局数
- **副数 = mtime 窗内 JSON / 2**
- 累计 = 历史 + 本批

## 4. Step 4：四层写入校验（必走，防数据污染）

| 层级 | 位置 | 写入时机 |
|------|------|----------|
| L1 | atch_executor/latest_victory_num.json | 每局结束 |
| L2 | logs/v7_vs_lalala_*.log | 实时（不进 Git） |
| L3 | 7_vs_lalala_scores.json | 每局结束 |
| L4 | game_records_v7/ | 每副结束 |

**三优先级校验**：
- **P1**：[0]+[1]==batch_games 且 [0]==[2] 且 [1]==[3] → 通过
- **P2**：任一不等 → 走 fallback
- **P3**：fallback 仅 atch_games==1 时认领 curTimes==1

**L1 + L4 必须核对一致性**（本次踩坑：18 个局号 vs vn=3 局 = L1≠L4 = 数据完整性事故）。

## 5. Step 5：避坑清单（常见误读）

| 误读 | 真相 |
|------|------|
| n[1]=3 循环 3 次 
ecord_game("team_b") | ❌ **典型 bug**——vn 是升级数不是胜局数 |
| 文件名 [idx]-[total] 的 idx 是局号 | ❌ idx 是 batch 内**副序号**（不是局号） |
| completed_games = 真打局数 | ❌ 是按 atch_games 累加的台账（方案 A） |
| 70 个 record 全是同一局 | ❌ 70/2 = 35 副 × 2 客户端（yf1/yf2） |
| 70/70 victoryNum 相同 = V7 引擎问题 | ❌ 是 **server gameResult 漏推**，backfill 用同 vn 回填 |
| game_round 字段 1,1,1,1... | ⚠️ **已知 bug**，不区分副号；按 mtime 窗算副数更稳 |
| lalala 客户端不写 record | ✅ 设计如此，不是 bug |

## 6. 自检三连问（写汇报前必答）

1. L1 的 n[0]+vn[1] 与 L4 的实际局数是否一致？若不一致，先标注「数据完整性事故」再继续。
2. 工具输出里"会话 N = X 局 Y 副" 与 scores.json.total_games 是否对得上？
3. 副数公式 JSON/2 是否与你 L4 mtime 窗范围一致（避免把历史残留算进本批）？

## 7. 关联页面

- [[wf-04-batch-kpi]] — WF-04 KPI 概览
- [[batch-evaluation]] — 批跑评测体系（含 GUA-062 案例）
- [[局不等于副]] — 局副核心概念
- [[batch-victorynum-parsing]] — victoryNum 字段解析
- [[batch-end-victory-num-validation]] — 批末 victoryNum 校验
- 工作流侧简版：docs/guandan-brain/工作流.md §2.3