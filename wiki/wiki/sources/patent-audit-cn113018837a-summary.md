---
type: source-summary
title: "专利 CN113018837A 规避审计摘要"
sources:
  - docs/governance/patent-audit-cn113018837a.md
tags:
  - patent
  - legal
  - governance
  - v7
status: current
related_gua:
  - GUA-043
date: 2026-06-18
---

# 专利 CN113018837A 规避审计摘要

> **专利权人**：杭州师范大学  
> **专利号**：CN113018837A  
> **审计结论**：✅ 继续实施 V7，仅对分组优化模块调整  
> **关联 GUA**：GUA-043

## 风险评估

### ⚠️ 高风险模块

| 模块 | 风险点 | 说明 |
|------|--------|------|
| `dynamic_grouping_optimizer.py` | 可能落入 `Ea = E1 + E2` 公式保护范围 | 需规避设计 |

### ✅ 安全模块

- 四头网络
- BC 训练
- DMC / PPO
- 特征工程

## 规避设计原则

详见 [[patent-avoidance-design]]。

**推荐方案**：
1. **离散牌型分级** — 避免线性叠加公式
2. **NN win_rate 增量替代** — 用神经网络预测替代解析公式
3. **重构 grouping 优化器** — 改为基于查表 + 启发式的方案

## 审计建议

- **继续实施 V7 路径** ✅
- **仅对 `dynamic_grouping_optimizer.py` 进行规避重构**
- 其他模块（四头网络、BC、DMC/PPO、特征工程）不涉及专利风险

## 关联页面

- GUA-043 — 专利规避审计 GUA 条目
- [[patent-avoidance-design]] — 规避设计原则
- wiki/entities/engine-v7.md — V7 引擎
