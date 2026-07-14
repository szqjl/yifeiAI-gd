---
type: concept
title: "组牌引擎 v2 评分公式"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/iterations/v7-grouping-v2-gua062.md
tags:
  - v7
  - grouping
  - scoring
status: current
related_gua:
  - GUA-062
date: 2026-06-19
---

# 组牌引擎 v2 评分公式

## 五维加权
```
score = 0.3 * bomb_score
      + 0.3 * hand_count_score
      + 0.1 * recovery_score
      + 0.1 * flexibility_score
      + 0.2 * de_singleton_score
```

### 维度说明
| 维度 | 权重 | 含义 |
|------|------|------|
| 炸弹 | 0.3 | 炸弹数量与价值 |
| 手数 | 0.3 | 总手数（越少越好） |
| 回收 | 0.1 | 兜底大牌评估（`_score_recovery_static`）|
| 灵活 | 0.1 | 应对变化的灵活度 |
| 去单化 | 0.2 | 减少单张，提升牌型结构 |

## 角色阈值
按队友角色（主攻/超弱/助攻）调整各维度权重 — 例如超弱角色提高"回收"权重。

## 关联
- [[gua-062]] — GUA-062 实体
- [[v7-grouping-v2-gua062-summary]] — 迭代记录
