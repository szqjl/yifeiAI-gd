---
type: concept
title: "Guard-Heuristic 三层决策管道"
sources:
  - docs/guandan-brain/ISSUES.md
tags:
  - architecture
  - v7
  - decision
status: current
related_gua:
  - GUA-065
  - GUA-068
  - GUA-069
  - GUA-070
  - GUA-071
  - GUA-075
date: 2026-06-19
---

# Guard-Heuristic 三层决策管道

V7 引擎当前(2026-06-19 战略转向后)决策架构,由三层独立组件构成。

## 层级结构

### Layer 1: Guard 硬排除
- 15+ 条独立 guard(R01-R15+)
- 每条 guard 是单一职责的硬规则,秒级 pytest
- 命中即强制排除,不进入后续决策
- 代表: [[gua-065|GUA-065]] 队友保护 / [[gua-068|GUA-068]] 抑制牌 / [[gua-069|GUA-069]] 超弱角色 / [[gua-070|GUA-070]] 拆对子保护

### Layer 2: Heuristic 软排序
- 8 优先级引擎([[gua-071|GUA-071]])
- 候选动作按优先级打分排序
- 牌力评分 5 维加权: 炸弹 0.3 + 手数 0.3 + 回收 0.1 + 灵活 0.1 + 去单化 0.2
- 不做硬排除,只做软选择

### Layer 3: validate 兜底
- 最终合法性检查
- card_mask 覆盖所有合法出牌
- 应对 card_mask 退化保护([[gua-072|GUA-072]])

## 关键优势
- Guard 可独立测试,失败定位快
- Heuristic 调整不影响 Guard 体系
- validate 是最后防线,绝不允许非法动作

## 当前问题
- 2026-06-19 综合批跑副胜率 2.4%,远低于 [[gua-065|GUA-065]] 25.5% 基线
- Heuristic 8 优先级尚未完整实现
- 需补充 [[gua-072|GUA-072]] 规则记牌提供 24 维 state_vector

## 演进方向
- [[gua-075|GUA-075]] 推荐法改造:Heuristic 反向输出推荐而非排序
- [[gua-078|GUA-078]] 残局智能体作为残局子管道的独立实现
