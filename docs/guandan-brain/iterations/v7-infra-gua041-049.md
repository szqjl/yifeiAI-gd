---
tags: [V7, infrastructure, GUA-041, GUA-044, GUA-047, GUA-048, GUA-049, V7-006, V7-010]
created: 2026-06-04
updated: 2026-06-08
topic: V7 基础设施与路径修复
related: [[V7-Development]], [[batch-executor]]
---

# V7 基础设施：路径债 / 门闩 / 卡顿诊断（GUA-041 ~ GUA-049）

> 来源：[[ITERATIONS]] 2026-06-04 ~ 2026-06-08

## GUA-041：路径债清理

| 日期 | 迭代 | 内容 |
|------|------|------|
| 2026-06-04 | 落地 | `config/v7_paths.yaml`（env > yaml > 候选回退）；`v7_paths.py` 无任何 `D:` 硬编码；pytest **6 passed**；**GUA-041 closed** ✅ |
| 2026-06-07 | 服务器 exe 迁出仓库 | `.gitignore` 精确匹配；服务器路径→`D:/guandanscore/guandan-offline-serve/` |

**涉及文件**：
- `config/v7_paths.yaml`
- `src/utils/v7_paths.py`
- `tests/test_v7_paths.py`

## GUA-044：四席就绪门闩

- 现象：批跑误报 0/4 连接仍开局
- 修复：`client_ready.py`（`clients_ready.json` + 顺位门闩 + `wait_for_all_clients`）
- `test_client_ready.py` **3 passed**；**GUA-044 closed** ✅

## GUA-047：73s 卡顿诊断（误判 → 确认真问题）

| 日期 | 迭代 | 发现 |
|------|------|------|
| 2026-06-07 | 立条 | 4 席全停 ~20s（疑似 exe 内部） |
| 2026-06-07 | 误判关单 | 原"全停 20s"是 stdout dump 延迟 73s 假象；**GUA-047 closed**（误判） |
| 2026-06-07 | 深入分析 | M3 对照批跑无停顿，V7 特有 73s → 根因锁定 WebSocket recv 层；perf 打点已加 |

**最终结论**：73s 是真问题且 V7 特有（非 stdout dump），根因在 WebSocket `async for` 迭代阻塞。

## GUA-048：日志 dump 延迟 + GUA-049：race condition

| 日期 | GUA | 根因 | 修复 |
|------|-----|------|------|
| 2026-06-07 | GUA-048 立条 | stdout 双读者（开局检测后台线程 + 主线程 `for line`）→ 主日志延迟 73s | `ServerStdoutReader` 单线程实时 drain + flush |
| 2026-06-07 | GUA-049 根因锁定 | `game_ready.json` 缺 yf2_v7 entry → 3 子根因：race condition（非原子写）+ 无 try/except + 60s 超时 | pytest 复现成功 |
| 2026-06-08 | GUA-049 P0 修复 | 文件锁（fcntl/msvcrt）+ temp+rename 原子写；批跑验收 3 局 0 WARNING；**GUA-049 P0 关单** ✅ |

**涉及文件**：
- `batch_executor/client_ready.py`
- `batch_executor/server_stdout_reader.py`
- `tests/test_game_ready_race.py`（5 passed）
- `tests/test_batch_stdout_reader.py`
