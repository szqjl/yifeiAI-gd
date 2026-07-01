---
tags: [M1, strategy, GUA-022, GUA-014, team-win-rate]
created: 2026-04-21
updated: 2026-05-31
topic: M1 队胜率策略攻关
related: [[M1-Development]], [[m1-pass-gua020-021]]
---

# M1 队胜率策略攻关（GUA-022 / GUA-014）

> 来源：[[ITERATIONS]] 2026-04-21 ~ 2026-05-31（10 条迭代）

## 策略迭代时间线

| 日期 | 迭代名 | 关键改动 | 队胜率 |
|------|--------|----------|--------|
| 2026-04-21 | GUA-022/014 共用层落地 | `strategy_engine.py` 对手冲关减弱队友让牌；`enhanced_priority_system.py` 钢板/三连对权重 | 0/10 |
| 2026-04-21 | GUA-022/014 第二轮验收 | 进一步收紧队友保护逻辑；pytest 7→10 passed | 0/10 |
| 2026-04-21 | victoryNum 链路修复后复跑 | `yf1_m1.py`/`yf2_m1.py` pending 回填机制 | 0/10（vn 非空率 100%） |
| 2026-05-25 | Phase 2 context 补全 | `stage_router._build_context` 上下文注入；`strategy_engine._should_full_protect` | 0/10 |
| 2026-05-25 | PHASE2-003 拆牌优先级 | `enhanced_priority_system.py` rank 拆牌惩罚 + Trips 降权 | 0/10 |
| 2026-05-25 | PHASE2-004 队级进攻 | `TeamOffensiveStrategy` + `find_minimal_beat_action` | 0/10 |
| 2026-05-26 | PHASE2-005 清 yf2 近似 PASS | 智能路由缓存 coerce；接风判主动 | 0/10（yf2 近似 PASS 8→1 ✅） |
| 2026-05-26 | Hermes 验收 | pytest 19/19 passed；yf1 近似 PASS 仍 10 ⚠️ | 0/10 |
| 2026-05-31 | M1 净盘 12 局批跑 | 无代码变更，纯 KPI 观测 | **0/12（0%）** |
| 2026-05-31 | **M1 frozen 定音** | M1 = frozen / 非交付线 | **GUA-022 closed** |

## 关单结论

- M1 队胜率始终 0%，无法突破 lalala
- ISUES 增「引擎维护策略」— M1 frozen，KPI 迁 M3
- M1 0/12 vs M3 7/10 同机对照确认非口径错误
- P0 guard 改 `m3_decision_engine`，组牌/牌力走 V5+

**涉及文件**：
- `src/decision/strategy_engine.py`
- `src/decision/stage_router.py`
- `src/decision/phase_handlers.py`
- `src/decision/enhanced_priority_system.py`
- `src/decision/intelligent_router.py`
- `src/communication/yf1_m1.py` / `yf2_m1.py`
