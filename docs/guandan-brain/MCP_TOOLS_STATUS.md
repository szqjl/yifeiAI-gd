# MCP 工具状态（MCP Tools Status）

> **新 Agent 必须读**：[`AGENT_BOOTSTRAP.md`](./AGENT_BOOTSTRAP.md) §1～§3.5  
> 现状：**`codebase-memory-mcp` 不可用**；本文件登记生效的 MCP 与回退路径。

## 1. 现状快照

| MCP 服务器 | 状态 | 备注 |
|---|---|---|
| `codebase-memory-mcp` | **不可用** | 服务器未挂载；所有 MCP 工具调用立即 `unsupported call`。不得假定其能力。 |
| `lark-*`（lark-approval / lark-attendance / lark-base / …） | 可用 | 飞书审批/考勤/云文档/日历/通讯录/邮件/妙记等。 |
| `codex_app_*`（navigate_to_codex_page / read_thread_terminal / load_workspace_dependencies） | 可用 | Codex 桌面应用桥。 |
| `automation_update` | 可用（按需） | Codex 桌面自动化。 |

## 2. 回退路径（`codebase-memory-mcp` 缺失时）

按 `AGENTS.md` 优先级 1→5 的"反序"——MCP 全断则用底层文件命令：

| 用途 | MCP 原工具 | 回退方案 |
|---|---|---|
| 找函数/类/路由定义 | `search_graph` / `search_code` | `rg <pattern>` 在仓库根（PowerShell 慎用 `*` wildcard；用 `git grep -l` 防扫 `.git`/`node_modules`）。 |
| 读源码上下文 | `get_code_snippet(qualified_name=...)` | `git show HEAD:path/to/file.py` 或 `Get-Content -LiteralPath`（`select -Skip … -First N`）。 |
| 调用关系/依赖 | `trace_path` | `rg -n 'def foo\\|class foo\\|-> foo'` + 手画调用链。 |
| 复杂 Cypher/统计 | `query_graph` | 直接 parse Python AST（`ast.parse(open(path).read())`） + `python -c ...`。 |
| 项目结构概览 | `get_architecture` | `Get-ChildItem -Recurse -Depth 1` + 读 `docs/guandan-brain/`。 |

## 3. 验证 MCP 不可用的最小操作

遇到疑似 MCP 工具调用时，先发一条最小调用探活；返回 `unsupported call` 即视为不可用：

```text
mcp__codebase_memory_mcp__list_projects   → unsupported call: ...
```

一旦确认不可用，全程走 §2 回退路径；**不要重试**以免污染会话 token。

## 4. 维护

- 本文件状态会随 MCP 服务器挂载变化而变化；当 harness 把 `codebase-memory-mcp` 重新挂上后，把 §1 中"不可用"改为"可用"并在 §2 标记为"非 fallback"。
- 任何 Agent 发现新的可用 MCP 服务器时，在 §1 表格追加一行并注明工具前缀。

## 5. 与其他文档的关系

- 与 `AGENT_BOOTSTRAP.md` §3.5「快速查上下文（LLM Wiki）」互补：Wiki 是**项目知识**缓存，MCP 是**会话工具**分发层。
- 与 `AGENTS.md`（动态注入的 Knowledge Graph 段落）对应：本文件是仓库**真源**，动态注入段落若与本文件冲突，以本文件为准。
