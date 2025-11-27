# 架构设计文档

本文档详细说明模块依赖关系和数据流设计。

## 一、模块依赖关系

### 1.1 依赖关系图

```
DecisionEngine (决策引擎)
├── DecisionTimer (时间控制)
│   └── (无依赖)
├── CooperationStrategy (配合策略)
│   └── EnhancedGameStateManager (状态管理)
│       └── CardTracker (记牌模块)
│           └── (无依赖)
├── MultiFactorEvaluator (多因素评估)
│   ├── EnhancedGameStateManager (状态管理)
│   │   └── CardTracker (记牌模块)
│   ├── HandCombiner (手牌组合)
│   │   └── (无依赖)
│   └── CooperationStrategy (配合策略)
│       └── EnhancedGameStateManager (状态管理)
└── CardTypeHandlerFactory (牌型处理器工厂)
    ├── EnhancedGameStateManager (状态管理)
    │   └── CardTracker (记牌模块)
    └── HandCombiner (手牌组合)
        └── (无依赖)
```

### 1.2 详细依赖说明

#### 决策引擎 → 状态管理 → 记牌模块
```
DecisionEngine
  └─> EnhancedGameStateManager
        └─> CardTracker
              ├─> 维护出牌历史
              ├─> 跟踪剩余牌库
              └─> 记录PASS次数
```

**数据流**:
- `DecisionEngine` 通过 `EnhancedGameStateManager` 访问游戏状态
- `EnhancedGameStateManager` 内部使用 `CardTracker` 维护记牌信息
- 状态更新时，`EnhancedGameStateManager` 自动更新 `CardTracker`

#### 决策引擎 → 配合策略 → 状态管理
```
DecisionEngine
  └─> CooperationStrategy
        └─> EnhancedGameStateManager
              ├─> 获取队友位置
              ├─> 获取剩余牌数
              └─> 判断是否队友动作
```

**数据流**:
- `DecisionEngine` 调用 `CooperationStrategy` 评估配合机会
- `CooperationStrategy` 通过 `EnhancedGameStateManager` 获取状态信息
- 配合策略基于状态信息做出判断

#### 决策引擎 → 手牌组合 → 游戏规则
```
DecisionEngine
  └─> HandCombiner
        ├─> 识别牌型组合
        ├─> 识别顺子和同花顺
        └─> 优化组牌策略
```

**数据流**:
- `DecisionEngine` 使用 `HandCombiner` 分析手牌结构
- `HandCombiner` 基于游戏规则识别牌型
- 手牌组合结果用于决策评估

### 1.3 依赖注入设计

所有模块通过依赖注入方式连接，避免硬编码依赖：

```python
# 初始化顺序
card_tracker = CardTracker()  # 1. 最底层
state_manager = EnhancedGameStateManager()  # 2. 依赖 CardTracker
hand_combiner = HandCombiner()  # 3. 独立模块
cooperation = CooperationStrategy(state_manager)  # 4. 依赖 StateManager
evaluator = MultiFactorEvaluator(state_manager, hand_combiner, cooperation)  # 5. 依赖多个模块
decision_engine = DecisionEngine(state_manager, max_decision_time=0.8)  # 6. 顶层，依赖所有模块
```

## 二、数据流设计

### 2.1 完整数据流图

```
WebSocket消息接收
    ↓
消息解析 (JSON)
    ↓
状态更新 (EnhancedGameStateManager.update_from_message)
    ├─> 更新基础状态 (myPos, handCards, curPos, etc.)
    ├─> 更新记牌信息 (CardTracker.update_from_play)
    │   ├─> 更新玩家历史
    │   ├─> 更新剩余牌库
    │   └─> 更新PASS次数
    └─> 更新公共信息 (publicInfo)
    ↓
决策引擎 (DecisionEngine.decide)
    ├─> 开始计时 (DecisionTimer.start)
    ├─> 判断主动/被动 (EnhancedGameStateManager.is_passive_play)
    │
    ├─> [被动出牌分支]
    │   ├─> 评估配合机会 (CooperationStrategy.get_cooperation_strategy)
    │   │   └─> 查询状态信息 (EnhancedGameStateManager)
    │   │       └─> 查询记牌信息 (CardTracker)
    │   │
    │   ├─> 使用牌型专门处理器 (CardTypeHandlerFactory.get_handler)
    │   │   ├─> 分析手牌结构 (HandCombiner.combine_handcards)
    │   │   └─> 处理被动出牌 (Handler.handle_passive)
    │   │
    │   └─> 多因素评估 (MultiFactorEvaluator.evaluate_all_actions)
    │       ├─> 评估剩余牌数因素 (查询 CardTracker)
    │       ├─> 评估牌型大小因素
    │       ├─> 评估配合因素 (查询 CooperationStrategy)
    │       ├─> 评估风险因素
    │       ├─> 评估时机因素
    │       └─> 评估手牌结构因素 (查询 HandCombiner)
    │
    └─> [主动出牌分支]
        └─> 多因素评估 (MultiFactorEvaluator.evaluate_all_actions)
            └─> (同上)
    ↓
检查超时 (DecisionTimer.check_timeout)
    ↓
选择最佳动作
    ↓
构建响应消息 ({"actIndex": X})
    ↓
WebSocket消息发送
```

### 2.2 关键数据流节点

#### 节点1: 消息接收和解析
```python
# WebSocket消息 → JSON解析
message = json.loads(websocket_message)
# message格式: {"type": "act", "stage": "play", "handCards": [...], ...}
```

#### 节点2: 状态更新
```python
# 状态管理器更新
state_manager.update_from_message(message)
# 内部流程:
#   1. 更新基础字段 (myPos, handCards, etc.)
#   2. 如果是notify消息，更新记牌信息
#   3. 更新公共信息
```

#### 节点3: 记牌模块更新
```python
# 记牌模块自动更新（在状态更新时触发）
if message.get("type") == "notify" and message.get("stage") == "play":
    card_tracker.update_from_play(cur_pos, cur_action, my_pos)
    # 更新:
    #   - 玩家出牌历史
    #   - 剩余牌库
    #   - PASS次数
```

#### 节点4: 配合策略评估
```python
# 配合策略评估
cooperation_result = cooperation.get_cooperation_strategy(
    action_list, cur_action, greater_action
)
# 内部流程:
#   1. 判断是否是队友出的牌 (state.is_teammate_action)
#   2. 获取对手剩余牌数 (state.get_opponent_remain_cards)
#   3. 获取队友剩余牌数 (state.get_teammate_remain_cards)
#   4. 评估配合机会
```

#### 节点5: 多因素评估
```python
# 多因素评估
evaluations = evaluator.evaluate_all_actions(action_list, cur_action)
# 评估流程:
#   1. 剩余牌数因素 (查询 state.get_player_remain_cards)
#   2. 牌型大小因素 (计算动作值)
#   3. 配合因素 (查询 cooperation)
#   4. 风险因素 (查询 state.get_pass_count)
#   5. 时机因素 (查询 state.stage, state.cur_rank)
#   6. 手牌结构因素 (查询 combiner.combine_handcards)
```

## 三、关键设计参考

### 3.1 队友识别公式
```python
# 参考获奖代码
teammate_pos = (myPos + 2) % 4
# 实现位置: EnhancedGameStateManager._update_team_info()
```

### 3.2 状态数据结构
```python
# 参考获奖代码的 state.py
history = {
    '0': {'send': [], 'remain': 27},
    '1': {'send': [], 'remain': 27},
    '2': {'send': [], 'remain': 27},
    '3': {'send': [], 'remain': 27},
}
remain_cards = {
    "S": [2, 2, 2, ...],  # 按花色和点数分类
    "H": [2, 2, 2, ...],
    ...
}
# 实现位置: CardTracker.__init__()
```

### 3.3 决策函数分离
```python
# 参考获奖代码的 action.py
# 主动出牌: active_decision()
# 被动出牌: passive_decision()
# 实现位置: DecisionEngine.active_decision() 和 DecisionEngine.passive_decision()
```

### 3.4 手牌组合算法
```python
# 参考获奖代码的 utils.py 的 combine_handcards()
# 实现位置: HandCombiner.combine_handcards()
# 功能:
#   - 识别单张、对子、三张、炸弹
#   - 识别顺子（考虑单张、对子、三张分布）
#   - 识别同花顺
```

## 四、配置管理

### 4.1 配置文件结构
配置文件: `config.yaml`

```yaml
decision:
  max_decision_time: 0.8
  enable_card_tracking: true
  enable_inference: true
  enable_cooperation: true
  cache_size: 1000

evaluation:
  weights:
    remaining_cards: 0.25
    card_type_value: 0.20
    cooperation: 0.20
    risk: 0.15
    timing: 0.10
    hand_structure: 0.10

cooperation:
  support_threshold: 15
  danger_threshold: 4
  max_val_threshold: 14
```

### 4.2 配置加载
```python
from src.config_loader import get_config

config = get_config()
max_time = config.get("decision.max_decision_time", 0.8)
weights = config.get_evaluation_weights()
```

## 五、测试框架

### 5.1 单元测试
- 测试每个模块的独立功能
- 测试模块接口的正确性

### 5.2 集成测试
- 测试模块之间的协作
- 测试完整决策流程

### 5.3 性能测试
- 测试决策时间
- 测试内存使用

### 5.4 策略测试
- 测试不同权重配置
- 测试不同策略参数

## 六、总结

### 6.1 已实现的依赖关系
- ? 决策引擎 → 状态管理 → 记牌模块
- ? 决策引擎 → 配合策略 → 状态管理
- ? 决策引擎 → 手牌组合 → 游戏规则

### 6.2 已实现的数据流
- ? WebSocket消息 → 消息解析 → 状态更新
- ? 状态更新 → 记牌模块更新
- ? 状态更新 → 决策引擎 → 动作选择
- ? 决策引擎 → 配合策略评估
- ? 决策引擎 → 多因素评估

### 6.3 已参考的关键设计
- ? 队友识别公式: `(myPos + 2) % 4`
- ? 状态数据结构: `history` 和 `remain_cards`
- ? 决策函数分离: `active_decision()` 和 `passive_decision()`
- ? 手牌组合算法: `combine_handcards()`

### 6.4 已实现的配置管理
- ? 配置文件: `config.yaml`
- ? 配置加载器: `ConfigLoader`
- ? 支持所有关键参数配置

