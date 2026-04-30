# 指挥系统（大脑职责说明）

本目录 **`docs/guandan-brain/`** 在流程上承担 **规划、统筹、部署**——即「指挥系统」：不替代你写每一行代码或替你点离线 exe，但负责 **定目标、定口径、定顺序、验收与归档**。

## 三层分工

| 层级 | 做什么 | 产出 / 载体 |
|------|--------|----------------|
| **指挥（大脑）** | 从开放缺陷里选 Top 1～2；写清完成定义与评测口径；下发给执行层 | `ISSUES.md`、`ITERATIONS.md`、`EVAL.md`、`scenarios/`、`PROMPT_FOR_DECISION_FIX.md` 等 |
| **执行（本机 + 人 + 执行 AI）** | 改 `src/`、跑批量对战、生成 `game_records/`、跑训练脚本 | 代码、对局文件、日志 |
| **验收（大脑闭环）** | 对照 `EVAL.md` 统计口径，把数字写回 `ITERATIONS.md`，关/开 `ISSUES` | 台账更新、Git 提交 |

## 标准一轮（可重复）

1. **盘点**：`ISSUES.md` 里 **open** 的 `GUA-xxx`。  
2. **定迭代**：在 `ITERATIONS.md` 追加一行——目标 GUA、完成定义、评测命令/路径。  
3. **部署任务**：把 [`PROMPT_FOR_DECISION_FIX.md`](PROMPT_FOR_DECISION_FIX.md) 与**自写说明**发给「执行 AI」；**自写说明须按 [`README.md`](README.md) 中「大脑下发指令（交接规范）」模板写全**（任务 / 范围 / 依据 / 交付 / 完成定义），**勿仅粘贴 `ITERATIONS` 表格一行**——否则执行层易只做文档、不落代码。本机事项见 [`LOCAL_EVAL_CHECKLIST.md`](LOCAL_EVAL_CHECKLIST.md)。  
4. **收结果**：新 `game_records` 或日志就绪后，更新 **评测结果摘要**；达标则 **closed** + `closed_in`。  
5. **下轮唯一 priority**：写在同一行表格末列，避免并行多主线失焦。

## 与 Cursor / 助手的关系

- **助手默认角色**：在对话中遵循本目录台账，**优先引用 `ISSUES` / `ITERATIONS` / `EVAL`**，不编造未发生的评测数字。  
- **用户指令**：可明确要求「按大脑当前 open 项规划下一轮」或「把结果写入 ITERATIONS」——即 **指挥系统 + 执行层** 的协作方式。

## 当前开放缺陷（以 `ISSUES.md` 为准）

以仓库内 **`ISSUES.md` 表格 `open` 行** 为实时真源；若与本文件列举不一致，**以 `ISSUES.md` 为准**。

---

**一句话**：**大脑 = 台账 + 口径 + 迭代顺序**；**手与机器 = 执行**；**跑完局 = 把数字写回大脑**。
