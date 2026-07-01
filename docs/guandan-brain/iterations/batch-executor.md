---
tags: [infrastructure, batch-executor, GUA-033, victoryNum]
created: 2026-05-29
updated: 2026-05-31
topic: 批跑器改进与 victoryNum 链路
related: [[Infrastructure]], [[v7-infra-gua041-049]]
---

# 批跑器改进与 victoryNum 链路

> 来源：[[ITERATIONS]] 2026-05-29 ~ 2026-05-31

## 批跑器核心修复

| 日期 | 迭代 | 修复内容 |
|------|------|----------|
| 2026-05-29 | M3 PASS 记牌 + actIndex 防护 | `_update_play_state` 跳过 PASS 记牌；`actIndex` clamp |
| 2026-05-30 | M3 成对计数修复 | `_GAME_RECORD_ROUND_PATTERN` 缺 `]` 导致 M3 成对计数恒为 0 |
| 2026-05-31 | 台账计数修复（方案 A+C） | 移除 `max(game_id,round)` 驱动进度；新增 `_scan_game_records_stats`；pytest **5 passed** |
| 2026-05-31 | 批跑局数 3 倍数定音 | `--target-games` 须 3 的倍数；档位 3/9/12；`input_validator` 拒绝非整批目标 |

## GUA-033：批末 victoryNum 异常

| 日期 | 迭代 | 关键内容 |
|------|------|----------|
| 2026-05-31 | 登记 | 批 4 `batch_games=1` 但 `[2,1,2,1]`；backfill 49 副 |
| 2026-05-31 | gameResult 校验+fallback | `game_result_utils.py`；`yf1/yf2_m3` RAW/gameOver 早退/batch_wins fallback；pytest **11 passed** |
| 2026-05-31 | **GUA-033 closed** ✅ | 真源：`batch_games`；禁止裸信 `gameResult.victoryNum` |
| 2026-05-31 | exe argv 实测定音 | v1006 exe **argv 1/3/10 均固定 3 局/会话**；`settingTimes=3` 非字段陈旧 |

## 关键约定

- `--target-games` 须为 **3 的倍数**（推荐 3 / 9 / 12，勿用 10）
- `completed_games` 按平台批次 `+= batch_games`
- 队胜看 `victoryNum[0] vs [1]`（0+2 一队，1+3 一队）
- 禁止裸信 `gameResult.victoryNum`

**涉及文件**：
- `batch_executor/executor.py`
- `game_result_utils.py`
- `tests/test_batch_executor_counting.py`
- `tests/test_m3_gua033.py`
