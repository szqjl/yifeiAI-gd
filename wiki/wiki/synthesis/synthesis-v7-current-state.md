---
type: synthesis
title: "V7 当前状态综合分析"
sources:
  - docs/guandan-brain/README.md
  - docs/guandan-brain/v7-win-rate-history.md
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/ITERATIONS.md
tags:
  - v7
  - synthesis
  - state-of-play
status: current
related_gua:
  - GUA-039b
  - GUA-064
  - GUA-065
  - GUA-071
date: 2026-06-29
---

# V7 当前状态综合分析

## 一句话结论
V7 NN 引擎历经 BC v1→v3（val_acc 35%→80.88%），但实战副胜率长期接近 0%；当前以 heuristic_select 四优先级作为实战兜底，单行达 25.5% 巅峰，综合批跑仍仅 3.7%。

## 关键 KPI（截至 2026-06）
| 指标 | 数值 | 备注 |
|------|------|------|
| BC v3 val_acc | 80.88% | 训练指标 |
| 实战副胜（早期） | 0/164 | 与 val_acc 严重脱节 |
| 综合批跑胜率 | 3.7% | 同月数据 |
| 单行最高副胜 | 25.5% | GUA-065 |
| 累计局队胜 | 1/138 ≈ 0.7% | 极低 |

## 当前破局方向

### 主线：heuristic_select 四优先级
- 已切换（GUA-071）
- 实战可用但缺乏系统性优化

### 副线：Guard 叠加
- 出现 [[guard-overlap-puzzle]] 悖论
- 暂停推进

### 储备：BC 模型
- argmax collapse（GUA-064）未根治
- val_acc 与实战脱节巨大

## 与 README 叙事的张力
README 强调「M3 主交付、队 KPI 只看 M3 批跑」，但实际：
- 最新 GUA-061~080 全在 V7 线
- 批跑数据全聚焦 V7
- M3 线无 KPI 护栏文件

→ **V7 已成为事实焦点，建议更新 README 叙事**

## 下一步建议

### P0
1. 巩固 heuristic 方案，争取综合批跑 ≥15%
2. 解决 Guard 叠加悖论
3. 决定 BC 路线是否继续

### P1
4. 补充 M3 线 KPI 护栏（治理对称）
5. 更新 README 叙事对齐现状

## 相关页面
- [[engine-v7]]
- [[engine-m3]]
- [[v7-kpi-guardrail]]
- [[heuristic-vs-bc]]
- [[bc-collapse-pattern]]
- [[gua-071]]
- [[gua-064]]
