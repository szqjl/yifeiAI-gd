---
type: source-summary
title: "推送前检查指南 摘要"
sources:
  - docs/development/推送前检查指南.md
tags:
  - git
  - pre-push
  - source
status: current
related_gua: []
date: 2026-06-18
---

# 推送前检查指南 摘要

> 来源：`docs/development/推送前检查指南.md`（约 1887 字符）

## 目的

防止大文件（模型权重、日志、对局记录）被推送到 Git 仓库。

## .gitignore 规则

| 目录/文件 | 原因 |
|-----------|------|
| `models/` | 模型权重文件大 |
| `logs/` | 日志文件持续增长 |
| `Testscore/` | 评测输出 |
| `game_records/` | 对局回放数据 |

## 验证工具

### `verify_gitignore.py`
- 推送前运行，验证 `.gitignore` 规则是否覆盖所有敏感目录
- 检查 `git status` 输出，确认无大文件待提交

### `pre_push_check.bat`（Windows）
- Windows 下的推送前检查脚本
- 调用 `verify_gitignore.py` + 基础 lint

## 推送前清单

1. ✅ `.gitignore` 规则已更新
2. ✅ `verify_gitignore.py` 通过
3. ✅ `git status` 无大文件
4. ✅ 本地测试通过
5. ✅ 分支命名规范

## 关联

- wiki/overview — 全局概览（含 Git 工作流）
