# KANBAN.md — yifeGDBOT 看板使用指南

## 快速参考

```bash
# 创建任务
hermes kanban create "任务标题" --assignee opencode-eng --workspace worktree

# 查看看板
hermes kanban list

# 实时监控
hermes kanban watch

# 验收
hermes kanban complete <task_id>
```

## 任务状态流转

```
triage → todo → ready → running → done
                   ↓
                 blocked → ready（解除阻塞后）
```

## Worker 方案

| 方案 | 状态 | 说明 |
|------|------|------|
| ACP (opencode acp) | ⚠️ 实验中 | 协议兼容性问题待解决 |
| opencode run | ✅ 可用 | 通过 terminal 调用，稳定 |
| cursor-agent -p | ⚠️ 未测试 | 需要 CURSOR_API_KEY |

## 详细文档

见 `docs/guandan-brain/AGENT_HUB.md`
