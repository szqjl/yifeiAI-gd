# 项目脚本索引（Script Index）

> **用途**：快速定位所有可执行脚本，避免到处翻找。
> **范围**：`.py` / `.bat` / `.cmd` / `.ps1` 可执行文件。
> **维护**：新增脚本时同步更新本文档。

---

## 一、根目录脚本（直接入口）

### 批跑（最常用）

| 脚本 | 用途 |
|------|------|
| `batch_executor_gui_v7.py` | **V7 批跑 GUI**：预填 V7 vs Lalala 四客户端，选择局数一键批跑 |
| `batch_executor_gui_m1.py` | Phase 5 stub → `scripts/gui/batch_executor_gui_m1.py` |

### 启动器

| 脚本 | 用途 |
|------|------|
| `start_gui.py` | Phase 5 stub → `scripts/gui/start_gui.py` |

### V7 专用 .bat（根目录快捷方式）

| 脚本 | 实际指向 |
|------|---------|
| `START_V7_GUI.bat` | → `scripts/launchers/v-nn/START_V7_GUI.bat` |
| `START_V7_CLIENTS.bat` | → `scripts/launchers/v-nn/START_V7_CLIENTS.bat` |
| `START_V7_COMPLETE.bat` | → `scripts/launchers/v-nn/START_V7_COMPLETE.bat` |
| `START_V7_AUTO.bat` | → `scripts/launchers/v-nn/START_V7_AUTO.bat` |
| `RUN_V7_VS_LALALA.bat` | → `scripts/launchers/v-nn/RUN_V7_VS_LALALA.bat` |

### 其他 V/M 系列

| 脚本 | 实际指向 |
|------|---------|
| `START_V4_GUI.bat` | → `scripts/launchers/v-learn/START_V4_GUI.bat` |
| `START_V5_GUI.bat` | → `scripts/launchers/v-learn/START_V5_GUI.bat` |
| `START_V5_CLIENTS.bat` | → `scripts/launchers/v-learn/START_V5_CLIENTS.bat` |
| `START_V6_GUI.bat` | → `scripts/launchers/v-learn/START_V6_GUI.bat` |
| `START_M1_TRAINING.bat` | → `scripts/launchers/m/START_M1_TRAINING.bat` |
| `START_M1_WORKFLOW_FULL.bat` | → `scripts/launchers/m/START_M1_WORKFLOW_FULL.bat` |
| `START_M2_GUI.bat` | → `scripts/launchers/m/START_M2_GUI.bat` |
| `START_M3_GUI.bat` | → `scripts/launchers/m/START_M3_GUI.bat` |

### 工具/检查

| 脚本 | 用途 |
|------|------|
| `verify_gitignore.py` | **推送前检查**：`.gitignore` 与暂存区大文件检查 |
| `pre_push_check.bat` | 推送前检查批处理入口 |
| `YF_REPLAY.bat` | 回放工具入口 → `scripts/launchers/tools/YF_REPLAY.bat` |
| `batch_convert_replays.bat` | 批量转换回放 → `scripts/launchers/tools/batch_convert_replays.bat` |

### 训练

| 脚本 | 实际指向 |
|------|---------|
| `START_SMART_TRAINING.bat` | → `scripts/launchers/training/START_SMART_TRAINING.bat` |
| `START_STAGE7_TRAINING.bat` | → `scripts/launchers/training/START_STAGE7_TRAINING.bat` |
| `START_STRATEGY_TASKS_TRAINING.bat` | → `scripts/launchers/training/START_STRATEGY_TASKS_TRAINING.bat` |
| `INSTALL_STAGE7_DEPENDENCIES.bat` | → `scripts/launchers/training/INSTALL_STAGE7_DEPENDENCIES.bat` |

---

## 二、scripts/ 核心脚本

### scripts/ 根

| 脚本 | 用途 |
|------|------|
| `wiki.py` | **LLM Wiki 管理**：`status` / `ingest` / `query` / `config` |
| `batch_executor.py` | 批跑执行器（Python 模块入口） |
| `train_bc_v7.py` | V7 BC 行为克隆训练入口 |
| `analyze_decisions.py` | M3 决策分析 |

### scripts/v7/ — V7 训练启动（Python）

| 脚本 | 用途 |
|------|------|
| `run_bc_training.py` | **V7 BC 训练启动器** |
| `start_v7_complete.py` | V7 完整流程启动（客户端+训练一条龙） |
| `start_v7_gui.py` | V7 GUI 启动器 |

### scripts/training/ — 训练脚本

| 脚本 | 用途 |
|------|------|
| `train_stage5_ultra_optimized.py` | Stage 5 超优化训练 |
| `train_stage6_game_oriented.py` | Stage 6 对局导向训练 |
| `train_stage6_optimized.py` | Stage 6 优化训练 |
| `train_stage7_online_rl.py` | Stage 7 在线强化学习 |
| `train_stage8_full_rl.py` | Stage 8 全 RL 训练 |
| `train_strategy_tasks.py` | 策略任务训练 |
| `run_stage6_training_gui.py` | Stage 6 训练 GUI |
| `stage6_training_gui.py` | Stage 6 训练 GUI 界面 |
| `monitor_training.py` | 训练监控 |
| `view_training_results.py` | 查看训练结果 |
| `view_training_summary.py` | 查看训练摘要 |

### scripts/analysis/ — 分析脚本

| 脚本 | 用途 |
|------|------|
| `analyze_v7_rounds.py` | **V7 副级批跑分析**（主要分析工具） |
| `analyze_game_rounds.py` | 对局副级分析 |
| `analyze_game_record_format.py` | 游戏记录格式分析 |
| `analyze_loss_calculation.py` | Loss 计算分析 |
| `analyze_and_improve_training.py` | 训练分析与改进 |
| `analyze_m1_games.py` | M1 对局分析 |
| `analyze_practical_records_for_training.py` | 实战记录训练分析 |

### scripts/tools/ — 工具脚本

| 脚本 | 用途 |
|------|------|
| `yf_replay.py` | **回放工具**（YF_REPLAY.bat 的真源） |
| `replay.py` | 通用回放 |
| `gen_replay_word.py` | 生成 replay_word.md 文字记录 |
| `_gen_replay_word.py` | 内部辅助生成 replay_word |
| `analyze_v7_round_levels.py` | V7 副级水平分析 |
| `export_batch_warnings_comparison.py` | 批跑 WARNING 对比导出 |
| `convert_rep_to_xml.py` | 回放文件转 XML |
| `_extract_replay_steps.py` | 提取回放步骤 |
| `verify_replay_rank_order.py` | 验证回放排名顺序 |
| `audit_greater_in_records.py` | 审计记录中的 greaterPos/greaterAction |
| `batch_update_json_from_rep.py` | 批量从 REP 更新 JSON |
| `batch_update_szqjl_only.py` | 批量仅更新数字记录 |
| `delete_non_replay_records.py` | 删除非回放记录 |
| `download_models.py` | 下载模型文件 |
| `fix_model_compatibility.py` | 修复模型兼容性 |
| `fix_doc_encoding.py` | 修复文档编码 |
| `clean_git_history.py` | 清理 Git 历史 |
| `clean_large_files.py` | 清理大文件 |
| `probe_exe_argv.py` | 探测 exe 命令行参数 |
| `probe_exe_argv_ws.py` | 探测 exe 命令行参数（含 WebSocket） |
| `run_t9_direct.py` | T9 直接运行 |
| `sync_lalala_reference.py` | 同步 Lalala 参考 |
| `sync_github_mirror.ps1` | 同步 GitHub 镜像 |
| `feishu_gateway_auth.py` | 飞书网关认证 |
| `feishu_kanban_card_generator.py` | 飞书看板卡片生成器 |
| `migrate_*.py` (5个) | Phase 5 目录迁移脚本 |

### scripts/gui/ — GUI 界面

| 脚本 | 用途 |
|------|------|
| `batch_executor_gui.py` | **通用批跑 GUI**（基类） |
| `batch_executor_gui_v7.py` | V7 批跑 GUI（= 根目录同名文件的真源） |
| `batch_executor_gui_m1.py` | M1 批跑 GUI |
| `batch_executor_gui_m2.py` | M2 批跑 GUI |
| `batch_executor_gui_m3.py` | M3 批跑 GUI |
| `start_gui.py` | 通用启动 GUI |

### scripts/hooks/ — Git Hooks

| 脚本 | 用途 |
|------|------|
| `pre_push_validate.py` | **推送前验证**（大文件/敏感信息检查） |
| `pre-push` | pre-push hook shell 脚本 |
| `install-hooks.bat` | 安装 hooks 到 `.git/hooks/` |

### scripts/checks/ — 检验脚本（27个）

覆盖组牌引擎、行动验证、规则合规等。核心检验：
- `check_grouping_engine.py` — 组牌引擎单元测试

### scripts/launchers/v7/ — V7 启动脚本（生产环境）

| 脚本 | 用途 |
|------|------|
| `run_v7_vs_lalala_games.py` | **V7 vs Lalala 批跑入口**（生产端） |
| `run_v7_vs_m3_games.py` | V7 vs M3 批跑 |
| `run_v7_train_and_eval.py` | V7 训练+评测一体 |
| `v7_config.json` | V7 启动配置 |
| `v7_lalala_config.json` | V7 vs Lalala 配置 |
| `START_V7_GUI.bat` | V7 GUI 一键启动 |
| `START_V7_CLIENTS.bat` | V7 多客户端一键启动 |
| `RUN_V7_VS_LALALA.bat` | V7 vs Lalala 批跑 bat 入口 |

### scripts/launchers/_env.bat — 环境变量

**关键文件**：所有 .bat 启动器的公共环境变量（Python 路径、venv 激活等）。

---

## 三、常用操作速查

| 操作 | 命令 |
|------|------|
| **V7 批跑（GUI）** | `python batch_executor_gui_v7.py` |
| **V7 批跑（命令行）** | `python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3` |
| **分析批跑结果** | `python scripts/analysis/analyze_v7_rounds.py` |
| **回放单局** | `YF_REPLAY.bat` |
| **BC 训练** | `python scripts/train_bc_v7.py` |
| **Wiki 摄入** | `python scripts/wiki.py ingest` |
| **Wiki 查询** | `python scripts/wiki.py query "关键词"` |
| **Wiki 状态** | `python scripts/wiki.py status` |
| **推送前检查** | `python verify_gitignore.py` |
| **组牌引擎测试** | `python scripts/checks/check_grouping_engine.py` |

---

## 四、根目录 .bat 一览

> 根目录 .bat 均为 Phase 5 后的 stub，指向 `scripts/launchers/` 下的真源。
> 直接运行即可，无需手动 cd 到 scripts/ 下。

```
batch_convert_replays.bat     CHECK_RECORD_CONSISTENCY.bat
INSTALL_STAGE7_DEPENDENCIES.bat  pre_push_check.bat
run_new_test.bat              RUN_V7_VS_LALALA.bat
START_AUTO_RESTART_WORKFLOW.bat  START_M1_TRAINING.bat
START_M1_WORKFLOW_FULL.bat    START_M2_GUI.bat
START_M3_GUI.bat              START_SMART_TRAINING.bat
START_STAGE7_TRAINING.bat     START_STRATEGY_TASKS_TRAINING.bat
START_V4_GUI.bat              START_V5_CLIENTS.bat
START_V5_GUI.bat              START_V6_GUI.bat
START_V7_AUTO.bat             START_V7_CLIENTS.bat
START_V7_COMPLETE.bat         START_V7_GUI.bat
YF_REPLAY.bat
```

---

> **维护规则**：新增 `.py` / `.bat` 脚本时同步更新本文档。删除旧脚本时同步删除对应行。
