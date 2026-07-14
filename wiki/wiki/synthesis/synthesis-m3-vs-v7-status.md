---
type: synthesis
title: "M3 决策引擎 vs V7 神经网络引擎 当前状态对比"
sources:
  - docs/guandan-brain/MOCs/M3-Development.md
  - docs/guandan-brain/MOCs/V7-Development.md
tags:
  - synthesis
  - m3
  - v7
  - status-comparison
status: current
related_gua:
  - GUA-036
  - GUA-060
  - GUA-061
date: 2026-06-18
---

# M3 vs V7 状态对比综合分析

## 核心结论
- **M3**：现役、可用，但已触及规则引擎天花板
- **V7**：未来方向，但当前严重不达标（3.0% vs 30% 门槛）

## 性能对比

| 指标 | M3 决策引擎 | V7 NN 引擎 | 备注 |
|------|------------|-----------|------|
| 队胜率区间 | 55.6% ~ 81.0% | 3.0% | V7 远低于 30% 门槛 |
| 峰值 | 78.8%（GUA-034/035） | — | M3 峰值 |
| 近期 | 52.2%（GUA-036） | — | M3 存在回落 |
| 开放 P0 | 0 | 1（GUA-061） | V7 有未解阻塞 |
| 已关 GUA | 12 | 20 | V7 已完成大量前置 |

## 战略意义
- **M3 是稳定收入**：现役引擎，批跑 KPI 可用
- **V7 是增长期权**：当前 3% → 30% 是 10 倍空间，但需突破 GUA-061
- **共存期**：M3 维持团队战绩，V7 在后台持续迭代

## 关键张力
1. **M3 稳定性**声明（55.6%~81.0%）vs GUA-036 回落至 52.2%
2. **V7 关闭 GUA 多**但胜率仍 3%，说明关单 ≠ 接近达标
3. **GUA-060 关闭 ≠ V7 胜利**，反而标志着模仿学习路径终结

## 行动建议
1. M3 继续维护，监控 GUA-036 类回落的复现条件
2. V7 集中资源攻克 GUA-061（模块化架构）
3. 建立 M3 vs V7 的对照批跑，定期追踪 V7 何时跨越 30%

## 关联页面
- wiki-minimax/entities/engine-m3.md
- wiki/entities/engine-v7.md
- [[modular-architecture-gua061]]
- wiki/concepts/bc-argmax-collapse.md
- 批跑评测体系
