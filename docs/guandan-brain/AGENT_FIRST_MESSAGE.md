# 新 Agent 首条消息（复制即用）

## 默认（通用）

```text
按 docs/guandan-brain/工作流.md WF-01 自启动：读 ITERATIONS 最新一行 + ISSUES 的 open P0，完成后汇报当前任务与分支，等我派活。
```

## 按场景

| 场景 | 首条消息 |
|------|----------|
| 换机 / handoff 接续 | `按工作流 WF-07 接续：读 handoff + ITERATIONS 最新一行，执行「下一步唯一动作」。` |
| 批跑 / 胜率分析 | `按工作流 WF-04：解读批跑数据；L2 日志用 Shell 列 logs/（§2.3 Step 4a），禁止 IDE Grep 报找不到。` |
| **yf 出牌 / 决策链路 / 败招** | `按工作流 WF-12：分析 yf 决策链路，格式见工作流 §2.6 与 workflows/WF-12-yf-decision-trace.md。` |
| **Botzone 对局 / 该压不压 / 牌型误判** | `按工作流 WF-13：分析 Botzone 平台对局适配层链路，格式见工作流 §2.7 与 workflows/WF-13-botzone-decision-trace.md。` |
| 改 V7/V8 引擎 / 组牌 | `按工作流 WF-02 + WF-05：先读 ISSUES（v7/v8）与 ITERATIONS，再动手。当前活跃分支 v8-dev（OpenGuanDan 新平台迁移）或 v7-dev（v1006 回退）。` |
| 提交 / 推送 | `按工作流 WF-08 + AGENT_PUSH_CHECKLIST 执行 commit/push。` |
| 组牌引擎单测 | `按工作流 WF-05：python scripts/checks/check_grouping_engine.py` |
