---
type: concept
title: "残局管线注入点定位"
sources:
  - docs/knowledge/skills/07_opening/end position.md
  - docs/guandan-brain/handoff/2026-05-31-M3-skills映射与组牌总纲.md
tags:
  - endgame
  - injection
  - pipeline
status: current
related_gua:
  - GUA-078
date: 2026-06-21
---

# 残局管线注入点定位

## 触发点

主决策管线在以下条件满足时挂起，转交残局管线：
- 手牌 ≤ 10 张
- 进入收官阶段

## 注入内容

| 字段 | 类型 | 说明 |
|------|------|------|
| `banned_types` | List[牌型] | 残局禁用牌型（如过早炸弹） |
| `recommended_types` | List[牌型] | 残局推荐牌型 |

## 时序

```
主决策 decide()
   ↓
检测手牌数 ≤ 10？
   ├─ 否 → 走主路径（Layer1~3）
   └─ 是 → 注入 banned_types / recommended_types
              ↓
           EndgamePreprocessor
              ↓
           残局决策器
              ↓
           调试脚本记录
```

## 中局重评估

残局管线内可触发中局重评估，必要时回到主路径（罕见）。

## 关联

- [[gua-078]] — 残局管线 GUA
- [[endgame-pipeline]] — 残局管线概念
- [[module-endgame-preprocessor]] — 预处理器实现
