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
| `RUN_V8_VS_LALALA.bat` | **V8 批跑入口** → `scripts/launchers/v8/RUN_V8_VS_LALALA.bat` |

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
| `RUN_V7DAN_VS_DANZERO.bat` | → `scripts/launchers/v-nn/RUN_V7DAN_VS_DANZERO.bat` |

### V8 专用 .bat（根目录快捷方式）

| 脚本 | 实际指向 |
|------|---------|
| `START_V8_GUI.bat` | → `scripts/launchers/v8/START_V8_GUI.bat` |
| `START_V8_CLIENTS.bat` | → `scripts/launchers/v8/START_V8_CLIENTS.bat` |
| `START_V8_COMPLETE.bat` | → `scripts/launchers/v8/START_V8_COMPLETE.bat` |
| `START_V8_AUTO.bat` | → `scripts/launchers/v8/START_V8_AUTO.bat` |
| `RUN_V8_VS_LALALA.bat` | → `scripts/launchers/v8/RUN_V8_VS_LALALA.bat` |

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
| `START_M1_GUI.bat` | → `scripts/launchers/m1/START_M1_GUI.bat` |

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
| `train_bc_v8.py` | V8 BC 行为克隆训练入口（`game_records_v8/`） |
| `analyze_decisions.py` | M3 决策分析 |
| `check_github_auth.ps1` | GitHub 认证检查 |

### batch_executor/ — 批跑引擎

| 脚本 | 用途 |
|------|------|
| `server_stdout_reader.py` | 服务器 stdout 读取器（解析离线平台输出，供批跑对账用） |

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
| `run_stage6_training_gui.bat` | Stage 6 训练 GUI 启动器 → `scripts/launchers/training/run_stage6_training_gui.bat` |
| `QUICK_START_STAGE7.bat` | Stage 7 快速启动（轻量版） |
| `QUICK_START_STAGE7_ULTRA.bat` | Stage 7 快速启动（超优化版） |

### scripts/analysis/ — 分析脚本

| 脚本 | 用途 |
|------|------|
| `analyze_v7_rounds.py` | **V7/V8 批跑 KPI 主工具（WF-04 Step 2）**；`--all` 会话/局胜/副胜；`--dir game_records_v8` 自动检测 V8 平台（gc 重置检测+yf1 过滤+双上率/末游率） |
| `analyze_game_rounds.py` | 对局副级分析 |
| `analyze_game_record_format.py` | 游戏记录格式分析 |
| `analyze_loss_calculation.py` | Loss 计算分析 |
| `analyze_and_improve_training.py` | 训练分析与改进 |
| `analyze_m1_games.py` | M1 对局分析 |
| `analyze_practical_records_for_training.py` | 实战记录训练分析 |
| `analyze_grouping_engine_freq.py` | 组牌引擎出牌频率统计 |
| `compare_sf_detection_vs_multipass.py` | 同花顺检测：单轮 vs 多轮对比 |
| `dump_grouping_plans_scores.py` | 组牌方案分数导出 |
| `simulate_gua072_delay.py` | GUA-072 延迟效应模拟 |
| `trace_grouping_order.py` | 组牌引擎出牌顺序追踪 |

### scripts/tools/ — 工具脚本

| 脚本 | 用途 |
|------|------|
| `yf_replay.py` | **回放工具**（YF_REPLAY.bat 的真源）；YF 出牌步支持 A/B/C 决策链路离线分析 |
| `replay.py` | 通用回放 |
| `gen_replay_word.py` | 生成 replay_word.md 文字记录 |
| `_gen_replay_word.py` | 内部辅助生成 replay_word |
| `analyze_v7_round_levels.py` | **V7 副级 curRank 逐局分析（WF-04 可选 Step 2）**；完整路径 `scripts/tools/`（**非** `scripts/analysis/`） |
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
| `kaggle/sync_v8.py` | **V8 Kaggle 数据集同步**（`scripts/kaggle/`）；`--zip` 打包供手动上传；`--upload` CLI 上传（有 bug 风险） |
| `sync_github_mirror.ps1` | 同步 GitHub 镜像 |
| `gua033_run_matrix.ps1` | GUA-033 跑矩阵脚本 |
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

### scripts/checks/ — 检验脚本（30个）

覆盖组牌引擎、行动验证、规则合规等。核心检验：
- `check_grouping_engine.py` — 组牌引擎单元测试
- `check_endgame_agent.py` — **残局智能体独立调试**（独立/扫描/单记录三种模式）
- `check_q1_rule_table_consistency.py` — **Q1 规则表静态校验**（`endgame_rule` / `BAOSHU_RULE` 自洽性）
- `check_endgame_anomalies.py` — **残局异常扫描器**（优先抓“临门 PASS”与“推荐被过滤到只剩 PASS”）

### scripts/cos/ — COS 云端存储

| 脚本 | 用途 |
|------|------|
| `cos_client.py` | 腾讯云 COS Python SDK 封装（cos-python-sdk-v5） |
| `verify_cos.py` | COS 连通性验证 |
| `upload_regression.py` | 上传 replay JSON 到 COS 并输出 manifest 条目 |
| `pull_regression.py` | 按 manifest 从 COS 拉取 regression 数据到本地 |
| `batch_upload_regression.py` | 从 game_records 选取对局批量上传至 COS 并刷新 manifest |
| `upload_szqjl_batch.py` | 上传含 szqjl 的 game_records JSON 到 COS |
| `sync_pull_all.py` | 同步 COS 全量 artifact 到本地 data/artifacts/ |

### scripts/lark/ — 飞书 Bot 集成

| 脚本 | 用途 |
|------|------|
| `start-bot.bat` | Lark Bot 事件消费者启动（yife-gd-bot profile） |
| `start-bot.ps1` | Lark Bot 事件消费者（PowerShell 版） |
| `send-message.ps1` | 通过 lark-cli 发送消息到指定 chat |

### scripts/sdk/ — Qoder Agent SDK

| 脚本 | 用途 |
|------|------|
| `qoder_smoke.py` | Qoder Agent SDK 冒烟测试（读 V7 实施方案 + 流式验证） |
| `qoder_review_template.py` | Qoder 派单 v2：复审 V7 实施方案（8 补丁逐项验证） |

### scripts/clients/ — 标准测试客户端

| 脚本 | 用途 |
|------|------|
| `client_std_1.py` | 标准掼蛋客户端 - 位置 1（websockets 库，自动化测试用） |
| `client_std_3.py` | 标准掼蛋客户端 - 位置 3（websockets 库，自动化测试用） |

### scripts/shell/ — Shell 脚本

| 脚本 | 用途 |
|------|------|
| `auto_clean_large_files.sh` | 自动清理 Git 历史中的大文件 |
| `clean_large_files.sh` | 清理大文件（完整版） |
| `check_repo_size.sh` | 检查仓库大小 |
| `run_new_test.sh` | 启动新游戏测试（bash 版，调用 batch_executor.py） |
| `train_m1_optimized.sh` | M1 优化训练启动 |

### scripts/launchers/v7/ — V7 启动脚本（生产环境）

| 脚本 | 用途 |
|------|------|
| `run_v7_vs_lalala_games.py` | **V7 vs Lalala 批跑入口**（生产端） |
| `run_12games_test.py` | V7 端到端测试 — 12 局完整对战（含详细日志） |
| `run_e2e_simple.py` | V7 端到端测试简化版 |
| `run_v7_e2e_debug.py` | V7 端到端测试调试版（详细日志+错误处理） |
| `test_v7_engine_load.py` | V7 引擎模型加载验证 |
| `START_V7_GUI.bat` | V7 GUI 一键启动 |
| `START_V7_CLIENTS.bat` | V7 多客户端一键启动 |
| `START_V7_COMPLETE.bat` | V7 完整系统一键启动 |
| `RUN_V7_VS_LALALA.bat` | V7 vs Lalala 批跑 bat 入口 |
| `run_v7_test.bat` | V7 端到端测试 bat 入口 |
> **注**：`run_v7_vs_m3_games.py`、`run_v7_train_and_eval.py`、`v7_config.json`、`v7_lalala_config.json` 已移除（索引残留）。

### scripts/launchers/v7dan/ — v7Dan vs DanZero 启动脚本（v1006）

| 脚本 | 用途 |
|------|------|
| `run_v7dan_vs_danzero_games.py` | **v7Dan vs DanZero 批跑入口**（BatchExecutor；队A yf1_v7dan+yf2_v7dan，队B DanZero client3+client4） |
| `RUN_V7DAN_VS_DANZERO.bat`（根目录） | v7Dan vs DanZero 批跑 bat 入口（stub → `scripts/launchers/v-nn/`） |

### scripts/launchers/m/ — M 系列启动器

| 脚本 | 用途 |
|------|------|
| `run_m3_vs_lalala_games.py` | **M3 vs Lalala 批跑入口**（BatchExecutor，默认 3 局） |
| `START_M3_BATCH.bat` | M3 命令行批跑 bat 入口 |

### src/communication/ — V8 核心通信模块

| 模块 | 用途 |
|------|------|
| `botzone_adapter.py` | **Botzone Local AI 适配器** — 牌编码双射（int↔str）、CardTracker（两副牌追踪）、ActionListGenerator（合法动作枚举）、BotzoneAdapter（HTTP 轮询 + V8 对接）；默认 base_url `https://www.botzone.org.cn/api` |
| `new_platform_adapter.py` | OpenGuanDan 新平台协议适配器 |
| `yf1_v8.py` | V8 选手 0 客户端 |
| `yf2_v8.py` | V8 选手 2 客户端 |
| `v8_lalala_adapter.py` | Lalala 对手适配器 |
| `v8_websocket_manager.py` | WebSocket 连接管理器 |
| `v8_game_recorder.py` | 牌谱记录器 |

### src/communication/ — v7Dan vs DanZero（v1006 批跑）

| 模块 | 用途 |
|------|------|
| `yf1_v7dan.py` | v7Dan 队A 席位0 客户端（v7 引擎，牌谱 game_records_v7dan/） |
| `yf2_v7dan.py` | v7Dan 队A 席位2 客户端（v7 引擎，牌谱 game_records_v7dan/） |
| `danzero_nn.py` | DanZero DMC Q-net 推理（`models/danzero/q_network.ckpt`，567 维 state → argmax Q 取 actIndex）+ client1 状态机 / tribute/back 移植 |
| `danzero_policy.py` | DanZero 决策策略（play 走真实模型 argmax Q；模型未就绪时降级最小可行动作） |
| `danzero_adapter.py` | DanZero 队B websockets 客户端适配器 |
| `_danzero_launcher.py` | DanZero 客户端统一启动（CONNECT_DELAY 错峰） |
| `run_danzero_client3.py` / `run_danzero_client4.py` | DanZero 队B 席位1/3 入口 |

### scripts/launchers/v8/ — V8 启动脚本（OpenGuanDan）

| 脚本 | 用途 |
|------|------|
| `RUN_V8_VS_LALALA.bat` | V8 vs Lalala 批跑 bat 入口 |
| `START_V8_GUI.bat` | V8 GUI 一键启动 |
| `START_V8_CLIENTS.bat` | V8 多客户端一键启动 |
| `START_V8_COMPLETE.bat` | V8 完整系统一键启动 |
| `START_V8_AUTO.bat` | V8 自动重启启动 |
| `run_v8_test.bat` | V8 端到端测试 bat 入口 |
| `run_v8_vs_v8_games.py` | **V8 vs V8 自对弈批跑** — 用 V8 引擎替代 lalala 担任对手，最强对手压力测试 |
| `run_v8_vs_botzone.py` | **V8 vs Botzone（Local AI 模式）** — 通过 HTTP API 与 Botzone 平台对战 DanLM 等 bot；需 Botzone 账号 + API key；默认 base_url `https://www.botzone.org.cn/api` |
| `test_v8_engine_load.py` | V8 引擎模型加载验证 |
| `run_12games_test.py` | V8 端到端测试（12 局） |
| `run_e2e_simple.py` | V8 端到端测试简化版 |
| `run_v8_e2e_debug.py` | V8 端到端测试调试版 |

### scripts/launchers/m1/ — M1 启动器

| 脚本 | 用途 |
|------|------|
| `START_M1_GUI.bat` | M1 GUI 一键启动 |

### scripts/launchers/checks/ — 校验启动器

| 脚本 | 用途 |
|------|------|
| `CHECK_RECORD_CONSISTENCY.bat` | 记录一致性校验入口 |

### scripts/launchers/workflow/ — 工作流启动器

| 脚本 | 用途 |
|------|------|
| `START_AUTO_RESTART_WORKFLOW.bat` | 自动重启工作流入口 |

### scripts/launchers/_env.bat — 环境变量

**关键文件**：所有 .bat 启动器的公共环境变量（Python 路径、venv 激活等）。

---

## 三、常用操作速查

| 操作 | 命令 |
|------|------|
| **V7 批跑（GUI）** | `python batch_executor_gui_v7.py` |
| **V7 批跑（命令行）** | `python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3` |
| **V8 批跑（命令行）** | `.\RUN_V8_VS_LALALA.bat`（当前未冒烟） |
| **WF-04 批跑解读（主）** | `python scripts/analysis/analyze_v7_rounds.py --all`（V7）/ `--dir game_records_v8 --all`（V8） |
| **WF-04 批跑解读（副级 curRank，可选）** | `python scripts/tools/analyze_v7_round_levels.py` |
| **WF-04 L1/L3 对账文件** | `<repo_root>/batch_executor/latest_victory_num.json` · `<repo_root>/v7_vs_lalala_scores.json` · `<repo_root>/v7_vs_lalala_state.json`（**均在仓库根**，勿找 `batch_executor/v7_vs_lalala_scores.json`） |
| **WF-04 L2 日志** | `<repo_root>/logs/v7_vs_lalala_*.log` + `yf1_v7_*.log` + `yf2_v7_*.log`（**Shell 列目录**；`.cursorignore` 屏蔽 IDE 读） |
| **分析批跑结果** | 见上行「WF-04 批跑解读」；详规 [`工作流.md`](./工作流.md) §2.3 |
| **yf 单步决策链路（WF-12）** | **yf1**：直开 `*yf1_*` JSON；**yf2**：`[副序]-[后缀]` 配对 → §2.2 **`find_decision_at_step`** 对齐 `handCards` + `logs/yf*_*.log`；回归 `python scripts/tools/wf12_find_decision_at_step.py`；见 [`WF-12`](./workflows/WF-12-yf-decision-trace.md) §2.0–§2.2 |
| **Botzone 适配层链路（WF-13）** | `python scripts/checks/check_botzone_trace.py <logs/v8_vs_botzone_*.log> --match <前缀> --by-cards <greater 牌面>`（或 `--step N`）；数据源**无 game_records**，`greater=Free` = R-B01 判型 bug 信号；结论只追加进 `docs/guandan-brain/ITERATIONS.md`（不写报告）；见 [`WF-13`](./workflows/WF-13-botzone-decision-trace.md) §2.0–§2.4 |
| **回放单局** | `YF_REPLAY.bat` |
| **BC 训练** | `python scripts/train_bc_v7.py` |
| **推送前冗余校验** | `python verify_gitignore.py` |
| **Wiki 摄入** | `python scripts/wiki.py ingest` |
| **Wiki 查询** | `python scripts/wiki.py query "关键词"` |
| **Wiki 状态** | `python scripts/wiki.py status` |
| **推送前检查** | `python verify_gitignore.py` |
| **组牌引擎测试** | `python scripts/checks/check_grouping_engine.py` |
| **残局智能体调试** | `python scripts/checks/check_endgame_agent.py --hand ... --players ...` |

---

## 四、根目录 .bat 一览

> 根目录 .bat 均为 Phase 5 后的 stub，指向 `scripts/launchers/` 下的真源。
> 直接运行即可，无需手动 cd 到 scripts/ 下。

```
batch_convert_replays.bat     CHECK_RECORD_CONSISTENCY.bat
INSTALL_STAGE7_DEPENDENCIES.bat  pre_push_check.bat
run_new_test.bat              RUN_V7_VS_LALALA.bat
RUN_V8_VS_LALALA.bat          START_AUTO_RESTART_WORKFLOW.bat
START_M1_GUI.bat              START_M1_TRAINING.bat
START_M1_WORKFLOW_FULL.bat    START_M2_GUI.bat
START_M3_GUI.bat              START_SMART_TRAINING.bat
START_STAGE7_TRAINING.bat     START_STRATEGY_TASKS_TRAINING.bat
START_V4_GUI.bat              START_V5_CLIENTS.bat
START_V5_GUI.bat              START_V6_GUI.bat
START_V7_AUTO.bat             START_V7_CLIENTS.bat
START_V7_COMPLETE.bat         START_V7_GUI.bat
START_V8_AUTO.bat             START_V8_CLIENTS.bat
START_V8_COMPLETE.bat         START_V8_GUI.bat
YF_REPLAY.bat
```

---

> **维护规则**：新增 `.py` / `.bat` / `.ps1` / `.sh` 脚本时同步更新本文档（临时测试/调试脚本除外）。删除旧脚本时同步删除对应行。
