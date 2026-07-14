---
type: source-summary
title: "Agent 提交推送检查清单摘要（AGENT_PUSH_CHECKLIST.md）"
sources:
  - docs/guandan-brain/AGENT_PUSH_CHECKLIST.md
tags:
  - checklist
  - push
  - git
  - agent-protocol
status: current
related_gua: []
date: 2026-06-17
---

# Agent 提交推送检查清单摘要

> 与 `AGENT_BOOTSTRAP.md` 分工：**BOOTSTRAP = 新会话第一站**，**PUSH_CHECKLIST = 提交推送前必检**。
> 详见 [[AGENT_BOOTSTRAP-summary]] 与 [[agent-protocol]]。

## 1. 核心约束

- **分支隔离**：v7-dev ↔ m-dev 绝不可混推
- **Layer 2 大文件不进 Git**（game_records、logs、models 等）
- **Commit 前缀规范**：
  - `[V-nn-v7]` — V7 引擎代码
  - `[docs]` — 文档
  - `[M-m2]` / `[M-m3]` — M 系列代码

## 2. 推送前检查项

1. 当前分支是否与目标分支一致
2. 是否有 Layer 2 文件被误 `git add`
3. Commit message 是否带规范前缀
4. 是否通过 `scripts/hooks/pre_push_validate.py`
5. 是否更新了对应 GUA/迭代记录

## 3. 配套工具

- `scripts/hooks/pre_push_validate.py` — 推送前自动校验
- `scripts/wiki.py lint` — Wiki 健康检查

## 4. 与 AGENTS.md 的关系

`AGENT_PUSH_CHECKLIST.md` 引用 `AGENTS.md` 的：
- §分支说明
- §治理要点
- §Git 提交与推送规则

## 关联页面

- [[AGENT_BOOTSTRAP-summary]] — 配套启动指南
- [[agent-protocol]] — 完整协作规约
- [[branch-strategy]] — 分支策略详解
```

---
