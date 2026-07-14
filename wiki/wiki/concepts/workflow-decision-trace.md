---
type: concept
title: "yf 决策链路分析 (WF-12)"
sources:
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
  - docs/guandan-brain/工作流.md
tags:
  - wf12
  - decision-trace
  - debugging
  - r-d01-r-d08
status: current
related_gua:
  - GUA-080
  - GUA-081
date: 2026-07-03
---

# yf 决策链路分析 (WF-12)

## 概念

WF-12 是还原 yf 客户端在某副牌中每个出牌时刻的 decide 管线调用链路的工作流，对应 `workflows/WF-12-yf-decision-trace.md`。

## R-Dxx 根因 Taxonomy

| 编码 | 含义 | 典型场景 |
|------|------|----------|
| **R-D01** | 推荐被 mask 挡 | banned types 误命中 |
| **R-D02** | 推荐缺失 | heuristic fallback 兜底 |
| **R-D03** | 残局未命中 | EndgamePreprocessor 未激活 |
| **R-D04** | 组牌锁死 | grouping_engine 输出空集 |
| **R-D05** | 启发式劣选 | _heuristic_select 退化解 |
| **R-D06** | 场态误读 | curRank / player count 错误 |
| **R-D07** | 记录/贡还 | game_records 写入或还贡异常 |
| **R-D08** | 知识未接入 | Skill / GUA 规则未生效 |

## 配对算法

- 配对键：`[round]-[suffix]`（如 `20260703-001-A`）
- **不是 `game_id`**（yf1 和 yf2 JSON 的 game_id 命名空间不同）
- 工具：`yf_replay.py` + `_try_load_teammate_record`

## 时刻级牌读

- 使用：`my_decisions[i].context.curRank`
- **禁止**：JSON 根 `game_info.curRank`（该值是整局的 curRank，不是出牌时刻的）

## 输出物

1. R-Dxx 根因编码
2. 对应 GUA 编号
3. pytest regression test 名

## 关联

- [[WF-12-yf-decision-trace-summary]] — WF-12 工作流详情
- [[工作流-summary]] — 工作流索引
- [[recursion-game-round]] — 局 ⊃ 副定音
