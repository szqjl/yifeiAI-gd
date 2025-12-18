# lalala决策机制分析 - 02: passive()

## 📋 方法概述

**方法名**: `passive()`  
**位置**: `action.py` 第964-1019行  
**作用**: 被动出牌（管牌）的核心逻辑，根据当前牌型调用对应的处理方法

---

## 🔍 方法签名

```python
def passive(self, actionList, handcards, rank, curAction, greaterAction, 
            myPos, greaterPos, remaincards, numofplayers, pass_num, 
            my_pass_num, remain_cards_classbynum):
```

### 参数说明

- `actionList`: 可选动作列表
- `handcards`: 手牌
- `rank`: 当前等级
- `curAction`: 当前动作
- `greaterAction`: 最大动作
- `myPos`: 自己的位置
- `greaterPos`: 最大动作的位置
- `remaincards`: 剩余牌库
- `numofplayers`: 所有玩家的剩余牌数列表
- `pass_num`: 连续PASS次数
- `my_pass_num`: 自己的PASS次数
- `remain_cards_classbynum`: 按数量分类的剩余牌

---

## 🎯 核心逻辑

### 1. 初始化牌值系统

```python
rank_card = 'H' + str(rank)  # 等级牌，如 'H2'
restcards = rest_cards(handcards, remaincards, rank)  # 计算剩余牌

# 牌值字典
card_value_s2v = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, 
                  "8": 8, "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, 
                  "A": 14, "B": 16, "R": 17, "JOKER": 10000}
card_value_s2v[rank_card[1]] = 15  # 等级牌值为15
```

**策略**:
- 建立牌值评估系统
- 等级牌（如当前等级是2，则H2）的值设为15，高于A（14）
- 大小王（B=16, R=17）和JOKER（10000）有特殊值

### 2. 处理PASS动作

```python
actIndex = 0  # 默认PASS
if curAction[0] == "PASS":
    curAction = greaterAction  # 如果当前是PASS，使用最大动作
print(curAction)
```

**策略**: 如果当前动作是PASS，使用最大动作作为参考。

### 3. 残局处理（关键策略）

```python
numofmy = numofplayers[myPos]  # 自己的剩余牌数
if numofmy <= 10:  # 残局判断
    numofnext = numofplayers[(myPos+1)%4]  # 下家剩余牌数
    actIndex = one_hand(numofmy, numofnext, actionList, myPos, greaterPos, 7,
                       restcards, card_value_s2v, rank_card)
    if actIndex != -1:
        return actIndex  # 残局有专门策略，直接返回
```

**关键策略**:
- **残局判断**: 当自己剩余牌数≤10时，进入残局模式
- **专门处理**: 调用`one_hand()`函数进行残局专门处理
- **优先级高**: 如果残局策略返回有效动作，直接返回，不再进行常规处理

**为什么重要**:
- 残局是游戏的关键阶段，需要特殊策略
- 残局时牌数少，决策更关键
- 需要快速出完牌，避免被对手压制

### 4. 根据牌型分发处理

```python
if curAction[0] == "Single":
    actIndex = self.Single(actionList, curAction, rank_card, handcards, 
                          numofplayers, restcards, card_value_s2v, 
                          myPos, greaterPos, pass_num, my_pass_num)

elif curAction[0] == "Pair":
    actIndex = self.Pair(actionList, curAction, rank_card, handcards, 
                        numofplayers, restcards, card_value_s2v, 
                        myPos, greaterPos, pass_num, my_pass_num)

elif curAction[0] == "Trips":
    actIndex = self.Trips(actionList, curAction, rank_card, handcards, 
                         numofplayers, restcards, card_value_s2v, 
                         myPos, greaterPos, pass_num, my_pass_num)

elif curAction[0] == "ThreeWithTwo":
    actIndex = self.ThreeWithTwo(actionList, curAction, rank_card, handcards, 
                                 numofplayers, restcards, card_value_s2v, 
                                 myPos, greaterPos, pass_num, my_pass_num)

elif curAction[0] == "ThreePair":
    actIndex = self.ThreePair(actionList, curAction, rank_card, handcards, 
                             numofplayers, restcards, card_value_s2v, 
                             myPos, greaterPos, pass_num, my_pass_num)

elif curAction[0] == "TwoTrips":
    actIndex = self.TwoTrips(actionList, curAction, rank_card, handcards, 
                            numofplayers, restcards, card_value_s2v, 
                            myPos, greaterPos, pass_num, my_pass_num)

elif curAction[0] == "Straight":
    actIndex = self.Straight(actionList, curAction, rank_card, handcards, 
                            numofplayers, card_value_s2v, pass_num, 
                            my_pass_num, myPos, greaterPos)

elif curAction[0] == "Bomb" or curAction[0] == "StraightFlush":
    actIndex = self.Bomb(actionList, curAction, rank_card, handcards, 
                        numofplayers, restcards, card_value_s2v, 
                        myPos, greaterPos)
```

**策略**:
- **牌型专门处理**: 每种牌型有专门的处理方法
- **参数统一**: 所有牌型处理方法接收相同的参数
- **职责分离**: 每种牌型的逻辑独立，易于维护和优化

---

## 💡 关键策略总结

### 1. 残局优先策略

**重要性**: ⭐⭐⭐⭐⭐

- 当剩余牌数≤10时，进入残局模式
- 使用专门的残局处理函数`one_hand()`
- 残局策略优先级最高，直接返回结果

**对YF的启示**:
- YF应该增加残局专门处理
- 残局时决策更关键，需要特殊策略
- 可以基于剩余牌数、下家牌数等因素制定残局策略

### 2. 牌值系统

**重要性**: ⭐⭐⭐⭐

- 建立清晰的牌值评估系统
- 等级牌有特殊值（15）
- 大小王和JOKER有特殊值

**对YF的启示**:
- YF应该有统一的牌值评估系统
- 考虑当前等级对牌值的影响
- 特殊牌（大小王）应该有特殊处理

### 3. 牌型专门处理

**重要性**: ⭐⭐⭐⭐⭐

- 每种牌型有专门的处理方法
- 逻辑清晰，易于维护
- 可以针对性地优化每种牌型

**对YF的启示**:
- YF应该为每种牌型创建专门的处理方法
- 避免使用通用的评估方法处理所有牌型
- 每种牌型有独特的策略需求

### 4. 参数传递

**重要性**: ⭐⭐⭐

- 所有牌型处理方法接收相同的参数
- 包括手牌、剩余牌、牌值系统、玩家信息等
- 为每个处理方法提供完整的上下文

**对YF的启示**:
- YF的牌型处理方法应该接收完整的上下文信息
- 包括手牌结构、剩余牌、玩家状态等
- 避免在方法内部重复计算

---

## 🔄 与YF对比

### YF当前实现

YF的被动出牌在`DecisionEngine.passive_decision()`中：

```python
def passive_decision(self, message: Dict, action_list: List[List]) -> int:
    # 1. 计算牌力
    my_power = calculate_card_power(handcards)
    teammate_power = estimate_teammate_power(...)
    
    # 2. 配合策略评估
    cooperation_result = self.cooperation.get_cooperation_strategy(...)
    if cooperation_result.get("should_pass"):
        return 0
    
    # 3. 使用特定牌型处理器
    handler = CardTypeHandlerFactory.get_handler(...)
    result = handler.handle_passive(...)
    
    # 4. 多因素评估
    evaluations = self.evaluator.evaluate_all_actions(...)
    return best_action
```

**问题**:
- 没有残局专门处理
- 多层评估，可能过于复杂
- 没有针对每种牌型的专门策略

### lalala的优势

1. **残局专门处理**: 当剩余牌数≤10时，使用专门策略
2. **牌型专门处理**: 每种牌型有专门方法，逻辑清晰
3. **简单直接**: 没有复杂的多层评估

---

## 🎯 优化建议

### 1. 增加残局处理

```python
def passive_decision(self, message: Dict, action_list: List[List]) -> int:
    my_remain = len(message.get("handCards", []))
    
    # 残局处理（剩余牌数≤10）
    if my_remain <= 10:
        return self._endgame_strategy(message, action_list)
    
    # 常规处理
    # ...
```

### 2. 牌型专门处理

为每种牌型创建专门的处理方法：

```python
def passive_decision(self, message: Dict, action_list: List[List]) -> int:
    cur_action = message.get("curAction")
    card_type = cur_action[0]
    
    # 根据牌型分发处理
    if card_type == "Single":
        return self._handle_single_passive(message, action_list)
    elif card_type == "Pair":
        return self._handle_pair_passive(message, action_list)
    # ...
```

### 3. 统一牌值系统

建立统一的牌值评估系统：

```python
class CardValueSystem:
    def __init__(self, rank):
        self.rank = rank
        self.base_values = {"2": 2, "3": 3, ..., "A": 14, "B": 16, "R": 17}
        self.base_values[str(rank)] = 15  # 等级牌
    
    def get_value(self, card):
        # 返回牌的实际值
        pass
```

---

## 📝 总结

`passive()`是lalala被动出牌的核心方法，其设计特点：

1. ✅ **残局优先**: 当剩余牌数≤10时，使用专门策略
2. ✅ **牌型专门处理**: 每种牌型有专门方法，逻辑清晰
3. ✅ **牌值系统**: 统一的牌值评估系统
4. ✅ **简单直接**: 没有复杂的多层评估

**对YF的启示**:
- **增加残局处理**: 当剩余牌数≤10时，使用专门策略
- **牌型专门处理**: 为每种牌型创建专门方法
- **统一牌值系统**: 建立清晰的牌值评估系统
- **简化架构**: 避免过于复杂的多层评估

---

**下一步**: 分析`active()`方法 - 主动出牌的核心逻辑

