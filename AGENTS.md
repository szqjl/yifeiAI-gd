# 项目操作手册

> Hermes Agent 操作手册。每次新会话/换模型时，首先加载此文件。
> 版本: v3 | 最后更新: 2026-06-06 | 分支: v7-dev

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

# V7 vs lalala 批跑（队胜率 KPI；局数须为 3 的倍数）
RUN_V7_VS_LALALA.bat          # 默认 3 局
RUN_V7_VS_LALALA.bat 12       # 12 局
python run_v7_vs_lalala_games.py --games 9

# V7 测试
python tests/test_v7_engine_load.py   # 引擎加载测试

# 牌谱回放（GUI，见下文「牌谱回放」）
YF_REPLAY.bat
python scripts/tools/yf_replay.py
```

## 改 AI 行为前必读

本仓库掼蛋 AI 相关开发以 **`docs/guandan-brain/`** 为真源，与聊天上下文无关。

执行任何「修改掼蛋 AI 行为/规则/模型/训练配置」的任务前必须：

1. 阅读 `docs/guandan-brain/ISSUES.md`，确认与本次改动相关的 **open** `GUA-xxx` 及标签（`rules` / `observation` / `policy`）。
2. 阅读 `docs/guandan-brain/ITERATIONS.md` 中**最新一条**（或本轮草稿），对齐本轮目标与完成定义；若本轮未登记，先追加一条再改代码。
3. 阅读 `docs/guandan-brain/EVAL.md` 中的评测入口与通过标准；改动后更新评测结果与 ITERATIONS（含回归：pass→fail）。
4. **改 V7 引擎**（`ultimate_win_rate_engine_v7.py`、`src/rl_agent/`）：读 V7 open GUA、V7-实施方案.md；特征向量 512 维、有效特征 127 维。
5. **改 M3 决策**（`src/m/m3/`、`yf1_m3`/`yf2_m3`）：读 open 且 tag=`m3` 的 GUA、`PRINCIPLES_MAPPING.md` 相关 guard；**P0 guard 只改 `m3_decision_engine`**；组牌/牌力走 **V5+**。队胜率 KPI **只看 M3 批跑**。**M1 frozen**（`GUA-022` closed）：仅 bugfix / 协议 / 记录与 pytest 回归，**勿再开 M1 策略 GUA**（见 ISSUES「引擎维护策略」）。

### 完成后

- 在 `ISSUES.md` 更新相关条目的状态与 `closed_in`（若关闭）。
- 在 `ITERATIONS.md` 追加一行：目标 GUA、改动摘要、评测摘要、下轮 priority。

## 数据解读口径

解读批跑 / 平台 / lalala 对局数据前，阅读 `docs/knowledge/platform-data-interpretation.md` 与 `docs/guandan-brain/README.md` 相关章节。固定口径：

| 问什么 | 看什么 | 叫什么 |
|--------|--------|--------|
| 本批 **共打几局** | `completed_games`、`settingTimes` | **局**（整局 / 一次游戏） |
| **各队赢几局** | 批末 **`victoryNum[0]` vs `[1]`**（0+2 一队，1+3 一队；**禁止四席相加**） | **局**胜负（平台整局结束计胜） |
| **共打几副** | `total_rounds`、成对 match_key | **副**（平台 **小局** / `episodeOver`） |
| 牌谱 / PASS | **`game_records` 每条 JSON = 一副** | **副**，不是局 |

**定音**：**局 ⊃ 多副**；**平台 1 局 ≠ 1 副**。小局 = 副 ≠ 整局。

**批跑 `--target-games`**：须为 **3 的倍数**（exe 每会话 **3 局**）。推荐 **3 / 9 / 12**；**勿用 10**（尾批 `batch_games=1` → fallback，队胜难对账）。见 `docs/guandan-brain/EVAL.md`「批跑局数档位」。

**`victoryNum` 自检**（平台下发，按规则正确）：同队 **`[0]=[2]`、`[1]=[3]`**；批跑 N 局时 **`[0]+[1]` 应 = N**（无平局时）。异常如 `[1,1,1,1]`（只合 2 局）、`[1,2,1,0]`（同队不一致）→ **不可信**，查回填 / `gameResult` 原文。

**禁止**：用 `game_records` 文件数、`episodeOver` 次数当局数；用 `victoryNum` 当副数。

## 牌谱回放

批跑 / 对战落盘在 **`game_records/`**（每条 JSON = **一副**，见上表）。复盘 **只用 M3 最新 GUI**，真源在 `m-dev` 的 `scripts/tools/yf_replay.py`（v7-dev 已迁入；根目录旧 `yf_replay.py`、`replay.py`、`src/communication/replay_*.py` **已删，勿再用**）。

### 入口

| 方式 | 命令 |
|------|------|
| Windows（推荐） | 双击 **`YF_REPLAY.bat`**（转发 `scripts/launchers/tools/YF_REPLAY.bat`） |
| Python | `python scripts/tools/yf_replay.py` |
| 指定牌谱 | `YF_REPLAY.bat "game_records\<game_id> [yf1_v7]-[opponent_1_3]-[1]-[2].json"` |

路径含空格时 **必须加引号**（`game_id` 与 `[yf1_*]` 之间有空格）。

### 牌谱文件名

```text
{game_id} [{player}]-[opponent_1_3]-[{game_round}]-[{start_level}].json
```

- **`game_round`**：本文件是第几**副**（不是平台「局」）
- 支持 **`yf1_m3` / `yf2_m3` / `yf1_v7` / `yf2_v7`** 等客户端落盘格式
- 成对复盘：同一 `game_round` 可分别打开 yf1、yf2 两条 JSON

### 能力（相对旧命令行回放）

- Tk GUI：四席手牌、逐步播放、级牌徽章（**curRank 以 play·act 为准**，见 GUA-027/回放 curRank 迭代）
- 贡还段：`apply_tribute_back_to_hand` 校正初始手牌
- 资源：`assets/replay/joker_*.png`；依赖 **`tkinter`**

### 辅助工具

| 脚本 | 用途 |
|------|------|
| `scripts/tools/gen_replay_word.py` | 导出文字复盘 → `replay_word.md` |
| `scripts/tools/audit_greater_in_records.py` | 审计 greater 与牌谱一致性 |
| `pytest tests/test_yf_replay_levels.py tests/test_yf_replay_tribute_back.py` | 回放逻辑回归 |

**勿与训练管线混淆**：`src/knowledge_processor/*replay*` 用于知识库/训练数据转换，不是牌谱 GUI。

## 禁止

- 仅凭对话历史推断「上次修了什么」或「约定是什么」而不查上述文件。
- 在同一迭代内无目标地同时改多处 unrelated 逻辑（除非 ITERATIONS 明确列出并说明原因）。

---

## 多步骤任务与接续

### 新开 Agent（人类第一句）

复制 **`docs/guandan-brain/AGENT_FIRST_MESSAGE.md`** 里默认那句，粘贴给新 Agent 作为首条消息。

### 换机 / 多步骤接续

- 索引：`docs/guandan-brain/ITERATIONS.md`（本轮目标与完成定义）
- 换机 / 新 Agent：`docs/governance/分析接续-handoff.md` + `docs/analysis/handoffs/` 最新一篇
- 缺陷：`docs/guandan-brain/ISSUES.md`

### 关键词触发

用户说「继续之前的任务」「按 handoff」「按迭代」时，先读上述文件再动手。

- **V7 引擎**：读 `docs/guandan-brain/V7-实施方案.md` + `ISSUES.md` V7 段落；引擎入口 `ultimate_win_rate_engine_v7.py::decide()`
- **M 系列**：读 `ISSUES.md` 对应 tag + `ITERATIONS.md`

---

## Git 提交与推送规则

### 触发条件

用户要求 **提交、推送、commit、push、开 PR**；或 Agent 自行决定执行 `git commit` / `git push`。

### 动手前必须（按顺序，不可跳过）

1. 阅读本文件：§ 分支说明、§ 治理要点、§ Git 推送规则。
2. 打开 **`docs/guandan-brain/AGENT_PUSH_CHECKLIST.md`**，逐项勾选后再 staging。

### 硬性约束

| 项 | 要求 |
|----|------|
| 分支 | 日常 **`m-dev`** 或 **`v7-dev`**；禁止在 `main` 上提交功能代码 |
| 远程 | **`m-dev` → `git push origin m-dev`**，**`v7-dev` → `git push origin v7-dev`**；GitHub 用 `scripts/tools/sync_github_mirror.ps1`，非默认 push |
| Commit 标题 | 前缀：`[docs]`、`[M-m2]`、`[M-m3]`、`[V-nn-v7]` 等 |
| Layer 2 | 禁止提交：`models/*.pth`、`logs/`、`game_records/`、`game_scores_m2.json`、大体积 replay |
| 禁止 | 改 git config、`--force`、跳过 hooks（除非用户明确要求） |

### 推送前必须执行

1. 检查当前分支：`git branch -vv` → 确认 **非 main**
2. 检查暂存范围：`git status` / `git diff --stat`，**禁止** `git add .` 盲加
3. 推送前向用户 **一句话确认**：已读本文件治理要点、目标 **`origin/<当前分支>`**（m-dev 或 v7-dev）

### 禁止

- 未读上述治理文档即 `git commit` / `git push`。
- 仅凭通用 Git 习惯或聊天上下文推断分支/远程策略。

---

## Git 认证

- Gitee Token 在 `~/.git-credentials`
- `credential.helper store` 已启用

---
