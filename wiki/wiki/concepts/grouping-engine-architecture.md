---
type: concept
title: "组牌引擎双轨：scanner 9 维 vs engine 24 维 + 静默降级路径"
status: current
date: 2026-06-22
sources:
  - docs/guandan-brain/issues/GUA-080-completion.md
  - docs/guandan-brain/playbooks/PB-001-gua072-bomb-break-timing.md
tags:
  - v7
  - grouping-engine
  - architecture
  - degradation
related_gua:
  - GUA-080
  - GUA-054
  - GUA-061
  - GUA-062
related_workflow: WF-05
---

# 组牌引擎双轨架构

## 双轨定义

V7 组牌引擎存在**两套并行的中间表示**：

| 轨 | 模块 | 维度 | 角色 | 状态 |
|----|------|------|------|------|
| **主路径** | `src/v/nn/features/grouping_engine.py` | **24 维** | V7 NN 特征工程的权威输入 | 目标态（GUA-061 open） |
| **降级基线** | `grouping_scanner`（旧模块） | **9 维** | 历史遗留 / 应急降级 | 长期 open（GUA-054） |

## 24 维主路径（engine）

- 完整牌型分类：单张、对子、三张、三连对、顺子、连三、钢板、炸弹、王炸
- 配套 `memory_tracker.py` 维护跨轮组牌状态
- 唯一权威验收入口：`scripts/checks/check_grouping_engine.py`（WF-05）
- 阻塞 GUA：GUA-080（中炸 vs 三连对拆炸取舍）

## 9 维降级基线（scanner）

- 简化牌型分类，丢失部分细节（如钢板 vs 三连对的区分）
- 当前**唯一**作用：主路径失败时的应急回退
- GUA-054 open：长期未关单，是「债」

## 四条静默降级路径（重要！）

`memory_tracker.py` 在 `grouping_engine` 导入失败时会触发降级。原代码存在 **4 条静默 fallback 路径**：

| 路径 | 触发条件 | 当前行为 | 风险 |
|------|----------|----------|------|
| **A** | `grouping_engine` 导入失败 → 自动 fallback 到 scanner | 静默切换 | ⚠️ 高（生产环境不可见） |
| **B** | 24 维特征计算异常 → 降级到 9 维 | 静默 + 日志 | ⚠️ 中 |
| **C** | 某种牌型识别超时 → 用简化规则 | 静默 | ⚠️ 中 |
| **D** | 整体引擎崩溃 → 用 heuristic 默认值 | 静默 | ⚠️ 极高 |

> **R-G080-4（待定音）**：**生产端禁止静默降级**。所有 fallback 必须显式抛异常或返回明确的 degraded 标记，由上层决策是否接受降级结果。

## GUA-054 vs GUA-080 关系

- **GUA-054**：scanner 9 维是「债」，应被 engine 24 维完全替代
- **GUA-080 R-G080-4**：禁止静默降级，但未给关单计划

两者**强耦合**，可能的处置方案：

| 方案 | 含义 | 代价 |
|------|------|------|
| **方案 1：合并** | GUA-054 并入 GUA-080，统一关单 | 失去历史归属 |
| **方案 2：新建** | 新建 GUA-081「scanner 9 维下线计划」 | 编号蔓延 |
| **方案 3：维持分离** | GUA-054 保留为「基线债」，GUA-080 加 R-G080-4 子项 | 关联复杂 |

**建议**：方案 1（合并），由 GUA-080 关单时一并下线 scanner。

## 关联代码

- `src/v/nn/features/grouping_engine.py` — 主路径
- `src/v/nn/features/memory_tracker.py` — 降级触发点
- `scripts/checks/check_grouping_engine.py` — WF-05 验证
- `scripts/analysis/compare_sf_detection_vs_multipass.py` — SF 检测 vs multi_pass 对照

## 关联阅读

- [[gua-080]] — 当前主战场
- [[gua-054]] — 9 维基线债
- [[gua-061]] — 24 维主路径
- [[gua-062]] — 组牌 v2 基线
- [[playbook-pb-001]] — 拆炸时序押后（关键修复模式）
