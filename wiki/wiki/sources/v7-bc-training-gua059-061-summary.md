---
type: source-summary
title: "V7 BC 训练诊断与模块化摘要"
sources:
  - docs/guandan-brain/iterations/v7-bc-training-gua059-061.md
tags:
  - v7
  - bc
  - training
  - modular
  - diagnostic
status: current
related_gua:
  - GUA-059
  - GUA-060
  - GUA-061
date: 2026-06-17
---

# V7 BC 训练诊断与模块化摘要

## 范围

GUA-059 / GUA-060 / GUA-061，三条**方向性转弯**的 GUA：前两条关闭并给出 V7 BC 路线的「死亡证明」，第三条开启模块化新路径。

## GUA-059 — action_head 修复 + Guard 接入（CLOSED）

- **问题**：`action_head` 输出与 Guard 约束不一致
- **修复**：在 `ultimate_win_rate_engine_v7.py` 中强制 action_head 走 Guard 过滤
- **效果**：队胜 100% 稳定，副胜仍 0%

## GUA-060 — argmax collapse 诊断（CLOSED 2026-06-17）

- **核心结论**：在掼蛋动态贝叶斯决策下，端到端 BC **理论必然**导致 argmax collapse
- **证据**：
  - V2-V7 六个版本端到端 BC/RL 全部 ≤3% 队胜率
  - 归一化熵 0.489（远低于阈值 0.7）
  - val_acc 锁死 36% 区间与 loss 完全解耦（label_smoothing=0.1 实验 loss=9.12e7）
  - **反例**：败局训练反而学败方决策（V7 4.2% regression）
- **理论支撑**：见 [[argmax-collapse]] 概念页
- **产物**：`bc_model_v2_GUA060_20260617_36pct.pth`（val_acc 36.46% 的「最佳」模型）

## GUA-061 — 模块化架构（P0 OPEN 当前活跃）

- **背景**：GUA-060 关闭后，团队决定**放弃端到端 BC 路线**
- **新路径**：模块化分阶段训练（套路七），见 wiki/concepts/modular-staged-training.md
- **Week 1 立项**：wiki/entities/module-grouping-engine.md（`GroupingEngine`）P0 立项
  - 把 M3 的纯函数组牌逻辑**提取为 V7-internal** 模块
  - 用 pytest 覆盖
- **Week 2-5 规划**：角色 → 记忆 → 动态 → 动作（顺序由易到难）
- **关键约束**：
  - **必须 M3 胜局训练**（避免 win-rate-loss-trap）
  - class_weight=1/sqrt(count) 反比加权
  - 备选 focal loss γ=2.0
- **诊断脚本**：`tmp_action_dist_diag.py`（action 分布诊断）
- **训练入口**：`run_bc_training.py` 重构以支持分阶段

## 关键 KPI

- **V7 副胜 0/236**：纯 NN 决策能力为零
- **val_acc 36.46%**：GUA-060 关闭时的「天花板」模型
- **回归 33/48/34 passed**：M3 旧脚本在模块化迁移后的回归测试结果

## 状态切换

- GUA-059 CLOSED → GUA-060 CLOSED → **GUA-061 OPEN（P0）**
- 团队当前真正在做的：**从 BC 调参 → 模块化架构**，方向性重大转弯

## 关联

- [[gua-059]]
- [[gua-060]]
- [[gua-061]]
- wiki/entities/module-grouping-engine.md
- wiki/concepts/modular-staged-training.md
- [[argmax-collapse]]
- win-rate-loss-trap
- wiki/synthesis/synthesis-v7-current-state.md
- synthesis-v7-bc-failure-map
