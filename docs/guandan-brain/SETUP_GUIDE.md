# 批跑路径准备（新电脑首次拉取必读）

> 从 AGENTS.md 提取，日常会话不需要加载。

## 1. 仓库内依赖（git clone 自带，不需额外操作）
- 所有 Python 源码、批跑脚本、配置文件已纳入版本控制
- `config/v7_paths.yaml` — 路径配置模板（可选修改）
- `scripts/launchers/m/START_M3_BATCH.bat` — M3 批跑双击入口
- `scripts/launchers/v7/START_V7_COMPLETE.bat` — V7 交互启动入口
- `scripts/launchers/v7/run_v7_vs_lalala_games.py` — V7 批跑入口

## 2. 仓库外依赖（需手动准备，不在 git 中）

| 必需项 | 目标路径 | 说明 |
|--------|----------|------|
| 离线服务器 exe | `offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe` | 离线掼蛋引擎，每会话固定 3 局 |
| lalala 核心文件 | `reference/lalala/`（含 `state.py` `action.py` `utils.py`） | lalala 一等奖 AI，需纯 ASCII 路径 |
| V7 模型文件 | `models/bc_model_ultimate_win_rate.pth` 或 `models/v-nn/bc_model_ultimate_win_rate.pth` | V7 胜率模型（M3 不需要模型） |

## 3. 路径解析规则（`src/utils/v7_paths.py`）

所有路径按优先级解析：**环境变量 > `config/v7_paths.yaml` > 仓库内候选路径**

| 环境变量 | 默认候选路径 |
|----------|-------------|
| `SERVER_EXE` | `offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe` 等 |
| `LALALA_DIR` | `reference/lalala/` → `offline_platform/guandan_offline_v1006/lalala/` 等 |
| `MODEL_DIR` / `V7_MODEL_PATH` | `models/` → `models/v-nn/` |

**快速提示**：如果你原离线 exe 不在仓库内（如 `D:/guandanscore/guandan-offline-serve/`），强烈建议设环境变量 `SERVER_EXE=完整路径`，避免踩候选路径。

**跨机器部署（如仓库在 C 盘）**：只需改 `config/v7_paths.yaml` 里的 `server_exe` 路径（或设 `SERVER_EXE` 环境变量），**无需改任何 Python 代码**。所有启动脚本和引擎均已通过 `v7_paths.py` 统一解析路径。

## 4. 首次准备 checklist

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

## 5. 验证就绪

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

## 6. 常见问题

| 现象 | 原因 | 解决方案 |
|------|------|----------|
| `FileNotFoundError: 服务器 exe 未找到` | 候选路径全不存在 | `set SERVER_EXE=D:/your/path/guandan_offline_v1006.exe` 或改 `config/v7_paths.yaml` 中 `server_exe` 路径 |
| 仓库在 C 盘，exe 在其他盘 | 候选路径在仓库内，但 exe 实际在其他盘 | 改 `config/v7_paths.yaml` 的 `server_exe` 为实际路径（或 `set SERVER_EXE=实际路径`），**不需要改任何 Python 代码** |
| 客户端启动后秒退 | lalala 目录缺文件或含中文路径 | `python -c "from src.utils.v7_paths import sync_lalala_to_reference; sync_lalala_to_reference()"` |
| V7 启动报模型找不到 | 模型未放到 correct 路径 | `set V7_MODEL_PATH=D:/your/models/bc_model_ultimate_win_rate.pth` 或放到 `models/` 下 |
| `ImportError: No module named 'yaml'` | 没有 pyyaml | `pip install pyyaml`（缺失时自动降级，非阻塞） |

## 7. 启动命令速查

```
M3 批跑    → scripts/launchers/m/START_M3_BATCH.bat       （双击）
              py scripts/launchers/m/run_m3_vs_lalala_games.py --games 9
V7 批跑    → py scripts/launchers/v7/run_v7_vs_lalala_games.py --games 9
V7 交互    → scripts/launchers/v7/START_V7_COMPLETE.bat     （双击）
```
