# YiFeiAI-GD · Agent 入口

> **工作流真源（步骤 / 产出格式 / Skill 索引）**：[`docs/guandan-brain/工作流.md`](docs/guandan-brain/工作流.md)  
> **新会话人类首句**：[`docs/guandan-brain/AGENT_FIRST_MESSAGE.md`](docs/guandan-brain/AGENT_FIRST_MESSAGE.md)  
> **V7 深读（环境/批跑/命令）**：[`docs/guandan-brain/AGENT_BOOTSTRAP.md`](docs/guandan-brain/AGENT_BOOTSTRAP.md)

新 Agent 默认执行 **工作流 WF-01**（读 ITERATIONS 最新一行 + ISSUES open P0 → 3 行汇报），无需人类重复项目背景。

---

## 项目一句

掼蛋 AI 客户端（南邮 v1006）；**改 AI 行为真源** = `docs/guandan-brain/`（ISSUES、ITERATIONS、EVAL）。当前活跃：**v7-dev**（V7/组牌）与 **m-dev**（M3 交付）；**M1 frozen**；队 KPI **只看 M3 批跑**。

---

## 用户偏好

- 简体中文；Agent **自动执行**终端命令（git/python/pytest 已 allowlist）。
- **仅明确要求时** commit / push → 工作流 **WF-08** + [`AGENT_PUSH_CHECKLIST.md`](docs/guandan-brain/AGENT_PUSH_CHECKLIST.md)。
- 改 M3/V7 决策或解读批跑前：读 ISSUES open + ITERATIONS 最新行（`.cursor/rules/guandan-context.mdc`）。
- 接续：「继续 / handoff / 按迭代」→ 工作流 **WF-07**。
- 脚本前先查 [`SCRIPT_INDEX.md`](docs/guandan-brain/SCRIPT_INDEX.md)；新脚本须登记索引。
- 知识检索：**Wiki 综合** → `python scripts/wiki.py query`；**实时**（ITERATIONS/ISSUES/handoff）→ 直接读原文件（工作流 **WF-09**）。
- 掼蛋规则：`.cursor/rules/guandan-knowledge.mdc`；回放不篡改真实流水。

---

## 数据口径（三句）

- **副** = `game_records` 每条 JSON；**局** = 平台整局 / `completed_games`；**局 ⊃ 多副**。
- 队胜看 **`victoryNum[0]` vs `[1]`**（0+2 一队，1+3 一队）；禁止四席相加。
- 批跑 `--target-games` 须 **3 的倍数**（3/9/12）；勿用 10。

---

## 项目 Skill（`.cursor/skills/`）

| 场景 | Skill |
|------|-------|
| 新会话 / 自启动 | `guandan-session-start` |
| 批跑 / 胜率分析 | `guandan-batch-eval` |
| 组牌引擎测试 | `guandan-grouping-engine` |
| handoff 接续 | `guandan-handoff-continue` |
| commit / push | `guandan-git-push` |

完整列表与待建 Skill：工作流 §7。

---

## Wiki 速查

| 实时（不走 Wiki） | Wiki 适合 |
|-------------------|-----------|
| ITERATIONS 最新、ISSUES 状态、handoff | GUA 释义、概念、模块关系、批跑约束 |

```bash
python scripts/wiki.py query "关键词"
```

改了 `docs/` 后按需：`python scripts/wiki.py ingest`
