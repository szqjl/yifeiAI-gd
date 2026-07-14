---
type: concept
title: "禁止伪关单原则（构造态 + 零退化）"
sources:
  - docs/guandan-brain/issues/GUA-084-completion.md
  - docs/guandan-brain/issues/GUA-085-completion.md
tags:
  - methodology
  - validation
  - closure-principle
  - pytest
  - batch-evaluation
status: current
related_gua:
  - GUA-084
  - GUA-085
date: 2026-06-29
---

# 禁止伪关单原则（构造态 + 零退化）

## 核心论点

> 掼蛋两次发牌完全相同的概率约为 10⁻⁵⁸，因此**关单不能依赖批跑复现同副牌**。

批跑（[[batch-evaluation]]）的统计有效性与"复现同一副牌"的目标**根本矛盾**：
- 批跑的价值在于"大量随机副的胜率聚合"
- 单一副的精确复现要求两次发牌序列完全一致（概率极低）
- 把"批跑中偶发遇到目标副"当作关单证据 = **伪关单**

## 正确的关单路径

### 1. pytest 构造态

针对具体缺陷构造**确定性的手牌状态**：

```python
def test_gua084_five_star_bomb_protection():
    # 构造 5+ 同点场景
    hand = construct_hand([5, 5, 5, 5, 5, ...])
    plans = grouping_engine._enumerate_plans(hand)
    # 断言保炸核，未整炸 dump
    assert has_bomb_first_candidate(plans)
```

### 2. 零退化批跑

修复前后跑同一批次的副局，验证：
- 胜率不退化（核心 KPI）
- 关键场景覆盖率不退化
- 推荐法分支不退化

## 适用范围

适用于所有结构补丁类缺陷的关单：

| 缺陷 | 验证方式 |
|------|----------|
| [[gua-084]] 五星炸保护 | 构造态 + 零退化批跑 |
| [[gua-085]] 领出保 SF/炸核 | 构造态 + 零退化批跑 |
| [[gua-081]] 三带二禁吃炸对 | 构造态（与 R-G084-1 协同） |

## 错误示例（伪关单）

❌ "我在批跑中观察到一次与回放相同的副，修复后那副确实过了，所以关单"
- 概率约 10⁻⁵⁸，本质不可能
- 即使凑巧"看到"，也不构成统计证据

## 正确示例

✅ "我构造了一个 count≥4 的三带二场景，修复前会吃炸对，修复后不会"
✅ "修复前后跑 10000 副，胜率从 X% 提升到 Y%，无回退"

## 关联概念

- [[batch-evaluation]] 批跑评测体系
- [[gua-080|组牌冻结]] KPI 条款
- [[局不等于副]] 数据解读口径
