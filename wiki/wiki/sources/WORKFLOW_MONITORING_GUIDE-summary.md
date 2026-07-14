---
type: source-summary
title: "工作流监控通用指南摘要"
sources:
  - docs/guandan-brain/notes/WORKFLOW_MONITORING_GUIDE.md
tags:
  - workflow
  - monitoring
  - mlflow
status: current
related_gua: []
date: 2026-06-18
---

# 工作流监控通用指南摘要

## 文件信息
- **源文件**：`docs/guandan-brain/notes/WORKFLOW_MONITORING_GUIDE.md`（1690 字符）
- **主题**：训练工作流的通用监控方法论（不限于 M1）

## 与 MONITOR_WORKFLOW.md 的区别

| 文件 | 范围 | 目标系统 |
|------|------|----------|
| `MONITOR_WORKFLOW.md` | M1 特定 | Stage7 优化训练 |
| `WORKFLOW_MONITORING_GUIDE.md` | 通用 | 所有训练工作流 |

## 监控方法论

### 三层监控
1. **指标层**：MLflow UI 实时追踪 loss、accuracy、胜率
2. **流程层**：工作流状态检查（运行中/卡住/失败）
3. **产出层**：模型 artifact 验证

### 异常检测
- 损失爆炸（数量级 >10⁶）
- 预测坍缩（输出单一动作/全牌）
- 训练停滞（loss 不下降超过 N 轮）

## 对 V7 的可借鉴性
本指南虽是 M1 时代的产物，但其**三层监控架构**可复用于 V7 NN 引擎训练。建议 V7 训练启动时参考本指南并补充：
- NN 特有的梯度监控
- 分布式训练的 worker 健康检查

## 关联
- [[MONITOR_WORKFLOW-summary]] — M1 特定监控
- [[auto-restart-workflow]] — 自动化机制
