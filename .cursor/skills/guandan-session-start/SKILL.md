---
name: guandan-session-start
description: >-
  掼蛋 YiFeiAI-GD 新会话自启动：确认分支、读 ITERATIONS 最新一行与 ISSUES open P0、
  可选 wiki query，按固定格式 3 行汇报后等待派活。Use when starting a new chat,
  新 Agent, 首条消息, AGENT_FIRST_MESSAGE, 工作流 WF-01, or user says 自启动/当前任务.
---

# 掼蛋项目 · 会话自启动（WF-01）

## 步骤

1. 读 [`docs/guandan-brain/工作流.md`](../../docs/guandan-brain/工作流.md) §1（本 Skill 为其 executable 摘要）。
2. `git branch -vv` — V7 工作应在 `v7-dev`，M3 在 `m-dev`。
3. **必读原文件**（禁止仅用 Wiki）：
   - `docs/guandan-brain/ITERATIONS.md` — **最新一行**
   - `docs/guandan-brain/ISSUES.md` — **open + P0** 摘要
4. 可选：`python scripts/wiki.py query "V7 当前 P0"`（背景加速，不替代步骤 3）。
5. 用 **工作流 §2.1** 格式向用户汇报，然后**停止**，等派活。

## 产出格式

```text
分支：<branch> @ <短 hash>
当前迭代：<一行摘要>
open P0：<GUA 列表或「无」>
等你派：<一句>
```

## 禁止

- 未读 ITERATIONS 就改决策 / 组牌代码。
- 凭聊天历史假设上轮已完成的修复。

## 延伸阅读

- 完整工作流索引：[`docs/guandan-brain/工作流.md`](../../docs/guandan-brain/工作流.md)
- V7 环境深读：[`docs/guandan-brain/AGENT_BOOTSTRAP.md`](../../docs/guandan-brain/AGENT_BOOTSTRAP.md)
