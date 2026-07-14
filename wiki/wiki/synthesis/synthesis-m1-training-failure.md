---
type: synthesis
title: "M1 训练失败综合分析"
sources:
  - docs/guandan-brain/notes/TRAINING_EFFECTIVENESS_REPORT.md
  - docs/guandan-brain/notes/TRAINING_FIXES_SUMMARY.md
  - docs/guandan-brain/notes/TRAINING_IMPROVEMENT_REPORT.md
  - docs/guandan-brain/notes/MONITOR_WORKFLOW.md
  - docs/guandan-brain/notes/WORKFLOW_MONITORING_GUIDE.md
tags:
  - m1-training
  - failure-analysis
  - historical-lesson
  - synthesis
status: current
related_gua:
  - GUA-016
  - GUA-017
  - GUA-019
date: 2026-06-18
---

# M1 训练失败综合分析

## 摘要
M1 BC 模仿学习训练历经 10 次迭代（2026-01-12 → 2026-01-13），胜率始终为 0%，投入产出比极低。本文综合 5 份 notes 文档，还原失败全貌并提炼教训。

## 时间线

### 阶段一：问题爆发（2026-01-12 早期）
- 损失函数爆炸至 800 亿级别
- 模型预测 512/512 张卡牌
- 评估失败：游戏记录缺少胜负字段

### 阶段二：集中修复（2026-01-12 中后期）
- GUA-016 落地：损失函数 + 数据过滤
- 损失数量级恢复至 10³
- 真实卡牌数从 0.79 提升至 1.44

### 阶段三：自动迭代（2026-01-12 晚 → 2026-01-13）
- 启动 [[auto-restart-workflow]] 闭环
- GUA-017 / GUA-019 调整重启参数
- 10 次迭代后胜率仍为 0%

## 多维度失败分析

### 技术维度
1. **数据**：PASS 动作样本未先过滤，污染训练
2. **模型**：BC 多标签分类输出不适应掼蛋动作空间
3. **损失**：平方惩罚 + 指数稀疏奖励设计有缺陷
4. **评估**：游戏记录缺失胜负字段，无法形成有效反馈

### 流程维度
- 自动重启工作流有效运转，但**重启 ≠ 改进**
- 监控到位（MLflow + 脚本），但**指标改善 ≠ 胜率改善**

### 资源维度
- 占用大量训练资源（Stage7 优化框架 + MLflow）
- 产出物全部归档为历史教训，无可复用模型

## 核心教训

### 1. 损失函数修复 ≠ 模型能力修复
GUA-016 的损失数量级修复（80 亿 → 5000）虽然成功，但**未触及过度预测的根因**。这提醒我们：评估修复效果必须看**下游指标**（胜率），而非上游指标（损失值）。

### 2. 掼蛋的 BC 模仿学习存在结构性困难
- 动作空间高度结构化（牌型组合）
- 决策时序长（多轮出牌）
- "不出牌"是合法且常见的动作
→ 单纯的多标签分类 BC 无法捕捉这些特性。

### 3. Wiki 主线与实验分支的边界
M1 训练虽占用资源，但 Wiki 主线（wiki-minimax/entities/engine-m3.md → wiki/entities/engine-v7.md）不应被其牵制。M1 经验应**归档为历史教训**，而非阻塞主线推进。

## 与 Wiki 主线的关系

### 不影响
- M3 决策引擎的现役地位
- V7 NN 引擎的开发方向
- 批跑评测体系的有效性

### 影响（仅作为输入）
- V7 设计时应规避 [[m1-over-prediction-crisis]] 中的失败模式
- 自动重启工作流的**流程模板**可复用于 V7 训练
- 三层监控架构（MLflow + 流程检查 + artifact 验证）值得继承

## 归档建议

### 标记为 outdated 的页面
- [[GUA-016]] / [[GUA-017]] / [[GUA-019]] — 状态已置为 outdated
- 三个 source-summary 页面保留为 historical-lesson 标签

### 保留的核心资产
- [[auto-restart-workflow]] — 流程机制仍有效
- [[WORKFLOW_MONITORING_GUIDE-summary]] — 监控方法论可迁移
- [[m1-over-prediction-crisis]] — 失败模式的概念化抽象（最有价值的产出）

## 行动项
- [ ] M1 相关训练资源释放，转向 V7
- [ ] V7 设计评审时引用本分析
- [ ] 每季度回顾历史失败案例，更新"教训"段落

## 关联
- [[m1-over-prediction-crisis]] — 核心失败概念
- [[GUA-016]] / [[GUA-017]] / [[GUA-019]] — 缺陷条目
- [[auto-restart-workflow]] — 工作流机制
- wiki-minimax/entities/engine-m3.md — 现役引擎（M1 已被取代）
- wiki/entities/engine-v7.md — 未来方向
- wiki/concepts/bc-argmax-collapse.md — 同源的 BC 训练问题
