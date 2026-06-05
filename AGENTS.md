# 项目操作手册

> Hermes Agent 操作手册。每次新会话/换模型时，首先加载此文件。
> 版本: v3 | 最后更新: 2026-06-05 | 分支: v7-dev

---

## 角色定位

**Hermes = 总调度/总负责，不是执行者。**

- 职责：拆任务、定优先级、调度 Opencode 执行、审查产出、推进闭环
- 不替子 Agent 写代码、跑测试、改文件——除非 CEO 明确要求
- Opencode = 执行者，负责实际编码

## 协作原则

1. **短任务短 prompt**：单个提示词 <= 40 行
2. **长任务拆回合**：拆成多个短任务串行调度，不贪多
3. **一个回合一个目标**：做完验证关单再开下一个
4. **不传信任**：子 Agent 报告的结果必须验证，不信"全部通过"
5. **产出验证优先**：任何声称修复/完成的，必须读文件确认
6. **Git 切分支**：被 IDE 插件目录阻塞时直接 `git checkout -f`。仓库整理规则以 `docs/governance/M-V-Series-治理方案.md` 为准。

## 环境

- **项目**: YiFeiAI-GD (掼蛋AI客户端)，NJUPT AI比赛平台 v1006
- **工作目录**: `/mnt/d/guandanscore/YiFeiAI-GD` (WSL 挂载 Windows D盘)
- **Python**: 项目自带 venv (Windows Python 3.13)
- **Git 推送**: `m-dev` 和 `v7-dev` 均推 Gitee origin，禁止推 `main`
- **认证**: `credential.helper store` + `.git-credentials`

## 🧠 决策引擎概述

参考 [README.md 决策引擎概述](../README.md#决策引擎概述) 获取完整说明。

### V7 引擎 (本分支)

V7 采用深度学习胜率导向决策引擎，替代 M 系列硬编码规则引擎。

| 组件 | 路径 | 说明 |
|------|------|------|
| 决策引擎 | `src/decision/ultimate_win_rate_engine_v7.py` | 四头网络：action_logits/position_win_rate/action_value/long_term_reward |
| 客户端 | `src/communication/yf1_v7.py` / `yf2_v7.py` | V7 对战客户端 |
| 策略调整器 | `src/rl_agent/dynamic_strategy_adjuster.py` | 动态策略调整 |
| 分组优化 | `src/decision/dynamic_grouping_optimizer.py` | 动态分组优化 |
| 模型权重 | `models/bc_model_ultimate_win_rate.pth` (84.3% 分数) | 不入库，本地存放 |
| 路径配置 | `config/v7_paths.yaml` | V7 路径模板，支持环境变量覆盖 |
| 启动 GUI | `start_v7_gui.py` / `START_V7_GUI.bat` | 一键启动 GUI 对战 |
| 启动 Auto | `START_V7_AUTO.bat` | 自动启动服务器+客户端 |

#### 特征工程

- 输入特征：512 维（有效特征 127 维，利用率 ~25%）
- 特征类别：位置/手牌/等级/公共信息/动作列表
- 模型输出：action_logits (softmax) 参与决策，其余三个头暂未使用

## 参考资料

参考 [README.md 参考资料](../README.md#参考资料) 获取完整文档索引。

### 核心文档
- [掼蛋 AI 迭代大脑](docs/guandan-brain/README.md) - 缺陷、版本、评测台账
- [M/V 系列仓库治理方案](docs/governance/M-V-Series-治理方案.md) - 分支、冒烟、产物与 M/V 分层
- [V7 引擎实施方案](docs/guandan-brain/V7-实施方案.md) - V7 开发与部署计划
- [详细架构方案](docs/architecture/掼蛋AI客户端架构方案.md)
- [版本与分支状态矩阵](docs/versions/MATRIX.md)

### 治理要点

参考 `docs/governance/M-V-Series-治理方案.md` (origin/m-dev)：

- **M = 底座**, **V = 智能体** (V-learn: v4/v5/v6, V-nn: v7)
- **M 系列开发线**: `m-dev` — 规则引擎长期稳定对战线
- **V7 实验线**: `v7-dev` — 深度学习引擎，独立推进，不合并 m-dev
- **回归集**: 30 局 (20 高频 + 10 防回归)
- **V 冒烟**: OFF (需达到 lalala 50 局 >=40% 胜率或 m3 契约冻结)
- **Layer 2 产物** (模型/日志/replay): COS 存储，gitignore，不进库
- **IDE 工具配置** (.agents/.claude/.cursor/.kiro/.continue): 不纳入仓库整理
- **启动脚本**: `scripts/launchers/` 存放，根目录保留薄 stub
- **Commit 标签**: `[M-m2]`, `[V-learn-v5]`, `[V-nn-v7]`, `[artifact]`, `[docs]`
- **分支合并**: V7 成熟后 → `m-dev`，需评审+测试

## V7 任务台账 (GUA)

| GUA | 状态 | 说明 |
|-----|------|------|
| V7-001 引擎模型加载 | closed ✅ | 13/13 PASS，模型 651KB |
| V7-002 WebSocket 连接 | closed ✅ | 审计 6 大类，修复 P0x3+P1x4，30 项测试通过 |
| V7-003 启动脚本路径 | closed ✅ | 消除所有 D 盘硬编码 |
| V7-004 模型文件检查 | open 🔴 | 与 V7-001 联动，需 torch 环境验证 |
| V7-005 特征工程扩充 | closed ✅ | 27→127 维 (5.3%→24.8%) |
| V7-006 端到端链路 | open 🔴 | **待推进** — 引擎+客户端+平台全链路跑通 |
| V7-007 胜率基线测试 | open 🔴 | Phase 2，3 的倍数局数 |
| V7-008 模型权重管理 | open 🔴 | Phase 1 |
| V7-009 自对弈基础设施 | open 🔴 | Phase 3 |
| V7-010 路径债清理 | open 🔴 | Phase 3 |

### 下一步 Priority

1. **V7-006** 端到端决策链路测试 — 引擎+客户端+平台全链路跑通一轮对局
2. **V7-004** 模型文件验证 — 需 Windows torch 环境

### 关键数据

- 特征利用率 24.8%，目标 >=50%
- 服务器路径通过 `GUANDAN_SERVER` 环境变量配置
- WebSocket 端口 23456
- 模型：`bc_model_ultimate_win_rate.pth`，分数 84.3%

## 🌿 分支说明

参考 [README.md 分支说明](../README.md#分支说明) 获取完整说明。

### 本分支 (v7-dev)

- **当前开发主线**: V7 深度学习引擎实验线
- **包含**: `yf1_v7.py`/`yf2_v7.py`、`ultimate_win_rate_engine_v7.py`
- **特点**: 基于训练模型的终极胜率导向决策，四头网络输出

> V6 系列已归档（tag `archive/v6-dev-closed`），`v6-dev` 分支已删除。

## 常用命令

```bash
# 切分支（IDE 插件目录不碰，直接 -f 强制）
git checkout -f v7-dev

# 推送
git push origin v7-dev

# 语法检查
python3 -m py_compile path/to/file.py

# V7 启动
start_v7_gui.py          # Linux
START_V7_GUI.bat         # Windows GUI 对战

# V7 测试
python tests/test_v7_engine_load.py   # 引擎加载测试
```

## Git 认证

- Gitee Token 在 `~/.git-credentials`
- `credential.helper store` 已启用

---
