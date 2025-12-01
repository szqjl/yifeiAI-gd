# 知识规则转化器使用说明

## 概述

`KnowledgeTranslator` 类实现了将知识库中的文本规则转化为可执行代码逻辑的功能。它支持结构化规则（YAML/JSON格式）的解析和应用。

## 核心功能

### 1. 规则定义格式

规则采用结构化格式，支持条件表达式和动作调整：

```yaml
rules:
  - id: teammate_protection_1_2
    name: 队友保护-即将获胜
    description: 队友剩余1-2张牌，即将获胜
    condition:
      type: and
      conditions:
        - field: greater_pos
          op: "=="
          value: teammate_pos
        - field: teammate_cards
          op: "<="
          value: 2
    actions:
      - action_type: PASS
        score_adjust: 150
      - action_type: other
        score_adjust: -80
    priority: 10
```

### 2. 条件表达式

支持以下操作符：
- `==`: 等于
- `!=`: 不等于
- `<`: 小于
- `<=`: 小于等于
- `>`: 大于
- `>=`: 大于等于

支持逻辑组合：
- `and`: 所有条件都满足
- `or`: 任一条件满足

### 3. 上下文字段

规则评估时可用的上下文字段：
- `my_pos`: 我的位置
- `teammate_pos`: 队友的位置
- `next_pos`: 下家的位置
- `prev_pos`: 上家的位置
- `greater_pos`: 当前最大动作持有者的位置
- `cur_pos`: 当前出牌者的位置
- `teammate_cards`: 队友剩余牌数
- `min_opponent_cards`: 对手最少剩余牌数
- `max_opponent_cards`: 对手最多剩余牌数
- `cards_left`: 所有玩家剩余牌数字典

## 使用方法

### 基本使用

```python
from knowledge.knowledge_translator import KnowledgeTranslator
from knowledge.knowledge_loader import KnowledgeLoader

# 初始化
loader = KnowledgeLoader()
translator = KnowledgeTranslator(loader)

# 构建游戏状态
game_state = {
    "publicInfo": [...],
    "myPos": 0,
    "greaterPos": 2,
    "curPos": 2,
    "isActive": False,
    "curAction": ["Single", "A"]
}

# 增强动作分数
enhanced_score = translator.enhance_score("PASS", 100.0, game_state)
```

### 在决策引擎中使用

`KnowledgeEnhancedDecisionEngine` 已集成规则转化器：

```python
from knowledge.knowledge_enhanced_decision import KnowledgeEnhancedDecisionEngine

# 决策引擎会自动使用规则转化器
engine = KnowledgeEnhancedDecisionEngine(state_manager)
```

## 已实现的规则

当前已实现的核心规则：

1. **队友保护-即将获胜** (priority: 10)
   - 条件：队友控场且剩余1-2张牌
   - 动作：PASS +150，其他 -80

2. **队友保护-残局阶段** (priority: 8)
   - 条件：队友控场且剩余3-5张牌
   - 动作：PASS +100，其他 -50

3. **对手压制-即将获胜** (priority: 10)
   - 条件：对手剩余1-3张牌
   - 动作：PASS -100，其他 +150

4. **火不打四** (priority: 7)
   - 条件：对手剩余4张牌
   - 动作：Bomb -30

5. **逢五出对** (priority: 8)
   - 条件：对手剩余5张牌
   - 动作：Pair +100，其他 +60

## 添加新规则

### 方法1：在代码中添加

```python
translator = KnowledgeTranslator()

new_rule = {
    "id": "my_custom_rule",
    "name": "自定义规则",
    "description": "规则描述",
    "condition": {
        "type": "and",
        "conditions": [
            {"field": "teammate_cards", "op": "<=", "value": 5}
        ]
    },
    "actions": [
        {"action_type": "PASS", "score_adjust": 50}
    ],
    "priority": 5
}

translator.add_rule(new_rule)
```

### 方法2：从YAML文件加载 ✅ **已实现**

将规则定义在YAML文件中，系统会自动加载：

```yaml
# docs/knowledge/my_rules.yaml
rules:
  - id: my_custom_rule
    name: 自定义规则
    condition:
      type: and
      conditions:
        - field: teammate_cards
          op: "<="
          value: 5
    actions:
      - action_type: PASS
        score_adjust: 50
    priority: 5
```

系统会在初始化时自动扫描 `docs/knowledge/` 目录下的所有 `.yaml` 和 `.yml` 文件。

## 高级功能

### 嵌套条件

支持多层嵌套的and/or/not逻辑：

```yaml
condition:
  type: and
  conditions:
    - type: or
      conditions:
        - field: greater_pos
          op: "=="
          value: teammate_pos
        - field: cur_pos
          op: "=="
          value: teammate_pos
    - type: not
      condition:
        field: min_opponent_cards
        op: "<="
        value: 3
```

### 函数调用

支持内置函数：

```yaml
condition:
  type: function
  name: is_endgame
  args: []
```

**可用函数**：
- `min(value1, value2, ...)` - 返回最小值
- `max(value1, value2, ...)` - 返回最大值
- `abs(value)` - 返回绝对值
- `sum(value1, value2, ...)` - 返回和
- `has_bomb()` - 检查是否有炸弹
- `is_endgame()` - 判断是否残局

### in操作符

检查值是否在列表中：

```yaml
condition:
  field: action_type
  op: in
  value: [Pair, ThreeWithTwo, Straight]
```

### 函数计算字段值

使用函数计算字段值：

```yaml
condition:
  field:
    type: function
    name: min
    args:
      - field: teammate_cards
      - field: min_opponent_cards
  op: "<="
  value: 5
```

详细示例请参考 `docs/knowledge/advanced_rules_example.yaml`。

## 规则优先级

规则按 `priority` 字段排序，优先级高的规则先应用。相同优先级的规则按定义顺序应用。

## 注意事项

1. **规则冲突**: 如果多个规则同时满足条件，所有规则的分数调整会累加
2. **性能考虑**: 规则评估在每次决策时进行，应避免过于复杂的条件
3. **向后兼容**: 当前实现保留了原有的硬编码逻辑作为补充

## 相关文件

- `src/knowledge/knowledge_translator.py` - 规则转化器实现
- `src/knowledge/knowledge_enhanced_decision.py` - 决策引擎集成
- `docs/knowledge/structured_rules_example.yaml` - 规则格式示例

