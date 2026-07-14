---
type: entity-module
title: "v7_guards V7 守卫"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
  - docs/guandan-brain/v7-win-rate-history.md
tags:
  - module
  - v7
  - guards
  - teammate-protection
status: current
related_gua:
  - GUA-066
  - GUA-068
  - GUA-069
  - GUA-070
  - GUA-072
  - GUA-075
date: 2026-06-29
---

# v7_guards V7 守卫

## 身份

- **核心文件**：`v7_guards.py`
- **职责**：R10～R16 队友识别与保护

## 守卫规则

| 规则 | 描述 |
|------|------|
| **R10** | 队友识别（基础） |
| **R11** | 队友控牌检测（不抢出） |
| **R12** | 队友放牌节奏（不顶牌） |
| **R13** | 队友接牌窗口（让位） |
| **R14** | 残局队友保护（不抢关） |
| **R15** | 防误伤（不打队友牌型） |
| **R16** | 跨副上下文（接续防守） |

## 关键组件

| 组件 | 职责 |
|------|------|
| `to_card_mask` | 牌型感知掩码 |
| `_group_consistency_filter` | 组排一致性过滤 |
| 队友控牌→助攻放行 | 队友出小则己方助攻 |
| R-G080-4 | scanner / card_mask 降级观测（见 GUA-072） |

## 关联 GUA

- **GUA-066 / 068 / 069 / 070**：综合批跑副胜率跌至 3.7%
- **GUA-072**：card_mask 三项修复 + 拆炸时序押后
- **GUA-075**：信念注入 + heuristic ③b/③c

## 链接

- V7 引擎：[[engine-v7]]
- 守卫悖论：[[guard-overlap-puzzle]]
- 拆炸时序：[[gua-072]]
- heuristic vs BC：[[heuristic-vs-bc]]
