---
type: source-summary
title: "Gitee 仓库容量与 LFS 指南摘要"
sources:
  - docs/governance/gitee-repo-capacity-guide.md
tags:
  - governance
  - gitee
  - lfs
  - capacity
status: current
date: 2026-06-18
---

# Gitee 仓库容量与 LFS 指南摘要

## 来源
- **原始文件**：`docs/governance/gitee-repo-capacity-guide.md`（3664 字符）

## 内容要点
1. **Gitee 免费配额**：单仓 500MB（个人）/ 1GB（组织）
2. **超限后果**：push 被拒，CI 失败
3. **缓解方案**：
   - Git LFS（大文件指针化，本地仍存完整文件）
   - 外部对象存储（COS / OSS）— **当前主推**
   - 定期清理 `dist/` `build/` 产物
4. **LFS 局限**：Gitee LFS 配额 1GB，超出需付费

## 与 cleanup_summary 的关系
- cleanup_summary 是 2025-12-17 的应急快照
- 本文档是**持续性规范**，是 [[artifact-storage-strategy]] 概念的方法论支撑

## 关联条目
- [[artifact-storage-strategy]] — 大文件治理概念
- cos-access-guide — COS 真源（外部）
- [[governance-cleanup-summary-archive]] — 应急快照（已归档）
