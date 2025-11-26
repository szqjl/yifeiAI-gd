# 中优先级模块说明

本文档说明已实施的中优先级优化模块。

## 模块列表

1. **手牌组合优化模块** (HandCombiner) - 已完善
2. **牌型专门处理模块** (CardTypeHandlers) - 新建
3. **决策时间控制模块** (DecisionTimer) - 新建
4. **多因素评估系统** (MultiFactorEvaluator) - 新建

## 1. 手牌组合优化模块 (HandCombiner) - 完善版

**文件**: `src/game_logic/hand_combiner.py`

**改进内容**:
- 完整实现了顺子识别算法（参考获奖代码）
- 实现了同花顺识别
- 优化了组牌策略，优先保留有价值的牌型
- 添加了 `is_in_straight()` 辅助方法

**主要接口**:
```python
combiner = HandCombiner()

# 组合手牌（完整实现）
sorted_cards, bomb_info = combiner.combine_handcards(handcards, rank)

# 判断牌是否在顺子中
is_in = combiner.is_in_straight(action, straight_member)

# 获取组牌优先级
priority = combiner.get_grouping_priority()
```

## 2. 牌型专门处理模块 (CardTypeHandlers)

**文件**: `src/decision/card_type_handlers.py`

**功能**:
- 为每种牌型创建专门的处理类
- 实现针对性的决策逻辑
- 支持主动和被动两种出牌模式

**已实现的处理器**:
- `SingleHandler`: 单张处理
- `PairHandler`: 对子处理
- `TripsHandler`: 三张处理
- `BombHandler`: 炸弹处理
- `StraightHandler`: 顺子处理

**使用方式**:
```python
from decision.card_type_handlers import CardTypeHandlerFactory

# 获取处理器
handler = CardTypeHandlerFactory.get_handler("Single", state_manager, hand_combiner)

# 处理被动出牌
result = handler.handle_passive(action_list, cur_action, handcards, rank)

# 处理主动出牌
result = handler.handle_active(action_list, handcards, rank)
```

**设计模式**:
- 使用抽象基类 `BaseCardTypeHandler` 定义接口
- 每种牌型有独立的处理逻辑
- 通过工厂模式 `CardTypeHandlerFactory` 获取处理器

## 3. 决策时间控制模块 (DecisionTimer)

**文件**: `src/decision/decision_timer.py`

**功能**:
- 设置最大决策时间（默认0.8秒）
- 超时检测和保护
- 渐进式决策支持
- 装饰器支持

**主要接口**:
```python
from decision.decision_timer import DecisionTimer, with_timeout

# 基本使用
timer = DecisionTimer(max_time=0.8)
timer.start()
# ... 决策逻辑 ...
if timer.check_timeout():
    return default_result
remaining = timer.get_remaining_time()

# 装饰器使用
@with_timeout(max_time=0.8, default_return=0)
def my_decision_function():
    # 决策逻辑
    return result
```

**渐进式决策**:
```python
from decision.decision_timer import ProgressiveDecision

progressive = ProgressiveDecision(timer)
for candidate in candidates:
    if not progressive.should_continue():
        break
    score = evaluate(candidate)
    progressive.update(candidate, score)
result = progressive.get_result()
```

## 4. 多因素评估系统 (MultiFactorEvaluator)

**文件**: `src/decision/multi_factor_evaluator.py`

**功能**:
- 综合评估多个因素
- 计算动作的综合评分
- 支持权重调整

**评估因素**:
1. **剩余牌数因素** (25%): 考虑自己、队友、对手的剩余牌数
2. **牌型大小因素** (20%): 评估牌型大小和压制能力
3. **配合因素** (20%): 评估配合机会和配合效果
4. **风险因素** (15%): 评估出牌风险
5. **时机因素** (10%): 评估游戏阶段和时机
6. **手牌结构因素** (10%): 评估对手牌结构的影响

**主要接口**:
```python
evaluator = MultiFactorEvaluator(state_manager, hand_combiner, cooperation)

# 评估单个动作
score = evaluator.evaluate_action(action, action_index, cur_action, action_list)

# 评估所有动作
evaluations = evaluator.evaluate_all_actions(action_list, cur_action)
# 返回: [(索引, 评分), ...] 按评分降序排列

# 获取最佳动作
best_index = evaluator.get_best_action(action_list, cur_action)

# 更新权重
evaluator.update_weights({
    "remaining_cards": 0.30,
    "cooperation": 0.25,
    # ...
})
```

**评分范围**: 0-100，数值越大越好

## 集成使用

### 完整决策流程

```python
from game_logic.enhanced_state import EnhancedGameStateManager
from game_logic.hand_combiner import HandCombiner
from decision.decision_engine import DecisionEngine
from decision.cooperation import CooperationStrategy
from decision.multi_factor_evaluator import MultiFactorEvaluator
from decision.decision_timer import DecisionTimer

# 初始化
state_manager = EnhancedGameStateManager()
combiner = HandCombiner()
cooperation = CooperationStrategy(state_manager)
evaluator = MultiFactorEvaluator(state_manager, combiner, cooperation)
decision_engine = DecisionEngine(state_manager, max_decision_time=0.8)

# 处理消息
state_manager.update_from_message(message)

# 做出决策（自动集成所有模块）
act_index = decision_engine.decide(message)
```

## 模块特点

1. **模块化设计**: 每个模块职责清晰，易于维护
2. **可扩展性**: 可以轻松添加新的牌型处理器
3. **性能优化**: 时间控制确保决策在合理时间内完成
4. **灵活配置**: 评估权重可以调整以适应不同策略

## 下一步优化

1. **完善牌型处理器**: 实现更多牌型的专门处理逻辑
2. **优化评估权重**: 根据实际测试调整权重
3. **添加缓存机制**: 缓存常见局面的评估结果
4. **性能调优**: 优化算法，减少决策时间

## 注意事项

1. 决策时间默认设置为0.8秒，可以根据实际情况调整
2. 评估权重可以根据策略需求调整
3. 牌型处理器返回-1表示应该PASS
4. 所有模块都已集成到 `DecisionEngine` 中，可以直接使用

