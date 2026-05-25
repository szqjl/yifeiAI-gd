# AGENT_HUB.md — yifeGDBOT 多 Agent 协作中心

## 概述

本目录是 yifeGDBOT 项目的多 Agent 协作控制中心。
Hermes 作为总协调者（orchestrator），通过 Kanban 看板分配任务给编码 Agent（opencode-eng），
由编码 Agent 在隔离的 git worktree 中执行代码改动。

## 架构

```
良总（人类）
  ↓ 口述需求 / 验收
Hermes（总协调，profile: cursor）
  ↓ kanban_create / kanban_complete
Kanban 看板（~/.hermes/kanban.db）
  ↓ dispatch（60s tick）
opencode-eng（编码 Agent，profile: opencode-eng）
  ↓ opencode run（推荐）/ ~~ACP~~（暂停）
C:\yifeGDBOT（项目主目录）
```

## Profile 清单

| Profile | 角色 | Provider | 工作目录 | 说明 |
|---------|------|----------|----------|------|
| default | 主 Hermes | minimax-cn | — | CLI 交互入口 |
| cursor | Orchestrator | openrouter | — | 启用 kanban toolset，负责任务分配与验收 |
| opencode-eng | Worker | copilot-acp（⚠️ 不推荐） | C:\yifeGDBOT | 编码执行者；ACP 桥接与 Kanban worker 不兼容，见下文 |

## Kanban 看板状态

| 看板 | 说明 |
|------|------|
| yi-fei_gd | 当前激活，空 |
| default | 归档状态，历史任务 `t_50d3db0e`（已 done） |

切换：`hermes kanban boards switch <slug>`

## 启动顺序

### 1. 启动 Gateway（必须）

Gateway 内置 Kanban dispatcher，负责定时派发任务。

```bash
hermes gateway start
```

验证：
```bash
hermes gateway status
```

### 2. 初始化 Kanban（首次）

```bash
cd C:\yifeGDBOT
hermes kanban init
```

### 3. 创建任务

```bash
# 标准任务（worktree 模式，推荐）
hermes kanban create "实现 XX 功能" \
  --assignee opencode-eng \
  --workspace worktree \
  --body "详细需求描述..."

# 指定目录模式（已有目录）
hermes kanban create "修复 YY 问题" \
  --assignee opencode-eng \
  --workspace dir:C:\yifeGDBOT
```

### 4. 监控

```bash
# 实时看板
hermes kanban watch

# 查看任务详情
hermes kanban show <task_id>

# 查看 worker 日志
hermes kanban log <task_id>
```

### 5. 验收

```bash
# 验收通过
hermes kanban complete <task_id> --result "验收通过，代码已合并"

# 验收不通过，打回
hermes kanban block <task_id> "需要修改：XXX"
```

## Worker 执行方案

### 方案 A：ACP 模式（❌ 架构不兼容，暂停使用）

**配置**：`profiles/opencode-eng/.env`
```
HERMES_COPILOT_ACP_COMMAND=C:\Users\Surfa\AppData\Roaming\npm\opencode.cmd
HERMES_COPILOT_ACP_ARGS=acp
```

**原理（预期）**：Hermes dispatcher 启动 worker 时，通过 ACP 协议与 `opencode acp` 通信：
1. Hermes（ACP client）把 Hermes tool schema 写进 prompt
2. 期望 OpenCode 返回 `<tool_call>{...}</tool_call>` 文本块
3. Hermes 解析、执行工具、循环

**现实（不兼容根因）**：OpenCode ACP 是完整 Agent，有自己的工具集（bash、edit、read 等）。
OpenCode 在 session 内部尝试调 `kanban_show`、跑 bash、找 hermes.exe——这些全在 OpenCode 自己的 loop 里发生，
**不会**以 Hermes 能识别的 `<tool_call>` 形式回传。

所以 Hermes 侧永远是：**0 tool calls**，只收到一段 narrative 文本（如「让我 orient… worktree 不存在…」）。
Hermes 收到 `finish_reason=stop` 后结束本轮，worker 进程退出；
Kanban dispatcher 检测到 **pid not alive** → 记为 **crashed** → respawn → 无限循环。

#### 现象澄清：不是「60 秒超时杀进程」

2026-05-21 对任务 `t_b53fc45b`（GUA-022）的多轮 session 日志显示：

| 现象 | 真实原因 |
|------|----------|
| 每轮 ~54s–4m 结束 | OpenCode ACP 单次 `session/prompt` 往返耗时（内部思考），**不是** Hermes 60s kill |
| Messages: 2，0 tool calls | OpenCode 在内部跑 agent loop，不回传 Hermes 格式 `tool_call` |
| 前 N 次 crash | Worker 未 `kanban_complete` 就退出 → `detect_crashed_workers` 判 pid not alive |
| 只会「说」不「做」 | ACP 桥接架构与 Kanban worker 需求不匹配 |

典型日志（`profiles/opencode-eng/logs/agent.log`）：
```
API call #1: model=owl-alpha provider=copilot-acp latency=61.1s
Turn ended: reason=text_response(finish_reason=stop) tool_turns=0
```

OpenCode reasoning 中可见：`Model tried to call unavailable tool 'kanban_show'`——
Hermes 把 kanban 工具 schema 写进了 prompt，但 OpenCode 只认自己的 native 工具面，无法桥接回 Hermes。

**补充**：Hermes 默认 stale 杀连接超时是 **300s**（5 分钟），不是 60s。
`copilot-acp` 官方设计对象是 **GitHub Copilot CLI**（`copilot --acp --stdio`），
把命令 override 成 `opencode acp` 属于实验性 hack；协议字段（如 `protocolVersion`）也不完全匹配。

**状态**：❌ 暂停用于 Kanban worker
- ACP 握手（initialize、session/new）可以 work
- OpenCode CLI 使用子命令 `opencode acp`，非 Copilot 的 `copilot --acp --stdio`
- Profile 路径/`.cmd` 扩展名配置正确
- **但工具调用无法桥接**，Kanban 生命周期（show / complete / block）无法走通
- 要真正 work 需 Hermes 改 `copilot_acp_client.py` 适配 OpenCode 协议 + 双向 tool 桥接（工作量大）

### 方案 B：opencode run（✅ 推荐）

**原理**：绕过 ACP 协议层。Hermes worker 通过 `terminal` 工具直接调用 `opencode run`，
每次调用是独立进程，OpenCode 在自己的上下文里完成工作，结果通过 stdout 返回。

**配置**：worker 的 SOUL.md 或 kanban-worker skill 指导模型使用 `opencode run`。

**优点**：
- 稳定可靠，不依赖 ACP 协议
- 支持所有 OpenCode 功能（MCP、tools、etc）
- 可通过 `--model` 指定不同模型

**用法**：
```bash
# 在 worker 会话中，模型执行：
opencode run "读 docs/guandan-brain/README.md 并回复当前 GUA 优先级" \
  --print \
  --model openrouter/anthropic/claude-sonnet-4
```

**缺点**：
- 每次调用都是新会话，无持久上下文
- 需要 worker 模型自己解析任务并调用 opencode

**状态**：✅ 推荐为当前主力方案

**双 CLI 协同验证（2026-05-21 ✅）**

任务 `t_f1d0ca2f` 完整验证了三步工作流：

| 阶段 | 工具 | 结果 | 耗时 |
|------|------|------|------|
| Step 1 | `opencode run` | 创建 `utils.py` + `test_utils.py`，12/12 测试通过 | — |
| Step 2 | `ask-cursor review` | 发现 15+ 改进点（类型注解、docstring、错误处理、NaN 处理） | — |
| Step 3 | `opencode run` 修复 | 根据 review 修复，最终 13/13 测试通过 | — |
| **合计** | | **✅ 协同链路跑通** | 466s |

**实测命令语法**：
```bash
# opencode run（正确）
opencode run -m deepseek/deepseek-v4-flash "任务描述"

# cursor review（正确：cat + pipe，--file 参数传文件有问题）
cat utils.py test_utils.py | ask-cursor --prompt "审查代码质量"

# ask-cursor 也可用 --file 多次传递多个文件
ask-cursor --file utils.py --file test_utils.py --prompt "审查代码质量"
```

**关键发现**：
- `opencode run` 无 `--print` 标志（v1.15.6 去掉），用 `-m` 指定模型
- `ask-cursor --file` 传参方式未能正确传递文件内容，**必须用 `cat ... | ask-cursor`**
- `ask-cursor` 默认 model `composer-2.5-fast`，默认 mode `ask`，默认 timeout 120s

#### Cursor CLI：`--mode` 与 `--model`（Hermes 必读）

`ask-cursor` 是对 Cursor headless CLI（`%LOCALAPPDATA%/cursor-agent/agent.cmd`）的包装脚本，路径：`C:\Users\Surfa\bin\ask-cursor`。

**`--mode` 和 `--model` 是两个完全不同的参数，不可混用：**

| 参数 | 含义 | 示例 |
|------|------|------|
| **`--mode`** | 选「工作方式」—— Agent **能做什么**（只读 / 计划 / 可写） | `--mode ask` |
| **`--model`** | 选「底层模型」—— **哪个 AI** 来回答 | `--model composer-2.5-fast` |

##### `--mode`：选「工作方式」

| 模式 | 能否读文件 | 能否写文档/改代码 | 典型用途 |
|------|-----------|------------------|---------|
| **`ask`** | ✅ | ❌ **只读，不能写** | 代码审查、问答、理解文档 |
| **`plan`** | ✅ | ⚠️ 先出计划，人工批准后才写 | 先设计再动手 |
| **`agent`** | ✅ | ✅ **可写** | 改代码、写文档、落盘 |

> ⚠️ **`agent` 不是 `agent.cmd` 的真实选项**。底层只接受 `--mode ask` 和 `--mode plan`。wrapper `ask-cursor` 对 `--mode agent` 做了两层修复：
> 1. 映射为 `--mode ask`（内部 know this）
> 2. **关键：在 `--yolo` 后加 `--` 分隔符**，使 `--model` 等选项能正确路由到 Cursor CLI
>
> 实测验证（2026-05-21）：不加 `--` 时 `--model` 被当作 prompt 位置参数传入 AI，导致报错；加 `--` 后写入文件成功。

**默认行为**：`ask-cursor` 未指定 `--mode` 时，默认 **`ask`（只读）**。因此若 prompt 要求「把结果写入某 md 文件」，Cursor 会拒绝落盘，只在 stdout 输出内容并提示「当前为 Ask 模式，无法写入文件；请切换到 Agent 模式」——这是预期行为，不是故障。

##### 选用规则（调度 Cursor 前先看任务类型）

| 任务类型 | 应用模式 | 命令示例 |
|---------|---------|---------|
| 只 review、不改仓库 | `ask` | `cat a.py \| ask-cursor --prompt "审查代码"` |
| 要 Cursor **自己写入**评审/文档 | **`agent`** | `ask-cursor --mode agent --timeout 120 "读 REVIEW_cursor.md，把评审结果写入该文档"` |
| 先规划再执行 | `plan` | `ask-cursor --mode plan "设计 M1 重构方案"` |
| review 结果要落盘，但不想让 Cursor 写权限 | `ask` + Hermes 写文件 | Cursor 只输出 stdout → Hermes 用 `write_file` / `edit` 落盘 |

##### 常见组合示例

```bash
# 只 review，不写文件（默认 ask，适合双 CLI Step 2）
cat utils.py test_utils.py | ask-cursor --prompt "审查代码质量"

# 显式只读 review
ask-cursor --mode ask --prompt "总结 M1_ARCHITECTURE.md 的可理解性问题"

# 让 Cursor 读指令并写入评审文档（必须 agent）
cd /c/yifeGDBOT
ask-cursor --mode agent --timeout 300 \
  "请读 docs/guandan-brain/REVIEW_cursor.md，按要求评审，把结果写入该文档的「评审结果」区域"

# 同时指定模式与模型
ask-cursor --mode agent --model composer-2.5-fast --timeout 300 "实现 XX 并写入文件"
```

##### 与 opencode 的分工（推荐）

|| 场景 | 用谁 | `--mode` |
|------|------|----------|
| 写代码 / 写测试 | `ask-cursor` | **`agent`** |
| 轻量代码辅助（脚本、patch、验证） | `opencode run` | — |
| 只读 review | `opencode run` | — |

**踩坑记录（2026-05-21）**：
1. Kanban 评审任务要求 Cursor 写入 `REVIEW_cursor.md`，但调用未加 `--mode agent`，默认 `ask` 导致 Cursor 只输出评审正文到 stdout、无法落盘 → **已修复**：wrapper 已映射 `--mode agent` → `ask`
2. **根本原因**：`--yolo` 后缺少 `--` 分隔符，导致 `--model` 等选项被当作 prompt 位置参数传给 AI，写入功能静默失败 → **已修复**：wrapper 在 `--yolo` 后加 `--`
3. 正确命令：`ask-cursor --mode agent --timeout 300 "请读 X，写入 Y.md"`（wrapper 自动处理 `--` 分隔）

### 方案 C：cursor-agent Fallback（备选）

**原理**：使用 Cursor 的 headless CLI `cursor-agent -p` 执行任务。

**配置**：
```
# cursor-agent 路径
C:\Users\Surfa\AppData\Local\cursor-agent\cursor-agent.cmd
```

**用法**：
```bash
cursor-agent -p "实现 XX 功能" --model claude-sonnet-4
```

**状态**：⚠️ 未测试
- cursor-agent 版本 2026.04.17
- 需要 CURSOR_API_KEY 或 `cursor-agent login`

## 与 TASKS.md 衔接

`TASKS.md` 是项目级任务清单，`AGENT_HUB.md` 是 Agent 协作配置。

- `TASKS.md` 中的每个任务对应一个 Kanban 任务
- 创建 Kanban 任务时，在 body 中引用 `TASKS.md` 的任务 ID
- 验收通过后，更新 `TASKS.md` 状态

## 接下来要做的（2026-05-21 更新）

### 1. ~~立即停止 respawn 循环~~ ✅ 已解决
见上方「方案 A」根因分析。改用方案 B（opencode run）后链路稳定。

### 2. ~~Worker profile 改回稳定 provider~~ ✅ 已解决
`opencode-eng` profile 已切换到 `openrouter` + `deepseek/deepseek-v4-flash`，opencode run 验证通过。

### 3. ~~单独验证 Kanban 调度~~ ✅ 已解决
Kanban + opencode run 链路（任务 `t_87a0c932`，单 CLI）验证通过，119s 完成。

### 4. ~~双 CLI 协同验证（opencode + cursor）~~ ✅ 已解决
任务 `t_f1d0ca2f` 完整跑通三步工作流：opencode 执行 → cursor review → opencode 修复。详见上方「双 CLI 协同验证」。

### 5. 接下来：开始 GUA-022 实际工作
验证链路全部跑通，可以开始真正提升 M1 对 lalala 队胜率的工作。
见 `ISSUES.md` GUA-022 详情。

### 6. 其他已踩坑（一并记录）

- MiniMax CN：Base URL 必须用 `https://api.minimaxi.com/anthropic`，不要用 `/v1`（会 404/401）
- Hermes 向导写的密钥/base_url 在 `.env`，`config.yaml` 里 `model.api_key` 可能是旧残留，以 `.env` 为准

---

## 故障排除

### Worker 立即崩溃

```bash
# 检查 worker 日志
hermes kanban log <task_id>

# 常见原因：
# 1. ACP 桥接不兼容（最常见，2026-05-21）→ 0 tool calls 后 worker 退出，pid not alive
#    见上文「方案 A」与「接下来要做的」；切换到 opencode run 或原生 provider
# 2. opencode 命令被 Hermes shim 劫持 → 确认 opencode 指向正确路径
#    `which opencode` 应返回 C:\Users\Surfa\AppData\Roaming\npm\opencode.cmd
#    若指向 .local/bin/opencode（Hermes shim），需：
#    mv ~/.local/bin/opencode ~/.local/bin/opencode.hermes-shim
# 3. PATH 找不到 opencode → 在 .env 中设置绝对路径 + .cmd 扩展名
# 4. workspace 路径非绝对 → 使用 C:\yifeGDBOT 而非 C:yifeGDBOT
```

### 任务卡在 ready

```bash
# 检查 gateway 是否运行
hermes gateway status

# 手动触发 dispatch
hermes kanban nudge
```

### 任务 blocked

```bash
# 查看原因
hermes kanban show <task_id>

# 解除阻塞
hermes kanban unblock <task_id>
```

## 文件结构

```
C:\yifeGDBOT\
├── docs/
│   └── guandan-brain/
│       └── README.md          ← 项目说明
├── .hermes/
│   └── worktrees/             ← Kanban worker worktrees
│       └── t_xxxxx/           ← 每个任务一个 worktree
└── ...
```
