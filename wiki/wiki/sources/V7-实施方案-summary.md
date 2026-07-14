---
type: source-summary
title: "V7 实施方案总览"
sources:
  - docs/guandan-brain/V7-实施方案.md
tags:
  - v7
  - implementation
  - roadmap
  - neural-network
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

# V7 实施方案总览

## 文档定位

V7 实施方案是 V 系列 NN 引擎的**纲领性文档**，覆盖从 M3 规则引擎向 V7 NN 引擎迁移的完整路径，包含 9 条核心 GUA、4 个实施阶段、关键技术选型与硬性门槛设定。

## 核心架构

### 引擎形态
- **主框架**：actor-learner 异步强化学习架构（actor.py + learner.py）
- **通信**：ZMQ 桥接（zmq_bridge.py），actor 端推理、learner 端训练
- **决策契约**：IDecisionProvider v1.0 抽象层
- **权重管理**：weight_manager.py + COS manifest 上传下载

### 特征工程
| 维度 | 来源 | 维度数 |
|------|------|--------|
| 静态特征 | static_features.py | 124 维 |
| 动态特征 | dynamic_features.py（LSTM） | 64 维 |
| **合计** | — | **188 维** |

### 训练范式
- **两阶段训练**：BC 热启动 → Danzero+ 自对弈
- **BC teacher**：M3 game_records（存疑：M3 自身胜率 0%）
- **ABL-GD 168 伪动作**（GUA-042）：动作空间压缩方案

## 四阶段实施路径

### Phase 1：基础设施搭建
- GUA-014：V7 引擎骨架（ultimate_win_rate_engine_v7.py）
- GUA-015：BC 数据集与训练器（bc_dataset.py / bc_trainer.py）
- GUA-016：ZMQ actor-learner 桥接

### Phase 2：特征与状态
- GUA-017：静态特征 124 维实现
- GUA-018：动态 LSTM 64 维特征
- GUA-037a：context 字段对齐（pass_num 接线）

### Phase 3：训练与评估
- GUA-037b：V 默认冒烟 OFF 治理条款
- GUA-038：评估次数=0 即视为未实施
- GUA-039a：评估基线建立
- **GUA-039b**：V7 队胜率 **≥30%** 硬门槛

### Phase 4：上线与监控
- GUA-040：ONNX 导出 + 推理延迟 ≤50ms/step
- GUA-041：A+B 并行方案
- GUA-042：ABL-GD 168 伪动作
- GUA-043：CN113018837A 专利规避审计

## 关键技术决策

1. **路径治理**：v7_paths.yaml 配置化（消除 M1 路径债）
2. **冒烟治理**：V 默认冒烟 OFF（防误用）
3. **评估硬门槛**：队胜率 ≥30%（V 系列首次设定）
4. **训练合规**：BC teacher 选用需审计（劣师带劣徒风险）

## 已知张力

- **BC teacher 悖论**：M3 game_records 作 V7 BC teacher，但 M3 自身胜率 0%，存在「劣师带劣徒」风险
- **乐观预期**：GUA-039b 30% 门槛是关键路径 4-5 迭代可达成的预期，但当前 0/33 距门槛差 30 个百分点
- **历史教训**：V4-V5 6 个月从未跑对战 KPI（护栏条款能否真落地待观察）

## 关联页面

- wiki/entities/engine-v7.md
- wiki/synthesis/synthesis-v7-current-state.md
- wiki-minimax/concepts/batch-evaluation.md
- [[GUA-039b]]
