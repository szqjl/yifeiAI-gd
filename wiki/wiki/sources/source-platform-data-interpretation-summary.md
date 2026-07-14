---
type: source-summary
title: "平台数据解读摘要（9 节结构）"
sources:
  - docs/knowledge/platform-data-interpretation.md
  - docs/analysis/agent-sessions/guandan-basic-knowledge.md
tags:
  - data-interpretation
  - victory-num
  - batch
  - round-vs-game
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# 平台数据解读摘要

> 原文件：`docs/knowledge/platform-data-interpretation.md`（13,107 字）
> 已并入：`docs/knowledge/guandan-basic-knowledge.md`（已废弃，索引请指向本摘要）

## 核心定音（最重要的 4 条）

1. **局 vs 副的核心口径**（已定音，需持续强调）
   - **平台局（game）** = 一次「A 级双上过关」游戏（晋级 A 即结束）
   - **副（episodeOver）** = 一名玩家出完手牌
   - 二者都 **≠ 一圈**（一圈 = 4 个玩家各作为主牌一次）
   - 详见 concept-round-vs-game-multi-level

2. **v1006 exe argv 实测结论**（2026-05-31 定音）
   - 单次会话固定 **3 局**，`settingTimes` 恒为 3
   - N=1/3/10 都被钳制为 3，PDF 说明书与此冲突
   - 详见 concept-exe-argv-clamp 与 wiki-minimax/entities/gua-033.md

3. **victoryNum 4 席结构** `[P0,P1,P2,P3]`
   - 队级读法：**0+2 一队、1+3 一队**
   - 批跑只读 **[0] vs [1]**（禁止四席相加）
   - [2]、[3] 是冗余副本，与 [0]、[1] 一致

4. **victoryNum 校验三优先级**（详见 [[concept-victorynum-validation]]）
   - 优先级 1：`[0]+[1]==batch_games` 且 `[0]==[2]` 且 `[1]==[3]` → 校验通过
   - 优先级 2：上述任一不等 → 走 fallback
   - 优先级 3：fallback 仅在 `batch_games==1` 时认领 `curTimes==1` 的局

## 9 节结构概览

| 节 | 主题 | 关键产出 |
|----|------|----------|
| §1 | 平台基本盘 | exe 路径、台账目录 |
| §2 | exe argv 探测 | N=1/3/10 实测矩阵，settingTimes=3 钳制 |
| §3 | 局/副/圈定义 | 核心口径定音 |
| §4 | victoryNum 解析 | 4 席结构 + 三优先级校验 + fallback 语义 |
| §5 | game_records 解读 | 1 JSON = 1 副（单座） |
| §6 | M2 局检测 | curRank==A 且本队双上 = 赢一局 |
| §7 | M3 vs lalala 示例 | 10 局示例数据 |
| §8 | 常见误读 | 禁止四席相加、禁止按 JSON 数计数局 |
| §9 | 经验沉淀 | 探测方法、可视化建议 |

## 关键数据文件

- `data/eval/exe_argv_compare.json` — N=1/3/10 argv 实测对比
- `data/eval/exe_argv_10.json` — N=10 详细探测
- `batch_executor/latest_victory_num.json` — 含 `server_vn_raw`、`vn_source`
- `batch_executor/current_batch.json` — 真源台账

## 关联

- wiki-minimax/entities/gua-033.md — victoryNum 校验根因文档化于 §2-§4.3
- [[concept-batch-evaluation]] — 批跑评测体系直接对应 §2-§7
- wiki-minimax/entities/engine-m3.md — M3 vs lalala 10 局示例为 §7 案例
- wiki/entities/module-batch-executor.md — latest_victory_num.json 写入方
