﻿# 给执行 AI 的说明（修复 batch_executor 计数口径）

把下面**整段**复制到新对话里。执行前必须先读评审报告，**不要**凭聊天摘要改代码。

**评审真源**：[`docs/analysis/batch_executor_counting_review-2026-05-31.md`](../analysis/batch_executor_counting_review-2026-05-31.md)

---

## 复制起点（以下整段发给 Agent）

请先阅读：

1. `docs/analysis/batch_executor_counting_review-2026-05-31.md`（评审结论）
2. `batch_executor/executor.py`（`_count_new_paired_games`、`_sync_completed_from_game_records`、主循环 L610–1001、批内 L833–851）
3. `batch_executor/README.md`、`docs/guandan-brain/EVAL.md`、`docs/guandan-brain/LOCAL_EVAL_CHECKLIST.md`（文档口径）
4. `src/communication/game_recorder.py`（`RECORD_FILENAME_RE`、`parse_record_filename`、GUA-025 merge 键）

### 任务

按评审 **方案 A + C** 修复 `--target-games` 计数，使 M1/M2/M3 共用 `batch_executor` 行为一致。

**方案 A（主进度，必做）**

- `completed_games` 以 **平台会话批次数 × 每批 `batch_games`** 为准：每批服务器 **正常结束**（stdout「达到设定」或进程退出且 **非** `server_terminated_by_kill`）→ `completed_games += batch_games`（最后一批加 `remaining`）。
- 主循环退出条件仍为 `completed_games < target_games`；`restart_count` 在需续跑时递增（保持现有 L976–999 逻辑，但进度来源改为 A）。
- **删除或禁用**用 `_count_new_paired_games` 的返回值 **写入 / cap `completed_games`** 的逻辑（含 L445–446、L833–851 用 round 对数提前结束批次）。

**方案 C（落盘校验 + ITERATIONS 分析，必做）**

- 新增或抽取函数：统计本 Run 新增 **成对 match key** 数——键为 `GameRecorder.parse_record_filename` 的 `(opponent, round, level)`，要求 yf1_* 与 yf2_*（与 `_count_new_paired_games` 相同 prefix 参数）各至少一份 JSON。
- 该指标 **只打日志 / 可选 WARN**（例如单批 match_key 增量远大于 `batch_games`），**不得**驱动主循环完成。
- 保留 `_count_new_paired_games` 中 **成对 game_id** 计数仅作 **诊断日志**（可选）；**移除 `max(id, round)` 作为进度** 的行为。

**文档（必做，最小片段）**

- `batch_executor/README.md`：区分 **台账 `completed_games`（平台批次数累计）** vs **落盘 match_key / game_id（分析用）**；一句说明 **`victoryNum` 是四座位累计胜场，不是局数/副数**。
- `LOCAL_EVAL_CHECKLIST.md` / `EVAL.md` 各补 **一句** 与 README 一致（勿大改结构）。

**测试（必做）**

- 新增 `tests/test_batch_executor_counting.py`：用 `tmp_path` 伪造 `game_records/*.json` 文件名，**不启真实 exe**。至少覆盖：
  - 39 对 round、0 对 game_id → **新逻辑下 completed 仍由 batch 驱动，不由 round  cap 到 10**
  - M1 式同 game_id 成对 → 诊断计数正确，但不影响 A 主进度
  - match_key 成对计数与 GUA-025 键一致
- 跑 `pytest tests/test_batch_executor_counting.py tests/test_batch_executor_integration.py tests/test_game_recorder_merge.py -q`

**本机验收（改完后执行，结果写入 ITERATIONS 新行，勿关 GUA）**

```powershell
cd d:\guandanscore\YiFeiAI-GD
Remove-Item game_records\*.json -Force -ErrorAction SilentlyContinue
python -m batch_executor --target-games 10 `
  --server-path "offline_platform\guandan_offline_v1006\windows\guandan_offline_v1006.exe" `
  --clients src/communication/yf1_m3.py src/communication/run_lalala_client3.py `
            src/communication/yf2_m3.py src/communication/run_lalala_client4.py
```

**通过标准**：`execution_state.json` 中 `restart_count >= 3`、日志 ≥4 次「开始批次」、`completed_games == 10` 且与 4 批 `batch_games` 之和一致；**不再**出现「仅 1 批、39 round 对即 completed=10」。

### 约束

- **最小 diff**：只动 `batch_executor/`、上述测试、文档三处一句说明；**不改** M3 决策引擎、**不改** game_recorder 写文件格式（方案 B 不在本轮）。
- 时间戳用 `datetime.now()`，勿硬编码日期。
- **不要**在本轮将 GUA-022 / GUA-029 / GUA-031 等标 closed；仅在 `ITERATIONS.md` 追加一行「计数修复 + 批跑复验」。
- 若本机无法跑 exe，完成单测 + 代码审查后于 ITERATIONS 注明「待本机批跑」。

### 交付

1. 代码 + 单测 + 文档片段  
2. `ITERATIONS.md` 一行（改动摘要、pytest 结果、批跑 restart_count/completed_games 或「待本机」）  
3. 给用户 **3 句话**：victoryNum / completed_games / game_round 各是什么  

---

## 可选附言

- 历史 M3「10/10 批跑」行见 `ITERATIONS.md` 2026-05-30 M3 条目 —— **完成度结论无效**，修复后需净盘重跑再评 GUA-029。  
- Handoff：[`handoff/2026-05-31-M3-skills映射与组牌总纲.md`](../guandan-brain/handoff/2026-05-31-M3-skills映射与组牌总纲.md)
