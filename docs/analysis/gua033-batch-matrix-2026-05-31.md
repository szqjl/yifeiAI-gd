# GUA-033 三线对照与批跑矩阵（2026-05-31）

> 已按 `docs/guandan-brain/README.md` §Agent 批跑数据入门 掌握局/副/victoryNum 口径；胜率只看批末 `[0]` vs `[1]`，且须 `[0]+[1]=本批 batch_games`。

## 1. 谁为准（结论）

| 维度 | 真源 | 勿裸信 |
|------|------|--------|
| 本批打几 **局** | `batch_executor/current_batch.json` → `batch_games`（= exe argv N） | WebSocket `gameOver.settingTimes` |
| 批跑累计 | `execution_state.completed_games` | `game_records` 文件数 / match_key |
| 批末队胜 | 校验后的 `victoryNum`（或 gameOver 计数 fallback） | 原始 `gameResult.victoryNum` / `final` 未校验 |

**实测**：`exe 1` 时 WebSocket 仍发 `gameOver(settingTimes=3, curTimes=1→3)` 与 `gameResult.victoryNum=[2,1,2,1]` 或 `[3,0,3,0]`（`[0]+[1]=3≠1`）。**settingTimes 与 victoryNum 均可能陈旧/错误**；**exe 参数 + current_batch.json 为准**。

## 2. 三线对照（单批示例：target-games=1）

| 线 | 来源 | 观测 |
|----|------|------|
| **A exe/台账** | `current_batch.json` | `batch_games=1`；启动日志 `游戏场数: 1` |
| **B WebSocket** | yf1_m3 log | `gameOver` ×3：`settingTimes=3`，`curTimes=1→3`；`gameResult RAW`：`[2,1,2,1]` |
| **C 客户端落盘** | `latest_victory_num.json` | 校验失败后 fallback → `[0,1,0,1]`；executor 批末 **通过** |

证据 JSON：`data/eval/gua033_matrix_1.json`

## 3. 批跑矩阵记录表

| Run | target | 批次数 | completed | exe N（末批） | 服务器 RAW vn（典型） | fallback | 批末 vn（最终） | `[0]+[1]` vs batch_games |
|-----|--------|--------|-----------|---------------|----------------------|----------|-----------------|-------------------------|
| 1 | 1 | 1 | 1/1 | 1 | `[2,1,2,1]` | **是** → `[0,1,0,1]` | `[0,1,0,1]` | 1=1 ✓ |
| 2 | 3 | 1 | 3/3 | 3 | `[1,2,1,2]` | 否 | `[1,2,1,2]` | 3=3 ✓ |
| 3 | 10 | 4 | 10/10 | 1（批4） | 批4：`[3,0,3,0]` | **是** → `[1,0,1,0]` | 批1–4 均通过 | 批4：1=1 ✓ |

10 局四批 executor 批末校验：

| 批 | batch_games | 最终 vn | Team0–Team1 |
|----|-------------|---------|-------------|
| 1 | 3 | `[3,0,3,0]` | 3–0 |
| 2 | 3 | `[1,2,1,2]` | 1–2 |
| 3 | 3 | `[2,1,2,1]` | 2–1 |
| 4 | 1 | `[1,0,1,0]`（fallback） | 1–0 |

原始证据：`data/eval/gua033_matrix_{1,3,10}.json`；批跑日志 `logs/batch_executor_20260531_192640.log` 等。

## 4. exe 1 vs 3（启动侧）

`batch_executor --diagnose-only --target-games N` 启动 `guandan_offline_v1006.exe N`；诊断从 stdout 解析「游戏场数: N」。**与 WebSocket `settingTimes` 无关**。

| exe argv | 启动日志 | state.py 打印（需连客户端） |
|----------|----------|----------------------------|
| 1 | `游戏场数: 1` | `gameOver` 仍可能打印 `设定=3`（协议字段不可靠） |
| 3 | `游戏场数: 3` | 通常 `settingTimes=3` 与 argv 一致 |

## 5. yf2_m3 对齐

`yf2_m3` 已对齐 `yf1_m3`：`gameOver` 计数 + `gameResult` 校验失败时 `build_local_batch_victory_num` fallback。测试：`tests/test_m3_gua033.py::test_yf2_game_result_fallback_to_batch_wins`。

## 6. 代码与文档

- `src/communication/game_result_utils.py` — `resolve_expected_batch_games` 优先 `current_batch.json`
- `yf1_m3` / `yf2_m3` — RAW log、校验、fallback
- `docs/knowledge/platform-data-interpretation.md` §3.1/§3.3 — 禁止裸信 `gameResult.victoryNum`

复跑矩阵：`scripts/tools/gua033_run_matrix.ps1`
