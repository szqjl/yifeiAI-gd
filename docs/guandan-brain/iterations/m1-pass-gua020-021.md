---
tags: [M1, PASS-rate, GUA-020, GUA-021]
created: 2026-04-21
topic: M1 PASS率分析与问题PASS清零
related: [[M1-Development]], [[m1-strategy-gua022]]
---

# M1 PASS 率分析与问题 PASS 清零（GUA-020 / GUA-021）

> 来源：[[ITERATIONS]] 2026-04-21 段（5 条迭代）

## GUA-020：yf1 vs yf2 PASS 率对照

| 日期 | 迭代名 | 目标 | 关键结论 |
|------|--------|------|----------|
| 2026-04-21 | M1 对照与文档 | GUA-001, GUA-020 | yf1_m1 PASS 55.3% vs yf2_m1 64.6%；近似问题 PASS yf1=3, yf2=8 |
| 2026-04-21 | M1 GUA-020 扩样复测 | GUA-020 | 8 个 game_id，yf1 55.32% vs yf2 55.98%，差距缩小至 0.66% |
| 2026-04-21 | M1 GUA-020 达标样 | GUA-020 | 10 个 game_id，yf1 54.78% vs yf2 55.70%；**GUA-020 closed** |

**结论**：大样本下 yf1/yf2 PASS 率接近，无明显一方系统性更差。

## GUA-021：减少问题 PASS

| 日期 | 迭代名 | 目标 | 关键结论 |
|------|--------|------|----------|
| 2026-04-21 | M1 减少问题 PASS | GUA-021 | 12 局合计近似问题 PASS=20（未下降），GUA-021 保持 open |
| 2026-04-21 | M1 共用层收紧 PASS | GUA-021 | 改 `stage_router.py`、`phase_handlers.py`、`rule_based_decision_engine_m1.py`；新 3 局近似问题 PASS=0；**GUA-021 closed** |

**涉及文件**：
- `src/decision/stage_router.py`
- `src/decision/phase_handlers.py`
- `src/decision/rule_based_decision_engine_m1.py`
- `src/decision/intelligent_router.py`

**后续**：队胜率转 GUA-022。
