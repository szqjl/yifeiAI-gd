---
type: concept
title: "R-G080-4 卡牌/组牌零退化校验"
sources:
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
tags:
  - regression
  - r-g080-4
  - card-mask
  - grouping
status: current
related_gua:
  - GUA-080
date: 2026-07-03
---

# R-G080-4 卡牌/组牌零退化校验

## 概念

R-G080-4 是针对 GUA-080（card_mask / 组牌退化）的**零退化校验方法**，确保 grouping_engine 输出不退化为空集或单牌。

## 触发场景

- `_run_grouping_engine` 失败
- `_basic_classify` 失败
- `_group_consistency_filter` 失败
- 任一上述 rg 输出空集

## 校验正则

```python
rg = r"_run_grouping_engine 失败|_basic_classify 也失败|_group_consistency_filter 失败"
```

## 实现位置

- `check_grouping_engine.py` — 单测入口
- pytest 用例名遵循 `test_r_g080_4_*` 规范

## 与 R-Dxx 的对应

| 失败模式 | R-Dxx | GUA |
|----------|-------|-----|
| `_run_grouping_engine 失败` | R-D04 | GUA-080 |
| `_basic_classify 也失败` | R-D04 | GUA-080 |
| `_group_consistency_filter 失败` | R-D04 | GUA-080 |
| card_mask 全 mask | R-D01 | GUA-080 |

## 关联

- [[gua-080]] — GUA-080 详情
- [[workflow-decision-trace]] — R-Dxx taxonomy
- [[WF-12-yf-decision-trace-summary]] — WF-12 工作流
