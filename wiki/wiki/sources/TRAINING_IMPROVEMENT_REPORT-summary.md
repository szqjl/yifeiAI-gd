---
type: source-summary
title: "M1 训练自动改进记录摘要"
sources:
  - docs/guandan-brain/notes/TRAINING_IMPROVEMENT_REPORT.md
tags:
  - m1-training
  - auto-restart
  - stage7
  - historical-lesson
status: current
related_gua:
  - GUA-016
  - GUA-017
date: 2026-06-18
---

# M1 训练自动改进记录摘要

## 文件信息
- **源文件**：`docs/guandan-brain/notes/TRAINING_IMPROVEMENT_REPORT.md`（2222 字符）
- **主题**：M1 训练通过自动重启工作流的迭代改进过程

## 核心机制：训练-评估-优化闭环

### 工作流组件
1. **`scripts/workflow/auto_restart_workflow.py`** — 自动重启脚本
2. **`scripts/workflow/monitor_workflow_progress.py`** — 进度监控
3. **`scripts/training/view_training_summary.py`** — 摘要查看

### 闭环逻辑
```
训练崩溃 → 检测失败 → 自动重启 → 调整超参 → 再次训练
    ↑                                              ↓
    └──────────── 评估胜率反馈 ←─────────────────┘
```

## 改进记录（10 次迭代）

### 已应用的改进
- 损失函数：对数惩罚 + 倒数稀疏奖励（见 [[TRAINING_FIXES_SUMMARY-summary]]）
- 数据：过滤 PASS 动作样本
- 超参：lr=0.000005, alpha=0.05, gamma=6.0

### 未解决问题
- 过度预测（512 张卡牌）
- 评估失败：游戏记录缺少胜负字段，无法计算真实胜率
- 模型产出仍无法战胜 client

## 模型产出物
- `models/bc_model_stage7_optimized.pth` — Stage7 优化模型权重
- `models/bc_model_stage7_optimized_training_history.json` — 训练历史
- `models/m1_training_workflow_history.json` — 工作流历史
- `stage7_optimized_training.py.backup_20260113_111713` — 备份脚本

## 关联
- [[auto-restart-workflow]] — 自动重启工作流
- [[MONITOR_WORKFLOW-summary]] — 监控方法
- [[TRAINING_EFFECTIVENESS_REPORT-summary]] — 最终效果
