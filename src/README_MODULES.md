# 高优先级模块说明

本文档说明已实施的高优先级优化模块。

## 模块结构

```
src/
├── game_logic/          # 游戏逻辑模块
│   ├── __init__.py
│   ├── card_tracking.py      # 记牌与推理模块
│   ├── enhanced_state.py     # 增强状态管理
│   └── hand_combiner.py       # 手牌组合优化
│
└── decision/            # 决策引擎模块
    ├── __init__.py
    ├── decision_engine.py    # 决策引擎（主动/被动分离）
    └── cooperation.py        # 配合策略
```

## 1. 记牌与推理模块 (CardTracker)

**文件**: `src/game_logic/card_tracking.py`

**功能**:
- 维护每个玩家的出牌历史
- 跟踪剩余牌库（按花色和点数）
- 计算剩余牌概率分布
- 记录连续PASS次数

**主要接口**:
```python
tracker = CardTracker()

# 更新出牌信息
tracker.update_from_play(cur_pos, cur_action, my_pos)

# 获取玩家剩余牌数
remain = tracker.get_player_remain(pos)

# 获取剩余牌库
remain_cards = tracker.get_remaining_cards(rank)

# 计算剩余牌（排除手牌后）
rest_cards = tracker.calculate_rest_cards(handcards, rank)

# 重置小局数据
tracker.reset_episode()
```

## 2. 增强状态管理 (EnhancedGameStateManager)

**文件**: `src/game_logic/enhanced_state.py`

**功能**:
- 维护完整的游戏状态信息
- 集成记牌模块
- 提供状态查询接口
- 自动识别队友和对手

**主要接口**:
```python
state = EnhancedGameStateManager()

# 从消息更新状态
state.update_from_message(message)

# 判断是否被动出牌
is_passive = state.is_passive_play()

# 判断是否主动出牌
is_active = state.is_active_play()

# 判断是否是队友出的牌
is_teammate = state.is_teammate_action()

# 获取状态摘要
summary = state.get_state_summary()
```

## 3. 决策引擎 (DecisionEngine)

**文件**: `src/decision/decision_engine.py`

**功能**:
- 主动/被动决策分离
- 调用配合策略
- 综合评估和决策

**主要接口**:
```python
engine = DecisionEngine(state_manager)

# 主决策函数
act_index = engine.decide(message)

# 主动出牌决策
act_index = engine.active_decision(message, action_list)

# 被动出牌决策
act_index = engine.passive_decision(message, action_list)
```

## 4. 配合策略 (CooperationStrategy)

**文件**: `src/decision/cooperation.py`

**功能**:
- 识别队友意图
- 判断是否需要配合
- 制定配合策略

**主要接口**:
```python
cooperation = CooperationStrategy(state_manager)

# 判断是否应该配合队友
should_support = cooperation.should_support_teammate(cur_action_value)

# 判断是否应该接替队友
should_take_over = cooperation.should_take_over(cur_action_value, my_action_value)

# 评估配合机会
evaluation = cooperation.evaluate_cooperation_opportunity(action_list, cur_action)

# 获取配合策略
strategy = cooperation.get_cooperation_strategy(action_list, cur_action, greater_action)
```

## 5. 手牌组合优化 (HandCombiner)

**文件**: `src/game_logic/hand_combiner.py`

**功能**:
- 识别所有可能的牌型组合
- 优化组牌策略
- 考虑主牌对组合的影响

**主要接口**:
```python
combiner = HandCombiner()

# 组合手牌
sorted_cards, bomb_info = combiner.combine_handcards(handcards, rank)

# 获取组牌优先级
priority = combiner.get_grouping_priority()
```

## 使用示例

### 基本使用

```python
from game_logic.enhanced_state import EnhancedGameStateManager
from decision.decision_engine import DecisionEngine

# 初始化
state_manager = EnhancedGameStateManager()
decision_engine = DecisionEngine(state_manager)

# 处理消息
message = {
    "type": "act",
    "stage": "play",
    "handCards": ["S2", "H2", "C3", ...],
    "actionList": [[...], [...]],
    ...
}

# 更新状态
state_manager.update_from_message(message)

# 做出决策
act_index = decision_engine.decide(message)
```

### 完整客户端示例

参考 `src/communication/enhanced_client.py` 查看完整的客户端实现。

## 下一步优化

这些模块提供了基础框架，后续可以：

1. **完善决策算法**: 在 `active_decision()` 和 `passive_decision()` 中实现更智能的策略
2. **增强配合策略**: 优化 `CooperationStrategy` 的参数和逻辑
3. **完善手牌组合**: 在 `HandCombiner` 中实现更复杂的组牌算法
4. **添加推理功能**: 在 `CardTracker` 中实现对手手牌推理
5. **性能优化**: 添加缓存和预计算机制

## 注意事项

1. 所有模块都参考了获奖代码的实现
2. 队友识别公式: `(myPos + 2) % 4`
3. 状态更新需要在收到消息时及时调用
4. 记牌模块会在小局结束时自动重置

