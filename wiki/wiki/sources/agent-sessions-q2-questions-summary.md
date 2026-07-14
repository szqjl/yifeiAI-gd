---
type: source-summary
title: "关键问题深度展开 (Agent Session 02) - 摘要"
sources:
  - docs/analysis/agent-sessions/02-critical-questions.md
tags:
  - agent-session
  - questions
  - root-cause
status: current
related_gua:
  - GUA-014
  - GUA-022
  - GUA-033
  - GUA-042
date: 2026-06-18
---

# 关键问题深度展开 (Agent Session 02) - 摘要

## 文档定位

Hermes Agent 对项目五大关键问题的深度展开，每个问题包含：现象、证据、根因、行动项。

## 五个关键问题

### Q1：V7 引擎的当前状态与下一步？
- **现状**：BC 热启动完成，84.3% 分数但实战胜率 0%
- **根因**：BC→RL 链路未完成；BC 分数高但泛化差
- **行动**：GUA-039 启动自对弈 Actor（套路五）；不要用 BC 分数判断进度

### Q2：哪些 GUA 是 P0 open？
- **当前 P0**：GUA-022（M1 队胜率 0%）、GUA-014（拆牌与优先级）
- **本次决策**：GUA-042（ABL-GD 168 伪动作）→ 弃用
- **已闭环**：GUA-020（PASS 率差无明显差异）、GUA-021（近似 PASS 清零）

### Q3：最近一次批跑胜率？
- M3 70%（口径未明：局数、日期、vs 谁）
- V7 0%（BC 阶段，参考价值有限）
- 需建立 wiki-minimax/concepts/batch-evaluation.md 标准（50-100 局）

### Q4：M3 决策引擎已知缺陷？
- 缺陷集中在 Lv1 个别决策（拆牌/组牌）
- Lv2 队伙联动完全缺失
- Lv3 全局对抗未实现
- 详见 synthesis-m1-zero-winrate

### Q5：团队（yf1_m3 + yf2_m3）协作模式？
- M1/M2 时代：两人共享 src/decision/，仅 client 端口不同
- M3 时代：开始分化（yf1_m3 偏规则 / yf2_m3 偏网络）
- GUA-020 证明 M1 时代两人代码差异无意义
- **模式**：pair-programming 风格，分工按"引擎迭代版本"对齐

## 跨资料冲突识别

| 冲突 | 处理 |
|------|------|
| M3 70% 胜率无原始数据 | 标记为待验证（wiki-minimax/concepts/batch-evaluation.md 中追溯） |
| yf_v5 vs yf1_m3 命名 | 建议：迭代关系，yf1_m3 = yf1_v5 升级版 |
| V7 失败 vs 主迭代 | 同一项目不同时期，需在 wiki/entities/engine-v7.md 中明确 |

## 交叉引用

- 项目状态 → [[agent-sessions-q1-status-summary]]
- 深度解读 → [[agent-sessions-q3-deep-summary]]
- 批跑体系 → wiki-minimax/concepts/batch-evaluation.md
