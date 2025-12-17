# lalala决策机制分析 - 03: active()

## 📋 方法概述

**方法名**: `active()`  
**位置**: `action.py` 第1093-1183行  
**作用**: 主动出牌（首出）的核心逻辑，选择最佳出牌策略

---

## 🔍 方法签名

```python
def active(self, actionList, handcards, rank, numofplayers, mypos, remaincards):
```

### 参数说明

- `actionList`: 可选动作列表
- `handcards`: 手牌
- `rank`: 当前等级
- `numofplayers`: 所有玩家的剩余牌数列表
- `mypos`: 自己的位置
- `remaincards`: 剩余牌库

---

## 🎯 核心逻辑

### 1. 初始化

```python
restcards = rest_cards(handcards, remaincards, rank)  # 计算剩余牌
rank_card = 'H' + rank  # 等级牌
numofnext = numofplayers[(mypos + 1) % 4]  # 下家剩余牌数
if numofnext == 0:
    numofnext = numofplayers[(mypos - 1) % 4]  # 如果下家完牌，看上家

# 牌值系统
cur = [9,10,9,8,10,10,2]  # 阈值数组
card_value_s2v = {"2": 2, ..., "A": 14, "B": 16, "R": 17}
card_value_s2v2 = {"A": 1, "2": 2, ..., "K": 13, "B": 16, "R": 17}
card_value_s2v[rank] = 15  # 等级牌值为15
```

**关键点**:
- `cur`数组定义了不同牌型的阈值
- 两个牌值系统：`card_value_s2v`（正常）和`card_value_s2v2`（A=1，用于顺子）

### 2. 获取手牌列表

```python
sorted_cards, single_actionlist, pair_actionlist, trips_actionlist, 
threepair_actionlist, threetwo_actionlist, twotrips_actionlist, 
straight_actionlist = self.getlist(handcards, rank)
```

**策略**: 调用`getlist()`分析手牌结构，提取各种牌型组合。

### 3. 一手出完（最高优先级）

```python
for i in actionList:
    if len(handcards) == len(i[2]):  # 如果某个动作使用了所有手牌
        return actionList.index(i)  # 直接返回，一手出完
```

**策略**: 如果能一手出完，直接出完，最高优先级。

### 4. 两手出完（剩余牌数≤12时）

```python
twohand_candidatelist = []
if len(handcards) <= 12:
    for i in range(len(actionList)):
        for j in range(i+1, len(actionList)):
            if len(actionList[i][-1]) + len(actionList[j][-1]) == len(handcards):
                combine_list = actionList[i][-1] + actionList[j][-1]
                if combine_list.sort(key=mysort2) == handcards.sort(key=mysort2):
                    twohand_candidatelist.append((i,j))
```

**策略**: 当剩余牌数≤12时，寻找能两手出完的组合。

### 5. 优先级决策（按顺序）

#### 5.1 单张（小牌值）

```python
if len(single_actionlist) and card_value_s2v[single_actionlist[0][0]] < cur[0]:
    if numofnext == 1:  # 下家只剩1张，不出单张
        pass
    else:
        return getindex("Single", single_actionlist, actionList)
```

**策略**: 
- 如果最小单张值 < 9（cur[0]），优先出单张
- 但如果下家只剩1张，不出单张（避免被管）

#### 5.2 三连对/钢板

```python
if len(threepair_actionlist) or len(twotrips_actionlist):
    index = rankfour(twotrips_actionlist, threepair_actionlist, actionList, cur[1], cur[2])
    if index is not None:
        return index
```

**策略**: 如果有三连对或钢板，优先出（阈值cur[1]=10, cur[2]=9）。

#### 5.3 顺子

```python
if len(straight_actionlist) and card_value_s2v2[straight_actionlist[0][0]] < cur[4]:
    return getindex("Straight", straight_actionlist, actionList)
```

**策略**: 如果最小顺子值 < 8（cur[4]），优先出顺子。

#### 5.4 三带二

```python
if len(threetwo_actionlist):
    index = rankthree(single_actionlist, pair_actionlist, trips_actionlist, 
                     threetwo_actionlist, actionList, numofnext, rank, 
                     cur[0], cur[3], cur[4], cur[5], cur[-1])
    if index is not None:
        return index
```

**策略**: 调用`rankthree()`函数评估三带二。

#### 5.5 三张

```python
if len(trips_actionlist):
    return rankone(single_actionlist, trips_actionlist, actionList, numofnext, rank)
```

**策略**: 调用`rankone()`函数评估三张。

#### 5.6 对子

```python
if len(pair_actionlist):
    return ranktwo(handcards, single_actionlist, pair_actionlist, trips_actionlist, 
                  actionList, numofnext, rank, max_val)
```

**策略**: 调用`ranktwo()`函数评估对子。

#### 5.7 单张（特殊情况）

```python
if len(single_actionlist):
    if numofnext == 1 and len(trips_actionlist) == 0 and len(pair_actionlist) == 0 and rank_card in handcards:
        # 下家只剩1张，且没有三张和对子，且有等级牌
        # 尝试出对子（拆等级牌）
        for i in range(len(actionList)):
            if actionList[i][0] == 'Pair' and (actionList[i][-1][0] in sorted_cards['Single'] or ...):
                return i
    
    if numofnext == 1:
        # 下家只剩1张的特殊处理
        if len(trips_actionlist) == 0 and len(pair_actionlist) == 0 and rank_card not in handcards:
            # 没有三张和对子，且没有等级牌，出多张牌
            for acti in range(len(actionList)):
                if len(actionList[acti][-1]) > 1 and actionList[acti][0] != 'Bomb':
                    return acti
        # 出最大的单张（从单张成员中）
        now_max_act_value = 0
        now_max_act_key = 0
        for acti in range(len(actionList)):
            if actionList[acti][0] == 'Single' and actionList[acti][-1][0] in sorted_cards['Single']:
                if card_value_s2v[actionList[acti][1]] > now_max_act_value:
                    now_max_act_value = card_value_s2v[actionList[acti][1]]
                    now_max_act_key = acti
        return now_max_act_key
    
    return getindex("Single", single_actionlist, actionList)
```

**策略**: 
- 下家只剩1张时的特殊处理
- 优先出多张牌或最大单张

---

## 💡 关键策略总结

### 1. 优先级顺序

1. **一手出完** - 最高优先级
2. **两手出完** - 剩余牌数≤12时
3. **单张（小）** - 值 < 9
4. **三连对/钢板** - 值 < 10/9
5. **顺子** - 值 < 8
6. **三带二** - 评估后决定
7. **三张** - 评估后决定
8. **对子** - 评估后决定
9. **单张** - 最后选择

### 2. 下家只剩1张的特殊处理

- 不出小单张（避免被管）
- 优先出多张牌
- 如果没有多张牌，出最大单张

### 3. 阈值系统

`cur = [9,10,9,8,10,10,2]`定义了不同牌型的阈值：
- `cur[0] = 9`: 单张阈值
- `cur[1] = 10`: 钢板阈值
- `cur[2] = 9`: 三连对阈值
- `cur[3] = 8`: 三带二阈值
- `cur[4] = 10`: 顺子阈值
- `cur[5] = 10`: 其他阈值
- `cur[6] = 2`: 其他阈值

---

## 🔄 与YF对比

### YF当前实现

YF的主动出牌在`DecisionEngine.active_decision()`中：

```python
def active_decision(self, message: Dict, action_list: List[List]) -> int:
    # 多因素评估所有动作
    evaluations = self.evaluator.evaluate_all_actions(action_list, None)
    # 选择非PASS的最佳动作
    for idx, score in evaluations:
        if action_list[idx][0] != "PASS":
            return idx
    return 0
```

**问题**:
- 没有一手出完的优先判断
- 没有明确的优先级顺序
- 没有下家只剩1张的特殊处理

### lalala的优势

1. **一手出完优先**: 如果能一手出完，直接出完
2. **明确的优先级**: 按牌型优先级顺序决策
3. **特殊情况处理**: 下家只剩1张时的特殊策略

---

## 🎯 优化建议

### 1. 增加一手出完判断

```python
def active_decision(self, message: Dict, action_list: List[List]) -> int:
    handcards = message.get("handCards", [])
    
    # 一手出完（最高优先级）
    for i, action in enumerate(action_list):
        if len(handcards) == len(action[2]):
            return i
    
    # 常规决策
    # ...
```

### 2. 建立优先级系统

```python
def active_decision(self, message: Dict, action_list: List[List]) -> int:
    # 1. 一手出完
    if one_hand_complete:
        return one_hand_index
    
    # 2. 小单张
    if small_single_available:
        return small_single_index
    
    # 3. 三连对/钢板
    if threepair_or_twotrips_available:
        return threepair_index
    
    # ...
```

### 3. 特殊情况处理

```python
numofnext = get_next_player_remain_cards()
if numofnext == 1:
    # 下家只剩1张的特殊处理
    return handle_next_player_one_card(message, action_list)
```

---

## 📝 总结

`active()`是lalala主动出牌的核心方法，其设计特点：

1. ✅ **一手出完优先**: 如果能一手出完，直接出完
2. ✅ **明确的优先级**: 按牌型优先级顺序决策
3. ✅ **特殊情况处理**: 下家只剩1张时的特殊策略
4. ✅ **阈值系统**: 使用阈值数组控制不同牌型的出牌条件

**对YF的启示**:
- **增加一手出完判断**: 最高优先级
- **建立优先级系统**: 按牌型优先级顺序决策
- **特殊情况处理**: 下家只剩1张时的特殊策略
- **阈值系统**: 使用阈值控制出牌条件

---

**下一步**: 分析牌型处理方法（如`Single()`）

