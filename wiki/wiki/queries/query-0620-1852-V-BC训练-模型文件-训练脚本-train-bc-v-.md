---
type: query-answer
title: "V7 BC训练 模型文件 训练脚本 train_bc_v7"
date: 2026-06-20
sources:
  - queries/query-0618-1734-v-启动脚本-路径-lalala-import-改动.md
  - sources/SCRIPT_INDEX-summary.md
  - queries/query-0618-2144-V-vs-Lalala.md
  - entities/module-batch-executor.md
  - queries/query-0618-2149-v-批跑数据统计-局级-副级.md
  - queries/query-0619-0826-批跑脚本-命令-参数-批跑入口-batch-executor.md
  - sources/v7-system-fixes-summary.md
  - entities/module-v7-engine.md
  - concepts/batch-evaluation.md
  - queries/query-0619-0828-analyze-v-rounds-批跑局级副级分析脚本-末级分布-victory.md
---

# V7 BC训练 模型文件 训练脚本 train_bc_v7

# V7 BC 训练 · 模型文件 · 训练脚本 train_bc_v7

## 一、训练入口路径

根据 SCRIPT_INDEX [[2]]，V7 BC 训练存在**两个并行的入口引用**（其中之一为 Phase 5 stub，需注意）：

| 入口 | 路径 | 性质 |
|------|------|------|
| `train_bc_v7.py` | 根目录 | Phase 5 遗留 stub，真源在 `scripts/v7/` |
| `run_bc_training.py` | `scripts/v7/` | 真源入口（推荐引用） |

> ⚠️ **治理原则**：根目录 stub 仅作历史兼容，**所有新增引用应指向 `scripts/v7/` 下真源** [[2]]。

`train_bc_v7.py` 在 wiki/entities/module-batch-executor.md [[4]] 和 SCRIPT_INDEX [[2]] 中均被列为 **V7 BC 训练入口**，但未给出独立实体页或具体源码说明。

---

## 二、训练产出 · 模型文件上下游

来自 wiki/entities/module-v7-engine.md [[8]]：

```
train_bc_v7.py  →  models/*.pth  →  引擎加载（yf1_v7.py / yf2_v7.py）
                       ↓
            run_v7_train_and_eval.py（训练→评测一步到位）
                       ↓
            tools/download_models.py（模型版本与下载管理）
```

- **输出目录**：`models/*.pth`
- **下游加载方**：`ultimate_win_rate_engine_v7/yf1_v7.py`、`yf2_v7.py`
- **关联训练子任务**（来自 V7-实施方案 [[1]]）：
  - `bc_dataset.py` / `bc_trainer.py`（GUA-015）
  - `zmq_bridge.py`（GUA-016）
  - `static_features.py` / `dynamic_features.py`（GUA-017/018）

---

## 三、BC 训练在 V7 路线图中的位置

来自 wiki/entities/module-v7-engine.md [[8]] 和 V7-实施方案 [[1]]：

| Stage | 内容 | 状态 |
|-------|------|------|
| Stage 5 | ultra_optimized（BC 初版） | ✅ 已完成 |
| Stage 6 | game_oriented/optimized | 进行中 |
| Stage 7 | online_rl | ⏳ |
| Stage 8 | full_rl | ⏳ |

启动器：`START_SMART_TRAINING.bat` / `START_STAGE7_TRAINING.bat` / `START_STRATEGY_TASKS_TRAINING.bat` [[2]]。

---

## 四、Wiki 信息缺口

| 缺口 | 影响 |
|------|------|
| `train_bc_v7.py` 的**具体实现细节**（模型结构、超参、数据流） | 需查 `scripts/v7/train_bc_v7.py` 源码 |
| `run_bc_training.py` vs `train_bc_v7.py` 的**关系**（同一脚本？子调用？） | 未澄清 |
| 当前在用的 **checkpoint 版本号 / 命名规范** | Wiki 无记录 |
| **输入数据来源**（来自哪个 `game_records_v7/` 目录、`lalala` 复盘还是自对弈） | 未覆盖 |
| Stage 6 是否已切换到新数据通道（涉及 GUA-033 解析路径选择） | 待定 |

---

## 五、建议下一步

1. **直接读源码**：`scripts/v7/train_bc_v7.py`（或 `run_bc_training.py`）确认当前模型结构与数据流
2. **核对模型文件目录**：`ls models/` 列出当前最新 `.pth`，与 GUA-015 / GUA-017 / GUA-018 任务清单对照
3. **确认 GUA-033 解析路径选择**：BC 训练读取 `game_records_v7/` 时使用旧 `victoryNum` 路径还是新路径，影响数据预处理
4. **建立模型版本归档**：参考 `tools/download_models.py` 流程，把 checkpoint + 配置 + 数据快照绑定落盘

---

**主要来源**：
- [[1]] V7 启动脚本路径与 lalala import 改动（V7-实施方案引用）
- [[2]] SCRIPT_INDEX（训练入口矩阵）
- [[4]] 批跑执行器模块（训练-评测串联）
- [[8]] V7 胜率引擎模块（上下游关系）
