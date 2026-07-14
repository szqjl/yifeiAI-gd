---
type: source-summary
title: "文档审查台账摘要（DOCUMENT_AUDIT）"
sources:
  - docs/governance/DOCUMENT_AUDIT.md
tags:
  - governance
  - document-audit
  - stub
  - source-of-truth
status: current
date: 2026-06-18
---

# 文档审查台账摘要

## 来源
- **原始文件**：`docs/governance/DOCUMENT_AUDIT.md`（4251 字符）
- **时间戳**：2026-05-29

## 台账目的
定期审查根目录及散落文档，确保：
1. **真源唯一性**：同类主题只能有一个权威文档
2. **零散落**：根目录不允许堆放临时 / 过程性文档
3. **可追溯**：stub 跳转保留旧链接，避免 404

## 真源冲突表（关键）

| 主题 | 已废弃 / 旧文档 | 当前真源 | 状态 |
|------|----------------|----------|------|
| Git 初始化 | `docs/governance/git-setup-guide.md` | `docs/governance/main-branch-policy.md` | git-setup-guide 已废弃，保留 stub |
| Artifact 存储 | V7_SYSTEM_FIXES 提及"云盘下载" | `docs/governance/COS-接入指南.md` | COS 为现行真源 |
| 大文件治理 | `cleanup_summary.md`（2025-12-17 快照） | `COS-接入指南.md` + `gitee-repo-capacity-guide.md` | cleanup_summary 归档，不再更新 |
| 分支策略 | git-setup-guide 旧版段落 | `M-V-Series-治理方案.md` + `main-branch-policy.md` | 双文档分工 |

## 已执行的治理动作

1. **根目录散落文档归位**：所有过程性文档迁入 `docs/governance/archive/`
2. **stub 跳转**：原路径保留跳转文件，避免外部链接 404
3. **台账登记**：每条迁移动作在 DOCUMENT_AUDIT.md 中留痕

## TENSION 标注

> **TENSION-3**：`git-setup-guide.md` 已被治理方案明确废弃（2026-05-29），但其旧链接可能仍被 Wiki / 外部文档引用。
> **应对**：在 index 中统一标注"已弃用，以 main-branch-policy.md 为准"。

## 关联条目
- [[document-governance]] — 文档治理概念（待建）
- [[artifact-storage-strategy]] — 大文件治理概念（待建）
- [[main-branch-policy]] — 现行 Git 分支真源（外部文档）
- cos-access-guide — COS 接入指南（外部文档）
