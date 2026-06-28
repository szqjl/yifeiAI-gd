---
name: guandan-decision-trace
description: >-
  分析 yf1/yf2 某一出牌步的完整决策链路：读 game_records my_decisions、
  客户端日志 GUA-075/残局/Guard/heuristic，还原 decide() 管线，归类 R-D01～R-D08 根因，
  导向 GUA 与 pytest。Use when 决策链路, 为何出这手, yf 出牌分析, WF-12,
  我方不胜, 败招根因, actIndex, GUA-075 拦截.
---

# yf 决策链路分析（WF-12）

## 真源

完整步骤与模板：[`docs/guandan-brain/workflows/WF-12-yf-decision-trace.md`](../../docs/guandan-brain/workflows/WF-12-yf-decision-trace.md)

汇报格式：[`docs/guandan-brain/工作流.md`](../../docs/guandan-brain/工作流.md) §2.6

## 动手顺序（不可跳）

1. 定位牌谱：`game_records_v7/`（V7）或 `game_records/`（M3）
2. `actions[]` 还原圈况（步 N 前后）
3. `my_decisions[]` 找 act 快照（`action_index`、`card_mask`、`role`）
4. `logs/yf*_v7_*.log` 搜同时刻：`GUA-075`、`组牌保护拦截`、`残局管线命中`、`actIndex=`
5. 按 V7 管线表写「命中层 / 被挡层 / 回退层」
6. 打标签 **R-D01～R-D08** + 建议 GUA/pytest

## V7 管线速记

组牌 → 信念 → **残局** → **GUA-075** → mask 拦截? → Guard → 组牌过滤 → NN → heuristic

**关键**：`GUA-075 主路径 ✅` = L2 成功；仅有 `推荐被组牌保护拦截` = L2′ 失败 → 必写回退路径。

## 禁止

- 不读日志就下结论
- 用单局 replay 逐步一致作关单标准
- 改牌谱

## 产出

- 给用户：§2.6 格式报告
- 可复现缺陷：`ISSUES.md` 新 GUA 或更新 open GUA + `issues/GUA-xxx-completion.md`
- 可选：`replay_word.md` 追加典型步摘要
