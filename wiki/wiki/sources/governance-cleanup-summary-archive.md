---
type: source-summary
title: "大文件清理归档摘要（cleanup_summary，2025-12-17 快照）"
sources:
  - docs/governance/archive/cleanup_summary.md
  - docs/governance/cleanup_summary.md
tags:
  - governance
  - archive
  - cleanup
  - lfs
  - cos
status: outdated
date: 2026-06-18
---

# 大文件清理归档摘要

## 来源
- **原始文件**：
  - `docs/governance/archive/cleanup_summary.md`（2791 字符，完整版）
  - `docs/governance/cleanup_summary.md`（186 字符，根级 stub 跳转）
- **时间戳**：2025-12-17
- **状态**：**有效 · 归档快照**（2026-05-29 后不再更新，真源已迁至 COS-接入指南）

## 背景
仓库接近 Gitee 免费容量上限（持续集成构建产物体积大），触发清理。

## 三方案对比

| 方案 | 描述 | 优点 | 缺点 | 结论 |
|------|------|------|------|------|
| 方案 A | 仅删工作目录文件 | 见效快 | 历史中仍存在，仓库未真瘦身 | 临时应急 |
| 方案 B | 重写 Git 历史 | 彻底 | 不可逆，破坏所有 fork | 高风险，未执行 |
| 方案 C | LFS / 外部存储 | 可持续 | 需运维 + 学习成本 | **现行方案**（COS 真源） |

## 已执行动作
- 删除 `dist/`、`build/`、`*.pyc`、虚拟环境等
- `.gitignore` 增加对应规则
- 通知全员 `git pull --rebase`

## TENSION 标注

> **TENSION-4**：本文档提到"删除文件仍在 Git 历史中，仓库未真正瘦身"——长期方案（重写历史 或 LFS 全量迁移）未执行。
> **状态**：pending；现行缓解依赖 COS 外部存储增量兜底。
> **真源**：见 [[artifact-storage-strategy]] 概念页与 `docs/governance/COS-接入指南.md`。

## 关联条目
- [[artifact-storage-strategy]] — 大文件治理现行规范
- cos-access-guide — COS 接入真源
- [[gitee-repo-capacity-guide]] — Gitee 容量与 LFS 指南（外部文档）
