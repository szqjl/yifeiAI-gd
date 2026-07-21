# Agent Anchored Summary

> **最后更新**：2026-07-21  
> **分支**：`v8-dev`  
> **最新 commit**：`ba0ef54c`（GUA-156 三带二 pairs 排序修复）

---

## Objective

- Review and understand the YiFeiAI-GD project (Guandan AI client for v1006/OpenGuanDan platform)
- Verify and update project documentation status (GUA-148/GUA-150 closure)
- Evaluate CardCountingNetwork's role in the AI system
- Analyze V8 batch run results and CCN Phase 0 readiness
- Diagnose a specific yf1 decision flaw (大王压7) and identify root cause in grouping engine
- Fix GUA-156: three-with-two pair sorting bug

## Important Details

- **Project**: YiFeiAI-GD - 掼蛋 AI 客户端，南京邮电大学 v1006/OpenGuanDan 平台
- **Branch**: `v8-dev`（OpenGuanDan 新平台迁移），已与远端 `origin/v8-dev` 对齐
- **Active branches**: `v7-dev`（V7 回退基线），`v8-dev`（OpenGuanDan 新平台），`m-dev`（M3 交付）
- **M1 frozen**；队 KPI **只看 M3 批跑**
- **Data units**: 副（episode）= game_records JSON / episodeOver；局（game）= 2→A 双上过关 / completed_games；局 ⊃ 多副
- **Teams**: 0+2 一队，1+3 一队；`--target-games` 须为 3 的倍数
- **v1006 平台**: WebSocket `ws://127.0.0.1:23456`，TCP Socket
- **OpenGuanDan**: WebSocket `ws://127.0.0.1:8181`，JSON 协议
- **CardCountingNetwork**: 训练从出牌历史推断各家剩余牌分布的 NN 模块，108 槽位 × 3 类，Phase 0 数据验证是硬门槛
- **V8 批跑结果**: 局胜率 66.7%~100%，副头游率 60%~72%，双上率 24%~36%
- **V8 最新 batch**: `20260721131151461716`，145 副（290 文件），scores.json 正常
- **CCN Phase 0 任务拆解**: 5 项任务已审批通过（附 4 项修订条件），待执行
- **GUA-057 状态**: open P1 🔴，CCN 前置条件：GUA-072 closed（pytest 39/39）+ GUA-071 副胜率 ≥15%
- **GUA-071 状态**: open P0，`_heuristic_select` 仅 4 条元规则
- **GUA-079 状态**: open P0，全阶段决策崩坏三层根因（层①单牌倒置已确认）
- **GUA-156 状态**: open P0 🔴，三带二初始组牌 pairs 排序 bug，已实施 1 行修复
- **Wiki ingest**: 已执行，8 文件处理，745 页总量
- **净盘**: V8 环境已干净（game_records_v8/ 0 文件，logs/ 0 文件）

## Work State

### Completed
- Read all project documentation (AGENTS.md, AGENT_BOOTSTRAP.md, ITERATIONS.md, ISSUES.md, README.md, EVAL.md)
- Confirmed 副/局概念理解正确
- Committed and pushed `981a0cc0` to `origin/v8-dev`（grouping engine, tests, ITERATIONS）
- Deleted `D:\YiFeiAI-GD\nul` (Windows reserved device name)
- Verified no other reserved device name files exist in project
- Read latest handoff (2026-07-21): GUA-154 fixed, 145 副验证通过
- Verified GUA-148 and GUA-150 already closed in commit history
- Updated ISSUES.md: removed GUA-148/GUA-150 from active P0 list, committed `c24460a8`
- Provided objective evaluation of CardCountingNetwork
- Read `v8-win-rate-history.md` — all 4 batch runs analyzed (副头游率 60~72%, 双上率 24~36%)
- Read CCN 训练方案 v3 — 3 期训练 + 7 项评审发现
- Searched ISSUES/ITERATIONS for CCN status — GUA-057 open, GUA-072 closed, GUA-071 open
- Provided professional CCN opinion: 方向正确但时机偏早，建议先推 GUA-079→GUA-072 关单④→Phase 0
- Reviewed CCN Phase 0 任务拆解 — 审批通过，附 4 项修订条件
- Executed wiki ingest — 8 files processed, 745 pages total
- Ran V8 净盘 — environment confirmed clean (0 files in game_records_v8/, logs/, no state files)
- Analyzed game `20260721131151461716` step 2/120: yf1 played HR (大王) to压 D7 — diagnosed as 资源误判败招
- Proposed optimal grouping for yf1's hand and recommended PASS at step 2
- **Identified grouping engine bug**: `_detect_three_with_two` line 806 — `remaining_pairs` not sorted by rank, causing large pairs (TT, QQ) to be consumed by ThreeWithTwo instead of small pairs (55, 66)
- Proposed fix: add `remaining_pairs.sort(key=lambda p: _card_rank_value(p[0], cur_rank))` after line 806
- Confirmed this is a new GUA issue (not covered by GUA-114 which only fixes dynamic出牌 path, not initial组牌)
- Created GUA-156-completion.md with completion definition
- Added GUA-156 entry to ISSUES.md and ITERATIONS.md
- Implemented fix: 1 line added after grouping_engine.py line 806
- Verified pytest: test_grouping_engine 61/61, test_gua114 4/4 — all pass
- Committed `ba0ef54c` and pushed to v8-dev

### Active
- (none)

### Blocked
- (none)

## Next Move
1. **净盘 + V8 批跑 3+ 局验收 GUA-156**：验证三带二组牌不再消耗大对子
2. **抽 3~5 副 yf2 末游走 WF-12**：分析 yf2 末游率 41% 异常
3. **GUA-079 三层根因修复**：层①单牌倒置（_heuristic_select 4 条元规则）
4. **CCN Phase 0 启动**：需先完成净盘批跑生成牌谱
5. **路径 1**：写 v8_v4_adapter.py 引入非 lalala 对手

## Relevant Files

### Documentation
- `AGENTS.md`: 项目入口，工作流/术语/净盘规范
- `docs/guandan-brain/AGENT_BOOTSTRAP.md`: V7/V8 启动指南，环境/批跑/命令
- `docs/guandan-brain/ITERATIONS.md`: 迭代日志 MOC 入口（含 GUA-156）
- `docs/guandan-brain/ISSUES.md`: 缺陷登记簿（含 GUA-156）
- `docs/guandan-brain/README.md`: 项目真源，四角色概览
- `docs/guandan-brain/EVAL.md`: 评测入口与通过标准
- `docs/guandan-brain/v8-win-rate-history.md`: V8 批跑胜率历史（4 条记录）
- `docs/guandan-brain/CardCountingNetwork-训练方案.md`: CCN 训练方案 v3（GUA-057）
- `docs/guandan-brain/CCN-Phase0-任务拆解.md`: CCN Phase 0 任务拆解（已审批）
- `docs/guandan-brain/issues/GUA-156-completion.md`: GUA-156 关单条件

### Code
- `src/v/nn/features/grouping_engine.py`: 组牌引擎（GUA-156 fix at L806+1）
- `src/v/nn/ultimate_win_rate_engine_v7.py`: V7 胜率引擎（GUA-079 层①）
- `batch_executor/executor.py`: 批跑执行器
- `tests/test_grouping_engine.py`: 组牌引擎测试（61 项）
- `tests/test_gua114_three_with_two_kicker_orphan.py`: GUA-114 三带二测试（4 项）

### Data
- `game_records_v8/`: V8 牌谱目录（当前 0 文件，已净盘）
