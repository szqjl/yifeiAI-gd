---
type: source-summary
title: "GUA-034 完成定义摘要"
sources:
  - docs/guandan-brain/issues/GUA-034-completion.md
tags:
  - gua
  - m3
  - endgame
  - strategy
status: current
related_gua:
  - GUA-034
  - GUA-026
  - GUA-029
  - GUA-031
date: 2026-06-17
---

# GUA-034 完成定义摘要

## GUA 元信息

| 字段 | 值 |
|------|-----|
| 编号 | GUA-034 |
| 标题 | 残局拦头游 · M3 guard 切片 |
| 类型 | endgame-strategy |
| 状态 | open |
| 范围 | M3 |
| 依赖 | GUA-026、GUA-029、GUA-031 |
| Replay 依据 | `replay_word.md` round 38 yf2 |

## 关键条目

- **END-M01**：solo_sprint 模式——`numofplayers[(myPos+2)%4]==0` 或队友 `rest==0` 时进入拦头游分支
- **END-M02**：拦头游接风首出——solo_sprint + 接风 `_active` + `numofmy<=12`：优先 `ThreeWithTwo` / `Trips` / `Pair`
- **END-M03**：拦头游拆单压牌——solo_sprint + 跟小单：允许拆 trips 压牌（≥ 对手点）
- **END-M04**：拦头游拆对压牌——solo_sprint + 跟对子：拆 trips 凑更大对 或走 GUA-029 R3 兜底

## 跨 GUA 依赖

- **GUA-026**（边界冲突）：GUA-026 禁常态拆炸弹/级牌 trips，GUA-034 允许 solo_sprint 下定向拆
- **GUA-029**（复用）：END-M04 复用 GUA-029 R3（`numofplayers[greaterPos]<=7` 且无可跟）
- **GUA-031**（退出）：GUA-034 退出 GUA-031 队友让道分支，改走 solo_sprint

## 关联概念

- solo_sprint 模式：拦头游触发条件
- 拦头游接风首出（END-M02）
- 拦头游拆单压牌（END-M03）
- 拦头游拆对压牌（END-M04）

## 已知张力

- **不在范围**：完整 lalala「两手牌组合枚举」被推到 V5+/后续迭代
- **兜底风险**：GUA-034 复用 R3 兜底可能在某些局面让对手走光，需明确拦头游失败的兜底策略

## 相关页面

- [[GUA-034]]：实体页
- [[GUA-034-方案评审-summary]]：方案评审（早期）
- M3 末段拦头与让道博弈：综合分析（与 GUA-029/031 边界）

## 备注

本文档为 GUA-034 正式完成定义，与 [[GUA-034-方案评审-summary]] 是两份不同文档，应分别摘要。
