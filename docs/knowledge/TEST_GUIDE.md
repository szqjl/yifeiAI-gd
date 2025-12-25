# 知识库系统测试指南

## 概述

本文档说明如何测试知识库系统的各个组件。

## 测试脚本

### 1. 知识加载器测试

**文件**: `test_knowledge_loader_comprehensive.py`

**测试内容**:
- ✅ 初始化测试
- ✅ 知识摘要统计
- ✅ 按牌型检索
- ✅ 按阶段检索
- ✅ 关键词搜索
- ✅ 知识项结构完整性
- ✅ 索引一致性检查
- ✅ 边界情况测试
- ✅ 优先级排序验证
- ✅ 特定知识项检索

**运行方法**:
```bash
python test_knowledge_loader_comprehensive.py
```

**预期输出**:
- 显示10个测试项的测试结果
- 显示知识库统计信息
- 验证所有功能正常工作

### 2. 规则转化器测试

**文件**: `test_knowledge_translator.py`

**测试内容**:
- 规则转化器初始化
- 条件评估
- 规则应用
- 分数增强

**运行方法**:
```bash
python test_knowledge_translator.py
```

### 3. 高级规则测试

**文件**: `test_advanced_rules.py`

**测试内容**:
- 嵌套条件
- 函数调用
- in操作符

**运行方法**:
```bash
python test_advanced_rules.py
```

### 4. 知识增强决策引擎测试

**文件**: `test_knowledge_enhanced_decision.py`

**测试内容**:
- 初始化测试
- 队友保护场景
- 对手压制场景
- 火不打四场景
- 逢五出对场景
- 规则转化器集成
- 知识库技能加分
- 完整决策流程

**运行方法**:
```bash
python test_knowledge_enhanced_decision.py
```

### 5. 知识检索器测试

**文件**: `test_knowledge_retriever.py`

**测试内容**:
- 语义搜索
- 上下文检索
- 关联查询

**运行方法**:
```bash
python test_knowledge_retriever.py
```

## 测试依赖

确保已安装以下依赖:
```bash
pip install pyyaml
```

## 运行测试的正确方法

### ⚠️ 重要提示

**不要直接复制粘贴测试输出内容到终端**！测试输出是结果，不是命令。

### 正确方法

在PowerShell或命令提示符中运行：

```bash
# 方法1：直接运行（推荐）
python test_knowledge_enhanced_decision.py

# 方法2：使用完整路径
python D:\YiFeiAI-GD\test_knowledge_enhanced_decision.py

# 方法3：先切换到项目目录
cd D:\YiFeiAI-GD
python test_knowledge_enhanced_decision.py
```

### 常见错误

如果在PowerShell中看到：
```
ParserError: Unexpected token '规则转化器集成测试'
```

这说明你复制粘贴了测试输出，而不是运行测试脚本。请使用上面的命令运行测试。

## 测试覆盖

### 已测试功能
- ✅ KnowledgeLoader 加载和检索
- ✅ KnowledgeTranslator 规则转化
- ✅ 高级规则功能（嵌套条件、函数调用）
- ✅ KnowledgeEnhancedDecisionEngine 评分增强

### 待测试功能
- [ ] KnowledgeRetriever 增强检索
- [ ] 规则文件自动加载
- [ ] 集成测试
- [ ] 实战验证

## 测试结果

运行测试后，检查：
1. 所有测试项是否通过
2. 是否有警告信息
3. 统计信息是否合理

## 相关文件

- `test_knowledge_loader_comprehensive.py` - 知识加载器综合测试
- `test_knowledge_translator.py` - 规则转化器测试
- `test_advanced_rules.py` - 高级规则测试
- `test_knowledge_enhanced_decision.py` - 知识增强决策引擎测试（新增）
- `test_knowledge_retriever.py` - 知识检索器测试
- `test_priority_adjustment.py` - Priority调整测试

