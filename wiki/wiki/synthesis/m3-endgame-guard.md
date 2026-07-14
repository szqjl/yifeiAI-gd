---
type: synthesis
title: "M3 末段拦头与让道博弈：GUA-029/031/034 的边界与触发条件"
sources:
  - docs/guandan-brain/issues/GUA-029-completion.md
  - docs/guandan-brain/issues/GUA-031-completion.md
  - docs/guandan-brain/issues/GUA-034-completion.md
tags:
  - synthesis
  - endgame
  - m3
status: current
related_gua:
  - GUA-029
  - GUA-031
  - GUA-034
  - GUA-026
date: 2026-06-17
---

# M3 末段拦头与让道博弈：GUA-029/031/034 的边界与触发条件

## 综述

M3 决策引擎的残局策略由三个 GUA 共同定义：

- **GUA-029**：通用残局策略（R1/R2/R3 三档）
- **GUA-031**：队友让道（teammate-rest 后的让出分支）
- **GUA-034**：solo_sprint 拦头游（1v2 时独力阻止对手走光）

三者形成「常态 → 让道 → 拦头」的三层结构，触发条件互斥但又共享部分兜底逻辑。

## 触发条件矩阵

| 局面 | 主策略 | 让道？ | 拦头？ |
|------|--------|--------|--------|
| 4 人在场 | GUA-029 通用 | — | — |
| 队友 rest，对手全在 | GUA-029 R 档 + 队友牌型 | 让道 → GUA-031 | — |
| 对手 [myPos+2] rest | GUA-029 | — | solo_sprint → GUA-034 |
| 队友 + 对手均 rest | 终局结算 | — | — |

## GUA-031 vs GUA-034 互斥

```python
if teammate.rest == 0:
    # GUA-031 接管：队友让道
    apply_teammate_yield_strategy()
elif numofplayers[(myPos + 2) % 4] == 0:
    # GUA-034 接管：solo_sprint 拦头游
    apply_solo_sprint_strategy()
else:
    # 常态
    apply_general_endgame_strategy()
```

**关键边界**：队友 rest 优先于对手 rest；当两者同时发生时，走 GUA-031 而非 GUA-034。

## GUA-026 与 GUA-034 的拆 trips 冲突

| GUA | 行为 | 条件 |
|-----|------|------|
| GUA-026 | 禁常态拆炸弹 / 级牌 trips | 常规残局 |
| GUA-034 | 允许拆 trips 压牌 | solo_sprint + 跟小单 / 跟对子 |

**实现建议**：在 guard 切片中显式标记 `solo_sprint_active` 布尔位，GUA-026 的禁拆逻辑需先检查该位，互斥成立。

## END-M04 复用 GUA-029 R3 兜底

```python
# END-M04 伪码
if solo_sprint and following_pair:
    if can_split_trips_to_bigger_pair():
        return split_trips_to_bigger_pair()
    else:
        # 复用 GUA-029 R3
        return gua029_R3_fallback(greaterPos)
```

**风险**：GUA-029 R3 的触发条件是 `numofplayers[greaterPos]<=7 && 无可跟`，在 solo_sprint 1v2 局面下对手手数可能 > 7，兜底可能不命中，导致对手走光。

## 实现优先级建议

1. **GUA-031 + GUA-029 R 档**：先打通「队友让道 + 通用残局」
2. **GUA-034 END-M01~M02**：solo_sprint 触发 + 接风首出
3. **GUA-034 END-M03/M04**：拆 trips 压牌（需与 GUA-026 互斥）
4. **R3 兜底回归测试**：验证 1v2 局面不漏触发

## 不在范围 / 后续迭代

- 完整 lalala「两手牌组合枚举」：推到 V5+ / 后续迭代
- 拦头游失败后的更精细兜底策略：待 replay 积累

## 相关页面

- [[GUA-029]]：通用残局
- [[GUA-031]]：队友让道
- [[GUA-034]]：solo_sprint 拦头游
- [[GUA-026]]：拆 trips 禁例
- [[solo-sprint]]：solo_sprint 概念
