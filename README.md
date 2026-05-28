# 掼蛋AI客户端

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

南京邮电大学掼蛋AI算法对抗平台的客户端实现，支持AI自动出牌决策、自我对弈、数据收集和平台信息监控。

## 📋 目录

- [项目简介](#项目简介)
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

### 平台信息
- **平台名称**: 南京邮电大学掼蛋AI算法对抗平台
- **平台地址**: https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **当前版本**: v1006（内测中，可参与）
- **联系方式**:
  - 研究兴趣咨询: chenxg@njupt.edu.cn
  - 问题反馈: wuguduofeng@gmail.com
  - QQ: 519301156

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

本项目采用**双分支并行开发**策略，用于独立训练和对比不同 AI 模型效果。

### 当前分支

- **`main`**: 主分支，用于最终合并和发布
- **`m-dev`**: M1 系列硬编码规则引擎分支（本地开发）
  - 包含：`yf1_m1.py`, `yf2_m1.py`, `rule_based_decision_engine_m1.py`
  - 特点：全新的硬编码规则引擎，5阶段细分路由
- **`m1-dev-clean`**: M1 系列干净分支（已推送，推荐用于训练）
  - 轻量级干净分支，不含模型文件和游戏记录
  - 适合远程训练和协作
- **`v6-dev`**: V6 系列优化分支
  - 包含：`yf1_v6.py`, `yf2_v6.py` 及相关优化
  - 特点：基于现有架构的优化版本

### 分支使用

```bash
# 切换到 M1 分支
git checkout m-dev

# 切换到 V6 分支
git checkout v6-dev

# 切换回主分支
git checkout main
```

**⚠️ 重要提醒**：测试不同版本时必须切换分支！
- 测试 M1：必须在 `m-dev` 分支运行 `yf1_m1.py`
- 测试 V6：必须在 `v6-dev` 分支运行 `yf1_v6.py`

### M1 系列使用说明

**M1 不是机器学习模型，而是硬编码规则引擎**，基于阶段细分路由的决策系统。

#### M1 文件结构
- `src/decision/rule_based_decision_engine_m1.py` - M1决策引擎（主入口）
- `src/communication/yf1_m1.py` - M1客户端1（Player 0）
- `src/communication/yf2_m1.py` - M1客户端2（Player 2）

#### 运行 M1

1. **切换到 M1 分支**
```bash
git checkout m-dev
```

2. **运行 M1 客户端**
```bash
# 运行客户端1（Player 0）
python src/communication/yf1_m1.py

# 运行客户端2（Player 2，需要新开终端）
python src/communication/yf2_m1.py
```

3. **M1 特性**
- ✅ 5阶段细分路由（开局、中局前期、中局后期、残局前期、残局后期）
- ✅ 主动/被动出牌分离
- ✅ 策略引擎集成（队友保护、优先级系统、牌值系统）
- ✅ 手牌结构分析器增强
- ✅ 残局策略类（RushStrategy, DefendStrategy等）

#### M1 架构说明

M1 采用分层架构：
```
RuleBasedDecisionEngineM1 (主入口)
  ├── StageRouter (阶段路由器)
  │   ├── OpeningActiveHandler / OpeningPassiveHandler
  │   ├── MidEarlyActiveHandler / MidEarlyPassiveHandler
  │   ├── MidLateActiveHandler / MidLatePassiveHandler
  │   ├── EndgameEarlyActiveHandler / EndgameEarlyPassiveHandler
  │   └── EndgameLateActiveHandler / EndgameLatePassiveHandler
  ├── StrategyEngine (策略引擎)
  │   ├── TeammateProtectionStrategy (队友保护)
  │   ├── PrioritySystem (优先级系统)
  │   └── CardValueSystem (牌值系统)
  └── HandStructureAnalyzer (手牌结构分析器)
```

### 测试 M1

详细测试步骤请参考 [M1测试指南](docs/development/M1测试指南.md)

**方式1：GUI批量测试（推荐，最简单）**：
```bash
# 1. 切换到 M1 分支
git checkout m-dev

# 2. 启动M1测试GUI
START_M1_GUI.bat

# 3. 在GUI中配置参数并开始测试
```

**方式2：手动测试**：
```bash
# 1. 切换到 M1 分支
git checkout m-dev

# 2. 启动第一个客户端（Player 0）
python src/communication/yf1_m1.py

# 3. 新开终端，启动第二个客户端（Player 2）
python src/communication/yf2_m1.py
```

详细说明请参考：
- [分支开发指南](docs/development/分支开发指南.md) - M1/V6分支使用说明
- [M1测试指南](docs/development/M1测试指南.md) - M1详细测试步骤
- [YF硬编码完整提升计划优化版](docs/training/YF硬编码完整提升计划优化版.md) - M1实施计划

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
│   │   ├── yf1_m1.py      # M1系列客户端1（m-dev分支）
│   │   ├── yf2_m1.py      # M1系列客户端2（m-dev分支）
│   │   ├── yf1_v6.py       # V6系列客户端1（v6-dev分支）
│   │   └── yf2_v6.py       # V6系列客户端2（v6-dev分支）
│   ├── game_logic/         # 游戏逻辑模块
│   ├── decision/           # 决策引擎模块
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

详细结构说明请参考 [架构方案文档](docs/掼蛋AI客户端架构方案.md)

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
- 详细配置说明请参考 [架构方案文档 - 配置管理](docs/掼蛋AI客户端架构方案.md#六配置管理)

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
   - 阅读 [架构方案文档](docs/掼蛋AI客户端架构方案.md)
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
- 江苏省体育局掼蛋竞赛简易规则
- v1006版本特殊规则（抗贡规则调整）

### 技术文档
- [掼蛋 AI 迭代大脑](docs/guandan-brain/README.md) - 缺陷、版本、评测台账（与 [文档目录首页](docs/README.md) 中的入口一致）
- [M/V 系列仓库治理方案](docs/governance/M-V-Series-治理方案.md) - **分支、冒烟、产物与 M/V 分层（执行基准）**
- [腾讯云 COS 接入指南](docs/governance/COS-接入指南.md) - **回归 replay 上传/拉取**
- [版本与分支状态矩阵](docs/versions/MATRIX.md)
- [详细架构方案](docs/掼蛋AI客户端架构方案.md)
- [开发规范](docs/DEVELOPMENT_RULES.md) - **重要：包含时间处理规则**
- [参赛指南](docs/掼蛋AI比赛参赛指南.md)
- [比赛汇总](docs/掼蛋AI相关比赛汇总.md)

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

**最后更新**: 2025年1月  
**文档版本**: v1.0  
**平台版本**: v1006

