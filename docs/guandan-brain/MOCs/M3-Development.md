---
tags: [MOC, M3, decision-engine, GUA-024~GUA-036]
created: 2026-06-17
topic: M3 决策引擎开发全记录索引
---

# M3 决策引擎开发

> M3 = 主交付引擎 + `IDecisionProvider`。P0 guard 改 `m3_decision_engine`。

## 迭代文件

- [[m3-integration-gua024-028]] — 引擎集成与场态修复（GUA-024/025/027/028）
- [[m3-strategy-gua026-029]] — 三带二拆牌保护 + 炸弹规则（GUA-026/029）
- [[m3-guards-gua031-036]] — 传牌/算牌/残局 guard（GUA-031~036）
- [[m3-skills-mapping-gua030]] — 技能映射与原则评估（GUA-030 + §16–§22）

## GUA 索引

| GUA | 状态 | 文件 |
|-----|------|------|
| GUA-024 | closed | [[m3-integration-gua024-028]] |
| GUA-025 | closed | [[m3-integration-gua024-028]] |
| GUA-026 | closed | [[m3-strategy-gua026-029]] |
| GUA-027 | closed | [[m3-integration-gua024-028]] |
| GUA-028 | closed | [[m3-integration-gua024-028]] |
| GUA-029 | closed | [[m3-strategy-gua026-029]] |
| GUA-030 | closed | [[m3-skills-mapping-gua030]] |
| GUA-031 | closed | [[m3-guards-gua031-036]] |
| GUA-032 | closed | [[m3-guards-gua031-036]] |
| GUA-034 | closed | [[m3-guards-gua031-036]] |
| GUA-035 | closed | [[m3-guards-gua031-036]] |
| GUA-036 | closed | [[m3-guards-gua031-036]] |

## KPI 速查

- 队胜率稳定区间：**55.6% ~ 81.0%**
- GUA-034/035 后峰值：**78.8%（26/33）**
- GUA-036 回落：**52.2%（36/69）** — 非 solo 场景下限更差

## 涉及模块

- `src/m/m3/m3_decision_engine.py`
- `src/m/m3/m3_utils.py`
- `src/game_logic/trick_state.py`
- `src/communication/platform_act.py`
- `src/communication/yf1_m3.py` / `yf2_m3.py`
