---
type: query-answer
title: "V7 模型训练链路 bc_model_v3 来源 GUA-061"
date: 2026-06-20
sources:
  - queries/query-0618-1734-v-启动脚本-路径-lalala-import-改动.md
  - queries/query-0618-2144-V-vs-Lalala.md
  - sources/SCRIPT_INDEX-summary.md
  - queries/query-0618-2149-v-批跑数据统计-局级-副级.md
  - entities/module-batch-executor.md
  - queries/query-0619-0826-批跑脚本-命令-参数-批跑入口-batch-executor.md
  - sources/v7-system-fixes-summary.md
  - concepts/batch-evaluation.md
  - entities/module-v7-engine.md
  - queries/query-0619-0828-analyze-v-rounds-批跑局级副级分析脚本-末级分布-victory.md
---

# V7 模型训练链路 bc_model_v3 来源 GUA-061

# V7 模型训练链路 bc_model_v3 来源 GUA-061

## 一、核心结论

**GUA-061 是"V7 模块化架构"阻塞项**，与 `bc_model_v3` 的关系**未在 Wiki 中直接建立**。Wiki 仅明确：

> "GUA-061：V7 模块化架构 P0 阻塞，在 GUA-061 解决前，V7 难以跨越 30% 门槛" [{2}]

Wiki **未明确 `bc_model_v3` 是否由 GUA-061 产出**，也**未直接记录** V7 BC 训练链路中 `bc_model_v3` 的生成位置、版本号、commit 锚点。

---

## 二、Wiki 中可见的 V7 BC 训练链路

### 1. 训练入口

| 入口 | 路径 | 用途 |
|------|------|------|
| `run_bc_training.py` | `scripts/launchers/training/` | BC 训练调度 |
| `train_bc_v7.py` | 根目录 / `scripts/v7/` | V7 BC 训练入口 |
| `start_v7_complete.py` | 根目录 | 一条龙（训练+批跑+GUI）|
| `START_V7_COMPLETE.bat` | 根目录 | Windows 快捷方式 |

> 📌 **真源唯一**：`scripts/v7/` 或 `scripts/launchers/training/`，根目录 .bat 均为 stub [{3}]

### 2. BC 训练相关子模块（来源 [V7-实施方案]）[{1}]

```
src/training/
├── bc_dataset.py        ← GUA-015（数据集）
├── bc_trainer.py        ← GUA-015（训练器）
├── zmq_bridge.py        ← GUA-016（数据桥接）
├── static_features.py   ← GUA-017（静态特征）
└── dynamic_features.py  ← GUA-018（动态特征）
```

### 3. 模型产出与下游

```
training/train_bc_v7.py  →  models/*.pth
        ↓
run_v7_train_and_eval.py  →  训练 → 评测一步到位
        ↓
tools/download_models.py  →  模型版本与下载管理
```

### 4. V7 引擎加载模型

> "`train_bc_v7.py` 输出 `models/*.pth` → 引擎加载" [{9}]

---

## 三、`bc_model_v3` 在 Wiki 中的定位

### 已知信息

| 项 | 状态 |
|----|------|
| `bc_model_v3` 是 BC 训练产出的**模型版本**之一 | ⚠️ Wiki 未明示 |
| 归属训练链路 | `train_bc_v7.py` → `models/*.pth` |
| 与 GUA-061 的直接关系 | **未记录** |

### 间接关联

- **GUA-061 性质**：V7 **模块化架构** P0 阻塞——指 `ultimate_win_rate_engine_v7/` 下的子模块组织（`yf1_v7` / `yf2_v7` / `strategy_engine` / `phase_handlers` / `stage_router` / `rule_based`）[{9}]
- **GUA-015 性质**：BC 训练数据集/训练器，与 `bc_model_v3` 命名最相关
- **`bc_model_v3` 命名推断**：`bc_` 前缀 → BC（Behavior Cloning）训练产出；`_v3` → 第三次迭代模型

---

## 四、信息缺口

⚠️ **Wiki 未直接覆盖以下问题**：

| 缺口 | 说明 |
|------|------|
| `bc_model_v3` 具体路径（如 `models/bc_model_v3.pth`？） | 未记录 |
| `bc_model_v3` 训练 commit / 时间戳 | 未记录 |
| `bc_model_v3` 由 GUA-015 还是 GUA-061 产出 | 未明示 |
| `bc_model_v3` 是否已加载进 V7 引擎参与 3.0% 胜率批跑 | 未记录 |
| `_v3` 之前的 `_v1` / `_v2` 版本是否存在 | 未记录 |

---

## 五、Wiki 中关于 GUA-061 的全部已知信息

| 维度 | 详情 | 来源 |
|------|------|------|
| 编号 | GUA-061 | [{2}][{7}] |
| 性质 | V7 模块化架构 P0 阻塞 | [{2}] |
| 关联 | V7 系统双问题修复（早期 fix，未走 GUA 体系） | [{7}] |
| 影响 | 在解决前，V7 难以跨越 30% 门槛 | [{2}] |
| 建议 | 集中资源攻克 | [{2}] |
| 详情页 | `wiki/entities/gua-061.md` — **Wiki 未直接收录内容** | — |

---

## 六、建议下一步

1. **读源码确认**：
   - `src/training/bc_trainer.py` 中模型命名规则（搜 `bc_model`）
   - `models/` 目录下的实际模型文件清单
   - `train_bc_v7.py` 的 model save 逻辑

2. **查 GUA-061 详情页**：
   - `wiki/entities/gua-061.md`（若存在）确认是否提及 `bc_model_v3`

3. **建立映射**：
   - 若 Wiki 缺失，建议新增 `bc_model_v3` 实体页或追加到 `module-v7-engine.md` 的"上下游关系"章节
   - 在 GUA-061 详情页加 §"产出物"小节，记录其负责的模型版本

4. **批跑溯源**：
   - 3.0% 副级胜率 [{2}] 对应的批跑加载的是哪个 `bc_model_v*`？需查 `run_v7_vs_lalala_games.py` 配置中的 `model_path` 字段

---

**主要来源**：[1] V7 启动脚本 import 改动 · [2] V7 vs Lalala · [3] SCRIPT_INDEX · [7] V7 系统双问题修复 · [9] V7 引擎模块
