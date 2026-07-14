---
type: entity-module
title: "Auto-Restart Workflow 模块"
sources:
  - docs/guandan-brain/notes/AUTO_RESTART_WORKFLOW_GUIDE.md
tags:
  - module
  - workflow
  - m1
  - stage7
status: current
related_gua: []
date: 2026-06-18
---

# Auto-Restart Workflow 模块

## 模块身份
- **类型**：工作流脚本集
- **绑定管线**：M1 stage7（旧）
- **目录**：`scripts/workflow/` + `scripts/checks/`

## 文件清单

### 工作流主文件
- `scripts/workflow/auto_restart_workflow.py` — 主循环入口
- `scripts/workflow/monitor_workflow_progress.py` — 进度监控

### 状态检查
- `scripts/checks/check_workflow_status.py`
- `scripts/checks/check_auto_restart_status.py`
- `scripts/checks/check_training_progress_detailed.py`

### 训练入口
- `src/train/stage7_optimized_training.py`

## 关联页面
- [[auto-restart-workflow]]
- [[AUTO_RESTART_SYSTEM_STATUS-summary]]
- [[synthesis-m1-evaluation-failure]]
