---
type: synthesis
title: "V7 引擎当前状态综合分析"
sources:
  - docs/guandan-brain/v7-win-rate-history.md
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
  - docs/guandan-brain/工作流.md
  - docs/knowledge/skills/07_opening/end position.md
  - docs/governance/M-V-Series-治理方案.md
tags:
  - v7
  - synthesis
  - current-state
  - nn-engine
status: current
related_gua:
  - GUA-064
  - GUA-065
  - GUA-071
  - GUA-075
  - GUA-078
  - GUA-080
  - GUA-081
  - GUA-114
date: 2026-07-03
---

# V7 引擎当前状态综合分析

## 一句话现状

> **V7 引擎累计队胜率 < 1%（1/141+），正面对三线作战：残局管线 / heuristic 退化 / BC argmax collapse。**

## KPI 快照（截至 2026-07-03）

| 指标 | 数值 | 来源 |
|------|------|------|
| 累计局数 | ≈ 141 | v7-win-rate-history.md |
| 累计队胜 | 1 | 同上 |
| 累计队胜率 | ≈ 0.7% | 同上 |
| 历史副胜率峰值 | 25.5% (GUA-065) | 同上 |
| 历史副胜率谷值 | 2.4% (GUA-071) | 同上 |
| BC v3 val_acc | 80.88% | BC 训练日志 |
| 实战队胜（BC v3） | 0/12 | v7-win-rate-history.md |
| 实战副胜（BC v3） | 8/164 | 同上 |
| 残局模块激活率 | 66.0% (GUA-078) | 同上 |

## 三线作战

### 线 1：BC Argmax Collapse

- **现象**：BC v3 val_acc 80.88%，但实战 0/12 队胜、8/164 副胜
- **根因**：NN 输出 argmax 在实战分布上坍缩到单一牌型
- **应对**：_heuristic_select 替代 NN argmax（GUA-071），但又引入新退化
- **文档铁律**：训练指标**不能**作为实战失败的辩解

### 线 2：Heuristic 退化

- **现象**：副胜率从 GUA-065 的 25.5% 跌到 GUA-071 的 2.4%（-23.1pp）
- **根因**：_heuristic_select 替代 NN 后选择面收窄
- **诊断**：WF-12 R-D05 启发式劣选

### 线 3：残局管线激活 ≠ 收益

- **现象**：残局模块激活率 66.0%，但副胜仍 0
- **根因**：离线覆盖未转化为实战收益（Q1~Q3 战术执行失败）
- **关联**：GUA-075 推荐引擎、GUA-078 残局预处理器

## 当前 P0 GUA

| GUA | 主题 | 状态 |
|-----|------|------|
| GUA-064 | ??? | open |
| GUA-080 | card_mask / 组牌退化 | open |
| GUA-081 | _heuristic_select 退化 | open |
| GUA-114 | ??? | open |

## 关键矛盾 / 张力

1. **BC v3 高 val_acc vs 实战 0 队胜** → "训练-实战鸿沟"
2. **残局 66% 激活率 vs 0 副胜** → "覆盖-收益脱节"
3. **heuristic 替代 NN 后 -23.1pp** → "替代品也退化"
4. **v7-win-rate-history.md 末尾格式不一致** → "数据治理债务"

## 下一步建议

1. **短期（1-2 周）**：
   - 关闭 GUA-080（R-G080-4 零退化校验落地）
   - 修复 GUA-081（_heuristic_select 退化解）
   - 规范化 v7-win-rate-history.md 末尾格式
2. **中期（1 个月）**：
   - 解决 BC argmax collapse（探索 ensemble / temperature scaling）
   - 残局管线实战化（Q1~Q3 战术验证）
3. **长期**：
   - 达成 GUA-039b 阈值（30 局 ≥ 30% 队胜率）

## 关联

- [[v7-win-rate-history-summary]] — KPI 真源
- [[endgame-pipeline]] — 残局管线概念
- [[workflow-decision-trace]] — WF-12 决策链路
- [[win-rate-kpi]] — 队胜率定义
- [[engine-v7]] — V7 引擎实体
- [[M-V-Series-治理方案-summary]] — V 系列治理
