---
title: 开局阶段队友配合策略
type: strategy
category: phase_strategy
tags: [opening, teammate_cooperation, card_value, overkill]
difficulty: intermediate
priority: 8
game_phase: opening
related:
  - strategy/02_role_strategies/02_assist_attack/
  - strategy/01_core_strategies/01_teammate_protection.md
---

# 开局阶段队友配合策略

## 📖 概述

开局阶段（第一圈牌）是游戏的关键阶段，此时需要特别注意队友配合，避免浪费大牌和打断队友节奏。

## ❌ 错误案例：开局越级打大牌

### 案例描述

**对局场景**：第一圈牌，开局阶段

**出牌序列**：
1. 2号位（队友yf2_v4）打出 `Single 7`（开局首攻，小牌探路）
2. 3号位（对手lalala）打出 `Single 8`（顺牌，只比7大1级）
3. **0号位（队友yf1_v4）打出 `Single A`** ❌ **错误！**

### 问题分析

#### 1. 开局阶段不应该越级打大牌

- **阶段判断**：这是第一圈牌，开局阶段
- **队友意图**：2号位出小牌7，属于试探性出牌，可能是想控场或试探对手
- **对手行为**：3号位只是顺牌（8），不是大牌压制，只是正常接牌
- **正确策略**：0号位应该PASS，让队友2号位继续控场

#### 2. 牌值差距过大

- **牌值计算**：
  - 3号位出的是 `8`（牌值8）
  - 0号位出的是 `A`（牌值14）
  - **差距**：14 - 8 = **6级**
- **问题**：开局阶段用A越级打8，浪费了大牌

#### 3. 打断队友节奏

- **队友节奏**：2号位出小牌7，可能是想控场或试探
- **对手行为**：3号位顺牌8，控场权暂时转移，但不是威胁
- **正确策略**：0号位应该PASS，等2号位接牌，或者等1号位出牌后再决定
- **实际行为**：0号位直接越级打A，打断了队友的节奏

### 正确的策略应该是

```
2号位出7 → 3号位出8（顺牌）→ 0号位应该PASS → 
让2号位接牌，或者等1号位出牌后再决定
```

## ✅ 正确策略

### 开局阶段队友配合原则

#### 1. 队友出小牌，对手顺牌时

**情况**：
- 队友出小牌（如7、8、9等）
- 对手只是顺牌（只比队友牌大1-2级）
- 这是开局阶段

**策略**：
- ✅ **应该PASS**，让队友继续控场
- ❌ **不应该越级打大牌**（如A、2、Joker等）

**原因**：
- 开局阶段，大牌应该保留用于关键时刻
- 对手只是顺牌，不是威胁，不需要立即压制
- 让队友继续控场，可以更好地配合

#### 2. 越级打大牌的适用场景

**适用场景**（仅在以下情况才越级打大牌）：
- ✅ **后期冲刺阶段**：自己或队友快走完，需要争头游
- ✅ **对手大牌压制**：对手出大牌（如2、Joker）压制队友
- ✅ **残局阶段**：剩余牌数 <= 5，需要快速走完

**不适用场景**：
- ❌ **开局阶段**：第一圈牌，不应该越级打大牌
- ❌ **对手顺牌**：对手只是顺牌，不是威胁
- ❌ **队友控场**：队友刚出牌，应该让队友继续控场

### 判断标准

#### 1. 阶段判断

```python
# 判断是否开局阶段
is_opening = (round_number <= 3) or (cards_left >= 20)

# 判断是否后期冲刺
is_endgame = (cards_left <= 5) or (teammate_cards <= 3)
```

#### 2. 牌值差距判断

```python
# 计算牌值差距
card_value_diff = my_card_value - opponent_card_value

# 开局阶段：差距 > 3 级，不应该越级打
if is_opening and card_value_diff > 3:
    should_pass = True  # 应该PASS
```

#### 3. 对手行为判断

```python
# 判断对手是否只是顺牌
is_just_follow = (opponent_card_value - teammate_card_value) <= 2

# 开局阶段，对手只是顺牌，应该PASS
if is_opening and is_just_follow:
    should_pass = True  # 应该PASS
```

## 📋 应用场景

### 场景1：开局队友出小牌

**情况**：
- 队友出 `Single 7`
- 对手出 `Single 8`（顺牌）
- 自己手中有 `Single A`

**决策**：
- ❌ **错误**：出 `Single A` 越级打
- ✅ **正确**：PASS，让队友继续控场

### 场景2：开局队友出中等牌

**情况**：
- 队友出 `Single J`
- 对手出 `Single Q`（顺牌）
- 自己手中有 `Single 2`

**决策**：
- ❌ **错误**：出 `Single 2` 越级打
- ✅ **正确**：PASS，让队友继续控场

### 场景3：后期冲刺阶段

**情况**：
- 队友剩余3张牌
- 对手出 `Single 8`
- 自己手中有 `Single A`

**决策**：
- ✅ **正确**：出 `Single A` 越级打，帮助队友冲刺

## 🔗 相关知识

### 前置知识
- [队友保护策略](../01_core_strategies/01_teammate_protection.md)
- [助攻策略](../../02_role_strategies/02_assist_attack/)

### 后续知识
- [中局策略](../02_midgame/)
- [残局策略](../03_endgame/)

### 相关知识
- [大牌使用时机](../../03_card_strategies/)
- [阶段判断](../../05_common_strategy/03_situation_judgment.md)

## 📝 代码实现建议

### 在 `knowledge_enhanced_decision.py` 中添加

```python
def _should_pass_in_opening(self, action, message, teammate_pos, opponent_pos):
    """
    判断开局阶段是否应该PASS
    
    Args:
        action: 当前候选动作
        message: 游戏消息
        teammate_pos: 队友位置
        opponent_pos: 对手位置
    
    Returns:
        bool: True表示应该PASS
    """
    # 判断是否开局阶段
    cards_left = message.get('cards_left', 27)
    is_opening = cards_left >= 20
    
    if not is_opening:
        return False
    
    # 判断队友是否刚出牌
    cur_pos = message.get('curPos', -1)
    greater_pos = message.get('greaterPos', -1)
    
    # 队友控场，对手只是顺牌
    if greater_pos == teammate_pos:
        # 获取对手出的牌值
        cur_action = message.get('curAction', [])
        if cur_action:
            opponent_card_value = self._get_card_value(cur_action[1])
            teammate_card_value = self._get_card_value(cur_action[1])  # 需要从历史获取
            
            # 对手只是顺牌（差距 <= 2级）
            if abs(opponent_card_value - teammate_card_value) <= 2:
                # 判断自己的牌值
                my_card_value = self._get_card_value(action[1])
                
                # 如果越级打大牌（差距 > 3级），应该PASS
                if my_card_value - opponent_card_value > 3:
                    return True  # 应该PASS
    
    return False
```

## 🎯 总结

开局阶段队友配合的关键原则：

1. **队友出小牌，对手顺牌时，应该PASS**
2. **开局阶段不应该越级打大牌**
3. **越级打大牌只在后期冲刺阶段使用**
4. **大牌应该保留用于关键时刻**

---

**来源**：基于对战日志分析（yfv4_vs_lalala，行5-14）  
**优先级**：高（8/10）  
**难度**：中等

