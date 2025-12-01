# 增强知识检索器使用说明

## 概述

`KnowledgeRetriever` 类实现了增强的知识检索功能，包括语义搜索、上下文检索和知识关联查询。

## 核心功能

### 1. 语义搜索 (Semantic Search)

基于关键词匹配和相似度的智能搜索：

```python
from knowledge.knowledge_retriever import KnowledgeRetriever

retriever = KnowledgeRetriever()

# 语义搜索
results = retriever.semantic_search("队友保护", top_k=5)
for item in results:
    print(f"{item['title']} (相关性: {item['relevance_score']:.2f})")
```

**搜索维度**：
- 标题匹配（权重最高）
- 标签匹配
- 关键词匹配
- 内容匹配
- 优先级加权

### 2. 上下文检索 (Context-Aware Retrieval)

根据游戏状态检索相关知识：

```python
game_state = {
    'phase': 'endgame',        # 游戏阶段
    'card_types': ['Pair'],    # 关注的牌型
    'role': '助攻',            # 当前角色
    'situation': '队友剩5张牌'  # 情况描述
}

results = retriever.context_aware_retrieval(game_state)
```

**检索维度**：
- 游戏阶段（opening/midgame/endgame）
- 牌型（Single/Pair/Bomb等）
- 角色（主攻/助攻）
- 情况描述（语义搜索）

### 3. 知识关联查询 (Related Knowledge)

获取相关知识项：

```python
# 获取与某个知识项相关的其他知识
related = retriever.get_related_knowledge(
    "skills/03_assist_attack/01_passing_skills.md",
    top_k=5
)
```

**关联方式**：
- 基于tags关联
- 基于card_types关联
- 自动去重和排序

### 4. 综合上下文检索

结合多种条件进行检索：

```python
context = {
    'phase': 'midgame',
    'card_types': ['Bomb'],
    'role': '主攻',
    'query': '如何出炸弹'
}

results = retriever.get_knowledge_by_context(context)
```

## 使用示例

### 示例1：搜索传牌技巧

```python
retriever = KnowledgeRetriever()

# 语义搜索
results = retriever.semantic_search("传牌", top_k=3)
for item in results:
    print(f"{item['title']} - {item.get('relevance_score', 0):.2f}")
```

### 示例2：残局阶段检索

```python
game_state = {
    'phase': 'endgame',
    'card_types': ['Pair'],
    'situation': '对手剩5张'
}

results = retriever.context_aware_retrieval(game_state)
```

### 示例3：获取相关知识

```python
# 假设当前查看"传牌技巧"
knowledge_id = "skills/03_assist_attack/01_passing_skills.md"
related = retriever.get_related_knowledge(knowledge_id, top_k=3)

print("相关知识：")
for item in related:
    print(f"  - {item['title']}")
```

## 关键词索引

检索器内置了关键词映射，支持以下概念：

- **角色相关**: 主攻、助攻、队友、对手
- **牌型相关**: 单张、对子、三带二、顺子、炸弹、同花顺
- **阶段相关**: 开局、中局、残局
- **策略相关**: 组牌、传牌、出炸、保护、压制

## 性能优化

- **知识关联图**: 启动时构建，O(1)查询
- **关键词索引**: 启动时构建，快速匹配
- **结果缓存**: 可扩展支持结果缓存

## 相关文件

- `src/knowledge/knowledge_retriever.py` - 检索器实现
- `src/knowledge/knowledge_loader.py` - 基础知识加载器
- `test_knowledge_retriever.py` - 测试脚本

