---
tags: [MOC, M1, GUA-020, GUA-021, GUA-022, GUA-014]
created: 2026-06-17
topic: M1 开发全记录索引
---

# M1 开发（frozen）

> M1 = frozen / 非交付线。KPI 迁 M3，P0 guard 走 `m3_decision_engine`。

## 迭代文件

- [[m1-pass-gua020-021]] — PASS 率分析与问题 PASS 清零（GUA-020/021）
- [[m1-strategy-gua022]] — 队胜率策略攻关（GUA-022/014）

## GUA 索引

| GUA | 状态 | 文件 |
|-----|------|------|
| GUA-020 | closed | [[m1-pass-gua020-021]] |
| GUA-021 | closed | [[m1-pass-gua020-021]] |
| GUA-022 | closed (frozen) | [[m1-strategy-gua022]] |
| GUA-014 | closed (联动) | [[m1-strategy-gua022]] |

## 关键结论

- yf1/yf2 PASS 率接近（~55%），无系统性差异
- M1 队胜率始终 0%，无法突破 lalala
- M1 0/12 vs M3 7/10 同机对照 → M1 frozen

## 涉及模块

- `src/decision/stage_router.py`
- `src/decision/phase_handlers.py`
- `src/decision/strategy_engine.py`
- `src/decision/enhanced_priority_system.py`
- `src/decision/intelligent_router.py`
- `src/decision/rule_based_decision_engine_m1.py`
- `src/communication/yf1_m1.py` / `yf2_m1.py`
