---
type: synthesis
title: "V7 当前状态综合"
sources:
  - docs/development/M1_ARCHITECTURE.md
  - docs/development/AI首秀分析报告.md
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
  - docs/guandan-brain/ISSUES.md
tags:
  - synthesis
  - v7
  - m-series
  - v-series
  - strategy-lines
status: current
related_gua:
  - GUA-061
  - GUA-033
  - GUA-022
date: 2026-07-15
---

# V7 当前状态综合

## 双线开发格局

V7 与 M 系列是**两条独立策略线**，共享底层数据层但决策核心完全不同：

| 维度 | M 系列 (M1 frozen / M3 主迭代) | V 系列 (V7 实验 / V8 迁移) |
|------|-------------------------------|----------------------------|
| 决策方式 | 硬编码 if-else 规则 | 神经网络策略 |
| 阶段路由 | [[stage-router-architecture]] 5×2 | 部分继承 + NN 决策 |
| 客户端 | yf1_m1/m3, yf2_m1/m3 | yf1_v7, yf2_v7 |
| 数据目录 | game_records | game_records_v7 |
| 状态 | M1 frozen, M3 主迭代 | V7 实验 (v7-dev), V8 迁移 (v8-dev) |

## V7 当前状态

### 引擎配置

- 文件：`ultimate_win_rate_engine_v7.py`
- 路线：NN 策略
- 分支：v7-dev

### 批跑

详见 [[batch-evaluation]]：
- 命令：`python batch_run.py --engine v7 --target-games 300`
- 数据落盘：`game_records_v7/`
- `--target-games` 须为 3 的倍数（局数 × 3 副/局）

### 执行卡片闭环

V7 特有工作流：

```
replay → WF-12 → 准入审查 → 修复 → 批跑 → 复核
```

详见 [[agent-bootstrap-workflow]]。

## 与 M3 的关系

**独立开发**，但有以下耦合：
1. 共用层（牌型识别、回合驱动）
2. 同一组 yf1/yf2 玩家账户
3. 同一套 [[gua-033]] 胜利解读口径

## M1 的历史遗产

[[engine-m1]] frozen 之后，[[stage-router-architecture]] 和模块化设计沉淀为 M 系列共有资产，V 系列部分继承。

## 下一步建议

1. 持续维护 V7 v7-dev 分支，引入更多 replay 数据
2. M3 主迭代聚焦当前 P0 GUA（[[gua-061]]）
3. 关注 V8 平台迁移进度（v8-dev）

## 历史里程碑

- 2025-11-24 v0.1-Random 首秀（[[first-debut-baseline]]）
- M1 frozen（[[gua-022]]）
- V7 实验线启动（v7-dev）
- V8 平台迁移启动（v8-dev）
