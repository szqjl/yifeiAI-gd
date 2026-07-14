---
type: source-summary
title: "GUA-031 完成定义 - 源文档摘要"
sources:
  - docs/guandan-brain/issues/GUA-031-completion.md
tags:
  - source-summary
  - gua-031
  - passing
  - teammate-yielding
status: current
related_gua:
  - GUA-031
  - GUA-029
  - GUA-030
  - GUA-026
date: 2026-06-17
---

# GUA-031 完成定义 - 源文档摘要

## 文档信息

- **来源文件**：`docs/guandan-brain/issues/GUA-031-completion.md`
- **字符数**：1124
- **GUA 状态**：P0 完成定义（open 待实现）

## 核心内容

GUA-031 定义 **M3 传牌 guard（放队友）+ 队友让道** 的可执行规则。

## 传牌 guard 规则

- 主动场景：检测到队友可能冲刺/听牌时，**送小单 / 防送炸 / 逢五喂队友**
- 被动场景：`_is_teammate_greater` 时 `return 0` 让道

## 队友让道原则（PASS-P01 ~ PASS-P04）

| 原则 | 内容 | 置信度 |
|------|------|--------|
| **PASS-P01** | 主动场景下送小单让队友接牌 | high |
| **PASS-P02** | 主动场景下防送炸（不主动给队友出炸机会） | high |
| **PASS-P03** | 被动场景下 _is_teammate_greater 时 return 0 让道 | high |
| **PASS-P04** | 逢五喂队友 | **low**（弱推断） |

## 关键模块/函数

- `_is_teammate_greater` — 队友牌力判断
- `_active` / `_passive` — 主动/被动分流
- `one_hand` — 单手决策入口

## 与 GUA-029 的边界

- GUA-031 管**传牌 guard 放队友**
- GUA-029 管**炸弹执行**
- 两者**正交**：GUA-031 不放宽 GUA-029 的"不压队友"原则
- GUA-031 不放宽 GUA-026 的"三带二禁拆炸弹/耗级牌"保护

## 不确定性标注

- **PASS-P04 逢五喂队友** 标注 confidence=low（弱推断），来源于 `01_passing_skills.md` 的描述性原则，需更多批跑数据验证

## 关联实体

- [[gua-031]] — 完整 GUA 条目
- [[teammate-yielding]] — 队友让道与传牌策略概念页
- [[gua-029]] — 炸弹执行规则（边界）
- [[gua-026]] — 拆牌保护（边界）
