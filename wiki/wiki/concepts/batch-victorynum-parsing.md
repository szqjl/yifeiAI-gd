---
type: concept
title: "批末 victoryNum 解析"
sources:
  - docs/guandan-brain/issues/GUA-033-completion.md
  - docs/analysis/gua033-batch-matrix-2026-05-31.md
tags:
  - concept
  - batch
  - evaluation
  - kpi
status: current
related_gua:
  - GUA-033
date: 2026-06-17
---

# 批末 victoryNum 解析

## 背景

M3 批跑体系中，客户端与 executor 之间通过 WebSocket 传递三类结果事件，原始实现中存在事件误用（如 `episodeOver.result[4]`），导致胜利数与实际 batch_games 不一致。GUA-033（2026-05-31 closed）确立了统一解析规范。

## 三类事件区分

| 事件 | 触发时机 | 是否写 victoryNum | 备注 |
|------|----------|-------------------|------|
| `gameOver` | 早退 / 异常退出 | **否** | 早退局不计入胜率 |
| `gameResult` | 正常结束 | **是**（读 `final` / `victoryNum`） | 主要数据源 |
| `episodeOver` | 单局回合结束 | **禁止误用** `result[4]` | 仅回合层信号 |

## 批末自检

```python
victory_num = sum_victories_from_game_result()
if victory_num != expected_victory_num(batch_games):
    log.WARNING(...)
    skip_kpi_calculation()
```

- 不一致 → WARNING + 不计胜率
- 一致 → 正常计入 KPI

## Backfill 范围

backfill（补写历史胜利数）需同时满足：

- 本批 `[0]+[1] == batch_games`（胜利 + 失败 = 总局数）
- 同队 `[0] == [2]`（己方胜利数两队一致）
- 同队 `[1] == [3]`（己方失败数两队一致）

批间必须清空 `pending_result_files`，避免跨批污染。

## 平台侧限制（v1006）

- `windows/` 目录无 ini/json 覆盖 argv 机制
- argv 1/3/10 均为 `settingTimes=3`，会话固定 3 平台局
- 性质：平台问题，非代码缺陷
- 处置：更换 exe 需重跑矩阵再定音

## 与 EVAL 体系的关系

- [[EVAL-summary]]：共用 victoryNum / gameResult 解析逻辑
- 批跑评测体系：GUA-033 是批跑基建核心
- 胜利数是胜率 KPI 的输入，本规范的稳定性直接影响 批跑评测体系 的可信度

## V7 迁移

- M3 批跑体系已 closed
- V7 NN 引擎可能不再依赖 WebSocket `victoryNum`
- 当前 closed 仅针对 M3 批跑体系

## 相关页面

- [[GUA-033]]：实体页（根因 + 验收标准）
- M3 批跑基建关闭后的下游影响：综合分析
