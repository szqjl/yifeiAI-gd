---
type: source-summary
title: "main 分支策略摘要"
sources:
  - docs/governance/main-branch-policy.md
tags:
  - governance
  - branch-strategy
  - main-branch
status: current
related_gua: []
date: 2026-06-18
---

# main 分支策略摘要

> **拍板日期**：2026-05-29  
> **状态**：✅ 已结案，origin/main 冻结于 `e767f28`  
> **替代关系**：取代已废弃的 `git-setup-guide.md`

## 核心规则

main 分支为**里程碑合并**专用分支，非日常开发线。

| 项目 | 规则 |
|------|------|
| 冻结 commit | `e767f28` |
| 合并方向 | `v7-dev → m-dev → main` |
| 合并方式 | **merge commit**（保留历史） |
| 强制推送 | ❌ **禁用**（force push 永远禁止） |
| 日常开发 | 在 `m-dev` / `v7-dev` 进行 |

## 分支清单

| 分支 | 用途 | 状态 |
|------|------|------|
| `main` | 里程碑发布 | 冻结，e767f28 |
| `m-dev` | M 系列主集成 | 活跃 |
| `v7-dev` | V7 实验 | 活跃 |
| `v6-dev` | MOE 归档 | 归档 |
| `develop` | 早期通用开发 | 已弃用 |

## 与废弃文档的关系

| 文档 | 状态 |
|------|------|
| `git-setup-guide.md` | ❌ 已废弃 |
| `main-branch-policy.md` | ✅ 当前真源 |
| `M-V-Series-治理方案.md` | ✅ 上位总纲（§分支策略） |

## 关联页面

- [[M-V-Series-治理方案-summary]] — 上位总纲
- [[m-v-series-architecture]] — 架构概念
- [[governance-git-setup-guide-deprecated]] — 旧文档归档
