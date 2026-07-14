---
type: concept
title: "自动重启工作流"
sources:
  - docs/guandan-brain/notes/TRAINING_IMPROVEMENT_REPORT.md
  - docs/guandan-brain/notes/MONITOR_WORKFLOW.md
tags:
  - workflow
  - auto-restart
  - monitoring
status: current
related_gua:
  - GUA-016
  - GUA-017
  - GUA-019
date: 2026-06-18
---

# 自动重启工作流

## 机制定义
**自动重启工作流**（Auto-Restart Workflow）指训练任务失败后自动检测 → 调整参数 → 重启训练的闭环流程。

## 核心组件

### 脚本
- `scripts/workflow/auto_restart_workflow.py` — 主重启脚本
- `scripts/workflow/monitor_workflow_progress.py` — 进度监控
- `scripts/checks/check_workflow_status.py` — 状态检查
- `scripts/training/view_training_summary.py` — 摘要查看

### 监控
- **MLflow UI** — 实时指标追踪
- 三层监控：指标层 + 流程层 + 产出层（详见 [[WORKFLOW_MONITORING_GUIDE-summary]]）

## M1 案例：重启有效但未改善胜率

### 重启记录
M1 训练共重启 **10 次**，每次迭代后自动调整超参。

### 效果
- ✅ 流程层面：工作流稳定运行，无人工介入
- ✅ 指标层面：损失值从 80 亿降至 5000
- ❌ 终局指标：胜率仍为 0%

### 失败证据
详见 [[synthesis-m1-training-failure]]。重启工作流作为**运维机制**是成功的，但作为**模型改进机制**是失败的——它无法突破数据/模型架构层面的根本问题。

## 对 V7 的启示

### 可复用的部分
- 自动重启的工程实现
- 三层监控架构
- 训练历史 JSON 记录

### 必须改进的部分
- 重启决策不应只看损失值，应**直接看胜率**
- 超过 N 次重启无改善应**自动停止**（避免资源浪费）
- 引入 A/B 测试机制对比不同参数组合

## 关联
- [[m1-over-prediction-crisis]] — M1 重启未能解决的问题
- [[GUA-016]] / [[GUA-017]] / [[GUA-019]] — 重启涉及的 GUA
- [[MONITOR_WORKFLOW-summary]] — 监控细节
- [[TRAINING_IMPROVEMENT_REPORT-summary]] — 改进记录
```

## 生成完成

本次共生成 **13 个 Wiki 页面**：

### 新建页面（11 个）
**source-summary（6 个）**：
- `wiki/sources/MONITOR_WORKFLOW-summary.md`
- `wiki/sources/notes-README-summary.md`
- `wiki/sources/TRAINING_EFFECTIVENESS_REPORT-summary.md`
- `wiki/sources/TRAINING_FIXES_SUMMARY-summary.md`
- `wiki/sources/TRAINING_IMPROVEMENT_REPORT-summary.md`
- `wiki/sources/WORKFLOW_MONITORING_GUIDE-summary.md`

**entity-gua（3 个）**：
- `wiki/entities/gua-016.md`
- `wiki/entities/gua-017.md`
- `wiki/entities/gua-019.md`

**concept（1 个）**：
- `wiki/concepts/m1-over-prediction-crisis.md`

**synthesis（1 个）**：
- `wiki/synthesis/synthesis-m1-training-failure.md`

### 更新页面（3 个）
- `wiki/index.md` — 添加 M1 相关链接与 GUA 索引
- `wiki/overview.md` — 新增"M1 历史教训"段落
- `wiki/concepts/auto-restart-workflow.md` — 补充 M1 失败证据

### 关键设计决策
1. **GUA-016/017/019 标记为 outdated** — 反映 M1 训练已边缘化的事实，避免与现役 Wiki 主线混淆
2. **M1 失败抽象为概念页** — `m1-over-prediction-crisis` 是最有价值的复用资产
3. **synthesis 页承担"教训提炼"角色** — 明确"重启 ≠ 改进"的核心结论
4. **auto-restart-workflow 补充证据** — 区分"机制成功"与"目标失败"两个维度
5. **保留 notes 目录为 historical-lesson** — 不删除但明确标注历史定位
