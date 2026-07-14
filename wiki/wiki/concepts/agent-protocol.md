---
type: concept
title: "Agent 协作协议（第一句 / 分支 / Commit 前缀）"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
  - docs/guandan-brain/AGENT_PUSH_CHECKLIST.md
  - docs/guandan-brain/COMMANDER_NOTES.md
tags:
  - protocol
  - governance
  - branch-isolation
status: current
related_gua: []
date: 2026-06-17
---

# Agent 协作协议

> 规约横跨 [[AGENT_BOOTSTRAP-summary]] 与 [[AGENT_PUSH_CHECKLIST-summary]]，本概念页集中描述。

## 1. 新 Agent 第一句（场景分流）

新会话开场必须明确：

1. **当前分支**（v7-dev / m-dev / main）
2. **目标引擎**（V7 / M3 / 其他）
3. **任务类型**（P0 修复 / 迭代开发 / 评测 / 文档）

## 2. 分支隔离（硬约束）

| 分支 | 用途 | 不可推 |
|---|---|---|
| `v7-dev` | V7 引擎主开发 | 不可推 M 系列代码 |
| `m-dev` | M 系列维护 | 不可推 V7 代码 |
| `main` | 已废弃 | — |

**v7-dev ↔ m-dev 绝不可混推**。

## 3. Commit 前缀规范

| 前缀 | 用途 |
|---|---|
| `[V-nn-v7]` | V7 引擎代码（如 V-01-v7） |
| `[docs]` | 文档变更 |
| `[M-m2]` | M2 引擎代码 |
| `[M-m3]` | M3 引擎代码 |

## 4. Layer 2 文件禁入 Git

以下目录/文件**不进入版本控制**：

- `game_records/`、`game_records_v7/`
- `logs/`
- `models/*.pth`
- `*.json` 中的累计数据（如 `scores.json`）
- 详见 [[data-directory-segregation]]

## 5. 推送前检查项

详见 [[AGENT_PUSH_CHECKLIST-summary]]，核心工具：`scripts/hooks/pre_push_validate.py`。

## 6. 代码改动交叉评审

P0 级别改动必须：
1. 记录到对应 GUA
2. 经交叉评审
3. 通过批跑验证胜率

## 关联页面

- [[AGENT_BOOTSTRAP-summary]]
- [[AGENT_PUSH_CHECKLIST-summary]]
- [[branch-strategy]]
- [[data-directory-segregation]]
```

---
