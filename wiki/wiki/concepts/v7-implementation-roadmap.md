---
type: concept
title: "V7 实施路线图"
sources:
  - docs/guandan-brain/V7-实施方案.md
tags:
  - v7
  - roadmap
  - phases
  - milestones
status: current
related_gua:
  - GUA-014
  - GUA-015
  - GUA-016
  - GUA-017
  - GUA-018
  - GUA-037a
  - GUA-037b
  - GUA-038
  - GUA-039a
  - GUA-039b
  - GUA-040
  - GUA-041
  - GUA-042
  - GUA-043
date: 2026-06-18
---

# V7 实施路线图

## 路线图定位

V7 NN 引擎从概念到落地的**4 阶段、14 个 GUA** 的完整路径，整合自 [[V7-实施方案-summary]]。

## 四阶段实施路径

### Phase 1：基础设施搭建
**目标**：actor-learner 异步 RL 框架 + BC 热启动管道
- **GUA-014**：V7 引擎骨架 `ultimate_win_rate_engine_v7.py`
- **GUA-015**：BC 数据集 `bc_dataset.py` + 训练器 `bc_trainer.py`
- **GUA-016**：ZMQ actor-learner 桥接 `zmq_bridge.py`

### Phase 2：特征与状态
**目标**：188 维特征空间就位
- **GUA-017**：静态特征 124 维 `static_features.py`
- **GUA-018**：动态 LSTM 64 维 `dynamic_features.py`
- **GUA-037a**：context 字段对齐（pass_num 接线）

### Phase 3：训练与评估
**目标**：BC → PPO 训练闭环 + 评估体系
- **GUA-037b**：V 默认冒烟 OFF 治理
- **GUA-038**：评估次数=0 即视为未实施
- **GUA-039a**：评估基线建立
- **GUA-039b**：V7 队胜率 **≥30%** 硬门槛 ⭐

### Phase 4：上线与监控
**目标**：推理性能 + 合规上线
- **GUA-040**：ONNX 导出 + 推理延迟 ≤50ms/step
- **GUA-041**：A+B 并行方案
- **GUA-042**：ABL-GD 168 伪动作方案
- **GUA-043**：CN113018837A 专利规避审计

## 关键里程碑

### M1：环境可跑
- ZMQ 通信通
- BC 数据可生成
- 30 局 fallback 评估基线完成

### M2：模型可训
- BC 热启动 loss 收敛
- PPO 训练跑通
- 30 局 V7 vs lalala 评估启动

### M3：达标
- **队胜率 ≥30%**（GUA-039b 硬门槛）
- 推理延迟 ≤50ms/step
- 累计 100 局批跑数据

## 当前状态

- **累计局胜率**：1/33 = 3.0%（距 30% 门槛差 27 个百分点）
- **关键路径**：预计 4-5 迭代

## 治理条款（V 系列首次）

1. **冒烟 OFF**：V 默认不参与冒烟测试，防止误用
2. **评估即落地**：评估次数=0 即视为未实施
3. **胜率硬门槛**：≥30% 是上线必要条件

## 已知风险

- **BC teacher 悖论**：M3 game_records（胜率 0%）作 V7 BC teacher
- **乐观预期**：30% 门槛的关键路径 4-5 迭代可能过于乐观
- **历史教训**：V4-V5 6 个月从未跑对战 KPI

## 关联页面

- [[V7-实施方案-summary]]
- wiki/entities/engine-v7.md
- wiki/synthesis/synthesis-v7-current-state.md
- wiki-minimax/concepts/batch-evaluation.md
- [[GUA-039b]]
```

接下来创建关键 GUA 实体页（精选最重要的 8 个）：
