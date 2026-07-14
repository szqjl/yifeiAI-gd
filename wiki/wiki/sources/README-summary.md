---
type: source-summary
title: "README 项目门户与指挥系统"
sources:
  - docs/guandan-brain/README.md
tags:
  - readme
  - portal
  - command-system
  - data-onboarding
  - m3
status: current
related_gua:
  - GUA-022
  - GUA-036
date: 2026-06-29
---

# README 项目门户与指挥系统

## 摘要

`README.md` 是 [[double-up-knowledge-wiki]] 的项目门户文档，承担三重职责：
1. **项目定位与代际说明**（M1 frozen / M2 / M3 / V4 / V5 / V6 / V7）
2. **当前指挥与底座声明**（M3 + IDecisionProvider）
3. **新 Agent 批跑数据入门**（含「局 vs 副」口径与 victoryNum 解读）

> ⚠️ **叙述冲突提示**：README §当前指挥 把 M3 写成本轮主交付 + IDecisionProvider 底座；但 Wiki `index.md` 与 `synthesis-v7-current-state` 把 V7 标为主迭代。两套叙述并存，本 Wiki 在 [[overview]] 明确「项目级指挥仍 M3，本 Wiki 主跟踪 V7」。

## 项目基本信息

- **平台**：南邮掼蛋 AI 客户端 v1006（`offline_platform/guandan_offline_v1006/`）
- **友军基线**：`lalala3`（pos1）/ `lalala4`（pos3）
- **本队位置**：`yf1`（pos0）/ `yf2`（pos2）
- **分支**：`m-dev`（M3 指挥）/ `v7-dev`（V7 实验）

## 引擎代际

| 代际 | 状态 | 守卫职责 | 备注 |
|------|------|----------|------|
| M1 | **frozen**（GUA-022 closed） | — | 不再改策略 |
| M2 | 历史 | — | 演进路径 |
| M3 | **当前指挥** | **P0 guard = `m3_decision_engine`** | IDecisionProvider v1.0 底座 |
| V4 | 演进 | — | — |
| V5 | 演进 | 组牌/牌力 | V5+ 接管组牌与牌力评估 |
| V6 | 演进 | — | — |
| V7 | **Wiki 主跟踪 / 实验** | V7 KPI 护栏 ≥30% | `ultimate_win_rate_engine_v7.py` / `engine_v7.py` |

## 关键定义（Agent 数据入门）

### 局 vs 副口径（定音）

- `gameOver` = 副结束（一个玩家出完手中所有牌）
- `episodeOver` = 局结束（一局掼蛋包含若干副，直到双上/双下方结束）
- **completed_games** 统计的是「局」
- **game_records JSON** 里的 `players[i].plays` 数的是「副」
- 真源：`current_batch.json`（`batch_games` 字段）

### victoryNum 解读

```
victoryNum = [vf, vg, vh, vi]   # 四个玩家（pos0/1/2/3）
[0] vs [1] 队胜  ←  关键：yfv vs lalala3 / lalala4
[0]=[2]、[1]=[3]  ←  队内自洽（yf1=yf2 必相等）
```

### Joker 编码归一化

旧版 `SB/HR` → 新版 `BJ/RJ`（小王/大王）。所有解析与日志必须用 `BJ/RJ`。

## 关联 GUA

- **GUA-022**：M1 frozen 已关闭，不再修改 M1 策略
- **GUA-036**：2026-06-01 closed（具体内容详见对应 GUA 条目）

## 新 Agent 上手指南（来自 README）

1. 读 `README.md`（本文档）
2. 看 `SCRIPT_INDEX.md`（脚本索引）
3. 跑 `run_v7_vs_lalala_games.py` / `run_m3_vs_lalala_games.py`（批跑入口）
4. 看 `v7-win-rate-history.md`（V7 KPI 真源）
5. 看 `工作流.md`（WF-01～12 工作流矩阵）

## 链接

- 脚本索引：[[SCRIPT_INDEX-summary]]
- V7 KPI 真源：[[v7-win-rate-history-summary]]
- 工作流矩阵：[[workflow-summary]]
- M3 引擎：[[engine-m3]]
- V7 引擎：[[engine-v7]]
