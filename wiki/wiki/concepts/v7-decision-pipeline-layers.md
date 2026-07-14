---
type: concept
title: "V7 决策管线 L0~L8"
sources:
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
  - src/v/nn/ultimate_win_rate_engine_v7.py
tags:
  - v7
  - engine
  - decision-pipeline
  - architecture
status: current
related_gua:
  - GUA-062
  - GUA-075
  - GUA-078
  - GUA-079
  - GUA-081
date: 2026-06-29
---

# V7 决策管线 L0~L8

## 概述

`UltimateWinRateEngineV7.decide()` 采用**自上而下、先命中先 return**的八层管线结构。每一层独立决策，匹配则立即返回，否则下沉到下一层。

## 管线层级

| 层级 | 名称 | 职责 | 关键函数/模块 |
|------|------|------|--------------|
| **L0** | 上下文与预处理 | 加载手牌/curRank/last_play/玩家身份 | `decide()` 入口 |
| **L1** | Guard 综合检查 | R01~R12 规则校验 | `v7_guards.py` / `_quick_guard_validate` |
| **L2** | 场景推荐 | 四场景匹配（领出/跟上家/卡下家/让对家） | `_recommend_play()` |
| **L2′** | 组牌保护拦截 | bomb/SF 不被错误拆分 | `_group_consistency_filter`（行 268-287 已改） |
| **L3** | 残局管线 | Q0~Q3 残局判定 | `src/v/nn/endgame/` |
| **L4** | 启发式规则 | 最小压制/拆炸时序/三带二 | `R11` / GUA-079 / GUA-081 |
| **L5** | BC argmax | BC 神经网络 argmax 选牌 | `bc_policy()` |
| **L6** | 规则引擎 fallback | M3 风格规则匹配 | `m3_fallback()` |
| **L7** | PASS | 兜底返回 PASS | `return PASS` |
| **L8** | 异常处理 | 异常捕获 + 日志 | `except` 块 |

## 关键特性

### 先命中先 return

```python
def decide(self, hand, last_play, cur_rank, ...):
    if L1_guard.check(...):         return L1_result
    if L2_recommend.match(...):     return L2_result  # ← L2′ 保护在内部
    if L3_endgame.trigger(...):     return L3_result
    if L4_heuristic.match(...):     return L4_result
    if L5_bc.argmax(...):           return L5_result
    if L6_m3_fallback(...):         return L6_result
    return PASS                      # L7
```

### 关键缺陷分布

| 层级 | 已知缺陷 | GUA |
|------|----------|-----|
| L1 | Guard 误拦截（R01~R12 个别 case） | GUA-065~071 |
| L2 | 命中路径跳过 L2′ 保护 | GUA-075 |
| L3 | 残局管线 Q0~Q3 边界 case | GUA-078 |
| L4 | 缺 fallback（8888 压 666+22） | GUA-081 |
| L5 | BC argmax collapse | GUA-060 |
| L6 | MemoryTracker 降级路径 | GUA-072 |

## L2′ 保护机制详解

L2 推荐管线命中后，**先经过 L2′ 保护拦截**再做最终返回：

1. **L2 命中**：四场景推荐器返回候选动作
2. **L2′ 检查**：调 `_group_consistency_filter(hand, candidate)`
3. **保护场景**：
   - 候选是 bomb 但实际是 SF → **拦截，回退到 L3**
   - 候选是 SF 但手牌中 SF 已被拆散 → **拦截，回退到 L4**
4. **GUA-075 历史**：行 268-287 修复前，命中路径**直接绕过** L2′ 导致 bomb/SF 被拆

详见 [[gua075-recommendation-pipeline]]。

## 关键指标

- **卡 2 级 80.5% 决策为单张**（vs 全局 66.4%）：见 [[bc-argmax-collapse]]
- **PASS-only 比例 ~26%**（描述性统计，handoff 2026-06-28）：见 [[offline-platform-v1006]]

## 关联页面

- [[wf12-decision-trace]]
- [[gua075-recommendation-pipeline]]
- [[bc-argmax-collapse]]
- [[engine-v7]]（如已存在）
- [[v7-current-state]]
