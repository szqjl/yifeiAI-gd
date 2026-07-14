---
type: query-answer
title: "v7 启动脚本 路径 lalala import 改动"
date: 2026-06-18
sources:
  - wiki/wiki-minimax/synthesis/v7-current-state.md
  - entities/module-v7-engine.md
  - synthesis/m3-batch-infra-closure.md
  - concepts/v7-implementation-roadmap.md
  - wiki/wiki-minimax/concepts/branch-isolation.md
  - concepts/v7-nn-engine-migration.md
  - wiki/wiki-minimax/sources/AGENT_BOOTSTRAP-summary.md
  - sources/V7-实施方案-summary.md
  - synthesis/synthesis-m3-vs-v7-status.md
  - sources/V7-Development-moc-summary.md
---

# v7 启动脚本 路径 lalala import 改动

# V7 启动脚本路径与 lalala import 改动

## 一、启动脚本路径

V7 批跑主入口（vs lalala）：

```
scripts/launchers/v7/run_v7_vs_lalala_games.py
```

V7 客户端：
- `src/decision/ultimate_win_rate_engine_v7/yf1_v7.py`
- `src/decision/ultimate_win_rate_engine_v7/yf2_v7.py`

**绝不可与 M3 混推**，V7 走 `v7-dev` 分支，M3 走 `m-dev` 分支（详见 [[5]] branch-isolation 硬规则）。

---

## 二、lalala 相关的 import 改动

Wiki 中**未直接记录** `run_v7_vs_lalala_games.py` 内部的 import diff。但从以下页面可定位改动范围：

### 1. 引擎入口与子模块（[[2]] module-v7-engine）
```
ultimate_win_rate_engine_v7/
├── __init__.py
├── yf1_v7.py / yf2_v7.py
├── strategy_engine.py
├── phase_handlers/
├── stage_router.py
└── rule_based/
```
启动脚本很可能 import：`yf1_v7`, `yf2_v7`, `strategy_engine`, `stage_router`, 以及 `v7_game_recorder`。

### 2. 数据目录与解析路径变更（[[3]] m3-batch-infra-closure）
GUA-033 关闭后，规范可被 V7 复用，但 V7 是否沿用 `victoryNum` 旧解析路径**尚未定音**：
- 若保留旧路径 → 继承 v1006 `settingTimes=3` argv 限制
- 若切换新路径 → 需新建 `GUA-XXX-V7` 跟踪

> 行动项明确指出："V7 交接文档中明确解析路径选择（待办）"——意味着 import 层面 `game_records_v7/` 数据通道尚未最终拍板。

### 3. 上下文字段 import（[[4]] v7-implementation-roadmap, [[7]] AGENT_BOOTSTRAP）
P0 任务中要求 `context` 字段补 `pass_num/numofnext/numofgreaterPos`（GUA-037a / GUA-050）——这意味着 `stage_router` 或 `phase_handlers` 的 state dict 导入项需新增这三个 key。

### 4. BC 训练相关 import（[[8]] V7-实施方案）
若启动脚本涉及训练闭环，可能 import：
- `bc_dataset.py` / `bc_trainer.py`（GUA-015）
- `zmq_bridge.py`（GUA-016）
- `static_features.py` / `dynamic_features.py`（GUA-017/018）

---

## 三、Wiki 信息的缺口

⚠️ **以下信息 Wiki 未直接覆盖**：

| 缺口 | 说明 |
|------|------|
| `run_v7_vs_lalala_games.py` 当前完整 import 列表 | 需查 `scripts/launchers/v7/` 源码 |
| lalala 对手客户端 import 路径 | Wiki 只说"vs lalala"，未列 import |
| 最近一次 import 改动的 diff | Wiki 无 commit-level 记录 |
| `victoryNum` 解析路径在 V7 中的选择 | [[3]] 明确标记为"待办" |

---

## 四、建议下一步

1. 直接读 `scripts/launchers/v7/run_v7_vs_lalala_games.py` 源码确认当前 import
2. 参考 [[7]] AGENT_BOOTSTRAP §5 P0 任务清单，逐项核对 `choose_bomb` / `context` / `combine_handcards` 三件套的 import 是否到位
3. 若涉及 victoryNum 解析，按 [[3]] 行动项 #1 处理——明确 V7 解析路径选择并写入 handoff
