## Learned User Preferences

- 始终使用简体中文回复。
- 希望 Agent 自动执行批跑与终端命令，不必每次手动点 Run；已配置 terminalAllowlist（git、python、pytest、pip、npm）。
- 仅在用户明确要求时才 git commit / push；推送前须读治理方案与 AGENT_PUSH_CHECKLIST。
- 改 M3 决策或解读批跑数据前，须先读 docs/guandan-brain/（ISSUES open、ITERATIONS 最新行）及 handoff。
- 接续任务时先读 docs/governance/分析接续-handoff.md 与 docs/analysis/handoffs/ 最新篇。
- 回放界面：可复制区仅保留【游戏记录】文件名；本步动作文本区宽约 200px，放右下。
- 用 replay_word.md 记录典型副的文字出牌步骤与完整 YF_REPLAY.bat 回放命令，便于沟通引用。
- 批跑或新迭代前常清空 game_records 与 replay_word.md；分析完的 game_records 可删除。
- 回放不得篡改真实出牌流水（不能实战输、回放赢）。
- 重视仓库目录整洁，按 docs/governance/M-V-Series-治理方案.md 归档整理。
- 掼蛋规则问答以 .cursor/rules/guandan-knowledge.mdc 为唯一标准；民间变体标注「非标准规则」。
- 新开 Agent 时复制 docs/guandan-brain/AGENT_FIRST_MESSAGE.md 默认首句。

## Learned Workspace Facts

- 掼蛋 AI 项目；改 AI 行为真源为 docs/guandan-brain/（ISSUES、ITERATIONS、EVAL）。
- 日常开发分支 m-dev（Gitee 真相源 origin/m-dev）；GitHub 仅 main 与 m-dev（default m-dev）；禁止 push main。
- M1 frozen（GUA-022 closed）；队胜率 KPI 只看 M3 批跑；P0 guard 改 m3_decision_engine，组牌/牌力走 V5+。
- M3 客户端 yf1_m3 / yf2_m3；对手 run_lalala_client3 / run_lalala_client4；离线 exe 为 offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe。
- 批跑入口 python -m batch_executor；--target-games 须为 3 的倍数（推荐 3 / 9 / 12，勿用 10）。
- v1006 exe 单次会话固定 3 局（argv 无效）；batch_games 真源为 current_batch.json；禁止裸信 gameResult.victoryNum。
- 局 ⊃ 多副；game_records 每条 JSON = 一副；completed_games = 平台局数；队胜看 victoryNum[0] vs [1]（0+2 一队，1+3 一队）。
- M3 须用 curPos / curAction / greaterPos 最新字段，不能盲信 JSON 内录制的 greaterPos / greaterAction。
- 回放工具 scripts/tools/yf_replay.py / YF_REPLAY.bat；Phase 5 仓库治理已结案。
- yf1 与 yf2 同队（pos 0+2）；队友公式 (myPos+2)%4。
- .batch_executor.lock 已加入 .gitignore。
- 批跑对账看 latest_victory_num.json 的 server_vn_raw / vn_source。

## 批跑路径准备（新电脑首次拉取必读）

### 1. 仓库内依赖（git clone 自带，不需额外操作）
- 所有 Python 源码、批跑脚本、配置文件已纳入版本控制
- `config/v7_paths.yaml` — 路径配置模板（可选修改）
- `scripts/launchers/m/START_M3_BATCH.bat` — M3 批跑双击入口
- `scripts/launchers/v7/START_V7_COMPLETE.bat` — V7 交互启动入口
- `scripts/launchers/v7/run_v7_vs_lalala_games.py` — V7 批跑入口

### 2. 仓库外依赖（需手动准备，不在 git 中）

| 必需项 | 目标路径 | 说明 |
|--------|----------|------|
| 离线服务器 exe | `offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe` | 离线掼蛋引擎，每会话固定 3 局 |
| lalala 核心文件 | `reference/lalala/`（含 `state.py` `action.py` `utils.py`） | lalala 一等奖 AI，需纯 ASCII 路径 |
| V7 模型文件 | `models/bc_model_ultimate_win_rate.pth` 或 `models/v-nn/bc_model_ultimate_win_rate.pth` | V7 胜率模型（M3 不需要模型） |

### 3. 路径解析规则（`src/utils/v7_paths.py`）

所有路径按优先级解析：**环境变量 > `config/v7_paths.yaml` > 仓库内候选路径**

| 环境变量 | 默认候选路径 |
|----------|-------------|
| `SERVER_EXE` | `offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe` 等 |
| `LALALA_DIR` | `reference/lalala/` → `offline_platform/guandan_offline_v1006/lalala/` 等 |
| `MODEL_DIR` / `V7_MODEL_PATH` | `models/` → `models/v-nn/` |

**快速提示**：如果你原离线 exe 不在仓库内（如 `D:/guandanscore/guandan-offline-serve/`），强烈建议设环境变量 `SERVER_EXE=完整路径`，避免踩候选路径。

### 4. 首次准备 checklist

```bash
# 1) 确保离线 exe 就位（以下任一路径均可）
#    - 仓库内：offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe
#    - 或设环境变量：SERVER_EXE=D:/your/path/guandan_offline_v1006.exe

# 2) 同步 lalala 到 reference/（纯 ASCII 路径）
python -c "from src.utils.v7_paths import sync_lalala_to_reference; sync_lalala_to_reference(); print('OK')"

# 3) 模型文件就位（仅 V7 需要）
#    - 放到 models/bc_model_ultimate_win_rate.pth 或 models/v-nn/

# 4) 安装 Python 依赖
pip install pyyaml psutil
# pyyaml：配置文件解析（缺失时自动降级用候选路径）
# psutil：进程管理（缺失时用 subprocess 回退）
```

### 5. 验证就绪

```bash
# 验证路径解析
python -c "from src.utils.v7_paths import get_server_exe, get_lalala_dir, get_model_file; print('server:', get_server_exe()); print('lalala:', get_lalala_dir()); print('model:', get_model_file())"

# M3 批跑快速启动
cd <repo_root>
py scripts/launchers/m/run_m3_vs_lalala_games.py --games 3

# V7 批跑快速启动
cd <repo_root>
py scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3
```

### 6. 常见问题

| 现象 | 原因 | 解决方案 |
|------|------|----------|
| `FileNotFoundError: 服务器 exe 未找到` | 候选路径全不存在 | `set SERVER_EXE=D:/your/path/guandan_offline_v1006.exe` |
| 客户端启动后秒退 | lalala 目录缺文件或含中文路径 | `python -c "from src.utils.v7_paths import sync_lalala_to_reference; sync_lalala_to_reference()"` |
| V7 启动报模型找不到 | 模型未放到 correct 路径 | `set V7_MODEL_PATH=D:/your/models/bc_model_ultimate_win_rate.pth` 或放到 `models/` 下 |
| `ImportError: No module named 'yaml'` | 没有 pyyaml | `pip install pyyaml`（缺失时自动降级，非阻塞） |

### 7. 启动命令速查

```
M3 批跑    → scripts/launchers/m/START_M3_BATCH.bat       （双击）
              py scripts/launchers/m/run_m3_vs_lalala_games.py --games 9
V7 批跑    → py scripts/launchers/v7/run_v7_vs_lalala_games.py --games 9
V7 交互    → scripts/launchers/v7/START_V7_COMPLETE.bat     （双击）
```
