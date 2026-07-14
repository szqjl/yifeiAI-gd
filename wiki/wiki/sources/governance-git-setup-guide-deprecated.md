---
type: source-summary
title: "Git 设置指南（已废弃）"
sources:
  - docs/governance/git-setup-guide.md
tags:
  - governance
  - git
  - deprecated
status: outdated
date: 2026-06-18
---

# Git 设置指南（已废弃）

## 来源
- **原始文件**：`docs/governance/git-setup-guide.md`（714 字符）
- **状态**：⚠️ **已废弃（2026-05-29 DOCUMENT_AUDIT 台账确认）**

## 弃用原因
- 内容与 `main-branch-policy.md` 大量重叠
- 部分流程描述已过时（早期 fork 模式，与现行 m-dev 主开发线不一致）

## 现行真源
- **分支策略** → `docs/governance/main-branch-policy.md`
- **整体治理** → `docs/governance/M-V-Series-治理方案.md`

## 处置
- 文件保留为 stub，避免外部链接 404
- 头部添加跳转声明，指向 main-branch-policy.md
- 在 index 中标注"已弃用"

## TENSION 标注

> **TENSION-3**：本文档已被治理方案明确废弃，但其旧链接可能仍被 Wiki / 外部文档引用。
> **应对**：所有 Wiki 内部引用统一改为 [[main-branch-policy]]（外部），并在文末注明"git-setup-guide 已弃用"。

## 关联条目
- [[document-governance]] — 文档治理原则
- [[main-branch-policy]] — 现行真源（外部）
