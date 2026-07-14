---
type: source-summary
title: "组牌-NN衔接设计（软引导 vs 硬约束）"
sources:
  - docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md
tags:
  - grouping
  - nn-bridge
  - architecture
status: current
related_gua:
  - GUA-062
  - GUA-063
  - GUA-064
  - GUA-065
  - GUA-076
  - GUA-080
  - GUA-091
date: 2026-07-01
---

# 组牌-NN衔接设计

## 来源信息

- **路径**：`docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md`
- **字符数**：20,015
- **核心主题**：V7 引擎中 Guard / NN / Heuristic 三层衔接方案

## 重要发现时间线

⚠️ **文档包含不同代际方案**，需明确时间线：

### §0 重大发现（2026-06-20）
- **"按方案点菜"**：组牌候选桥接，按角色+牌型选最优方案
- 与后续方案**不同代际**

### §1-7 角色驱动前置过滤（2026-06-22 之后）
- Guard → _group_consistency_filter → NN/heuristic
- **主攻**：剔除拆 core 动作
- **助攻**：全部放行
- **硬例外**：自己 ≤5 张 / 对手 ≤2 张 / R16 队友送单

## 核心组件

| 组件 | GUA | 说明 |
|------|-----|------|
| MemoryTracker | — | decide 入口 ①b |
| _heuristic_select | [[gua-071]] | 4 优先级启发式（替代 NN） |
| _group_consistency_filter | R16 | 组牌一致性过滤 |
| _stage_mid_dispatch | [[gua-091]] | 中局入口调度 |
| grouping_engine v2 | — | 24 维评分 / A→2 包接 / NO_STRAIGHTS 双变体 / SF_FIRST 多 pass |

## 三缺口分析（GUA-063）

1. **候选桥接缺口**：组牌候选如何喂给 NN
2. **一致性缺口**：NN 输出与组牌候选的过滤规则
3. **回退缺口**：NN 失败时回退到 heuristic

## 跨引用

- [[gua-063]] — 三缺口问题
- [[gua-076]] — 组牌方案完整性
- [[gua-080]] — 拆炸时序押后
- [[gua-091]] — stage_2 中局入口
- [[bc-argmax-collapse]] — NN 失败模式
- [[three-layer-hybrid-architecture]] — 终极架构方向
```

---
