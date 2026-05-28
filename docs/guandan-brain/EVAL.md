# 评测说明（Evaluation）

> 目标：可重复。能写断言的写断言（合法动作集、固定局面期望）；需人工的列出牌局 ID 与「通过标准」一句。  
> **本机执行**：离线服务器与批量对战须在你电脑上跑；步骤见 **[LOCAL_EVAL_CHECKLIST.md](LOCAL_EVAL_CHECKLIST.md)**（跑完把结果写回 `ITERATIONS.md`）。

## 自动化 / 脚本入口

以下均为仓库内**真实**入口（相对路径自项目根目录）。离线服务器可执行文件需自备，GUI 内默认探测路径见 `batch_executor_gui.py` 的 `load_default_config`（如 `server/guandan_offline_v1006.exe` 等）。

| 版本 | 典型用途 | Windows 一键脚本 | 等价命令（推荐可脚本化） |
|------|----------|------------------|--------------------------|
| **M1** | 硬编码规则引擎批量对战 | `START_M1_GUI.bat` | `py batch_executor_gui_m1.py`（或 `python batch_executor_gui_m1.py`） |
| **M2** | 重构硬编码规则引擎（无分数累积+阈值保护）批量对战 | `START_M2_GUI.bat` | `py scripts/gui/batch_executor_gui_m2.py`（或 `python scripts/gui/batch_executor_gui_m2.py`） |
| **V4** | 混合决策 V4 批量对战 | `START_V4_GUI.bat` | `python scripts/gui/batch_executor_gui.py`，**须在界面将四条客户端改为 V4**（见下「GUI 与版本说明」） |
| **V5** | V5 批量对战 | `START_V5_GUI.bat` | `py scripts/gui/batch_executor_gui.py`，若需强制 V5 请看「GUI 与版本说明」 |
| **V6** | V6 批量对战 | `START_V6_GUI.bat` | `py scripts/gui/batch_executor_gui.py`，若需强制 V6 请看「GUI 与版本说明」 |
| **任意版本（无头，推荐复现）** | 指定四客户端跑满目标场次 | — | 见下「无头 CLI」 |
| **M1 辅助训练评估**（需先有模型与记录） | 训练后胜率评估 | `START_M1_TRAINING.bat`（内含多步） | `python src/train/m1_vs_client_evaluator.py --num_games 50 --opponent client --model_path models/bc_model_stage7_optimized.pth` |
| **单元测试**（若有用例） | 回归 | — | `pytest`（`pytest.ini` 指定 `testpaths = tests`） |

### 无头 CLI（可写进 CI / 脚本）

模块入口与 `batch_executor.py` 一致：

```bash
python -m batch_executor --server-path "<SERVER_EXE>" --target-games 3 --clients src/communication/yf1_v5.py src/communication/run_lalala_client3.py src/communication/yf2_v5.py src/communication/run_lalala_client4.py
```

将 `yf1_v5.py` / `yf2_v5.py` 换成 `yf1_v4.py` / `yf2_v4.py`、`yf1_v6.py` / `yf2_v6.py` 或 `yf1_m1.py` / `yf2_m1.py` 即对应版本。四元组金样例见 `scenarios/client_sets.json`。

仅诊断、不跑对局：

```bash
python -m batch_executor --server-path "<SERVER_EXE>" --diagnose-only
```

### GUI 与版本说明（重要）

`batch_executor_gui.py`（V4/V5/V6 各 `START_*_GUI.bat` 最终多调用它）在加载默认配置时，**优先级为：M1 四套路径齐全 → V6 → V5**，并不单独优先 V4。因此：

- 要评测 **V4**：请使用 **无头 CLI 显式传入 V4 四客户端**，或在 GUI 中手动改四条客户端为 `yf1_v4.py`、`yf2_v4.py`。
- 要评测 **V5/V6**：若仓库里同时存在 M1 客户端脚本，GUI 可能默认落到 M1；需手动改为 `yf1_v5.py` / `yf2_v5.py` 或 `yf1_v6.py` / `yf2_v6.py`，或直接使用无头 CLI。

`START_M1_GUI.bat` 单独调用 `batch_executor_gui_m1.py`，默认即为 M1 四客户端。

### M1：yf1_m1 与 yf2_m1 对照（台账 **GUA-020**，**已测**）

- **场景说明**：[`scenarios/M1_yf1_vs_yf2_comparison.md`](scenarios/M1_yf1_vs_yf2_comparison.md)（含 **§6 已测结果** 与 `game_id` 列表）。  
- **做法**：用 M1 四客户端跑对局，从 `game_records/` 中成对文件（`*[yf1_m1]*.json` / `*[yf2_m1]*.json` 同 `game_id`）解析「我的决策」数组，统计 PASS 率与近似「问题 PASS」（`actionList_size>1` 仍选 PASS）。

**实测结果（`m-dev`，2026-04-21，写入大脑真源）**

| 指标 | yf1_m1（座位 0） | yf2_m1（座位 2） |
|------|------------------|------------------|
| 成对 `game_id` 数 | **10**（见场景文档列举） | 同左 |
| 「我的决策」条数 | **230** | **228** |
| PASS 次数 / 率 | **126 / 54.78%** | **127 / 55.70%** |
| 近似问题 PASS（`actionList_size>1` 仍 PASS） | **7** | **10** |
| 样本内 `victoryNum` | 均为 **`[0,3,0,3]`**（YiFei 0+2 未胜） | 同左 |

**结论**：合并样本下 **PASS 率差约 0.92%**，**不支持「yf2_m1 明显弱于 yf1_m1」**；工程上**无需**为 yf2 单独开路由，后续优化走 **共用决策层 / 对局策略 / 胜率**。详见 `ISSUES.md` **GUA-020**（`closed`，`closed_in` 2026-04-21）与 `ITERATIONS.md` 对应行。

- **通过标准（已达成）**：≥10 个成对 `game_id`；`ITERATIONS.md` 已写结论；**GUA-020** 已关闭。

### 仅启动客户端（人工多窗口，不经过 batch_executor）

与批量 GUI 独立，按连接顺序抢占坐位（脚本内注释说明 0～3 号位）：

- V5 示例：`START_V5_CLIENTS.bat` → 依次 `python src/communication/yf1_v5.py`、`run_lalala_client3.py`、`yf2_v5.py`、`run_lalala_client4.py`。

## 金样例（Golden Cases）

| Case ID | 类型 | 输入/局面引用 | 期望 | 最后通过版本 | 备注 |
|---------|------|---------------|------|--------------|------|
| **GUA-001** | smoke / infra | `scenarios/GUA-001_diagnose_only.md` | `python -m batch_executor --diagnose-only` 退出码 0，服务器路径有效 | — | 需本机存在 `<SERVER_EXE>` |
| **GUA-002** | rules / repo | `scenarios/GUA-002_client_paths_golden.md`、`scenarios/client_sets.json` | 与当前分支一致的键（如 `m1`/`v4`/`v5`）下各脚本在仓库内存在；`v6` 若本分支无 `yf1_v6.py` 等则跳过；坐位语义 0+2 / 1+3 | — | 可做「文件存在」断言 |
| **GUA-003** | policy / batch | 无头 CLI + `client_sets.json` 中任一键（如 `v4`） | 给定 `--target-games 1` 时流程可完成且无客户端路径报错（完整胜负依赖环境与引擎） | — | 最小对局复现时与 GUA-001 配合 |
| **M1-yf1-yf2** | observation | `scenarios/M1_yf1_vs_yf2_comparison.md` + `game_records` | **10** 个成对 `game_id`：yf1 PASS **54.78%**（230 条决策）、yf2 **55.70%**（228 条）；近似问题 PASS **7 / 10**；结论：**无明显一方更差** | m-dev · 2026-04-21 | **GUA-020 closed**；详见 `EVAL.md` 本节与场景文档 §6 |

## 手工验收清单（可选）

- [ ] 选定版本的四条客户端与 `scenarios/client_sets.json` 一致。
- [ ] 离线服务器路径在 GUI 或 CLI 中指向真实 `.exe`。
- [ ] M1 分支约定：若团队要求仅在 `m-dev`，以团队文档为准（`START_M1_GUI.bat` 注释）。

## 通过标准（本轮发布）

GUA-001 在目标环境通过；GUA-002 文件存在性全部满足；若合入某版本对局修复，则 GUA-003 在该版本下完成至少 1 场目标场次且日志无客户端启动失败。

**M1 yf1 / yf2 对照（GUA-020）**：以 `EVAL.md`「M1：yf1_m1 与 yf2_m1 对照」**实测结果表**为准；复现时核对 `game_records` 中成对 `game_id` 与场景文档 §6 列表一致。
