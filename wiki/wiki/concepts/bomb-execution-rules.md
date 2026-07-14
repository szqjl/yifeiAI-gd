---
type: concept
title: "炸弹可执行规则（R1–R6）"
sources:
  - docs/guandan-brain/issues/GUA-029-completion.md
  - .cursor/rules/guandan-knowledge.mdc
tags:
  - concept
  - bomb
  - execution-rules
  - m3-engine
status: current
related_gua:
  - GUA-029
  - GUA-026
  - GUA-031
date: 2026-06-17
---

# 炸弹可执行规则（R1–R6）

## 定义

将掼蛋原则文档中的炸弹策略**逐条落地为 if-then 可执行代码**的规则包，是 M3 决策引擎炸弹决策的**唯一执行规范**。

## 规则总览

| 规则 | 名称 | 优先级 | 触发场景 | 决策 |
|------|------|--------|----------|------|
| **R1** | 修复 `choose_bomb` 点数读取 | P0 | 所有炸弹决策 | 读 `action[1]` 而非 `action[0]` |
| **R2** | 必回炸 | P0 | 被对手炸弹压制 | 队友未接管则回炸 |
| **R3** | 防冲刺必炸 | P0 | 对手听牌/冲刺 | 必炸拦截 |
| **R4** | 剩 4 张默认不炸 | P1 | 手牌 ≤ 4 | 默认不炸（R6 除外） |
| **R5** | 不压队友 | P0 | 主动出牌 | 队友已炸则不压 |
| **R6** | 残局冲刺 | P0 | 残局 + 对手牌力强 | 必出最大整炸 |

## 关键设计原则

### 1. 最小够用原则

- 能用小炸弹解决的不用大炸弹
- 能用普通牌型解决的不用炸弹
- 保留炸弹作为残局冲刺的最终手段（R6）

### 2. 不打四原则

- 不主动出 4 张炸弹（耗级牌）
- 例外：R3 防冲刺、R6 残局冲刺

### 3. 不压队友原则

- R5 与 [[gua-031]] PASS-P01~P04 配合
- 主动场景检测队友动作后再决定

### 4. 残局冲刺原则

- 残局 = 手牌 ≤ N 张 + 对手牌力强
- 必出整炸抢头游

## v1006 格式

Bomb action 的标准格式：

```python
['Bomb', '<point>', [<card_list>]]
# 示例：['Bomb', '8', ['8-01', '8-02', '8-03', '8-04']]
```

- 索引 0：固定字符串 `'Bomb'`
- 索引 1：点数字符串（`'2'`、`'3'`、...、`'A'`、`'J'`、`'Q'`、`'K'`、王）
- 索引 2：牌列表

**R1 修复要点**：`choose_bomb` 必须读取索引 1 而非索引 0。

## 实现位置

- `m3_utils.choose_bomb` — R1
- `_Bomb` 牌型处理 — R1~R6 通用
- `_active` 分支 — R4/R5/R6
- `_passive` 分支 — R2/R3
- `one_hand` 决策入口 — 串联所有规则

## 与其他规则包的关系

| 相关规则 | 关系 |
|----------|------|
| [[gua-026]] 拆牌保护 | 不冲突：GUA-029 主动出整炸；GUA-026 禁止拆炸弹/耗级牌 |
| [[gua-031]] 传牌 guard | 正交：GUA-031 放队友；GUA-029 不放宽 R5 不压队友 |
| [[teammate-yielding]] | 配合：R5 不压队友 + PASS-P01 送小单 = 完整队友配合 |

## 验证标准

- 单元测试：`test_m3_gua029.py` 覆盖 R1–R6
- 批跑验证：wiki-minimax/concepts/batch-evaluation.md 净盘 M3 批跑胜率提升
- lalala 对照：与 lalala 参考实现的 choose_bomb 行为一致

## 关联页面

- [[gua-029]] — GUA 完整条目
- [[gua-026]] — 拆牌保护边界
- [[gua-031]] — 传牌 guard 边界
- [[teammate-yielding]] — 队友让道策略
- wiki-minimax/entities/engine-m3.md — M3 决策引擎
- wiki-minimax/concepts/batch-evaluation.md — 批跑评测体系
