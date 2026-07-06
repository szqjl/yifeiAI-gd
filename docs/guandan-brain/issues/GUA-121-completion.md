# GUA-121 完成定义（助攻 P1 续包 · 117-P1-misc）

> 登记 **2026-07-05**。设计真源：[`助攻出牌-阶段划分设计口径.md`](../助攻出牌-阶段划分设计口径.md) §5 / §4.4 B7/B8 / §2.2。**不挡 GUA-117 v1**；可分子 PR 交付。

## 子任务（121-a … 121-e）

| 子任务 | 内容 | 落点倾向 | 验收 |
|--------|------|----------|------|
| **121-a** | **P1-R09**：rest=5 时 R09 vs Q2 `assist_prefer` 优先级 | 净盘批跑 + 构造态；`assist_prefer_table` / R09 | ≥1 批跑对比或构造态说明优先级 |
| **121-b** | **2.2 炸送同款**：最小炸拿权 → 出刚被封同款 | 091 `assist_bomb_then_same_shape` 或等价 intent | 构造态：封队友 → 炸 → 同款 feed |
| **121-c** | **B7**：红桃逢人配跑自身、不预留送队友 | guard / group_filter | role=助攻 构造态 ≥1 |
| **121-d** | **B8**：禁抢头游、耗大牌断队友链 | guard + 075 评分 | role=助攻 构造态 ≥1 |
| **121-e** | **sprint_fire 助攻开放**：L85 `mid_sprint_fire_bomb` 对助攻/超弱 | `_maybe_recommend_sprint_fire_bomb` 角色门 | 与 GUA-102 边界 pytest；助攻可触发或显式 PASS |

## 关单条件

| 项 | 要求 |
|----|------|
| **范围** | 121-a–121-e **至少完成用户本轮点名的子集**；全包关单需五项均有 pytest 或批跑证据 |
| **回归** | `pytest tests/test_gua117_*.py tests/test_gua091_stage_mid_dispatch.py -q` 不退化 |
| **文档** | `ITERATIONS` 按子任务追加实现行；ISSUES GUA-121 备注更新 |

**建议顺序**：121-a（批跑）可与 119/120 并行；121-b 依赖 091 炸弹路径稳定；121-c/d 随 117 Layer0 或 120 group_filter；121-e 依赖 GUA-102 信号稳定。
