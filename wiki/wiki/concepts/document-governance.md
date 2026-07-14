---
type: concept
title: "文档治理规范"
sources:
  - docs/governance/DOCUMENT_AUDIT.md
  - docs/governance/git-setup-guide.md
tags:
  - concept
  - governance
  - documentation
  - source-of-truth
status: current
date: 2026-06-18
---

# 文档治理规范

## 三大原则
1. **真源唯一**：同类主题只能有一个权威文档
2. **零散落**：根目录不允许堆放临时 / 过程性文档
3. **可追溯**：stub 跳转保留旧链接，避免 404

## 真源登记台账
见 [[governance-document-audit-summary]]（DOCUMENT_AUDIT.md）

### 关键真源
| 主题 | 真源 |
|------|------|
| Git 分支策略 | `docs/governance/main-branch-policy.md` |
| 整体治理方案 | `docs/governance/M-V-Series-治理方案.md` |
| Artifact 存储 | `docs/governance/COS-接入指南.md` |
| 仓库容量 | `docs/governance/gitee-repo-capacity-guide.md` |

### 已废弃（保留 stub）
- `docs/governance/git-setup-guide.md` → 跳 main-branch-policy
- `docs/governance/cleanup_summary.md`（根级）→ 跳 archive/cleanup_summary.md

## 弃用处理流程
1. DOCUMENT_AUDIT 台账登记
2. 原文件保留为 stub（带跳转声明）
3. 在 index 中标注"已弃用"
4. Wiki 内部引用统一改为真源

## TENSION 标注

> **TENSION-3**：`git-setup-guide.md` 已废弃（2026-05-29），旧链接可能仍被引用。
> **应对**：所有 Wiki 内部引用统一指向真源，并在文末注明"git-setup-guide 已弃用"。

## 关联条目
- [[governance-document-audit-summary]] — 台账
- [[artifact-storage-strategy]] — Artifact 治理
- [[main-branch-policy]] — 真源（外部）
