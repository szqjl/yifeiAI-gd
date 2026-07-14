---
type: source-summary
title: "M1 工作流监控指南摘要"
sources:
  - docs/guandan-brain/notes/MONITOR_WORKFLOW.md
tags:
  - m1-training
  - workflow
  - monitoring
  - historical-lesson
status: current
related_gua:
  - GUA-016
  - GUA-017
  - GUA-019
date: 2026-06-18
---

# M1 工作流监控指南摘要

## 文件信息
- **源文件**：`docs/guandan-brain/notes/MONITOR_WORKFLOW.md`（2140 字符）
- **主题**：M1 BC 模仿学习训练工作流的实时监控方法

## 核心内容

### 监控目标
M1 训练工作流（Stage7 优化训练框架）的实时监控，追踪损失函数、预测卡牌数、胜率等关键指标。

### 监控工具
- **MLflow UI**：实时查看训练指标、参数、artifact
- **`scripts/workflow/monitor_workflow_progress.py`**：进度监控脚本
- **`scripts/checks/check_workflow_status.py`**：状态检查脚本
- **`scripts/training/view_training_summary.py`**：训练摘要查看

### 关键监控指标
- 总损失值（关注爆炸：80 亿级别为异常）
- 真实卡牌数 vs 预测卡牌数（差距过大=过度预测）
- 预测比例（合理范围应在 1-5 倍）
- 评估胜率（目标 >50%）

## 关联文档
- [[TRAINING_EFFECTIVENESS_REPORT-summary]] — M1 训练效果报告
- [[TRAINING_FIXES_SUMMARY-summary]] — 修复总结
- [[auto-restart-workflow]] — 自动重启工作流机制

## Wiki 定位
本文件记录 M1 训练工作流的**监控方法论**，是 [[m1-over-prediction-crisis]] 的运维侧文档。M1 训练已在 Wiki 主线中被边缘化（0% 胜率），但监控流程仍可作为未来 V7 NN 训练的参考模板。
