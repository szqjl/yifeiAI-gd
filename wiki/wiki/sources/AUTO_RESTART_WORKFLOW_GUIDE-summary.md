---
type: source-summary
title: "AUTO_RESTART_WORKFLOW_GUIDE 摘要"
sources:
  - docs/guandan-brain/notes/AUTO_RESTART_WORKFLOW_GUIDE.md
tags:
  - auto-restart
  - workflow
  - m1
  - guide
status: current
related_gua: []
date: 2026-06-18
---

# AUTO_RESTART_WORKFLOW_GUIDE 摘要

## 概述
自动重启工作流（Auto-Restart Workflow）的使用指南，对应 M1 stage7 旧管线下的训练-评估-重启循环。

## 核心脚本
- `scripts/workflow/auto_restart_workflow.py` — 主工作流
- `scripts/workflow/monitor_workflow_progress.py` — 进度监控
- `scripts/checks/check_workflow_status.py` — 状态检查
- `scripts/checks/check_auto_restart_status.py` — 重启状态
- `scripts/checks/check_training_progress_detailed.py` — 训练详情
- `src/train/stage7_optimized_training.py` — 训练入口

## 方法论
自动重启-改进循环：
1. 训练 → 2. 评估 → 3. 失败检测 → 4. 自动重启 → 5. 回到 1

## ⚠️ 适用性说明
- 该工作流绑定 M1 stage7 旧管线
- V7 主线是否复用此工作流需验证
- 详见 [[auto-restart-workflow]] 概念页

## 关联页面
- [[module-auto-restart-workflow]]
- [[AUTO_RESTART_SYSTEM_STATUS-summary]]
