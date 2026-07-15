---
type: source-summary
title: "南邮离线平台 actionList 候选缺失观测报告"
sources:
  - docs/analysis/archive/南邮离线平台-actionList候选缺失观测报告.md
tags:
  - gua-124
  - actionlist
  - vendor-platform
  - v7-replay
  - 离线评测
status: current
related_gua:
  - GUA-124
  - GUA-123
  - GUA-062
date: 2026-07-15
---

# 南邮离线平台 actionList 候选缺失观测报告

> 来源文件：`docs/analysis/archive/南邮离线平台-actionList候选缺失观测报告.md`（约 5631 字符）

## 核心论点

本报告记录了在 V7 引擎 (`yf2_v7`) 复盘过程中观测到的 **actionList 候选完备性** 问题——南邮 (NJUPT) 离线平台下发的 `actionList` 在某些局面下漏列了本应可出的合法牌型。报告经历了「初稿误判 → 全量复核 → 推翻原结论 → vendor 反馈 → 部分闭环」五个阶段，是 Wiki 演进论点「**批跑是唯一真源**」与「**初稿结论必须经全量复核**」的具体案例。

## 关键事件时间线

| 时间 | 事件 | 结论 |
|------|------|------|
| 2026-06-28 | 初稿报告 (44 例明确可压但未给出) | 判定为平台 bug |
| 2026-06-29 | `verify_actionlist_pass_only.py` 全量复核 | **推翻原结论**：多数 PASS-only 按 `curRank` 重算合理 |
| 2026-06-30 | 锚定 step64 (`game_id=20260708230844225341`) | 锁定最小复现：仅 1 例逢人配竞争下漏候选 |
| 2026-07-05 | 向南邮发送 vendor 反馈信 (issue#124 形式) | 转交 vendor 处理 |
| 2026-07-12 | 南邮回复 (口头)：v1006 端 `ws://23456` 行为已说明 | ISSUES 标记 closed (临时) |
| 待办 | **OpenGuanDan (`ws://8181`)** 复验 | 尚未执行；不能算最终闭环 |

## 涉及实体

### 平台 / 协议
- **guandan_offline_v1006**（竞赛 exe，`ws://127.0.0.1:23456/game/{client}`）
- **OpenGuanDan**（GitHub 开源房间协议，`ws://8181` + HTTP 3000，CREATE_ROOM/JOIN_ROOM/PLAY）
- **actIndex 协议限制**：客户端无法补报未枚举动作

### 引擎 / 模块
- [[module-batch-executor]]（批跑复盘脚本宿主）
- `scripts/analysis/verify_actionlist_pass_only.py`（PASS-only 全量复核脚本）
- `src/communication/v7_game_recorder.py`（V7 局记录器）
- `normalize_action_list()`、`decision_context_from_act`、`find_latent_bomb_like_beaters_not_in_action_list`

### 牌型概念
- 逢人配 (级牌 H2)：同一张牌可同时编入多种牌型 → **逢人配竞争**
- 五星炸、同花顺 StraightFlush、Bomb/K、Bomb/J
- 牌型牌力比较：**同花顺 > 五星炸**

### 数据锚点
- `game_id = 20260708230844225341`
- `game_records_v7/20260708230844225341 [yf2_v7]-[opponent_1_3]-[1]-[2].json`
- `game_decision_traces/20260708230844225341.jsonl`
- 锚定 step：64

## 核心概念

- **actionList 候选完备性**（enumeration completeness）：服务端下发的合法出牌集合是否完备
- **PASS-only ≠ 漏候选**：玩家 PASS 仅代表当前未出，不能反推候选缺失（已被全量复核推翻的初稿假设）
- **最小复现**：从 44 例压缩到 step64 单步，定位「逢人配竞争」这一具体机制
- **vendor bug 报告流程**：初稿 → 复盘 → 精修 → 对外反馈 → 闭环（每步留痕）
- **局 ≠ 副**：同一 `game_id` 下 `actions[]` 步号口径统一

## 已识别张力

### 1. GUA-124 状态不一致（待复验）
- 正文标 `observation (open)`
- 第十一节写 `ISSUES GUA-124 closed (v1006 侧 vendor 说明)`
- 南邮回复称新版已修，但 **OpenGuanDan 上未复验**
- 闭环属临时结论，复验后可能正式 close 或 reopen

### 2. v1006 ≠ OpenGuanDan
- 两套 API、两套端口、两套消息格式
- V7 引擎迁移需「单独评估 v7 客户端协议适配」
- 与现有 V7-引擎调用链假设存在张力

### 3. 初稿结论被自我推翻（方法论教训）
- 「44 例明确可压但未给出」 → 经 `verify_actionlist_pass_only.py` 复核，多数 PASS 合理
- 不能作为平台 bug 依据
- 是「**批跑是唯一真源**」论点的具体案例

## 与现有 Wiki 的关联

| 关联页面 | 关联理由 |
|----------|----------|
| [[gua-124]] | 本批次核心实体条目 |
| [[gua-123]] | 同类 PASS-only 复盘范式（引用其 completion.md §8） |
| [[gua-062]] | 批跑评测范式先例 |
| [[actionlist-enumeration-completeness]] | 跨 GUA-124/123/062 的共性概念 |
| [[wildcard-competition]] | 逢人配竞争是本报告核心机制 |
| [[v1006-vs-openguandan]] | vendor 平台版本差异 |
| [[vendor-bug-report-workflow]] | 初稿→复盘→精修→闭环方法论 |
| [[v7-current-state]] | V7 复盘中发现的 actionList 现象 |
| [[batch-evaluation]] | 批跑评测体系（`verify_actionlist_pass_only.py` 是批跑复盘脚本） |

## 关键复盘教训（写入 Wiki）

1. **初稿报告须经全量复核**：44 例 → 1 例，方法论上不可跳过 `verify_*` 脚本
2. **PASS-only ≠ 平台 bug**：玩家 PASS 在 `curRank` 重算下多数合理
3. **vendor 闭环必须自验**：仅靠 vendor 口头说明不能算最终结论（V7 迁移到 OpenGuanDan 后必须复验）
4. **逢人配竞争是牌理层面的关键现象**：组牌衔接设计须显式处理多牌型共享级牌
5. **actIndex 协议限制**：客户端无法补报未枚举动作，所有候选完备性问题必须在服务端层解决

## 状态

- 本报告：**archived**（已归档）
- 关联 GUA-124：**closed with caveat**（v1006 侧闭环，OpenGuanDan 侧待复验）
