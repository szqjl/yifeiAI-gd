---
type: concept
title: "M3 Guard 设计模式"
sources:
  - docs/guandan-brain/iterations/m3-guards-gua031-036.md
related_gua:
  - GUA-031
  - GUA-032
  - GUA-034
  - GUA-035
  - GUA-036
tags:
  - m3
  - guard
  - design-pattern
date: 2026-06-18
---

# M3 Guard 设计模式

## 概览

M3 决策引擎 P0 guard 落地时的统一设计范式，已应用于 5 个 guard（GUA-031/032/034/035/036）。

## 四要素

1. **`_guaNNN_*` 前缀函数**：guard 内部函数统一以 GUA 编号命名，方便代码审计与 wiki 反向链接
2. **pytest 6+ passed**：guard 单元测试至少 6 条用例全过
3. **净盘批跑**：guard 启用后批跑对局无遗留 PASS / 异常分布
4. **`[0,3,0,3]` 异常检测**：多玩家对称性退化的兜底检测（详见 [[GUA-036]]）

## 模板

```python
def _guaNNN_decide(trick_state, hand, ctx):
    # 1. 触发条件判定
    if not _guaNNN_should_trigger(...):
        return None
    # 2. 候选动作生成
    candidates = _guaNNN_generate_candidates(...)
    # 3. 净盘校验
    if not _guaNNN_net_disk_ok(candidates):
        return None
    # 4. 选优
    return _guaNNN_pick_best(candidates, ctx)
```

## KPI 对接

| Guard | 批跑 KPI | 状态 |
|-------|---------|------|
| GUA-031 | 传牌：PASS 正常路径 | passed |
| GUA-032 | 记牌：vn非空率正常 | passed |
| GUA-034 | 残局拦头：78.8% | passed |
| GUA-035 | 对手剩张：78.8% | passed |
| GUA-036 | 控权+接风：52.2% | **regression** |

## 关联

- 批跑评测体系（回归对照表）
- [[GUA-036]]（异常回归案例）
