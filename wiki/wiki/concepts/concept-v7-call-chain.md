---
type: concept
title: "V7 引擎调用链（10 步管线）"
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

# V7 引擎调用链（10 步管线）

## 管线总览

V7 决策引擎的完整调用链，是后续所有 V7 调整的参考框架。

## 10 步详解

```
1. 通信层（yf1_v7/yf2_v7.process_message, line 114）
   ↓ 收到 game_state JSON
2. decide() 入口（ultimate_win_rate_engine_v7.py, line 121）
   ↓ 进入决策主流程
3. 前置守卫（v7_guards.filter_action_list, line 459）
   ↓ 合法动作集
4. 记忆同步（memory_tracker, line 255）
   ↓ 33/48 维记忆
5. 4 段特征拼接
   ├── 5a. 静态特征（static_features, line 215）→ 124 维
   ├── 5b. 局面信念（static_features, line 127）→ 8 维
   ├── 5c. 动态特征 LSTM（dynamic_features, line 179）→ 64 维
   └── 5d. 记牌（memory_tracker, line 255）→ 33/48 维
   ↓
6. 512 维拼接（含补零预留）
   ↓
7. NN 前向（UltimateWinRateNet 512→64→32→512, training.py line 77）
   ↓ 动作 Q 值
8. 后置守卫（v7_guards.validate_decision, line 556）
   ↓ 校验动作
9. 规则回退
   ↓ 兜底出牌
```

## 耗时分布

| 阶段 | 占比 |
|------|------|
| NN 推理 | ~60% |
| 组牌枚举 | ~20% |
| 其他 | ~20% |
| **总超时** | **0.8s** |

## 关键约束

- 总决策超时 0.8s
- 双重数据通道：WebSocket → latest_victory_num.json + stdout → 日志
- P0 守卫 vs V5+ 知识层：M3 做 P0 guard，V5+ 做组牌/牌力

## 关联

- wiki/entities/engine-v7.md
- [[gua-054]]（组牌质量中间表示）
- [[gua-055]]（动作空间二阶段过滤）
- gua-057（记牌模块）
- gua-058（策略模块）
