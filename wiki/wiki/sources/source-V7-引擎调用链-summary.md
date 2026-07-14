---
type: source-summary
title: "V7 引擎调用链 - 资料摘要"
sources:
  - docs/guandan-brain/V7-引擎调用链.md
tags:
  - v7
  - architecture
  - call-chain
status: current
related_gua:
  - GUA-061
  - GUA-037b
  - GUA-050
  - GUA-054
  - GUA-055
  - GUA-057
  - GUA-058
date: 2026-06-18
---

# V7 引擎调用链 - 资料摘要

## 文档定位

V7 决策引擎的 10 步调用链路图谱，描述从通信层到最终出牌的完整管线。来源：`ultimate_win_rate_engine_v7.py` 及其依赖模块。

## 10 步调用链

| 步 | 模块/函数 | 关键产物 | 关联 GUA |
|----|----------|---------|----------|
| 1 | 通信层（yf1_v7/yf2_v7） | 收到 game_state JSON | — |
| 2 | decide() 入口 (line 121) | 进入决策主流程 | — |
| 3 | 前置守卫 (v7_guards.filter_action_list, line 459) | 合法动作集 | GUA-055 |
| 4 | 记忆同步 (memory_tracker) | 33/48 维记忆 | GUA-057 |
| 5a | 静态特征 (static_features, line 215) | 124 维 | — |
| 5b | 局面信念 (static_features, line 127) | 8 维 | GUA-050 |
| 5c | 动态特征 LSTM (dynamic_features, line 179) | 64 维 | GUA-037b |
| 5d | 记牌 (memory_tracker, line 255) | 33/48 维 | GUA-057 |
| 6 | 512 维拼接 | 含补零预留 | — |
| 7 | NN 前向 (UltimateWinRateNet 512→64→32→512) | 动作 Q 值 | GUA-060 |
| 8 | 后置守卫 (v7_guards.validate_decision, line 556) | 校验动作 | GUA-055 |
| 9 | 规则回退 | 兜底出牌 | — |

## 关键概念

- **512 维特征向量 = 静态 124 + 动态 64 + 信念 8 + 记忆 33/48 + 补零**
- **决策链耗时分布**：NN 推理 ~60% + 组牌枚举 ~20% + 其他 ~20%，总超时 0.8s
- **双重数据通道**：WebSocket → latest_victory_num.json + stdout → 日志
- **组牌引擎双模**：scanner(9 维轻量) vs engine(24 维 V3 模式 use_grouping_engine=True)

## 重要发现

- 组牌引擎 v2（GUA-062）评分算了但决策链仍走 BC argmax，未接入动作选择
- 详见 [[gua-062]]、[[concept-bc-argmax-collapse]]、[[concept-v7-call-chain]]
