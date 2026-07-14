---
type: query-answer
title: "批跑脚本 命令 参数 批跑入口 batch_executor"
date: 2026-06-19
sources:
  - entities/module-batch-executor.md
  - concepts/script-directory-layout.md
  - sources/GUA-044-completion-summary.md
  - wiki/wiki-minimax/entities/tool-batch-executor.md
  - concepts/v1006-platform-params.md
  - entities/gua-044.md
  - wiki/wiki-minimax/concepts/batch-evaluation.md
  - concepts/quad-ready-gate.md
  - entities/gua-019.md
  - wiki/wiki-minimax/sources/EVAL-summary.md
---

# 批跑脚本 命令 参数 批跑入口 batch_executor

# 批跑执行器 (batch_executor) 全景

## 1. 模块定位

**批跑执行器**是项目离线对局、批量评测、胜率统计的核心执行模块，同时存在于 M 系列（规则引擎）与 V7（NN 引擎），是 批跑评测体系 的工程实现 [1]。

---

## 2. 入口清单

### V7 系列 (`scripts/launchers/v-nn/`) [1][2]

| 入口 | 用途 |
|------|------|
| `batch_executor_gui_v7.py` | V7 批跑 GUI 入口（推荐可视化操作） |
| `start_v7_gui.py` | V7 GUI 启动器（轻量级） |
| `start_v7_complete.py` | V7 完整启动器（含环境检查） |
| `run_v7_vs_lalala_games.py` | **V7 vs Lalala 离线批跑主入口** |
| `run_v7_vs_m3_games.py` | V7 vs M3 内部对比入口 |
| `run_v7_train_and_eval.py` | 训练后一键评测入口 |
| `analyze_v7_rounds.py` | V7 局级分析 |
| `analyze_v7_round_levels.py` | V7 副级粒度分析 |

**配置文件**：`v7_config.json` / `v7_lalala_config.json`（与脚本同目录）[2]

### M 系列 (`scripts/launchers/m/`) [1][2]

| 入口 | 用途 |
|------|------|
| `batch_executor_gui_m3.py` | **M3 引擎 GUI（当前主用基线）** |
| `batch_executor_gui.py` | 通用 GUI 启动器（⚠️ 默认优先级 M1→V6→V5，**V4 不在内**）[10] |
| `batch_executor.py` | 命令行入口（无 GUI） |
| `analyze_decisions.py` | M3 决策分析（必杀/接风/还贡） |
| `check_grouping_engine.py` | 分组引擎正确性检查 |

---

## 3. 常用命令速查

### V7 vs Lalala 批跑 [7]
```bash
# 1. 编辑配置
$EDITOR v7_lalala_config.json

# 2. GUI 模式
python scripts/launchers/v-nn/batch_executor_gui_v7.py

# 3. 命令行模式
python scripts/launchers/v-nn/run_v7_vs_lalala_games.py \
    --config v7_lalala_config.json
```

### V7 vs M3 内部对比 [7]
```bash
python scripts/launchers/v-nn/run_v7_vs_m3_games.py
```

### 结果分析 [7]
```bash
# 局级胜率
python scripts/launchers/v-nn/analyze_v7_rounds.py results/xxx/

# 副级胜率（局 ≠ 副口径校验）
python scripts/launchers/v-nn/analyze_v7_round_levels.py results/xxx/

# M3 决策分析
python scripts/launchers/m/analyze_decisions.py results/xxx/
```

### executor 进程管理 [4]
```bash
# 启动批跑
python -m src.batch.executor --target-games 12 --vs lalala

# 进程状态
ps aux | grep yf

# 日志路径
logs/batch_executor/
```

---

## 4. 关键配置参数 [1][5][10]

### v1006 平台参数
- **N = 局数（games）**；❌ **N ≠ 副数（rounds）**
- `episodeOver.order`：`[头游, 二游, 三游, 末游]`
- `gameResult.victoryNum`：本局升级数（0/1/2/3，**局级**）
- `gameResult.draws`：平局计数
- `act.stage.play.curRank`：当前副的 rank（**副级，跨副重置**）

### 批跑局数档位（v1006 · 定音）[10]
| 档位 | 局数 | 用途 |
|------|------|------|
| **标准档** | **12 局** | 默认主交付 |
| 中量档 | 9 局 | 快速验证 |
| 轻量档 | 3 局 | 冒烟/回归 |
| 对照档 | 10 局 | ⚠️ **仅历史对照，不再新开** |

---

## 5. 核心运行机制

### 四席就绪门闩（GUA-044）[3][6][8]
批跑开局前必须确保 4 个客户端席位全部连入并发送就绪信号：

- **状态文件**：`batch_executor/clients_ready.json`
- **同步顺序**：`CONNECT_ORDER_INDEX` + 逐席 `wait_for_connect_turn`
- **时间参数**（2026-06-06 调整）：

| 参数 | 旧值 | 新值 |
|------|------|------|
| client4 延迟 | 2s | **11s** |
| 末席稳定窗口 | 5s | **7s** |

- **调试旁路**：`YF_SKIP_CONNECT_GATE=1`（生产严禁）
- **排查口诀**：单席长时间无 act → **先查他席回包**，不要直接判定断连

### 进程管理（executor.py）[4]
- **TrackedClientProcess**（2026-05-22 修复）：异常退出检测 + 自动重启
- **单实例锁**：pid 文件 + 端口占用检查
- **宽限期（Grace Period）**：默认 30s，可调
- **熔断机制**：连续 N 次客户端崩溃 → 停止批跑 + 报警

---

## 6. 关键设计原则

1. **引擎无关核心 + 引擎相关 adapter**：`batch_executor.py` 框架不关心具体引擎，V7/M3 通过 adapter 接入 [1]
2. **可恢复性**：长跑批跑支持断点续跑 [1]
3. **双口径分析**：局级 + 副级两套指标，规避 局 ≠ 副 统计陷阱 [1][7]
4. **真源唯一**：`scripts/launchers/xxx/` 是脚本唯一权威位置，根目录 .bat 均为 stub [2]
5. **配置同目录**：`v7_config.json` 与 launcher 同目录 [2]

---

## 7. 与训练模块的串联 [1]

```
training/train_bc_v7.py  →  产出模型权重
        ↓
run_v7_train_and_eval.py  →  训练 → 评测一步到位
        ↓
tools/download_models.py  →  模型版本与下载管理
```

---

## 8. 关联 GUA

| GUA | 状态 | 说明 |
|-----|------|------|
| GUA-044 | open | 批跑四席就绪门闩 [6] |
| GUA-048 | open, P2 | batch_executor dump 延迟 [10] |
| GUA-020 | closed | yf1_m1 vs yf2_m1 对照 [10] |
| GUA-033 | — | 批跑基建历史（上游）[6] |
