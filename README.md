# 掼蛋AI客户端

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

南京邮电大学掼蛋AI算法对抗平台的客户端实现，支持AI自动出牌决策、自我对弈、数据收集和平台信息监控。

## 📋 目录

- [项目简介](#项目简介)
- [掼蛋与平台基础知识（新手必读）](#掼蛋与平台基础知识新手必读)
- [快速开始](#快速开始)
- [重要规则](#重要规则)
- [功能特性](#功能特性)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [使用指南](#使用指南)
- [开发规范](#开发规范)
- [参考资料](#参考资料)

---

## 📖 项目简介

### 项目目标
- 开发符合南京邮电大学掼蛋AI平台的客户端
- 实现AI自动出牌决策
- 支持自我对弈和数据收集
- 可扩展的架构设计
- 平台动态信息监控
- **V7 引擎**: 基于深度学习的终极胜率导向决策引擎

### 平台信息
- **平台名称**: 南京邮电大学掼蛋AI算法对抗平台
- **平台地址**: https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **当前版本**: v1006（内测中，可参与）
- **联系方式**:
  - 研究兴趣咨询: chenxg@njupt.edu.cn
  - 问题反馈: wuguduofeng@gmail.com
  - QQ: 519301156

---

## 🎴 掼蛋与平台基础知识（新手必读）

> 本节摘自 [docs/knowledge/guandan-basic-knowledge.md](docs/knowledge/guandan-basic-knowledge.md)。**离线平台协议与字段以** `offline_platform/掼蛋平台使用说明书v1006.pdf` **为准**；下文帮助你在读代码、跑批、看日志前先建立共同语言。

### 这是什么项目？

本仓库是 **掼蛋 AI 客户端 + 批量对战/训练工具链**：通过 WebSocket 连本地或局域网 **v1006 离线平台**，4 个 Python 客户端自动出牌；当前主开发线是 **M 系列（硬编码规则引擎）** 对战 **lalala**，详见 [M/V 治理方案](docs/governance/M-V-Series-治理方案.md)。

### 队伍与座位（必记）

| 概念 | 说明 |
|------|------|
| **4 人两两组队** | **0 号 + 2 号** 一队，**1 号 + 3 号** 一队 |
| **座位怎么定** | **连接顺序**决定座位号：第 1 个连入 → 0 号，依次 1、2、3 |
| **和代码的关系** | 批跑 GUI / 客户端脚本里 4 条路径的顺序，必须对应上述座位 |

这与 README 后文「第 1、3 连接一队」表述一致：**连接序 1→0 号、2→1 号、3→2 号、4→3 号**。

### 一副、一局、升级（别混）

| 术语 | 含义 |
|------|------|
| **一副牌** | 108 张发完、每人 27 张 →（第二副起：**进贡 → 还贡**，或 **抗贡**）→ 多**圈**出牌，直至四人完牌顺序确定（`episodeOver.order` 四名；双上时可有 `restCards`）→ 按名次升级，并决定下一副进贡关系 |
| **一圈出牌** | 一人首发，三家跟压/过；连续三人过则结束，接风者下一圈首发。**一副内含多圈** |
| **一局** | 从打 **2** 起，某队打到 **A** 且在 **A 级拿到双上**（头游+二游），才算赢下一局 |
| **名次** | 头游（第 1）→ 二游 → 三游 → 末游（第 4） |

**术语区分**：**一副 ≠ 一圈 ≠ 比赛一轮 ≠ 一局**（「比赛一轮」指编排上全体选手普遍出场一次，与一副牌无关）。

**本队升级级数**（本副结束后，仅当本队有人拿头游时）：

| 本队两人名次 | 升级 |
|--------------|------|
| 头游 + 二游（**双上**） | **+3 级**（例：2→5） |
| 头游 + 三游 | **+2 级** |
| 头游 + 末游 | **+1 级** |
| 本队无人头游 | **不升级** |

- **A 级特殊**：到 A 后须在本级一副 **双上** 才算赢局；若 A 级连续 2 副未胜（含被对手双上），**降回 2 重打**；A↔2 循环满 50 次可判平局。
- **对方**拿头游时，对方按上表升级，本队不升。

### 离线平台 v1006 怎么理解

```bash
guandan_offline_v1006.exe N
```

| 项 | 说明 |
|----|------|
| 说明书里的 N | 「**游戏次数**」：一次「游戏」= 一方 A 级且本副 **双上** 过关（见 PDF `gameOver` 段注释） |
| **本仓库称法** | **N = 平台局数**（`--target-games` / `completed_games` 同口径）；跑满 N 局即 `gameOver` |
| **与规则「一副」** | **1 平台局 ≠ 1 副**。平台局内含多副；1 副 = 1 次 `episodeOver`。实测：`target-games 1` → **59 副**（2026-05-31）。详见 [platform-data-interpretation.md](docs/knowledge/platform-data-interpretation.md) |
| 如何判断规则「一局结束」 | 与平台「一次游戏」同义；客户端跨副跟踪 `game_scores_m2.json`；**不能**用 `episodeOver` 次数当局数 |

常用协议字段（日志 / JSON 里常见）：

| 字段 | 含义（与 [v1006 使用说明书](offline_platform/掼蛋平台使用说明书v1006.pdf) 用语一致） |
|------|------|
| `episodeOver.order` | 本副名次 `[头游, 二游, 三游, 末游]`（座位号 0–3） |
| `episodeOver.curRank` | 小局结束时**所打的当前等级**（说明书 § `episodeOver` 示例） |
| `gameResult.victoryNum` / `draws` | 各队本批 **赢局数** / 平局（`[0]` vs `[1]` 比队胜负；**不是副数**） |
| `act.*.selfRank` | **我方等级**（跨副累积） |
| `act.*.oppoRank` | **对方等级**（跨副累积） |
| `act.*.curRank` | **当前等级**（本副级牌点数；`play` 阶段即本副打几） |

等级字符：`2,3,4,5,6,7,8,9,T,J,Q,K,A`（T=10）。

#### `selfRank` / `oppoRank` / `curRank` 别混（`beginning` vs `act`）

> **平台原文**：`act` · `stage=play` 示例的字段释义为「**我方等级：K，对方等级：9，当前等级 9**」。见 [掼蛋平台使用说明书 v1006](offline_platform/掼蛋平台使用说明书v1006.pdf) **第 5–7 页**（`tribute` / `back` / `play` 三阶段 `act` 示例）。  
> **`notify` · `beginning` 官方示例仅含 `handCards`、`myPos`，不含三字段**（同 PDF 第 3 页）。本仓库 `game_info` 中的三字段来自客户端 `gameStart` 快照，非 PDF 中 `beginning` 示例结构。

同一副牌里，**`gameStart` 快照与 `act` 上的三字段可能不一致**；回放、JSON 若只读 `game_info` 或只读 `actions[].context`，会误以为「当前等级 6 又 9」矛盾。按掼蛋规则与说明书应这样理解：

| 字段 | 说明书用语 | 含义 |
|------|------------|------|
| **`selfRank`** | 我方等级 | 我方从 2 起按副升级后的等级（跨副累积） |
| **`oppoRank`** | 对方等级 | 对方从 2 起按副升级后的等级（跨副累积） |
| **`curRank`** | **当前等级** | 本副级牌点数（哪一点数是级牌）；`play` 阶段即本副打几 |

**`gameStart` → `game_info`（本副开局快照，非 PDF `beginning` 示例字段）**

- 表示**本副开始前**（通常是**上一副结束瞬间**）的我方等级、对方等级与当前等级上下文。
- 例：`selfRank=8`，`oppoRank=6`，`curRank=6` → 上一副结束时我方等级 8、对方等级 6；`curRank=6` 反映**上一副**语境下的当前等级，**不等于**进贡还贡结束后本副 `play` 的当前等级。
- 第二副起，本副开局后往往先 **进贡 / 还贡**（说明书 § `tribute` / `back`）；此阶段 `act` 仍带三字段，且 **`curRank` 常与 `selfRank` 相同**（还贡示例：我方等级 5、当前等级 5，系统跳过等级 5 的牌）。

**`act` · `stage=play`（进贡还贡结束、正式出牌）**

- 表示**本副出牌**时的我方等级、对方等级与**当前等级**；分析 AI 决策、比牌、级牌**以此时为准**（说明书：`我方等级 / 对方等级 / 当前等级` 三者可不同，如 K / 9 / 9）。
- 升级在**上一副结束时**结算：仅当某队有人拿**头游**，该队才按名次表升级（双上 +3、头游+三游 +2、头游+末游 +1；无人头游则不升）。见上文「本队升级级数」表及 [江苏掼蛋规则](docs/gdrules/江苏掼蛋规则.md)「从而确定下轮的级牌」。
- 例（与常见回放样例一致）：
  - 上一副结束：我方等级 8、对方等级 6；**对方**头游+二游 → 对方 **+3** → 6→**9**；我方未拿头游 → **我方等级仍为 8**。
  - 本副 `act` · `play`：`selfRank=8`，`oppoRank=9`，`curRank=9`（**当前等级 9**，9 为级牌）。
  - 而 `game_info` 仍可能是 `8 / 6 / 6`——**不是**本副当前等级 6，而是**进贡还贡前**的快照未更新。
- 进贡还贡结束后，由**进贡方**先出牌（上一副对方赢 → 我方进贡 → 还贡后常由我方首发）。

**`notify` · `stage=play`（他人出牌广播）**

- **不带** `selfRank` / `oppoRank` / `curRank`（说明书 `play` notify 示例仅含出牌字段）。
- `game_records` 里 `actions[].context` 若出现三字段，多为客户端用**最近一次 `act` 缓存**填充，**不能**当作该条 notify 的服务器下发值。

**读 JSON / 回放时**

| 用途 | 优先读 |
|------|--------|
| 本副**当前等级**、级牌、比牌 | `my_decisions[].context` 或同副 **`act` · `play`** |
| 本副开局前等级（参考） | `game_info` |
| 逐步出牌里的三字段 | 勿单独信 `actions[].context`；notify 无真源 |

文件名 `[6]` 等后缀来自保存时 `game_info.curRank`，**不能**代替本副 `act` · `play` 的当前等级。

**离线平台数据解读（`victoryNum`、批跑台账、勿与规则一局混）** → [docs/knowledge/platform-data-interpretation.md](docs/knowledge/platform-data-interpretation.md)。  
更细的副/局判定与 M2 追踪 → [docs/knowledge/guandan-basic-knowledge.md](docs/knowledge/guandan-basic-knowledge.md) 第三节；字段写入路径 → [docs/README.md](docs/README.md#selfrank--opporank--currank-写入位置2026-05-29)；平台 JSON 全文 → [offline_platform/掼蛋平台使用说明书v1006.pdf](offline_platform/掼蛋平台使用说明书v1006.pdf)。

### 本仓库如何记「副 / 局」胜负（M2）

M2 客户端在 `yf1_m2.py` / `yf2_m2.py` 里做 **副级 + 局级** 追踪：队长 `yf1_m2` 写入根目录 `game_scores_m2.json`，队友 `yf2_m2` 只打日志避免写文件冲突。批跑统计场次见 `batch_executor/`。

新手只需知道：**看胜率 / 回归别只数「副数」**——平台参数 N、批跑 `target-games` 与「完整局」可能不一致；分析时优先看 `game_scores_m2.json` 或治理文档中的 **30 局回归集**（[COS 拉取](docs/governance/COS-接入指南.md)）。

更细的判定函数、JSON 格式与注意点 → [docs/knowledge/guandan-basic-knowledge.md](docs/knowledge/guandan-basic-knowledge.md) 第三节。

### 新手建议阅读顺序

1. 本节（规则 + 平台参义）
2. [快速开始](#快速开始) → 装依赖、配 `config.yaml`
3. [M/V 治理方案](docs/governance/M-V-Series-治理方案.md) → 分支 `m-dev`、目录约定
4. [掼蛋 AI 迭代大脑](docs/guandan-brain/README.md) → 改 AI 行为前必读  
   - **新开 Agent**：复制 [AGENT_FIRST_MESSAGE.md](docs/guandan-brain/AGENT_FIRST_MESSAGE.md) 里那句话，粘贴给 Agent 第一句  
   - **提交推送**：复制 [AGENT_PUSH_CHECKLIST.md](docs/guandan-brain/AGENT_PUSH_CHECKLIST.md) 默认第一句；本机一次性跑 `scripts/hooks/install-hooks.bat`
5. 跑 M1：`START_M1_GUI.bat` 或 [M1 测试指南](docs/development/M1测试指南.md)

---

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Windows / Linux
- 网络连接（用于平台信息监控）

### 安装步骤

1. **克隆项目**
```bash
git clone https://gitee.com/Philsz/yifei-ai-gd.git
cd YiFeiAI-GD
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **模型文件说明**
   - **注意**：M1 系列是硬编码规则引擎，不是机器学习模型，无需模型文件。
   - 其他机器学习模型文件（包括检查点）不会被推送到Git仓库（见下方"模型文件管理"章节）

4. **配置设置**
```bash
# 复制配置文件模板
cp config.yaml.example config.yaml
# 编辑配置文件
vim config.yaml
```

4. **运行程序**
```bash
python main.py
```

### 依赖包
- `websockets` / `websocket-client` - WebSocket通信
- `requests` / `httpx` - HTTP请求（信息监控）
- `beautifulsoup4` / `lxml` - HTML解析（信息监控）
- `schedule` / `APScheduler` - 定时任务（信息监控）
- `pyyaml` - 配置文件解析

---

## ⚠️ 重要规则

### 🔴 核心规则（必须遵守）

#### 1. 时间处理规则（强制要求）

**所有涉及当前时间、实时时间的场景必须调用系统时间API，禁止使用硬编码时间。**

##### ✅ 正确做法
```python
from datetime import datetime

# 获取当前时间
current_time = datetime.now()

# 获取当前时间戳
timestamp = datetime.now().timestamp()

# 格式化当前时间
formatted_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 判断是否在静默时段
def is_quiet_hours():
    now = datetime.now()  # 必须调用系统时间
    hour = now.hour
    return 0 <= hour < 6

# 计算下次检查时间
def schedule_next_check(interval):
    next_time = datetime.now() + timedelta(seconds=interval)  # 基于当前时间计算
    return next_time
```

##### ❌ 错误做法
```python
# 禁止硬编码时间
current_time = "2025-01-01 12:00:00"  # ❌ 错误

# 禁止使用固定时间戳
timestamp = 1704067200  # ❌ 错误

# 禁止在代码中写死时间
if hour == 12:  # ❌ 错误，应该从系统时间获取
```

##### 适用场景
- ✅ 日志时间戳：`datetime.now()`
- ✅ 信息抓取时间：`datetime.now()`
- ✅ 静默时段判断：`datetime.now().hour`
- ✅ 定时任务调度：基于`datetime.now()`计算
- ✅ 数据记录时间：`datetime.now()`
- ✅ 文件命名时间戳：`datetime.now().strftime('%Y%m%d_%H%M%S')`
- ❌ 历史日期记录：可以使用固定日期（如"2025年10月5日"这样的具体历史时间）

#### 2. JSON格式规则
- **严格遵循平台JSON格式要求**
- 所有消息必须符合平台规范
- 消息格式验证必须通过

#### 3. 组队规则
- **第1个和第3个连接**的AI自动为一队
- **第2个和第4个连接**的AI自动为一队
- 必须正确识别队友并配合

#### 4. 响应时间规则
- 决策响应时间建议 < 1秒
- 避免超时导致判负

#### 5. 信息监控规则
- 检查间隔 ≥ 6小时
- 每日 0:00-6:00 为静默时段，不进行检查
- 遵守网站使用条款，不造成服务器压力

---

## ✨ 功能特性

### 核心功能
- ✅ WebSocket通信（本地/局域网）
- ✅ 完整牌型识别（Single/Pair/Trips等）
- ✅ 牌型比较和压制判断
- ✅ AI决策引擎（策略评估、出牌决策、配合策略）
- ✅ 游戏状态管理
- ✅ 错误处理和自动重连

### 扩展功能
- ✅ 对局记录和数据收集
- ✅ 平台信息监控（自动抓取平台动态）
- ✅ 信息通知（控制台/日志/可选邮件）
- ✅ 日志系统

---

## 🌿 分支说明

### 当前分支

- **`main`**: 主分支，用于最终合并和发布
- **`m-dev`**: M 系列（M1-M3）硬编码规则引擎开发线
  - 包含：`yf1_m1.py`/`yf2_m1.py`、`rule_based_decision_engine_m1.py`
  - 特点：5阶段细分路由规则引擎，长期稳定对战线
- **`v7-dev`**: **V7 深度学习引擎实验线**（本分支）
  - 包含：`yf1_v7.py`/`yf2_v7.py`、`ultimate_win_rate_engine_v7.py`
  - 特点：基于训练模型的终极胜率导向决策，四头网络输出
  - 启动：`START_V7_GUI.bat` / `START_V7_AUTO.bat` / `start_v7_gui.py`

> V6 系列已归档（tag `archive/v6-dev-closed`），`v6-dev` 分支已删除。详见 [M/V 治理方案](docs/governance/M-V-Series-治理方案.md)。

### 切换分支

```bash
# M 系列规则引擎
git checkout m-dev
python src/communication/yf1_m1.py

# V7 深度学习引擎
git checkout v7-dev
python start_v7_gui.py
```

---

## 🧠 决策引擎概述

本项目同时维护两种决策引擎：

| 引擎 | 类型 | 分支 | 核心文件 |
|------|------|------|----------|
| **M 系列** | 硬编码规则引擎 | `m-dev` | `src/decision/rule_based_decision_engine_m1.py` |
| **V7** | 深度学习胜率引擎 | `v7-dev` | `src/decision/ultimate_win_rate_engine_v7.py` |

- M 系列测试：`START_M1_GUI.bat`（详见 [M1 测试指南](docs/development/M1测试指南.md)）
- V7 引擎测试：`START_V7_GUI.bat`（详见 [V7-实施方案](docs/guandan-brain/V7-实施方案.md)）
---

## ⚠️ 模型文件管理（重要）

**所有模型文件（包括检查点）都不会被推送到Git仓库。**

### 其他电脑首次使用

1. **拉取最新的 `.gitignore`**：
   ```bash
   git pull origin main
   ```

2. **检查模型文件是否会被推送**：
   ```bash
   python scripts/checks/check_models_before_push.py
   ```

3. **如果发现模型文件被跟踪，执行以下命令移除**（保留本地文件）：
   ```bash
   git rm --cached models/*
   git commit -m "移除模型文件跟踪"
   ```

### 推送前检查

每次推送前建议运行检查脚本：
```bash
python scripts/checks/check_models_before_push.py
```

如果脚本显示 ✅，说明模型文件不会被推送，可以安全推送。

---

## 📁 项目结构

```
guandan_ai_client/
├── main.py                 # 主程序入口
├── config.yaml             # 配置文件
├── requirements.txt        # 依赖包
├── README.md              # 说明文档（本文件）
│
├── docs/                    # 文档目录
│   ├── guandan-brain/      # 迭代大脑：缺陷/迭代/评测台账（改代码前先读 README）
│   ├── development/        # 开发文档
│   │   └── 分支开发指南.md  # M1/V6分支使用说明
│   ├── 掼蛋AI客户端架构方案.md
│   ├── 掼蛋AI比赛参赛指南.md
│   └── 掼蛋AI相关比赛汇总.md
│
├── src/
│   ├── communication/      # 通信模块
│   │   ├── yf1_m1.py / yf2_m1.py    # M1客户端（m-dev分支）
│   │   ├── yf1_v7.py / yf2_v7.py    # V7客户端（v7-dev分支）
│   ├── game_logic/         # 游戏逻辑模块
│   ├── decision/           # 决策引擎模块
│   │   ├── rule_based_decision_engine_m1.py  # M1规则引擎
│   │   ├── ultimate_win_rate_engine_v7.py    # V7深度学习引擎
│   │   ├── dynamic_grouping_optimizer.py     # V7动态分组优化
│   ├── rl_agent/           # RL智能体模块
│   │   └── dynamic_strategy_adjuster.py  # V7策略调整器
│   ├── data/               # 数据收集模块
│   ├── monitor/            # 信息监控模块
│   └── utils/              # 工具模块
│
├── tests/                  # 测试代码
├── data/                   # 数据目录
│   ├── replays/           # 回放文件
│   └── platform_info/     # 平台信息存储
└── logs/                   # 日志目录
```

详细结构说明请参考 [架构方案文档](docs/architecture/掼蛋AI客户端架构方案.md)

---

## ⚙️ 配置说明

### 基本配置

```yaml
# config.yaml
platform:
  name: "南京邮电大学掼蛋AI平台"
  version: "v1006"
  url: "https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html"

websocket:
  local_url: "ws://127.0.0.1:23456/game/{user_info}"
  network_url: "ws://[局域网IP]:23456/game/{user_info}"
  reconnect_interval: 5
  heartbeat_interval: 30
  timeout: 10

ai:
  strategy_level: "medium"  # basic/medium/advanced
  cooperation_enabled: true
  risk_tolerance: 0.5
  max_decision_time: 1.0  # 最大决策时间（秒）

info_monitor:
  enabled: true  # 是否启用信息监控
  check_interval: 21600  # 检查间隔（秒），默认6小时（≥6小时）
  quiet_hours:  # 静默时段，不进行检查
    enabled: true
    start: "00:00"  # 静默开始时间（24小时制）
    end: "06:00"    # 静默结束时间（24小时制）
```

### 配置说明
- 详细配置说明请参考 [架构方案文档 - 配置管理](docs/architecture/掼蛋AI客户端架构方案.md#六配置管理)

---

## 📖 使用指南

### 基本使用

1. **启动客户端**
```bash
python main.py
```

2. **连接平台**
   - 本地测试：使用 `ws://127.0.0.1:23456/game/{user_info}`
   - 局域网对战：使用 `ws://[局域网IP]:23456/game/{user_info}`

3. **查看日志**
   - 日志文件：`logs/ai_client.log`
   - 控制台输出：根据配置显示

### 信息监控

信息监控功能会自动在后台运行，定期检查平台动态：

- **检查频率**: 每6小时（≥6小时）
- **静默时段**: 每日 0:00-6:00 不进行检查
- **通知方式**: 控制台输出、日志记录
- **信息存储**: `data/platform_info/` 目录

### 手动触发检查

```python
from src.monitor.fetcher import PlatformInfoFetcher

fetcher = PlatformInfoFetcher()
updates = fetcher.check_updates()
```

---

## 📝 开发规范

### 代码规范
- 遵循 PEP 8 Python代码规范
- 使用类型提示（Type Hints）
- 编写清晰的注释和文档字符串

### 文档规范
- **文档尽量简洁**：避免一次性生成过长文档导致超时
- **先列提纲再填充**：先创建文档框架和提纲并保存，再逐步填充内容
- **定期保存**：每3分钟保存一次，避免长时间编辑导致内容丢失
- **遵守时间规范**：文档中的时间信息应使用系统时间API，禁止硬编码时间

### 时间处理规范（重要）

#### 必须使用系统时间API
```python
from datetime import datetime, timedelta

# ✅ 正确：使用系统时间
current_time = datetime.now()
timestamp = datetime.now().timestamp()

# ✅ 正确：基于当前时间计算
next_check = datetime.now() + timedelta(hours=6)

# ✅ 正确：判断当前时间
if datetime.now().hour < 6:
    # 静默时段处理
    pass

# ❌ 错误：硬编码时间
fixed_time = "2025-01-01 12:00:00"  # 禁止

# ❌ 错误：使用固定时间戳
fixed_timestamp = 1704067200  # 禁止
```

#### 时间处理工具函数示例
```python
from datetime import datetime, timedelta

def get_current_time() -> datetime:
    """获取当前系统时间"""
    return datetime.now()

def get_current_timestamp() -> float:
    """获取当前时间戳"""
    return datetime.now().timestamp()

def format_time(dt: datetime = None) -> str:
    """格式化时间"""
    if dt is None:
        dt = datetime.now()  # 默认使用当前时间
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def is_quiet_hours(current_time: datetime = None) -> bool:
    """判断是否在静默时段（0:00-6:00）"""
    if current_time is None:
        current_time = datetime.now()  # 必须调用系统时间
    hour = current_time.hour
    return 0 <= hour < 6
```

### 测试规范
- 编写单元测试
- 进行集成测试
- 性能测试（响应时间<1秒）

### 提交规范
- 代码必须通过所有测试
- 遵循时间处理规则
- 完整的日志记录
- 清晰的提交信息

---

## 🔧 开发指南

### 开发环境搭建

1. **安装Python**
   - Python 3.8 或更高版本
   - 推荐使用虚拟环境

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置开发环境**
   - 配置IDE（推荐VS Code或PyCharm）
   - 配置代码格式化工具
   - 配置代码检查工具

### 开发流程

1. **阅读文档**
   - 若涉及 AI 行为/规则/训练改动：先读 [掼蛋 AI 迭代大脑](docs/guandan-brain/README.md)（`ISSUES` / `ITERATIONS` / `EVAL`）
   - 阅读 [架构方案文档](docs/architecture/掼蛋AI客户端架构方案.md)
   - 理解游戏规则和JSON格式
   - 了解平台要求

2. **开发功能**
   - 按照架构设计实现各模块
   - 遵循开发规范
   - 编写测试代码

3. **测试验证**
   - 本地测试
   - 完整对局测试
   - 稳定性测试

### 常见问题

**Q: 如何获取当前时间？**
A: 必须使用 `datetime.now()` 获取系统时间，禁止硬编码。

**Q: 信息监控的检查频率是多少？**
A: 默认6小时（≥6小时），且每日0:00-6:00为静默时段不检查。

**Q: 如何判断是否在静默时段？**
A: 使用 `datetime.now().hour` 获取当前小时，判断是否在0-6之间。

**Q: 组队规则是什么？**
A: 第1、3个连接为一队，第2、4个连接为一队。

---

## 📚 参考资料

### 官方资源
- **平台网站**: https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **离线平台**: 需从平台网站下载
- **使用说明书**: 对应版本v1006

### 游戏规则
- [掼蛋与平台基础知识（本文档摘要）](#掼蛋与平台基础知识新手必读)
- [掼蛋基础知识（完整版）](docs/knowledge/guandan-basic-knowledge.md) — 升级规则、v1006 协议、M2 胜负追踪与 `game_scores_m2.json`
- 江苏省体育局掼蛋竞赛简易规则
- v1006版本特殊规则（抗贡规则调整）

### 技术文档
- [掼蛋 AI 迭代大脑](docs/guandan-brain/README.md) - 缺陷、版本、评测台账（与 [文档目录首页](docs/README.md) 中的入口一致）
- [M/V 系列仓库治理方案](docs/governance/M-V-Series-治理方案.md) - **分支、冒烟、产物与 M/V 分层（执行基准）**
- [V7 引擎实施方案](docs/guandan-brain/V7-实施方案.md) - V7 深度学习引擎开发与部署计划
- [腾讯云 COS 接入指南](docs/governance/COS-接入指南.md) - **回归 replay 上传/拉取**
- [版本与分支状态矩阵](docs/versions/MATRIX.md)
- [详细架构方案](docs/architecture/掼蛋AI客户端架构方案.md)
- [开发规范](docs/DEVELOPMENT_RULES.md) - **重要：包含时间处理规则**
- [参赛指南](docs/掼蛋AI比赛参赛指南.md)
- [比赛汇总](docs/competition/掼蛋AI相关比赛汇总.md)

### 技术参考
- WebSocket协议文档
- JSON格式规范
- Python官方文档

### 智能体设计模式参考
- **[Agentic Design Patterns 中文版](https://github.com/ginobefun/agentic-design-patterns-cn)** - 《Agentic Design Patterns》中文翻译版，智能体设计模式实践指南
  - 包含21个核心设计模式的完整文档和代码示例
  - 核心章节：路由(Routing)、规划(Planning)、多智能体协作(Multi-Agent Collaboration)、优先级排序(Prioritization)等
  - 与M1掼蛋AI项目相关：可用于参考智能体架构设计、决策路由、多智能体协作等模式
  - 在线阅读：https://adp.xindoo.xyz/
  - 原书作者：Antonio Gulli


## 📄 许可证

本项目采用 MIT 许可证。

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

### 贡献指南
- 默认向 **`m-dev`** 提交 PR；规范见 [M/V 系列仓库治理方案](docs/governance/M-V-Series-治理方案.md)
1. Fork 本项目: https://gitee.com/Philsz/yifei-ai-gd
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 在Gitee上开启 Pull Request

### 仓库信息
- **Gitee仓库**: https://gitee.com/Philsz/yifei-ai-gd
- **详细说明**: 查看 [REMOTE_REPO_INFO.md](REMOTE_REPO_INFO.md)

**注意**: 提交代码前请确保：
- ✅ 遵循时间处理规则（必须调用系统时间API）
- ✅ 代码通过所有测试
- ✅ 遵循代码规范
- ✅ 更新相关文档

---

## 📞 联系方式

- **研究兴趣咨询**: chenxg@njupt.edu.cn
- **问题反馈**: wuguduofeng@gmail.com
- **QQ**: 519301156

---

## 📌 重要提醒

### ⚠️ 必须遵守的规则

1. **时间处理**: 所有涉及当前时间的场景必须调用系统时间API（`datetime.now()`），禁止硬编码时间
2. **JSON格式**: 严格按照平台JSON格式要求
3. **组队规则**: 正确识别队友（1-3一队，2-4一队）
4. **响应时间**: 决策响应时间建议<1秒
5. **信息监控**: 检查间隔≥6小时，静默时段（0:00-6:00）不检查

### ✅ 开发建议

- 先实现基础功能，确保能正常连接和通信
- 逐步优化，先实现基本策略，再逐步优化
- 充分测试，本地完整测试后再提交
- 保持联系，遇到问题及时联系主办方

---

**最后更新**: 2026年6月  
**文档版本**: v1.1  
**平台版本**: v1006  
**当前引擎**: M 系列（规则） + V7（深度学习）

