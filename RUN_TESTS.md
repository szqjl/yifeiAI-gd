# 测试运行指南

## 问题说明

如果在PowerShell中直接复制粘贴测试输出内容，PowerShell会将其解释为命令，导致错误。

**错误示例**：
```
PS D:\YiFeiAI-GD> [测试6] 规则转化器集成测试
ParserError: Unexpected token '规则转化器集成测试' in expression or statement.
```

## 正确的运行方法

### 方法1：使用Python直接运行（推荐）

在PowerShell或命令提示符中运行：

```bash
# Windows PowerShell
python test_knowledge_enhanced_decision.py

# 或者使用完整路径
python D:\YiFeiAI-GD\test_knowledge_enhanced_decision.py
```

### 方法2：使用Python模块方式

```bash
cd D:\YiFeiAI-GD
python -m pytest test_knowledge_enhanced_decision.py
```

### 方法3：在Python交互式环境中运行

```bash
python
>>> exec(open('test_knowledge_enhanced_decision.py').read())
```

## 测试脚本列表

### 1. 知识加载器测试
```bash
python test_knowledge_loader_comprehensive.py
```

### 2. 知识增强决策引擎测试
```bash
python test_knowledge_enhanced_decision.py
```

### 3. 规则转化器测试
```bash
python test_knowledge_translator.py
```

### 4. 高级规则测试
```bash
python test_advanced_rules.py
```

### 5. 知识检索器测试
```bash
python test_knowledge_retriever.py
```

### 6. Priority调整测试
```bash
python test_priority_adjustment.py
```

## 常见问题

### 问题1：找不到模块

**错误**：`ModuleNotFoundError: No module named 'knowledge'`

**解决**：确保在项目根目录运行，或使用：
```bash
cd D:\YiFeiAI-GD
python test_knowledge_enhanced_decision.py
```

### 问题2：缺少yaml模块

**错误**：`No module named 'yaml'`

**解决**：
```bash
pip install pyyaml
```

### 问题3：编码问题

**错误**：`UnicodeEncodeError`

**解决**：测试脚本已包含编码修复，如果仍有问题，设置环境变量：
```bash
# PowerShell
$env:PYTHONIOENCODING="utf-8"
python test_knowledge_enhanced_decision.py
```

## 预期输出

成功运行后，应该看到类似以下输出：

```
============================================================
知识增强决策引擎 (KnowledgeEnhancedDecisionEngine) 测试
============================================================

[测试1] 初始化知识增强决策引擎
------------------------------------------------------------
✅ 初始化成功
   知识加载器: 已加载
   规则转化器: 已加载

[测试2] 评分增强 - 队友保护场景
------------------------------------------------------------
   ✅ PASS分数增强正确: 50.0 -> 175.0

...

============================================================
测试结果总结
============================================================
✅ 所有测试完成
```

## 注意事项

1. **不要直接复制粘贴测试输出**：测试输出是结果，不是命令
2. **确保在正确的目录**：在项目根目录 `D:\YiFeiAI-GD` 运行
3. **检查Python版本**：建议使用Python 3.8+
4. **安装依赖**：运行 `pip install -r requirements.txt`

## 快速验证

运行以下命令快速验证环境：

```bash
# 检查Python版本
python --version

# 检查依赖
python -c "import yaml; print('PyYAML OK')"

# 检查模块导入
python -c "import sys; sys.path.insert(0, 'src'); from knowledge.knowledge_loader import KnowledgeLoader; print('Import OK')"
```

