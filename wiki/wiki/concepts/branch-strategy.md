---
type: concept
title: "分支策略（v7-dev / m-dev / main 隔离）"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
  - docs/guandan-brain/AGENT_PUSH_CHECKLIST.md
  - docs/guandan-brain/COMMANDER_NOTES.md
tags:
  - branch
  - governance
  - isolation
status: current
related_gua: []
date: 2026-06-17
---

# 分支策略

> 项目核心治理约束。AGENT_BOOTSTRAP 与 AGENT_PUSH_CHECKLIST 都强约束分支。

## 1. 分支角色

| 分支 | 角色 | 活跃度 | 备注 |
|---|---|---|---|
| `v7-dev` | V7 引擎主开发 | 高 | **当前主线** |
| `m-dev` | M 系列维护 | 中 | M1/M2/M3 仍在治理 |
| `main` | 已废弃 | 无 | — |

## 2. 隔离原则

- **代码隔离**：v7-dev 不可出现 `yf1_m3.py` / `yf2_m3.py` 之外混推
- **Commit 前缀**：见 [[agent-protocol]] §3
- **推送检查**：`scripts/hooks/pre_push_validate.py` 自动校验分支一致性

## 3. 切换流程

1. 确认当前任务归属（V7 迭代 → v7-dev；M 维护 → m-dev）
2. `git checkout <branch>`
3. `git pull --rebase`
4. 开新分支前缀遵循 Commit 前缀规范

## 4. 历史说明

- 2026-05-24（COMMANDER_NOTES 时代）：m-dev 是主线
- 2026-06-17（AGENT_BOOTSTRAP v7.1）：**v7-dev 成为主线**
- M 系列未消亡，仍有 m-dev 维护

详见 [[COMMANDER_NOTES-summary]]（outdated）与 [[AGENT_BOOTSTRAP-summary]]。

## 关联页面

- [[agent-protocol]]
- [[AGENT_BOOTSTRAP-summary]]
- wiki/entities/engine-v7.md
- wiki-minimax/entities/engine-m3.md
```

---
