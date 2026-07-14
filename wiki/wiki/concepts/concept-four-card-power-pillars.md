---
type: concept
title: "掼蛋四项基本原则（强结构化版）"
sources:
  - docs/knowledge/strategy/01_core_strategies/01_teammate_protection.md
tags:
  - concept
  - principles
  - four-pillars
  - core-strategy
status: current
related_gua:
  - GUA-030
  - GUA-031
date: 2026-06-17
---

# 掼蛋四项基本原则（强结构化版）

## 概述
掼蛋策略的四项根本原则，源自对战日志 yfv4_vs_lalala 的实战经验总结。

## 四项原则

### 1. 谁打谁收
- **先发有回手**：先手出牌必须考虑能否收回牌权
- **搭档接牌慎重**：队友接牌要谨慎，避免让其陷入困境

### 2. 配合至上（四大喂牌技巧）
| 技巧 | 说明 |
|------|------|
| **让道** | 避开队友牌型 |
| **反向喂牌** | 逆向支援队友 |
| **拆牌喂牌** | 拆自家牌型喂队友 |
| **先大后小** | 先用大牌清路、再用小牌喂 |

### 3. 打上家卡下家
- 压制对家上游
- 阻止其跑牌

### 4. 强牌弱打 / 弱牌强打
- **强牌时**：隐藏实力、避免暴露
- **弱牌时**：强攻抢分、争取主动

## 炸弹使用红黑名单

### 红名单（建议使用）
- 关键冲刺阶段
- 队友即将跑牌
- 必胜局面

### 黑名单（避免使用）
- 牌力不足时
- 不能保证回手
- 浪费在非关键局面

## 开局阶段判断

| 阶段 | cards_left | 策略 |
|------|-----------|------|
| 开局 | ≥ 20 | 保留实力、判断牌型 |
| 中局 | 10-19 | 配合为主 |
| 残局 | < 10 | 决胜时刻 |

## 紧张点
- **强牌弱打 vs 牌力 8 分以上主攻**：
  - "强牌弱打"是配合原则（隐藏实力）
  - 牌力 8+ = 主攻（[[concept-card-power-scoring]]）
  - 两者不矛盾：8+ 分时**强牌弱打**仍可主攻，只是**不暴露**
  - **6 分主攻可转助攻**的临界点需统一决策树

## 配套实施

### Python 伪代码
```python
def is_teammate_controlling(state, teammate_id):
    """判断队友是否在控制牌权"""
    pass

def should_pass_for_teammate(state, teammate_id, action):
    """判断是否应让道给队友"""
    pass

def _should_feed_teammate(state, teammate_id, my_action):
    """判断是否应喂牌给队友"""
    pass
```

### 关联 GUA
- **GUA-030**：原则→引擎映射
- **GUA-031**：传牌技巧实施跟踪（让道/反向喂牌/拆牌喂牌/先大后小）

## 相关页面
- [[source-strategy-01-core-01-teammate-protection-summary]]
- [[concept-passing-skills-matrix]]
- [[concept-card-power-scoring]]
- [[gua-030]]
- [[gua-031]]
