# 知识库模块说明

## 功能概述

知识库模块用于将 `docs/knowledge` 文件夹中的掼蛋知识和策略注入到AI决策系统中。

## 模块结构

```
src/knowledge/
├── __init__.py                      # 模块初始化
├── knowledge_loader.py              # 知识库加载器
├── knowledge_enhanced_decision.py   # 知识库增强决策引擎
└── README.md                        # 本文件
```

## 核心组件

### 1. KnowledgeLoader（知识库加载器）

**功能**：
- 自动加载 `docs/knowledge` 文件夹中的所有 markdown 文件
- 解析 frontmatter 元数据（标题、类型、标签、优先级等）
- 提取牌型信息（Single, Pair, Trips 等）
- 按牌型和游戏阶段分类知识

**主要接口**：
```python
from knowledge.knowledge_loader import KnowledgeLoader

# 创建加载器
loader = KnowledgeLoader()

# 根据牌型获取技能
skills = loader.get_skills_by_card_type("Pair")

# 根据游戏阶段获取技能
skills = loader.get_skills_by_phase("midgame")

# 搜索知识库
results = loader.search_knowledge("对子")

# 获取知识库摘要
summary = loader.get_knowledge_summary()
```

### 2. KnowledgeEnhancedDecisionEngine（知识库增强决策引擎）

**功能**：
- 继承自 `DecisionEngine`，在原有决策基础上应用知识库规则
- 根据知识库中的技能优先级调整动作评分
- 在决策时考虑知识库中的策略建议

**使用方式**：
```python
from knowledge.knowledge_enhanced_decision import KnowledgeEnhancedDecisionEngine
from game_logic.enhanced_state import EnhancedGameStateManager

# 初始化
state_manager = EnhancedGameStateManager()
decision_engine = KnowledgeEnhancedDecisionEngine(state_manager)

# 决策（自动应用知识库规则）
act_index = decision_engine.decide(message)
```

## 集成到客户端

### Test1.py 和 Test2.py

这两个客户端已经集成了知识库增强决策引擎：

```python
from game_logic.enhanced_state import EnhancedGameStateManager
from knowledge.knowledge_enhanced_decision import KnowledgeEnhancedDecisionEngine

class BasicGuandanClient:
    def __init__(self, user_info):
        # 初始化状态管理器
        self.state_manager = EnhancedGameStateManager()
        
        # 初始化知识库增强的决策引擎
        self.decision_engine = KnowledgeEnhancedDecisionEngine(self.state_manager)
    
    async def handle_messages(self):
        # ...
        if data.get("type") == "act":
            # 更新状态
            self.state_manager.update_from_message(data)
            
            # 使用知识库增强的决策引擎（自动应用知识库规则）
            act_index = self.decision_engine.decide(data)
```

## 知识库结构

知识库位于 `docs/knowledge/`，包含：

- **rules/**: 游戏规则知识
  - `01_basic_rules/`: 基础规则
  - `02_advanced_rules/`: 高级规则
  - `02_competition_rules/`: 比赛规则

- **skills/**: 技能策略知识
  - `01_foundation/`: 基础技能
  - `02_main_attack/`: 主攻技能
  - `03_assist_attack/`: 助攻技能
  - `04_common_skills/`: 通用技能
  - `07_opening/`: 开局技能
  - `08_endgame/`: 残局技能

## 知识库文件格式

每个知识库文件使用 markdown 格式，包含 frontmatter 元数据：

```markdown
---
title: 对子技巧
type: skill
category: Skills/CommonSkills
tags: [对子, 牌型, 通用技巧]
difficulty: 中级
priority: 4
game_phase: midgame
---

# 对子技巧

内容...
```

## 工作原理

1. **加载阶段**：启动时自动加载所有知识库文件
2. **解析阶段**：提取元数据和牌型信息
3. **决策阶段**：
   - 根据当前动作的牌型查找相关技能
   - 根据技能优先级计算评分加成
   - 调整动作评分，影响最终决策

## 评分加成规则

- **高优先级技能** (priority >= 5): +5.0 分
- **中优先级技能** (priority >= 3): +2.0 分
- **低优先级技能** (priority < 3): +0.5 分
- **最大加成**: 20.0 分

## 注意事项

1. 知识库加载在初始化时完成，启动后不会重新加载
2. 如果知识库路径不存在，会输出警告但不影响运行
3. 知识库规则作为评分加成，不会完全覆盖基础评估系统
4. 知识库文件需要符合 markdown + frontmatter 格式

## 扩展开发

### 添加新的知识库规则

1. 在 `docs/knowledge/` 相应目录下创建 markdown 文件
2. 添加 frontmatter 元数据
3. 在内容中提及相关牌型（如 `Pair`, `Single` 等）
4. 重启客户端，知识库会自动加载

### 自定义评分规则

修改 `knowledge_enhanced_decision.py` 中的 `_calculate_knowledge_bonus()` 方法来自定义评分加成规则。

