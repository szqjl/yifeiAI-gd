---
type: source-summary
title: "WF-12 yf 决策链路分析摘要"
sources:
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
tags:
  - workflow
  - wf12
  - decision-trace
  - debugging
status: current
related_gua:
  - GUA-080
  - GUA-081
date: 2026-07-03
---

# WF-12 yf 决策链路分析摘要

## 工作流目标

还原 yf 客户端在某副牌中每个出牌时刻的 decide 管线调用链路，从牌谱 `my_decisions` + 客户端 log 出发，逐层定位到具体的 Guard（R01-R12）/ GUA / pytest 用例。

## 执行步骤

1. **加载牌谱**：从 yf_replay.py 读取 `game_records`，提取目标副的 `my_decisions` 数组
2. **配对 yf1 / yf2 记录**：配对键是 `[round]-[suffix]`，**不是 `game_id`**（GUA-yfyf2 pairing）
3. **时刻级牌读**：使用 `my_decisions.context.curRank`，**禁止**用 JSON 根 `game_info.curRank`
4. **定位 decide 入口**：从客户端 log 反查 `engine_v7.py decide()` 调用
5. **trace 管线**：L0 → L1 → ... → L8 各层产出（grouping / guards / heuristic / endgame）
6. **诊断归类**：套用 R-D01~R-D08 taxonomy 输出根因编码
7. **写入 pytest**：根据根因落到 GUA-080/081 等的 regression test

## 关键工具

| 工具 | 用途 |
|------|------|
| `wf12_find_decision_at_step.py` | 在牌谱中定位指定 step 的决策 |
| `yf_replay.py` | 加载 `_try_load_teammate_record`，配对 yf1/yf2 |
| `analyze_v7_rounds.py` | 批量轮次分析 |
| `RECORD_NAME_RE` | yf_replay.py 中匹配记录文件名的正则 |

## 输出物

- R-Dxx 根因编码（如 R-D01 推荐被 mask 挡）
- 对应 GUA 编号 + pytest 用例名
- 决策链路 trace 文件（可重放）

## 关联

- [[workflow-decision-trace]] — R-Dxx taxonomy 概念定义
- [[工作流-summary]] — 工作流索引
- [[gua-080]] — card_mask / 组牌退化校验
- [[gua-081]] — _heuristic_select 退化诊断
