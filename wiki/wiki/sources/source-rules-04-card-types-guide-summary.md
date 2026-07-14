---
type: source-summary
title: "规则摘要：04 牌型手册"
sources:
  - docs/knowledge/rules/01_basic_rules/04_card_types_guide.md
tags:
  - rules
  - card-types
  - encoding
  - m3-core
status: current
related_gua: []
date: 2026-06-18
---

# 规则摘要：04 牌型手册

## 来源

- 原始文件：`docs/knowledge/rules/01_basic_rules/04_card_types_guide.md`（4139 字符）
- 重要性：**M3 引擎核真源**

## 核心内容

### 11 种合法牌型

1. **单张**（Single）：任意一张牌
2. **对子**（Pair）：两张同点
3. **三张**（Triple）：三张同点
4. **三带二**（Triple+Single）：三张+任意两张单
5. **顺子**（Straight）：5 张连续单张，含 2 但不含王
6. **同花顺**（Flush Straight）：5 张同花连续，仅次于王炸
7. **三连对**（Consecutive Pairs）：3 个连续对子
8. **钢板**（Plate）：2 个连续三张
9. **炸弹**：四张及以上同点
10. **天王炸**（王炸）：2 大王 + 2 小王 = 4 张
11. **星级炸弹**：4~8 星同花顺

### 总序（从大到小）

```
天王炸（4 张王）> 8 星 > 7 星 > 6 星 > 5 星 > 4 星 > 普通炸弹 > 同花顺 > 其他牌型
```

### 平台 JSON 编码（3 元组）

```json
["Single", "rank", ["cards"]]
["Pair", "rank", ["cards"]]
["Bomb", "R", ["HR","HR","SB","SB"]]   // 王炸示例
```

- `type`：牌型名
- `rank`：级牌标记（"R" 表示王炸无级牌）
- `cards`：牌面编码（H=红桃 S=黑桃 D=方块 C=梅花；B=大王 R=小王）

## 与其他页面的关系

- 上游：[[source-rules-02-quick-start-summary]]
- 下游：[[source-rules-05-card-distribution-summary]]
- 相关概念：[[concept-card-type-encoding]]
- 引擎引用：wiki-minimax/entities/engine-m3.md

## 关键约束

- 逢人配（H+curRank）不得与王组牌
- 同花顺必须 5 张同花连续
- 炸弹比较：星级 > 张数 > 点数
