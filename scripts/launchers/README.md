# 启动脚本索引

本目录包含所有启动、测试和训练脚本，按版本和功能分类组织。

## 📁 目录结构

```
scripts/launchers/
├── v7/           # V7 终极胜率导向版本
├── m1/           # M1 硬编码规则引擎版本
├── training/     # 训练相关脚本
├── tools/        # 工具脚本（回放等）
└── v-nn/         # V-nn 系列（已有）
```

## 🚀 V7 启动器（scripts/launchers/v7/）

### GUI批跑（推荐）
| 脚本 | 说明 |
|------|------|
| `START_V7_GUI.bat` | V7 GUI批跑界面（预填V7配置） |
| `start_v7_gui.py` | V7 GUI Python入口（兼容） |

### 手动启动客户端
| 脚本 | 说明 |
|------|------|
| `START_V7_CLIENTS.bat` | 手动启动4个客户端（服务器需先启动） |
| `START_V7_COMPLETE.bat` | 完整启动（服务器+4客户端） |
| `start_v7_complete.py` | 完整启动 Python版 |

### 批跑（命令行）
| 脚本 | 说明 |
|------|------|
| `run_v7_vs_lalala_games.py` | V7 vs lalala批跑（支持--games参数） |
| `RUN_V7_VS_LALALA.bat` | 批跑Stub（→v-nn/） |

### 端到端测试
| 脚本 | 说明 |
|------|------|
| `run_v7_test.bat` | V7端到端测试（批处理版） |
| `run_v7_e2e_debug.py` | V7调试版测试（详细日志） |
| `run_e2e_simple.py` | V7简化测试 |
| `run_12games_test.py` | V7 12局完整测试 |
| `test_v7_engine_load.py` | V7引擎加载验证 |

### V7 配置
- **客户端**: `yf1_v7.py` + `yf2_v7`（队伍A） vs `run_lalala_client3/4.py`（队伍B）
- **路径配置**: `config/v7_paths.yaml`
- **批跑局数**: 建议 3 / 9 / 12（须为3的倍数）

---

## 🎮 M1 启动器（scripts/launchers/m1/）

### GUI批跑
| 脚本 | 说明 |
|------|------|
| `START_M1_GUI.bat` | M1 GUI批跑界面 |

### M1 特性
- 硬编码规则引擎（非机器学习）
- 5阶段细分路由
- 无需模型文件

---

## 🏋️ 训练启动器（scripts/launchers/training/）

### Stage 6 训练
| 脚本 | 说明 |
|------|------|
| `run_stage6_training_gui.bat` | Stage 6 GUI训练启动器 |
| `run_stage6_training_gui.py` | Stage 6 GUI Python入口 |

### Stage 7 训练
| 脚本 | 说明 |
|------|------|
| `QUICK_START_STAGE7.bat` | Stage 7 快速启动 |
| `QUICK_START_STAGE7_ULTRA.bat` | Stage 7 超级优化版 |

---

## 🛠️ 工具脚本（scripts/launchers/tools/）

| 脚本 | 说明 |
|------|------|
| `YF_REPLAY.bat` | 回放工具Stub |
| `yf_replay.py` | 回放引擎 |

---

## 📌 根目录Stub入口

为保持根目录整洁，所有启动脚本已移至本目录。根目录保留轻量Stub入口，双击即可启动：

| 根目录Stub | 指向 |
|-----------|------|
| `START_V7_GUI.bat` | → `scripts/launchers/v7/START_V7_GUI.bat` |
| `START_V7_CLIENTS.bat` | → `scripts/launchers/v7/START_V7_CLIENTS.bat` |
| `START_V7_COMPLETE.bat` | → `scripts/launchers/v7/START_V7_COMPLETE.bat` |
| `START_M1_GUI.bat` | → `scripts/launchers/m1/START_M1_GUI.bat` |
| `YF_REPLAY.bat` | → `scripts/launchers/tools/YF_REPLAY.bat` |
| `RUN_V7_VS_LALALA.bat` | → `scripts/launchers/v-nn/RUN_V7_VS_LALALA.bat` |

---

## 💡 使用建议

### 快速开始
1. **V7批跑**: 双击根目录 `START_V7_GUI.bat`
2. **M1批跑**: 双击根目录 `START_M1_GUI.bat`
3. **回放**: 双击根目录 `YF_REPLAY.bat`

### 命令行批跑
```bash
# V7 3局对战
python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3

# V7 12局对战
python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 12
```

### 测试验证
```bash
# V7引擎加载测试
python scripts/launchers/v7/test_v7_engine_load.py

# V7端到端调试测试
python scripts/launchers/v7/run_v7_e2e_debug.py
```

---

## 📝 维护说明

- **新增版本**: 创建新子文件夹（如 `v8/`）
- **新增脚本**: 放入对应子文件夹
- **根目录Stub**: 保持4-5行代码，仅转发调用
- **命名规范**: `START_`（启动）/ `RUN_`（批跑）/ `QUICK_START_`（快速启动）
