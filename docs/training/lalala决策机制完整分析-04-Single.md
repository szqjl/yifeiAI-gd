# lalala决策机制分析 - 04: Single()

## 📋 方法概述

**方法名**: `Single()`  
**位置**: `action.py` 第37-179行  
**作用**: 处理单张牌型的管牌逻辑，是lalala最复杂的牌型处理方法之一

---

## 🔍 方法签名

```python
def Single(self, actionList, curAction, rank_card, handcards, numofplayers, 
           rest_cards, card_val, myPos, greaterPos, pass_num, my_pass_num):
```

### 参数说明

- `actionList`: 可选动作列表
- `curAction`: 当前需要管的单张动作
- `rank_card`: 等级牌（如'H2'）
- `handcards`: 手牌
- `numofplayers`: 所有玩家的剩余牌数列表
- `rest_cards`: 剩余牌库
- `card_val`: 牌值字典
- `myPos`: 自己的位置
- `greaterPos`: 最大动作的位置
- `pass_num`: 连续PASS次数
- `my_pass_num`: 自己的PASS次数

---

## 🎯 核心逻辑

### 1. 提取玩家信息

```python
numofnext = numofplayers[(myPos+1)%4]      # 下家剩余牌数
numofgreaterPos = numofplayers[greaterPos]  # 最大动作者剩余牌数
numoffri = numofplayers[(myPos + 2) % 4]   # 队友剩余牌数
numofmy = numofplayers[myPos]               # 自己剩余牌数
numofpre = numofplayers[(myPos-1)%4]        # 上家剩余牌数
```

### 2. 分析手牌结构

```python
sorted_cards, bomb_info = combine_handcards(handcards, rank_card[-1], card_val)

# 提取各种牌型成员
single_member = sorted_cards["Single"]      # 单张成员
pair_member = []                            # 对子成员
trip_member = []                            # 三张成员
bomb_member = []                            # 炸弹成员
straight_member = []                        # 顺子成员

# 填充成员列表
for pair in sorted_cards["Pair"]:
    pair_member += pair
for trip in sorted_cards["Trips"]:
    trip_member += trip
for bomb in sorted_cards["Bomb"]:
    bomb_member += bomb
if len(sorted_cards["Straight"]) != 0:
    straight_member += sorted_cards["Straight"][0]
if len(sorted_cards["StraightFlush"]) != 0:
    straight_member += sorted_cards["StraightFlush"][0]
```

**策略**: 详细分析手牌结构，识别各种牌型成员，避免破坏有价值的组合。

### 3. 分离单张动作和炸弹动作

```python
single_actionList = []
bomb_actionList = []
for action in actionList[1:]:  # 跳过PASS
    tag += 1
    if action[0] == 'Single':
        single_actionList.append((tag, action))
    else:
        bomb_actionList.append((tag, action))
```

**策略**: 将单张动作和炸弹动作分开处理，因为它们的决策逻辑不同。

### 4. 计算关键值

```python
curVal = card_val[curAction[1]]           # 当前单张的牌值
max_val = card_val[rest_cards[-1][0][1]]  # 剩余牌库中最大牌值
```

### 5. 残局/关键阶段处理（下家≤4或上家≤3）

```python
if numofnext <= 4 or (numofpre <= 3 and numofpre >= 1):
    # 5.1 保护队友（关键策略）
    if (myPos+2)%4 == greaterPos and curVal >= max_val:
        return 0  # PASS，保护队友
    if (myPos+2)%4 == greaterPos and curVal >= 15 and numofnext != 1:
        return 0  # PASS，保护队友
    
    # 5.2 优先选择：单张成员 + 大牌值 + 非等级牌
    for action in single_actionList:
        if card_val[action[1]] >= max_val and action[2][0] in single_member and rank_card not in action[2]:
            return Index
    
    # 5.3 次优选择：非炸弹成员 + 大牌值 + 非等级牌 + 不在顺子中
    for action in single_actionList:
        if card_val[action[1]] >= max_val and action[2][0] not in bomb_member and rank_card not in action[2]:
            if is_inStraight(action, straight_member):
                continue  # 跳过在顺子中的牌
            return Index
    
    # 5.4 考虑使用炸弹
    index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
    if index != -1:
        return index
    
    # 5.5 放宽条件：牌值 >= max_val-2
    for action in single_actionList:
        if card_val[action[1]] >= max_val-2 and action[2][0] not in bomb_member and rank_card not in action[2]:
            if is_inStraight(action, straight_member):
                continue
            return Index
    
    # 5.6 使用等级牌（特殊情况）
    for action in single_actionList:
        if rank_card in action[2] and (len(sorted_cards["Pair"]) < 3 or numofnext == 1):
            return Index
```

### 6. 队友是最大动作者的处理

```python
if (myPos+2)%4 == greaterPos:  # 队友是最大动作者
    # 6.1 如果当前牌值很大，PASS
    if curVal >= 14 or curVal >= max_val-2:
        return 0
    
    # 6.2 如果队友剩余牌数≤4
    elif numoffri <= 4:
        index = normal(single_actionList, single_member, rank_card)
        if index == -1:
            return 0
        if curVal <= 10:
            return index
        else:
            # 只出比当前牌大1的牌
            if card_val[actionList[index][1]] == curVal+1:
                return index
    
    # 6.3 队友剩余牌数>4
    else:
        index = normal(single_actionList, single_member, rank_card)
        if index != -1:
            return index
        else:
            return 0
```

### 7. 对手是最大动作者的处理

```python
else:  # 对手是最大动作者
    # 7.1 优先使用normal策略
    index = normal(single_actionList, single_member, rank_card)
    if index != -1:
        return index
    
    # 7.2 如果PASS次数过多，使用special策略
    if pass_num >= 5 or my_pass_num >= 3:
        index = special(single_actionList, bomb_member, straight_member, rank_card)
        if index != -1:
            return index
    
    # 7.3 考虑使用炸弹
    cur_bomb_num = cal_bomb_num(sorted_cards, handcards, rank_card)
    if curVal >= max_val and numofgreaterPos >= 15 and cur_bomb_num > 1:
        p = random()
        index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
        if p > 0.5:  # 50%概率使用炸弹
            if index != -1:
                return index
    elif ((curVal >= 15 or curVal >= max_val-2) and numofgreaterPos <= 15) or pass_num >= 7 or my_pass_num >= 5:
        index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
        if index != -1:
            return index
        else:
            return 0
```

### 8. 辅助函数

#### normal() - 正常策略

```python
def normal(single_actionList, single_member, rank_card):
    for action in single_actionList:
        if (action[2][0] in single_member or card_val[action[1]] >= 15) and rank_card not in action[2]:
            return Index
    return -1
```

**策略**: 优先使用单张成员或大牌（≥15），避免使用等级牌。

#### special() - 特殊策略

```python
def special(single_actionList, bomb_member, straight_member, rank_card):
    for action in single_actionList[::-1]:  # 从大到小
        if action[2][0] not in bomb_member and rank_card not in action[2]:
            if is_inStraight(action, straight_member):
                continue
            return Index
    return -1
```

**策略**: 从大到小选择，避免使用炸弹成员、等级牌和顺子成员。

---

## 💡 关键策略总结

### 1. 保护队友（最高优先级）

- 如果队友是最大动作者，且当前牌值很大（≥max_val或≥15），选择PASS
- 如果队友剩余牌数≤4，只出比当前牌大1的牌

### 2. 手牌结构分析

- 详细分析手牌结构，识别各种牌型成员
- 避免破坏有价值的组合（对子、三张、炸弹、顺子）

### 3. 优先级选择

1. **单张成员 + 大牌值** - 最优
2. **非炸弹成员 + 大牌值** - 次优
3. **放宽条件（max_val-2）** - 再次优
4. **使用等级牌** - 特殊情况
5. **使用炸弹** - 最后选择

### 4. PASS次数控制

- 如果PASS次数过多（pass_num >= 5或my_pass_num >= 3），使用special策略
- 如果PASS次数过多（pass_num >= 7或my_pass_num >= 5），考虑使用炸弹

### 5. 残局处理

- 当下家≤4或上家≤3时，进入残局模式
- 残局时优先保护队友，避免破坏组合

---

## 🔄 与YF对比

### YF当前实现

YF的单张处理在`CardTypeHandler`中，逻辑相对简单：
- 没有详细的手牌结构分析
- 没有明确的保护队友逻辑
- 没有PASS次数控制

### lalala的优势

1. **详细的手牌结构分析**: 识别各种牌型成员，避免破坏组合
2. **明确的保护队友逻辑**: 多种情况下的队友保护策略
3. **PASS次数控制**: 根据PASS次数调整策略
4. **优先级清晰**: 明确的优先级选择顺序

---

## 🎯 优化建议

### 1. 增强手牌结构分析

```python
def analyze_hand_structure(self, handcards, rank):
    sorted_cards = combine_handcards(handcards, rank)
    return {
        'single_member': sorted_cards["Single"],
        'pair_member': [card for pair in sorted_cards["Pair"] for card in pair],
        'trip_member': [card for trip in sorted_cards["Trips"] for card in trip],
        'bomb_member': [card for bomb in sorted_cards["Bomb"] for card in bomb],
        'straight_member': sorted_cards["Straight"][0] if sorted_cards["Straight"] else []
    }
```

### 2. 实现保护队友逻辑

```python
def should_protect_teammate(self, myPos, greaterPos, curVal, max_val):
    teammate_pos = (myPos + 2) % 4
    if teammate_pos == greaterPos:
        if curVal >= max_val or curVal >= 15:
            return True
    return False
```

### 3. 实现优先级选择

```python
def select_single_action(self, action_list, hand_structure, curVal, max_val):
    # 优先级1: 单张成员 + 大牌值
    for action in action_list:
        if self._is_single_member(action, hand_structure) and self._is_large_value(action, max_val):
            return action
    
    # 优先级2: 非炸弹成员 + 大牌值
    # ...
```

---

## 📝 总结

`Single()`是lalala最复杂的牌型处理方法，其设计特点：

1. ✅ **详细的手牌结构分析**: 识别各种牌型成员，避免破坏组合
2. ✅ **明确的保护队友逻辑**: 多种情况下的队友保护策略
3. ✅ **PASS次数控制**: 根据PASS次数调整策略
4. ✅ **优先级清晰**: 明确的优先级选择顺序
5. ✅ **残局处理**: 残局时的特殊策略

**对YF的启示**:
- **增强手牌结构分析**: 详细分析手牌，识别各种牌型成员
- **实现保护队友逻辑**: 多种情况下的队友保护策略
- **PASS次数控制**: 根据PASS次数调整策略
- **优先级清晰**: 建立明确的优先级选择顺序

---

**下一步**: 创建完整分析报告，总结所有方法的分析结果

