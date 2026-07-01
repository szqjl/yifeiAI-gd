---
tags: [MOC, V7, NN, BC-training, GUA-037~GUA-061]
created: 2026-06-17
topic: V7 神经网络引擎开发全记录索引
---

# V7 神经网络引擎开发

> V7 = BC 模仿学习 + 模块化架构。当前队胜率 **3.0%（1/33）**，距 30% 门槛差距巨大。

## 迭代文件

- [[v7-infra-gua041-049]] — 基础设施：路径债/门闩/卡顿诊断（GUA-041~049, V7-006/010）
- [[v7-features-gua037-038]] — 特征工程与 BC 训练（GUA-037a/b, GUA-038, GUA-050/052）
- [[v7-strategy-gua045-053]] — Guard 壳与策略增补（GUA-045, GUA-051~053）
- [[v7-bc-training-gua059-061]] — BC 训练诊断与模块化架构（GUA-059~061）

## GUA 索引

| GUA | 状态 | 文件 |
|-----|------|------|
| V7-006 | closed | [[v7-infra-gua041-049]] |
| V7-007 | open (队胜率未达标) | [[v7-features-gua037-038]] |
| V7-010 | closed | [[v7-infra-gua041-049]] |
| GUA-037a | closed | [[v7-features-gua037-038]] |
| GUA-037b | closed | [[v7-features-gua037-038]] |
| GUA-038 | closed (基建) / open (训练) | [[v7-features-gua037-038]] |
| GUA-041 | closed | [[v7-infra-gua041-049]] |
| GUA-042 | closed | (ABL-GD 调研) |
| GUA-043 | closed | (专利审计) |
| GUA-044 | closed | [[v7-infra-gua041-049]] |
| GUA-045 | closed | [[v7-strategy-gua045-053]] |
| GUA-047 | closed (误判) | [[v7-infra-gua041-049]] |
| GUA-048 | open (P2) | [[v7-infra-gua041-049]] |
| GUA-049 | closed (P0) | [[v7-infra-gua041-049]] |
| GUA-050 | open | [[v7-features-gua037-038]] |
| GUA-051 | closed | [[v7-strategy-gua045-053]] |
| GUA-052 | closed | [[v7-strategy-gua045-053]] |
| GUA-053 | open (仅文档) | [[v7-strategy-gua045-053]] |
| GUA-059 | closed (阶段 1 ✅) | [[v7-bc-training-gua059-061]] |
| GUA-060 | closed (路线终止) | [[v7-bc-training-gua059-061]] |
| GUA-061 | **open (当前)** | [[v7-bc-training-gua059-061]] |

## 当前阻塞

- **GUA-061**：模块化架构 — 从 M3 提取组牌逻辑封装 GroupingEngine
- BC argmax collapse 是理论必然（GUA-060 关单理由）
- 正确路径：组牌 → 角色定位 → 记忆追踪 → 动态调整 → 动作选择

## 涉及模块

- `src/v/nn/features/static_features.py`（124 维）
- `src/v/nn/features/dynamic_features.py`（LSTM 64 维）
- `src/v/nn/features/memory_tracker.py`（24 维）
- `src/v/nn/guards/v7_guards.py`（R01~R06）
- `src/v/nn/training/bc_dataset.py` / `bc_trainer.py`
- `src/decision/ultimate_win_rate_engine_v7.py`
- `src/train/ultimate_win_rate_training.py`
