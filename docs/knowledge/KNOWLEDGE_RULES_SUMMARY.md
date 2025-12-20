# 知识库规则提取总结

## 概述

从知识库文档中提取关键规则并转化为结构化规则（YAML格式），共创建4个规则文件，提取29条核心规则。

## 规则文件列表

### 1. 组牌技巧规则 (`rules_card_grouping.yaml`)

**来源**: `docs/knowledge/skills/07_opening/04_card_grouping_skills.md`

**规则数量**: 7条

**核心规则**:
1. 炸弹越多越好，单牌越少越好 (priority: 8)
2. 主攻组牌轮次优先 (priority: 7)
3. 助攻保留炸弹 (priority: 7)
4. 拆4头炸组同花顺的条件 (priority: 6)
5. 组顺生两单避免 (priority: 8)
6. 主攻牌型套路化 (priority: 6)
7. 助攻牌型多样化 (priority: 5)

### 2. 传牌技巧规则 (`rules_passing_skills.yaml`)

**来源**: `docs/knowledge/skills/03_assist_attack/01_passing_skills.md`

**规则数量**: 7条

**核心规则**:
1. 队友剩5张判断三带二 (priority: 9)
2. 队友剩9-10张送三带二 (priority: 8)
3. 队友跟三连对送三连对 (priority: 7)
4. 队友出顺子后可能有对子 (priority: 6)
5. 传队友被拦截的牌 (priority: 8)
6. 高单传牌 (priority: 5)
7. 队友不要观察需求 (priority: 4)

### 3. 牌语分析规则 (`rules_card_language.yaml`)

**来源**: `docs/knowledge/skills/04_common_skills/02_card_language.md`

**规则数量**: 7条

**核心规则**:
1. 首发出小单牌牌力强 (priority: 7)
2. 开局出对子情况不明 (priority: 5)
3. 开局出三张弱牌 (priority: 6)
4. 三带二与顺子关系 (priority: 8)
5. 队友出顺子送顺子或对子 (priority: 8)
6. 对手不接牌保留牌型 (priority: 4)
7. 上家出小单张牌力强 (priority: 5)

### 4. 相生相克规则 (`rules_card_interactions.yaml`)

**来源**: `docs/knowledge/skills/04_common_skills/03_card_interactions.md`

**规则数量**: 8条

**核心规则**:
1. 顺子与三带二相克 (priority: 7)
2. 三带二多顺子少 (priority: 7)
3. 对子与三张相克 (priority: 6)
4. 对手首打三张打对子 (priority: 6)
5. 单牌对子互补 (priority: 5)
6. 炸弹多三带二少 (priority: 5)
7. 炸弹多单张概率高 (priority: 4)
8. 组顺子形成单和对子 (priority: 5)

## 规则统计

- **总规则数**: 29条
- **高优先级规则** (priority >= 8): 8条
- **中优先级规则** (5 <= priority < 8): 15条
- **低优先级规则** (priority < 5): 6条

## 规则分布

### 按游戏阶段
- **开局阶段** (opening): 8条
- **中局阶段** (midgame): 15条
- **残局阶段** (endgame): 6条

### 按牌型
- **炸弹相关**: 3条
- **顺子相关**: 5条
- **三带二相关**: 6条
- **对子相关**: 5条
- **单张相关**: 4条
- **其他**: 6条

## 使用说明

这些规则文件会被 `KnowledgeTranslator` 自动加载：

```python
from knowledge.knowledge_translator import KnowledgeTranslator

# 初始化时会自动加载所有YAML规则文件
translator = KnowledgeTranslator(rules_dir="docs/knowledge")

# 规则会自动应用到决策中
enhanced_score = translator.enhance_score(action_type, base_score, game_state)
```

## 规则格式

所有规则遵循统一格式：

```yaml
rules:
  - id: rule_id
    name: 规则名称
    description: 规则描述
    source: 来源文档
    condition:
      type: and/or/not
      conditions: [...]
    actions:
      - action_type: 动作类型
        score_adjust: 分数调整
        description: 动作描述
    priority: 优先级(1-10)
    game_phase: 游戏阶段
```

## 后续优化

1. **规则验证**: 添加规则有效性验证
2. **规则测试**: 编写规则测试用例
3. **规则优化**: 根据实战效果调整规则参数
4. **规则扩展**: 从更多知识库文档中提取规则

## 相关文件

- `docs/knowledge/rules_card_grouping.yaml` - 组牌技巧规则
- `docs/knowledge/rules_passing_skills.yaml` - 传牌技巧规则
- `docs/knowledge/rules_card_language.yaml` - 牌语分析规则
- `docs/knowledge/rules_card_interactions.yaml` - 相生相克规则
- `src/knowledge/knowledge_translator.py` - 规则转化器（自动加载这些规则）

