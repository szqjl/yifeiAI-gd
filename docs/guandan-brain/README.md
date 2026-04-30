# 掼蛋 AI 迭代大脑（项目真源）

本目录与代码同仓，用于**可追溯**的缺陷、版本修复、评测与迭代焦点。通用知识库见 `docs/knowledge/`；此处只记**本仓库版本—问题—验收**相关事实。

本目录在流程上即 **指挥系统**：负责 **规划、统筹、部署任务**（见 **[COMMAND_SYSTEM.md](COMMAND_SYSTEM.md)**）；**不**替代本机离线对局与真实 `game_records` 生成。

**当前指挥（本轮）**：主目标 **GUA-022**（M1 对 lalala 队胜率），联动 **GUA-014** ——以 [`ITERATIONS.md`](ITERATIONS.md) **记录表最后一行**为准。共用层代码已落地；**离线跑局与 `victoryNum`/PASS 统计须本机**（见 [`LOCAL_EVAL_CHECKLIST.md`](LOCAL_EVAL_CHECKLIST.md)），填回 **ITERATIONS** 后闭环。

## 使用顺序（改代码或调参前）

1. 阅读 [`ISSUES.md`](ISSUES.md) 中 **open** 条目，确认本轮是否与之相关。
2. 阅读 [`ITERATIONS.md`](ITERATIONS.md) **最新一条**（或本轮正在写的草稿），确认本轮目标与完成定义。
3. 阅读 [`EVAL.md`](EVAL.md) 中的评测入口与通过标准（含 **M1 yf1/yf2 已测结果表**）；改动后按该文档跑评测并更新 ITERATIONS。
4. 可选：在 [`scenarios/`](scenarios/) 中为复杂局面添加最小复现（YAML/JSON/Markdown 均可）。

## 大脑下发指令（交接规范）

[`ITERATIONS.md`](ITERATIONS.md) **表格最后一行**是**迭代契约**（目标 GUA、完成定义、约束），**不是**给执行层的完整施工单。若只把这一行复制给「执行 AI」而不说明**必须改代码**，对方容易只做文档对齐而**不写代码**。

**指挥方（人 / 任一助手）在部署任务时**，应**额外**给出下面这一段**自包含**文字（可复制粘贴），路径写仓库内相对路径（如 `src/decision/`、`docs/guandan-brain/...`），动词写死（如「修改」「实现」「禁止」）。

| 块 | 写什么 |
|----|--------|
| **【任务】** | 一句话：要达成什么；若对应某条 `GUA-xxx` 写明编号。 |
| **【范围】** | 允许改的目录/文件类型；**明确禁止项**（例如不做 yf1/yf2 双路由）。 |
| **【依据】** | 优先读的文档与条目（如 `ISSUES.md` 某行、`ITERATIONS` 某行）；与 [`PROMPT_FOR_DECISION_FIX.md`](PROMPT_FOR_DECISION_FIX.md) 冲突时**以 `ITERATIONS` 为准**。 |
| **【交付】** | 必须包含：**仓库内代码/配置改动** + 列出改动文件；评测按 [`LOCAL_EVAL_CHECKLIST.md`](LOCAL_EVAL_CHECKLIST.md) 或 `EVAL.md`；结果写回 **`ITERATIONS.md` 对应格**（及必要时 `ISSUES.md`）。 |
| **【完成定义】** | 可验收的一条或几条（局数、`game_id`、指标、不劣于哪条基线）。 |

**执行 AI 收到上述块后**：默认应**改代码**（若任务需要），而非仅改 `docs/`；若无法改代码须明确说明原因。

### 执行 AI → 指挥官「一句话交接」（收工范式）

每轮**在仓库内改完代码**后，执行 AI 必须给出**一句中文交接**，且直接可转发给指挥官；后续 AI 应**严格沿用本句式**，不要只给长段落。

**固定句式（必须包含两段，中间用分号连接）：**

- **前半句（我做了什么）**：已改哪些目录/文件、解决了什么问题、最好带验证结论。  
- **后半句（请指挥官做什么）**：指挥官需在本机执行的动作（离线跑局、统计指标、回填文档），并指向 [`LOCAL_EVAL_CHECKLIST.md`](LOCAL_EVAL_CHECKLIST.md) 或 `EVAL.md`。

**推荐可直接复用模板（其他 AI 看到即可照抄）：**

> 已在 `<改动目录/文件>` 修复 `<问题/编号>`，并完成 `<本机或自动化验证结论>`；请指挥官按 `LOCAL_EVAL_CHECKLIST.md` 再跑 `<约定局数/场景>`，统计 `<victoryNum/PASS/近似问题 PASS 等指标>` 并回填 `ITERATIONS.md`（必要时更新 `ISSUES.md`）。

**本轮示例（真实可用）：**

> 已在 `batch_executor` 与 `src/communication` 修复批跑回传卡住、状态台账对不上及 `client4`/记录补写异常，并通过本机回归验证 `--target-games 3` 与 `6` 均可正常结束且 `execution_state.json` 达到 `target_games==completed_games`；请指挥官按 `LOCAL_EVAL_CHECKLIST.md` 再跑一轮约定局数并将 `victoryNum`/PASS 统计回填 `ITERATIONS.md`（必要时更新 `ISSUES.md`）。

指挥官可把该句复制到会话顶或 IM，作为「本轮交付 + 待验收」的**唯一摘要行**。

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

当前仓库根路径：`D:\YiFeiAI-GD`，即掼蛋 AI 相关开发的**主工作仓**；本目录为该项目专用台账，通过 Git 做版本对照。
