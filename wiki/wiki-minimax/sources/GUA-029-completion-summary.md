---
type: source-summary
title: "GUA-029 完成定义 - 源文档摘要"
sources:
  - docs/guandan-brain/issues/GUA-029-completion.md
tags:
  - source-summary
  - gua-029
  - bomb
  - m3-engine
status: current
related_gua:
  - GUA-029
  - GUA-026
  - GUA-030
  - GUA-031
date: 2026-06-17
---

# GUA-029 完成定义 - 源文档摘要

## 文档信息

- **来源文件**：`docs/guandan-brain/issues/GUA-029-completion.md`
- **字符数**：1441
- **关联 GUA**：GUA-029（主）、GUA-026（边界）、GUA-030（映射登记）、GUA-031（传牌 guard）

## 核心内容

GUA-029 定义了 **M3 引擎炸弹可执行规则包 R1–R6**，将掼蛋炸弹策略从"原则描述"落地为"if-then 可执行代码"。

## 关键规则包（R1–R6）

| 规则 | 内容 | 优先级 |
|------|------|--------|
| **R1** | 修复 `choose_bomb`：读取 `action[1]` 作为炸弹点数（对齐 lalala 参考实现） | P0 |
| **R2** | 必回炸：被炸后若队友未接管则必须回炸 | P0 |
| **R3** | 防冲刺必炸：对手听牌/冲刺时必炸 | P0 |
| **R4** | 剩 4 张默认不炸 | P1 |
| **R5** | 不压队友：主动场景不压队友炸弹 | P0 |
| **R6** | 残局冲刺：残局必出最大整炸抢头游 | P0 |

## 关键模块/函数

- `m3_utils.choose_bomb` — R1 修复目标（point card 字段读取）
- `_Bomb` — 炸弹牌型处理
- `one_hand` — 单手决策入口
- `_active` / `_passive` — 主动/被动场景分流

## 关联原则

- **P-C**（原则）、**P-J**（进阶）、**P-G**（牌型）
- 来自 `01_bomb_techniques.md`、`guandan-knowledge.mdc`

## 边界澄清

- **vs GUA-026**：GUA-026 禁止拆炸弹/耗级牌（拆牌保护），GUA-029 主动出整炸——**二者不冲突**
- **vs GUA-030**：GUA-030 只登记映射表不写代码，GUA-029 写 M3 炸弹执行代码
- **vs GUA-031**：GUA-031 传牌 guard 放队友，与 GUA-029 **正交**（不放宽炸弹/三带二拆牌保护）

## 关联实体

- [[gua-029]] — 完整 GUA 条目
- [[gua-026]] — 拆牌保护边界
- [[gua-030]] — 原则映射登记
- [[gua-031]] — 传牌 guard + 队友让道
- [[bomb-execution-rules]] — 炸弹可执行规则概念页
- wiki-minimax/entities/engine-m3.md — M3 决策引擎

## v1006 格式

Bomb action 格式：`['Bomb', '8', [...]]`（点数字符串 + 牌列表），作为单元测试输入标准。
