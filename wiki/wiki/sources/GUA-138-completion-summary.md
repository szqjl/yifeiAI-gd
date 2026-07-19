---
type: source-summary
title: "GUA-138 完成定义摘要"
sources:
  - docs/guandan-brain/issues/GUA-138-completion.md
tags:
  - gua-completion
  - lru-cache
  - grouping-engine-performance
status: current
related_gua:
  - GUA-061
  - GUA-137
  - GUA-139
date: 2026-07-16
---

# GUA-138 完成定义摘要

## GUA 元信息

- **标题**：grouping_engine 推理性能优化
- **状态**：draft（2026-07-08 待登记）
- **优先级**：推断 P1（性能，非功能）
- **关联**：[GUA-061] grouping_engine / [GUA-137] 整手结构推断 / [GUA-139] 增量计算（未来）

## 核心改动

### _GroupingPlanCache LRU(64)
```python
class _GroupingPlanCache:
    """LRU(64) cache: (hand, cur_rank) → GroupingPlan"""
    def __init__(self, capacity=64):
        self._cache = OrderedDict()
        self._capacity = capacity
    
    def get_or_compute(self, hand, cur_rank, compute_fn):
        key = (frozenset(hand), cur_rank)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        plan = compute_fn(hand, cur_rank)
        self._cache[key] = copy.deepcopy(plan)  # 深拷贝防污染
        if len(self._cache) > self._capacity:
            self._cache.popitem(last=False)
        return plan
```

### 关键设计

1. **深拷贝防污染**：`GroupingPlan` 缓存返回前 deepcopy，避免下游修改污染缓存
2. **失效机制**：`cur_rank` 变化即失效（不同进贡阶段的牌级不同）
3. **key 设计**：`frozenset(hand)` — 牌组合的不可变表示
4. **容量**：64 条（覆盖典型对局的手牌变化序列）

### 性能提升

| 阶段 | 耗时 | 倍数 |
|------|------|------|
| 无缓存（GUA-137 直调） | 3.8ms / 次 | 1x |
| LRU 缓存命中 | < 0.1ms / 次 | **38x ~ 100x** |
| 增量计算（[GUA-139] 未来） | O(1) | 理论最优 |

## GUA-061 frozen 声明

> ⚠️ 本 GUA §6 声称「GUA-061 已 frozen」，但已有页面 [[module-grouping-engine]] 显示 grouping_engine 仍在迭代。
>
> **澄清需求**：frozen 含义需要明确
> - (a) 仅接口 frozen（API 签名不变）
> - (b) 内部实现允许外部 LRU 包装（缓存层在外）
> - (c) grouping_engine 整个模块 frozen（包括未来 GUA-139 增量计算）

## 下游 / 后续

- [[gua-139]] 增量计算 — 旧 plan 减去出牌增量计算（O(N) → O(1)）
- [[gua-140]]（推测）贡牌重建场景下的缓存策略

## 相关 Wiki 页面

- [[gua-138]] — 实体页
- [[gua-061]] — grouping_engine 模块
- [[gua-137]] — 数据源上游
- [[gua-139]] — 后续增量计算
- [[module-grouping-engine]] — 模块页（含 frozen 状态澄清）
- [[sprint-precision-upgrade-chain]] — 升级链综合
