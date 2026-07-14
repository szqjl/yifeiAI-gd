---
type: source-summary
title: "队友保护策略（基于对战日志 yfv4_vs_lalala）"
sources:
  - docs/knowledge/strategy/01_core_strategies/01_teammate_protection.md
tags:
  - strategy
  - teammate-protection
  - core-strategy
status: current
related_gua:
  - GUA-030
  - GUA-031
  - GUA-032
date: 2026-06-17
---

# 队友保护策略（基于对战日志 yfv4_vs_lalala）

## 文件位置
- 路径：`docs/knowledge/strategy/01_core_strategies/01_teammate_protection.md`
- 来源：基于对战日志 yfv4_vs_lalala

## 掼蛋四项基本原则

### 1. 谁打谁收
- 先发有回手
- 搭档接牌慎重

### 2. 配合至上（四大喂牌技巧）
- **让道**：避开队友牌型
- **反向喂牌**：逆向支援
- **拆牌喂牌**：拆自家牌型喂队友
- **先大后小**：先用大牌清路、再用小牌喂

### 3. 打上家卡下家
- 压制对家上游，阻止其跑牌

### 4. 强牌弱打 / 弱牌强打
- 强牌时隐藏实力，弱牌时强攻抢分

## 炸弹使用红黑名单

### 红名单（建议使用）
- 关键冲刺阶段
- 队友即将跑牌

### 黑名单（避免使用）
- 牌力不足时
- 不能保证回手

## 开局阶段判断

| 阶段 | cards_left |
|------|-----------|
| 开局 | ≥ 20 |

## Python 伪代码（来自原文）

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

## 跨资料引用
- 上游：[[concept-four-card-power-pillars]]（四项基本原则）
- 配套：[[concept-passing-skills-matrix]]（喂牌四法）
- 实施：GUA-031（传牌技巧实施跟踪）

## 紧张点
- **"送三张/三带二"与"P-J03 示弱送夯"可能重复**：需在 GUA-031 实施跟踪里区分：
  - **送三张**：破坏对手三带二
  - **示弱送夯**：牺牲自己保队友
  - 触发条件不同
