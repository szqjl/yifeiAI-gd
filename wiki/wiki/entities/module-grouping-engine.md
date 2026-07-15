```markdown
---
type: entity-module
title: "组牌引擎（grouping_engine）"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - module
  - grouping
  - v7
status: current
related_gua:
  - GUA-062
  - GUA-063
date: 2026-07-15
---

# 组牌引擎

## 文件
- `grouping_engine.py`
- `ultimate_win_rate_engine_v7.py`（调用方）

## 版本演进
- **v1**：基础枚举
- **v2**（GUA-062）：5 维评分 + 6 方案枚举 + 牌力计分，10+ 次迭代

## 当前定位
**已从主导引擎降级为特征提供者**。在 V7 决策管线中：
1. 输出中间态（候选牌型）
2. 提供 `to_card_mask`, `is_core`, `group_size` 给 NN
3. 不再直接决定出牌

## 子模块
- `grouping_scanner` — 牌型扫描

## 关联
- [[grouping-engine-v2]] — v2 详细设计
- [[gua-062]] — v2 主轴 GUA
- [[gua-063]] — 组牌→NN 衔接
```

---
