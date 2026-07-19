---
type: source-summary
title: "2026-07-18 V8 GUA-150 实施 + Kaggle 公开摘要"
sources:
  - docs/guandan-brain/handoffs/2026-07-18-v8-gua150-impl-kaggle-publish.md
tags:
  - source-summary
  - handoff
  - v8
  - kaggle
  - milepost
status: current
related_gua:
  - GUA-150
  - GUA-135
  - GUA-091
date: 2026-07-19
---

# 2026-07-18 V8 GUA-150 实施 + Kaggle 公开摘要

> 来源：`docs/guandan-brain/handoffs/2026-07-18-v8-gua150-impl-kaggle-publish.md`（约 6.4K 字符）

## 里程碑定位

本文档记录了 **GUA-150 全链路闭环**与 **V8 牌谱 Kaggle 首公开**两件里程碑事件。

## GUA-150 闭环

### 根因 R-D09
- self_sprint 让道误判：一刀切 PASS 未比较 self/teammate 冲刺路径
- 触发于 endgame_decide.py L2662 日志（**非 L962 兜底**，这是与 Q0 报告 v1 的关键分歧）

### 实施内容
- `endgame_decide.py` L3416-3424 情形 2 改 intent 比较
- 新增辅助函数：
  - `_find_min_non_bomb_lead_action` — 找最小非炸领出
  - `_estimate_self_num_rounds` — 估算自我剩余轮次
- pytest `test_gua150_self_sprint_short_path.py` 6/6 通过
- 原 GUA-135 28/28 测试未破坏
- commit `ad52a50` → v8-dev

### 5 问准入

| 问 | 答 |
|----|----|
| 一类局面？ | ✅ 残局冲刺决策 |
| 可沉意图层？ | ✅ _stage_mid_dispatch intent 体系 |
| P0 止血？ | ✅ R-D09 根因已定位 |
| pytest + trace + 批跑闭环？ | ✅ 6/6 单元测试通过；批跑待 12 局后回归 |
| 迁移出口？ | ✅ GUA-091 intent 体系已激活接收 |

## V8 KPI 首公开

| 指标 | 数值 | 含义 |
|------|------|------|
| 头游率 | 35.3% | 单局头游占比 |
| 末游率 | 32.1% | 单局末游占比 |
| **双上率** | **31.5%** | **核心 KPI 首次公开** |
| 平均决策 | 25.5 手/副 | 单副出牌手数 |
| 决策速度 | 0.62s/副 | 单副决策耗时 |

> 注：以上 KPI 基于 Kaggle 公开的 184 副牌谱，是 OpenGuanDan V8-dev 平台首份基线。

## Kaggle 公开里程碑

- **数据集**：`philsz/guandan-v8-data-exploration`（830KB zip，184 副牌谱）
- **Notebook**：`philsz/guandan-v8-data-exploration-184-episodes-31-5`
- **同步副本**：`game_records_v8_kaggle/` 与 `game_records_v8/` 内容一致
- **上传时间**：2026-07-18

## 补丁螺旋 → BC 训练管线切换

本次闭环确认了**补丁螺旋痛点**已逼近天花板：
- 规则补丁越打越细，但 R-D09 这种"边界意图冲突"问题仍层出不穷
- 必须切换到 **BC 预训练 + Self-play RL** 范式
- Kaggle 184 副是 BC 预训练的**首批公开数据底座**
- [[module-bc-trainer]] notebook 是 Kaggle 下一步

## V8 牌谱 Schema 关键差异

与 V7/M3 不同：
- **V8 无 `gameResult.victoryNum[4]`** 数组
- 用 `result.game_count` 累计 + 单值 `result.victory`
- 名次字段：`result.order = [头游座位, 二游, 三游, 末游]`
- 顶层：`game_id, start_time, player_id, player_name, initial_hand, all_players_hands, game_info, actions, my_decisions, result, game_round, end_time, duration`

→ 见 [[concept-recorder-bug]] 与 [[concept-batch-evaluation]]（V8 通道）

## 交叉引用

- [[gua-150]] — 详情
- [[gua-135]] — self_sprint 规则
- [[gua-091]] — 迁移出口 intent 体系
- [[synthesis-v8-gua150-kaggle-milestone]] — 综合分析
- [[concept-v8-win-rate-governance]] — KPI 治理
- [[engine-v8]] — V8 引擎
