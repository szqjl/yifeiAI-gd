---
type: source-summary
title: "GUA-034 方案评审摘要"
sources:
  - docs/guandan-brain/GUA-034-方案评审.md
tags:
  - review
  - gua-034
  - solo-sprint
  - source
status: current
related_gua:
  - GUA-026
  - GUA-029
  - GUA-030
  - GUA-031
  - GUA-034
date: 2026-06-17
---

# GUA-034 方案评审摘要

## 来源概述

`docs/guandan-brain/GUA-034-方案评审.md`（4980 字符）记录了 GUA-034「残局拦头游（solo_sprint）」的方案评审过程，是 P0 guard 路线实施前的关键决策记录。

## 核心问题

队友 `rest=0`（已出完牌进入 rest 状态）后，本方进入 **solo_sprint** 模式：需冲头游避免双下。评审解决「该何时 guard、guard 哪些动作」。

## 真源定义

```python
_is_solo_sprint() == (numoffri == 0)
```

⚠️ **关键约束**：不得误触 [[gua-031]] 的 P-F02（solo 时 greater 为对手，numoffri∈{1,5} 时不触发 solo_sprint）。

## 方案方向表决

| 方向 | 方案 | 决议 |
|------|------|------|
| **A** | Guard 切片（推荐） | ✅ **采纳** |
| B | rank 体系重写 | ❌ 拒绝 |

### 方向 A 实施项（END-M01–M04）

| 端点 | 描述 |
|------|------|
| **END-M01** | solo_sprint guard 检测 |
| **END-M02** | 接风禁 rank* 拆对出单 |
| **END-M03** | 被动允许拆 trips 压牌 |
| **END-M04** | 被动允许拆 trips 凑对 |

## 评审保留异议

1. **方向 A 不覆盖双下**：双下场景下 rank* 风险需另案
2. **END-M03/M04 与 GUA-026 冲突风险**：常态三带二禁拆炸/级牌 trips，需保证仅在 solo_sprint 被动分支生效
3. **R3 兜底可能牵动非 solo 路径**：需 test_m3_gua029 回归保护

## 验证结果

- ✅ `test_m3_gua034`：6 passed
- ✅ 回归 `test_m3_gua029`：24 passed
- ✅ **无回归 fail**

## 实施原则

- [[gua-030]]：guard 而非 rank 重写，可 pytest 的 guard
- 关联约束：[[gua-026]]（常态拆炸禁）、[[gua-029]]（R3/R4/R5 兜底）、[[gua-031]]（solo greater）

## 状态

- **closed_in**：2026-06-01
- 完整闭环见 synthesis-gua034-lifecycle

## 跨引用

- [[gua-034]] — GUA 实体页
- [[solo-sprint]] — 核心概念
- wiki-minimax/entities/engine-m3.md — M3 决策引擎
