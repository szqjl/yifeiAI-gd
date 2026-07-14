---
type: concept
title: "平台标准变量名规范"
sources:
  - docs/knowledge/知识库格式化方案.md
  - docs/knowledge/掼蛋AI知识应用框架.md
tags:
  - concept
  - naming-convention
  - platform-standard
status: current
related_gua: []
date: 2026-06-18
---

# 平台标准变量名规范

## 定义

南京邮电大学掼蛋平台（南邮平台）规定的**统一变量命名**——所有代码、JSON、YAML 知识库文件必须遵循的命名标准。是整个知识库/代码的命名基石。

## 牌型命名

| 变量名 | 含义 |
|--------|------|
| `Single` | 单张 |
| `Pair` | 对子 |
| `Triple` | 三张 |
| `Bomb` | 炸弹 |
| `StraightFlush` | 同花顺 |
| `Tube` | 钢板（三连对） |
| `Plate` | 钢板（三连张） |
| `Sequence` | 顺子 |
| `HR` | 大王花色（红心主牌） |
| `SB` | 小王花色（黑桃主牌） |

## 位置关系公式（顺时针）

```
下家    = (myPos + 1) % 4
上家    = (myPos - 1) % 4
对家    = (myPos + 2) % 4
```

## 进贡阶段变量

| 变量名 | 含义 |
|--------|------|
| `tribute` | 进贡动作 |
| `back` | 还贡动作 |
| `PASS` | 不进/不还 |

## 命名约定原则

1. **PascalCase** 用于牌型与角色
2. **camelCase** 用于运行时变量（`curPos`/`myPos`）
3. **UPPER_SNAKE** 用于常量/动作（`PASS`）
4. **缩写优先级**：`HR`/`SB` 在平台协议上下文中可单字符使用

## 演进历史

- `StraightFlush` 经历过从"同花顺"到当前命名的更正
- `HR`/`SB` 是 ⭐更新 引入的新命名
- 文档中存在多次"⭐更正"痕迹，说明**当前版本为定稿版**

## 跨域关联

- 命名规范贯穿 [[source-knowledge-format-spec-summary]] 与 [[source-knowledge-application-framework-summary]]
- L1 硬编码层使用此命名 → [[concept-knowledge-layered-decision]]
- 进贡变量对应 concept-tribute-stage
