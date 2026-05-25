# 多 Agent 协作探索笔记（知乎素材 · 未跑通）

> **状态**：调研与方案设计阶段，**尚未在本项目生产跑通**。跑通后补「实测章节」与截图/命令输出。  
> **用途**：为日后知乎文留素材；与 [`COMMAND_SYSTEM.md`](COMMAND_SYSTEM.md) 指挥分工对齐。  
> **记录时间**：2026-05-20

---

## 1. 我们要解决什么问题

掼蛋 AI 仓库采用四角色指挥（见 `COMMAND_SYSTEM.md`）：

| 角色 | 工具 | 职责 |
|------|------|------|
| Hermes | Claude 网页/API 或 **NousResearch Hermes Agent** | 定迭代、拆任务、验收、台账 |
| Opencode | 本机终端 AI | 执行、改代码、pytest |
| Cursor | Cursor IDE | 执行、改代码、pytest |
| 人类 | 本机 | 离线跑局、回填 `game_records` |

**痛点**：`TASKS.md` 是单向任务板，不是「像群一样讨论」；人类还要在中间转发「去认领」。  
**目标**：Hermes / Opencode / Cursor 能围绕同一 GUA 话题讨论、派活、交接，讨论结论再沉淀到 `TASKS.md` / `ITERATIONS.md`。

---

## 2. 飞书群为什么失败（已实测）

本仓曾用 `scripts/lark/` + `lark-cli event consume` 在飞书群测 `@Hermes-tencent` → `@opencode`。  
事件样例见 `.opencode/bot/events/*.json`。

| 现象 | 根因 |
|------|------|
| 人类 `@opencode` 能收到 webhook | 用户 @ 机器人会推 `im.message.receive_v1` |
| 机器人 `@` 机器人无反应 | **飞书/Lark 通常不把 bot→bot @ 推送给对方 webhook** |
| Cursor 无法进群 | IDE Agent **无飞书 Bot 身份**，不能常驻收群消息 |
| Hermes 只能发 API 教程让 Opencode 手动回 | 已是 workaround，不是群聊 |

**结论**：飞书群 = 给人用的 IM；多 Agent 需要 **消息总线** 或 **Kanban 协作层**，不是 IM 群。

飞书可保留为 **人类只读镜像**（Hub/Kanban → 飞书单向推送），不要当 Agent 总线。

---

## 3. 方案 A：本机 Agent Hub（自建）

**适用**：三 Agent 都在本机；不需要 ngrok/nginx。

```
Hermes / Opencode / Cursor  →  http://127.0.0.1:8787  (Agent Hub)
持久化：.agent-hub/messages.jsonl
```

| API | 用途 |
|-----|------|
| `POST /messages` | 发消息（含 `@hermes` `@cursor` `@opencode`） |
| `GET /messages?thread=GUA-022` | 拉历史 |
| `GET /messages/stream` | SSE 实时 |
| `POST /threads/{id}/resolve` | Hermes 标记讨论结束 |

**与台账关系**：

- **讨论层**：Agent Hub thread（如 `GUA-022`）
- **派工结论**：`TASKS.md`
- **验收闭环**：`ITERATIONS.md` / `ISSUES.md`

**防失控规则**：仅 `@` 触发回复；单 thread 最大自动轮次；Hermes 才能 `resolve`。

**Hermes 搭建任务书**：见本文档附录 A（可直接复制给 Hermes 执行）。

**知乎角度**：「为什么 IM 群做不了 AI 团队站会」「最小 Agent Hub 长什么样」。

---

## 4. 方案 B：OpenCastle（成熟框架 · 未在本仓试用）

- 仓库：[monkilabs/opencastle](https://github.com/monkilabs/opencastle) · MIT · `npx opencastle init`
- 官网称 Free / 开源；**模型与 IDE 订阅费用另算**

**官方支持的 IDE adapter（7 个）**：Copilot、**Cursor**、Claude Code、**OpenCode**、Windsurf、Codex CLI、Antigravity。

| 问题 | 答案 |
|------|------|
| 是否收费 | 框架本身免费 MIT；无 OpenCastle SaaS 订阅 |
| 是否支持 Hermes（我们文档里的协调角色） | **无**；对应物是 **Team Lead** 编排器，需定制读 `guandan-brain` |
| 是否支持 OpenClaw | **不支持**（OpenClaw 是另一产品 openclaw.ai） |
| 是否支持 OpenCode | **支持** |
| 是否像群聊 | **不像**；是 Team Lead 派工 + Quality Gate 流水线 |

**与 Agent Hub 对比**：OpenCastle 偏「项目经理 + 专家并行」；Agent Hub 偏「讨论串 + 人工/Kanban 收敛」。

**知乎角度**：「OpenCastle 免费但救不了三客户端自由讨论」「Team Lead ≠ 你的 Hermes 台账中枢」。

---

## 5. 方案 C：NousResearch Hermes Agent + Kanban + ACP（重点）

若 Hermes 指 [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)（非泛称），则 Kanban 是官方多 Agent 协作 primitives。

- 文档：[Kanban](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban) · [ACP](https://hermes-agent.nousresearch.com/docs/user-guide/features/acp)
- 看板 DB：`~/.hermes/kanban.db`（ durable，可 comment / unblock / 跨进程）

### 5.1 关键架构（必读）

**Cursor 不是 Kanban 的原生 worker。**

Kanban dispatcher **永远 spawn 完整 Hermes 子进程**（必须有 `kanban_show` / `kanban_complete` / `kanban_comment` 等工具）。  
不能把任务直接丢给 Cursor IDE 或裸 `cursor-agent` 进程——它们没有 kanban 工具。

```
Kanban 任务
  → dispatcher 启动 hermes -p <profile> -q "work kanban task …"
  → 该 worker 的 LLM 后端可以是：
       (1) Hermes 自带 provider
       (2) copilot-acp → 外部 ACP（Cursor / Copilot CLI / 等）
```

维护者说明：[Issue #18629](https://github.com/NousResearch/hermes-agent/issues/18629)（已 close，给出 copilot-acp 变通方案）。

### 5.2 `-w` / `--worktree`

CLI 的 `-w` 是 **git worktree 隔离**，不是「worker 模式」：

```bash
hermes chat --worktree -q "Review this repo"
```

Kanban 编码任务常用：

```bash
hermes kanban create "…" --assignee backend-eng --workspace worktree
```

### 5.3 方案 C1：Cursor 通过 ACP 当执行后端（需 CLI 支持 `agent acp` 子命令）

> **2026-05-20 实测备注**：Cursor **IDE 版本**（如 3.4.20）与 **CLI 构建号**（如 `2026.04.17-479fd04`）不是同一套数字。  
> Hermes 文档里常见的 `--acp --stdio` 是 **Copilot CLI 的 flag**；Cursor **没有** `--acp` 参数，较新 CLI 提供的是 **`agent acp` 子命令**（不是 flag）。  
> 若 `agent acp --help` 报错或不存在 → **不要硬走 C1**，改用 §5.4 print 模式。

#### 先自检（Windows / 本机）

```powershell
agent --version          # CLI 构建号，不是 IDE 3.4.x
agent --help             # 看 Commands 列表里有没有 acp
agent acp --help         # 有则 ACP 可用；无则当前 CLI 不支持
agent update             # 尝试升级 CLI（与 IDE 版本可能不同步）
```

本机较新 CLI（`2026.04.17`）示例输出：

```text
Commands:
  ...
  agent [prompt...]      # 嵌套子命令，易与顶层 agent 混淆
  ...

agent acp --help  →  "Start the Cursor Agent as an ACP server"
```

**没有 `agent acp` 时**（如 IDE 3.4.20 捆绑的旧 CLI）：C1 不可用；优先 **§5.4 `agent -p`** 或 **`agent update` 后再测**。

Cursor 官方 ACP 文档：[cursor.com/docs/cli/acp](https://cursor.com/docs/cli/acp)

```bash
# 正确：子命令（不是 agent --acp）
agent acp
agent --api-key "$CURSOR_API_KEY" acp
```

**与 Copilot / Hermes 文档的差异**：

| 产品 | 启动 ACP 的方式 |
|------|----------------|
| GitHub Copilot CLI | `copilot --acp --stdio` |
| Cursor CLI（新版） | `agent acp`（子命令，help 里通常无 `--stdio`） |
| Hermes `copilot-acp` provider | 通过 `HERMES_COPILOT_ACP_COMMAND` + `HERMES_COPILOT_ACP_ARGS` 拼命令 |

**Profile 示例**（变通：借用 `copilot-acp` provider；**仅当 `agent acp` 存在时**）：

```yaml
# ~/.hermes/profiles/cursor-coder/config.yaml
model:
  provider: copilot-acp
  model: composer-2
```

```bash
# 环境变量 — ARGS 是子命令名 acp，不是 --acp --stdio
HERMES_COPILOT_ACP_COMMAND=agent
HERMES_COPILOT_ACP_ARGS=acp
CURSOR_API_KEY=...
```

**派活**：

```bash
hermes gateway start
hermes kanban create "修复 GUA-022 …" \
  --assignee cursor-coder \
  --workspace worktree:feat/gua-022 \
  --body "读 docs/guandan-brain/TASKS.md；pytest tests/test_decision_gua022_gua014.py"
hermes kanban watch
```

**已知限制**：

- `copilot-acp` 命名/行为偏 Copilot，指 Cursor 是 **非正式路径**：[Issue #16282](https://github.com/NousResearch/hermes-agent/issues/16282) 仍 open
- **CLI 版本门槛**：无 `agent acp` 则 C1 不成立（IDE 3.4.20 用户反馈）
- 需验证 worker 日志，防止 ACP 失败时 Hermes **fallback 自己写 shell**（社区踩坑：[Issue #15300](https://github.com/NousResearch/hermes-agent/issues/15300)）

### 5.4 方案 C2：Cursor print 模式（**IDE 3.4.20 / 无 `agent acp` 时的首选**）

Cursor **没有** `--acp` flag；print 模式用 **`-p` / `--print`**，与 ACP 是两条路。

```powershell
# 本机 Kanban worker 或 Hermes orchestrator 内调用
agent -p --trust --workspace "c:\yifeGDBOT" `
  --output-format json `
  "读 docs/guandan-brain/TASKS.md，说明当前 Top GUA"
```

常用 flag（`agent --help`）：

| Flag | 用途 |
|------|------|
| `-p` / `--print` | 非交互，脚本/自动化 |
| `--trust` | headless 下信任工作区（仅配合 `--print`） |
| `--workspace <path>` | 指定仓库根 |
| `-w` / `--worktree` | 隔离 worktree（与 Hermes Kanban `--workspace worktree` 可配合） |
| `--output-format json` | 结构化输出，便于 Hermes 解析 |
| `--force` / `--yolo` | 少打断自动批准命令 |

Hermes worker 内用 `terminal()` / skill 调上述命令 → 解析输出 → `kanban_complete` / `kanban_comment`。

- 优点：**不依赖 ACP**；3.4.20 类 CLI 通常有 `-p`  
- 缺点：无 ACP 流式/permission 协议；Kanban 集成需自己写一层

**可选**：社区 [cursor-acp-bridge](https://www.npmjs.com/package/cursor-acp-bridge) 在 Cursor 未内置 ACP 时做桥接（未在本项目验证）。

### 5.5 Opencode 接入 Kanban

Hermes CLI 有 `opencode-zen` / `opencode-go` provider；或另建 profile + ACP（若 OpenCode CLI 支持 ACP）。  
Convoy/OpenCastle 侧则直接有 `opencode` adapter。

### 5.6 Kanban vs `delegate_task`

| | `delegate_task` | Kanban |
|--|-----------------|--------|
| 形态 | RPC，父进程阻塞 |  durable 队列 + 状态机 |
| 身份 | 匿名 subagent | 命名 profile + 持久记忆 |
| 人类介入 | 弱 | comment / unblock |
| 审计 | 易随 context 丢失 | SQLite 永久行 |

**知乎角度**：「Kanban 不是群聊，但 comment 线程比飞书 bot 互 @ 可靠」「为什么 Cursor 必须套一层 Hermes worker」。

---

## 6. 业界其他成熟方案（简述）

| 类别 | 代表 | 和本项目的距离 |
|------|------|----------------|
| 通用编排 | LangGraph、CrewAI、Microsoft Agent Framework | 要把三客户端收编进同一框架 |
| 编程助手编排 | OpenCastle | 见方案 B |
| Claude 生态 | Claude Code Agent Teams | 仅 Claude Code 互聊，Cursor 进不来 |
| 协议 | Google A2A + MCP | A2A=Agent 对 Agent；MCP=Agent 对工具 |
| 基础设施 | Dapr Agents、Conductor | 过重 |

**结论**：没有开箱「Hermes + Opencode + Cursor + guandan-brain 台账」一体包；需组合 **Kanban/Hub + Git 真源**。

---

## 7. 推荐路线（本机三 Agent）

| 阶段 | 做什么 |
|------|--------|
| P0 | 保持 `TASKS.md` + Git 真源不变 |
| P1 | Hermes 搭 **Agent Hub**（8787）或直接用 **Hermes Kanban**（若已装 hermes-agent） |
| P2 | Cursor：有 `agent acp` → C1 profile；**无则 `agent -p`（C2）**；Opencode：独立 profile |
| P3 | 飞书仅 mirror；OpenCastle 可选评估，不替代台账 |

---

## 8. 跑通后知乎文大纲（待填实测）

1. **引子**：我想让三个 AI 像群一样讨论掼蛋 bug，飞书群失败了  
2. **误区**：IM 群 ≠ Agent 总线；bot @ bot 的平台限制  
3. **架构图**：Hub-and-Spoke vs Kanban dispatcher vs OpenCastle Team Lead  
4. **Hands-on**：Agent Hub 最小实现 / Hermes Kanban + Cursor ACP profile  
5. **踩坑**：copilot-acp 借道 Cursor、ACP 失败 fallback、`-w` 不是 worker  
6. **与「真源文档」结合**：讨论在 Hub/Kanban，结论在 TASKS.md  
7. **成本**：框架免费，token 不免费  
8. **展望**：A2A 标准化、Hermes `cursor-acp` 一等公民

---

## 附录 A：Hermes 搭建 Agent Hub 提示词

（2026-05-20 定稿，执行状态：待 Hermes 认领）

```markdown
# 任务：在本机搭建 Agent Hub（三 Agent 讨论总线）

仓库：c:\yifeGDBOT
背景：飞书群不可行；三 Agent 全本机，用 127.0.0.1:8787，不用 ngrok。
技术：Python FastAPI + uvicorn；.agent-hub/messages.jsonl
交付：agent_hub/、scripts/agent-hub/、docs/guandan-brain/AGENT_HUB.md
完成定义：health 通；@hermes 能自动回；resolve 后停回复；不破坏 src/
```

（完整版提示词见对话记录 2026-05-20，或让 Hermes 读本文件 §3 + 附录 A 摘要后展开。）

---

## 附录 B：Hermes 配置 Cursor 为 Kanban ACP 后端

```markdown
1. agent --version（注意是 CLI 构建号，不是 IDE 3.4.x）
2. agent acp --help — 有则 C1；无则改 C2（agent -p --trust --workspace …）
3. 若需 C1：建 profile cursor-coder，provider copilot-acp，ARGS=acp（不是 --acp --stdio）
4. hermes gateway start → 测试任务 → kanban watch
5. 文档化 + 与 TASKS.md 衔接
```

---

## 附录 C：参考链接

- Hermes Kanban：https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban  
- Hermes ACP：https://hermes-agent.nousresearch.com/docs/user-guide/features/acp  
- Kanban + ACP 第三方后端：https://github.com/NousResearch/hermes-agent/issues/18629  
- Cursor 作 ACP harness：https://github.com/NousResearch/hermes-agent/issues/16282  
- Cursor ACP 文档：https://cursor.com/docs/cli/acp  
- OpenCastle：https://github.com/monkilabs/opencastle  
- Cursor Cloud Agents API：https://cursor.com/docs/cloud-agent/api/endpoints  

---

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-05-20 | 初稿：飞书失败、Agent Hub、OpenCastle 调研、Hermes Kanban+ACP 架构 |
| 2026-05-20 | 补充：Cursor IDE 3.4.20 无 `--acp`；ACP 为 `agent acp` 子命令（视 CLI 构建号）；无则走 `agent -p` |
