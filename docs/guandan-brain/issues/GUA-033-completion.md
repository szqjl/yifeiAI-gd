# GUA-033 完成定义（M3 批末 victoryNum / gameResult）

> 根因核查 **2026-05-31**：客户端混处理 `gameOver`/`gameResult`/`episodeOver`（已修）；**平台侧**见 [`platform-data-interpretation.md`](../knowledge/platform-data-interpretation.md) **§2**——本包 exe **argv 无效**，单次会话 **固定 3 局**，致 `batch_games=1` 时 WebSocket `[0]+[1]=3`。

| 项 | 完成标准 |
|----|----------|
| **解析** | 对齐 M1：`gameOver` **早退**不写 `victoryNum`；`gameResult` 读 **`final` 与/或 `victoryNum`**（以本机 WebSocket 真包为准）；禁止从 `episodeOver` 误用 `result[4]` |
| **日志** | `stage==gameResult` 打 **RAW JSON** 一行（可 `DEBUG`）；batch 日志可对照 `0号位胜利` |
| **回填** | 仅在本批 **`[0]+[1]==batch_games`** 且同队 `[0]=[2]`、`[1]=[3]` 时 `backfill`；批间 **清空 `pending_result_files`** |
| **校验** | 客户端或 executor **批末自检**：`victoryNum` 与 `execution_state` 本批 `batch_games` 一致，否则 **WARNING + 不计胜率** |
| **测试** | `tests/test_m3_gua033.py`（≥4 case：gameOver 无 vn、gameResult+final、backfill 范围、批末校验） |
| **验收** | 净盘 `--target-games 10` **4 批**满跑：每批末 `[0]+[1]` = 该批 `batch_games`；批 4 末条 **≠** 批 1/2 的 `[2,1,2,1]` 除非本批确为 3 局 |

**关单条件**：上述解析 + 测试 + **一次** 10 局满跑批末 vn 全批自洽。**不要求**队胜率达标（队胜率以 **M3 批跑**观测为准）。

**已关单（2026-05-31）**：矩阵 1/3/10 净盘；批 4 `[0]+[1]=1`；详见 [`gua033-batch-matrix-2026-05-31.md`](../analysis/gua033-batch-matrix-2026-05-31.md)。

## GUA-033 平台侧根因：v1006 exe argv 实测（定音，2026-05-31）

> 与 PDF 说明书「`exe N` → `settingTimes=N`」**不一致**；属 **离线 exe 实现**，非本仓库启动脚本写死 3 局。

| 项 | 结论 |
|----|------|
| **配置文件** | `windows/` 目录 **无** ini/json 覆盖 argv |
| **argv 1 / 3 / 10** | WebSocket 均为 **`settingTimes=3`**，`curTimes=1→2→3`，会话 **固定 3 平台局** |
| **`gameResult.victoryNum`** | 按 **3 局**累计 → `[0]+[1]=3`；`batch_games=1` 时与台账冲突 **可预期** |
| **批跑脚本** | `restart_manager` 传参正确；`completed_games` = **会话完成次数**（意图口径），≠ WebSocket 实际局数 |
| **客户端对策** | **`current_batch.json` → `batch_games`** 校验；失败 → **gameOver 本地计数 fallback**（已实现） |
| **复测** | `python scripts/tools/probe_exe_argv_ws.py --compare` |
| **真源** | [`platform-data-interpretation.md`](../knowledge/platform-data-interpretation.md) **§2** |

**后续**：若更换平台 exe，须重跑 §2 矩阵再定音；向南邮反馈 argv 无效时可附本节与探测 JSON。
