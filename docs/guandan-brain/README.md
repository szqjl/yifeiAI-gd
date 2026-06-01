# 掼蛋 AI 迭代大脑（项目真源）

> **新开 Agent？** 复制 **[`AGENT_FIRST_MESSAGE.md`](AGENT_FIRST_MESSAGE.md)** 里那句话，粘贴给新 Agent 作为第一句。  
> **提交 / 推送？** 复制 **[`AGENT_PUSH_CHECKLIST.md`](AGENT_PUSH_CHECKLIST.md)** 里默认第一句。

本目录与代码同仓，用于**可追溯**的缺陷、版本修复、评测与迭代焦点。通用知识库见 `docs/knowledge/`；**解读离线平台 `victoryNum` / 批跑台账**见 [`platform-data-interpretation.md`](../knowledge/platform-data-interpretation.md)；此处只记**本仓库版本—问题—验收**相关事实。

本目录在流程上即 **指挥系统**：负责 **规划、统筹、部署任务**（见 **[COMMAND_SYSTEM.md](COMMAND_SYSTEM.md)**）；**不**替代本机离线对局与真实 `game_records` 生成。

**当前指挥（本轮）**：**M3** = 主交付 + `IDecisionProvider` 底座；队胜率 KPI **只看 M3 批跑**（open 策略 tag=`m3`）——以 [`ITERATIONS.md`](ITERATIONS.md) **最后一行**为准。**P0 guard** → `m3_decision_engine`；组牌/牌力 → **V5+**。**M1 frozen**（`GUA-022` closed）。详见 [`ISSUES.md`](ISSUES.md)「引擎维护策略」。任务见 **[`TASKS.md`](TASKS.md)**；本机批跑见 **[`LOCAL_EVAL_CHECKLIST.md`](LOCAL_EVAL_CHECKLIST.md)**。

## 四角色概览

| 角色 | 职责 | 载体/工具 |
|------|------|----------|
| **Hermes（总协调）** | 定迭代、拆任务、审查验收、更新台账 | `ISSUES.md`、`ITERATIONS.md`、`TASKS.md`、`EVAL.md` |
| **Opencode（执行 AI-A）** | 认领任务、改代码、自动化验证 | 本终端 |
| **Cursor（执行 AI-B）** | 认领任务、改代码、自动化验证 | Cursor IDE |
| **人类（局主）** | 告诉 AI 去认领任务、本机跑离线对局 | 本机、批量脚本 |

详见 **[`COMMAND_SYSTEM.md`](COMMAND_SYSTEM.md)**。

**多 Agent 协作探索**（飞书失败、Agent Hub、OpenCastle、Hermes Kanban+ACP · 知乎素材 · 未跑通）：[`MULTI_AGENT_ORCHESTRATION.md`](MULTI_AGENT_ORCHESTRATION.md)

## 使用顺序（改代码或调参前）

1. 阅读 [`ISSUES.md`](ISSUES.md) 中 **open** 条目，确认本轮是否与之相关。
2. 阅读 [`ITERATIONS.md`](ITERATIONS.md) **最新一条**（或本轮正在写的草稿），确认本轮目标与完成定义。
3. 阅读 [`TASKS.md`](TASKS.md) 查看当前活跃任务，确认 Hermes 是否已拆好任务。
4. 阅读 [`EVAL.md`](EVAL.md) 中的评测入口与通过标准（含 **M3 批跑结果**）；改动后按该文档跑评测并更新 ITERATIONS。
5. 可选：在 [`scenarios/`](scenarios/) 中为复杂局面添加最小复现（YAML/JSON/Markdown 均可）。

## Agent 批跑数据入门（5 分钟）

新 Agent / 换机接续时，**解读批跑胜率、PASS、`game_records` 落盘**须先统一「局 vs 副」口径，再写 `ITERATIONS` / `EVAL`。Cursor 已自动加载 [`.cursor/rules/guandan-context.mdc`](../../.cursor/rules/guandan-context.mdc)（含批跑对照表与 `victoryNum` 自检）；以下为刻意阅读的推荐顺序。

### 阅读顺序

1. **[`guandan-context.mdc`](../../.cursor/rules/guandan-context.mdc)** — 「解读批跑…」整段（约 1 分钟）：什么字段数**局**、什么数**副**、`victoryNum` 怎么读。
2. **[`guandan-knowledge.mdc`](../../.cursor/rules/guandan-knowledge.mdc) §1** — 局 / 副 / 小局 / 整局 / `victoryNum` 完整定义（约 3 分钟）。
3. **改客户端或批跑脚本时** — [`guandan-platform-v1006.mdc`](../../.cursor/rules/guandan-platform-v1006.mdc) §局与副：`episodeOver` vs `gameOver`、协议字段。
4. **写 ITERATIONS / 分析报告时** — [`platform-data-interpretation.md`](../knowledge/platform-data-interpretation.md) §1～§3（详版真源，含 `--target-games 1` → 59 副实测）。

不必先读 PDF 或 `guandan-knowledge` §2～§8，除非任务涉及牌型、进贡或规则细节。

### 三句定音（背这个就够开工）

```text
副（小局）= episodeOver = game_records 每条 JSON
局（整局）= 2→A 双上过关；exe N / completed_games = N 局（≠ N 副）
victoryNum[0] vs [1] = 各队赢几局；须 [0]=[2]、[1]=[3]；批跑 N 局时 [0]+[1]=N
batch_games 真源=current_batch.json；本包 exe 会话固定 3 局；target-games 须 3 的倍数（3/9/12）；fallback 后看 server_vn_raw（§4.3.1）
```

关系：**局 ⊃ 多副**；**平台 1 局 ≠ 1 副**（实测 1 局可含数十副）。

### 按任务跳转

| 任务 | 必读 |
|------|------|
| 分析批跑胜率、填 ITERATIONS | `guandan-context` + `platform-data-interpretation` §3.3 |
| 改 `yf*_m*.py`、落盘逻辑 | `guandan-platform-v1006` + `platform-data-interpretation` §3.4 |
| 改 **M3** 决策 / 策略 | `ISSUES` open（tag=`m3`）、`ITERATIONS` 最新一行、[`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) 相关节、[`M3_DIAGNOSIS.md`](M3_DIAGNOSIS.md)；`guandan-knowledge` §1 + 相关规则节；**M1 frozen 不改策略** |
| 换机接续 | [分析接续-handoff](../governance/分析接续-handoff.md) + `ITERATIONS` 最新一行 |

### 30 秒自测

| 问题 | 答案 |
|------|------|
| `exe 3` 是 3 副还是 3 局？ | **3 局** |
| `game_records` 一条 JSON 是什么？ | **1 副**（小局） |
| 批跑 3 局、`[0,3,0,3]`（M3=0+2）谁赢？ | lalala **3 局**，M3 **0 局** |
| `[1,2,1,0]` 能用来算胜率吗？ | **不能**（同队 `[0]` 与 `[2]` 不一致） |
| `batch_games=1` 但 RAW `[3,0,3,0]`？ | **正常**（exe 固定 3 局）；台账用 fallback `[1,0,1,0]`，RAW 见 `server_vn_raw` |
| `--target-games` 应设多少？ | **3 的倍数**：**3 / 9 / 12**（勿用 10） |

Hermes 派活时可在任务块 **【依据】** 中写一句：「解读数据按本 README §Agent 批跑数据入门；胜率只看批末 `victoryNum[0]` vs `[1]`。」

## M 系列代际文档（M1 / M2 / M3）

| 文档 | 说明 |
|------|------|
| [M1_ARCHITECTURE.md](M1_ARCHITECTURE.md) | M1 架构与决策管线 |
| [M2_OPTIMIZATION.md](M2_OPTIMIZATION.md) | M2 优化日志、跑分记录、根因分析 |
| [M3_DIAGNOSIS.md](M3_DIAGNOSIS.md) | M3 完整诊断（22 副 0 胜根因、Bug 详析；**2026-05-30 GUA-027 场态消息重大发现**） |
| [../src/contracts/README.md](../../src/contracts/README.md) | M3 契约 `IDecisionProvider` **v1.0**（V 挂接门禁 ON） |
| [../src/m/README.md](../../src/m/README.md) | M 系列目录映射（渐进迁移） |

## 任务分派（Hermes → 执行 AI）

任务写入 **`TASKS.md`**（而非仅靠会话传递），每条任务包含以下块：

| 块 | 写什么 |
|----|--------|
| **【任务】** | 一句话：要达成什么；若对应某条 `GUA-xxx` 写明编号。 |
| **【范围】** | 允许改的目录/文件类型；**明确禁止项**（例如不做 yf1/yf2 双路由）。 |
| **【依据】** | 优先读的文档与条目（如 `ISSUES.md` 某行、`ITERATIONS` 某行）；与 [`PROMPT_FOR_DECISION_FIX.md`](PROMPT_FOR_DECISION_FIX.md) 冲突时**以 `ITERATIONS` 为准**。 |
| **【交付】** | 必须包含：**仓库内代码/配置改动** + 列出改动文件；评测按 [`LOCAL_EVAL_CHECKLIST.md`](LOCAL_EVAL_CHECKLIST.md) 或 `EVAL.md`；结果写回 **`ITERATIONS.md` 对应格**（及必要时 `ISSUES.md`）。 |
| **【完成定义】** | 可验收的一条或几条（局数、`game_id`、指标、不劣于哪条基线）。 |

**执行 AI 收到上述块后**：默认应**改代码**（若任务需要），而非仅改 `docs/`；若无法改代码须明确说明原因。

### 执行 AI → Hermes「一句话交接」（收工范式）

执行 AI 改完代码后必须在 `TASKS.md` 对应行填写**一句中文交接**。

**固定句式：**

> 已在 `<改动目录/文件>` 修复 `<问题/编号>`，并完成 `<自动化验证结论>`；请 Hermes 审查 diff 并验收，如需本机跑局请转人类按 `LOCAL_EVAL_CHECKLIST.md` 执行。

### 执行 AI 交接示例

> 已在 `src/decision/phase_handlers.py` 和 `src/decision/stage_router.py` 收紧 Opening 被动分支的非 PASS 兜底，`pytest tests/test_decision_gua022_gua014.py` 7 passed；请 Hermes 审查 diff 并验收，如需本机跑局请转人类按 `LOCAL_EVAL_CHECKLIST.md` 再跑 5 对局并回填 `game_records`。

## 维护约定（摘要）

- 缺陷编号：`GUA-001` 起，**永久不变**；关闭时注明 `closed_in`；复发新开一条并 `duplicate of GUA-xxx`。
- 根因标签（每条 Issue 至少选一个）：`rules`（规则/状态机）、`observation`（牌面/信息集/通信）、`policy`（选牌/策略/模型）。
- 每轮迭代优先解决 **Top 1～2** 条 Issue，并在 ITERATIONS 中写清「完成定义」与评测对比。

## 文档与评测：谁写什么、谁跑什么

| 内容 | 状态 | 谁来做 |
|------|------|--------|
| `ISSUES.md` / `ITERATIONS.md` / `EVAL.md` / `scenarios/` | 已在仓库中维护（含 M1 对照与 **GUA-020 / GUA-021 已关闭** 等记录） | 以 Git 文档为准，可持续改 |
| 离线批量对战、生成 **新** `game_records`、改代码后的回归 | **不能**在助手侧代替本机执行 | **须你本机执行** |

- **跑评测（通知）**：请你在本机按 **[本机评测清单](LOCAL_EVAL_CHECKLIST.md)** 操作；完成后把结果填入 **`ITERATIONS.md`**（并视情况更新 **`ISSUES.md`**）。  
- **当前开放缺陷**：以 **`ISSUES.md` 中 `open` 行** 为准（实时真源）；**指挥与任务流**见 **[COMMAND_SYSTEM.md](COMMAND_SYSTEM.md)**。

## 与本仓库的关系

当前仓库根路径（**主工作仓，以本机实际为准**）：`c:\yifeGDBOT`（掼蛋 AI 相关开发）；本目录为该项目专用台账，通过 Git 做版本对照。若在其他机器克隆，以该克隆的 Git 根目录为准，勿沿用旧路径 `D:\YiFeiAI-GD`。
