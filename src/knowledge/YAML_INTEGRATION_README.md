# YAML规则集成到yf_v4方案

## 方案概述

为了将pyyaml集成到yf_v4中，我们采用了**YAML转Python代码**的方案，这样yf_v4就可以完全独立，不需要外部依赖。

## 实现方式

### 方案1：YAML转Python代码（已实现，推荐）

**优点**：
- ✅ **完全独立**：不需要yaml模块，yf_v4可以独立运行
- ✅ **性能更好**：直接导入Python字典，无需运行时解析
- ✅ **类型安全**：Python代码可以更好地进行类型检查

**实现**：
1. 使用 `yaml_to_python_converter.py` 将YAML规则文件转换为Python模块
2. `KnowledgeTranslator` 优先从Python模块加载规则
3. 如果Python模块不存在，回退到YAML文件加载（需要yaml模块）

### 方案2：setup.py依赖（备选）

如果希望保持YAML文件的灵活性，可以创建setup.py：

```python
from setuptools import setup, find_packages

setup(
    name="yf_v4",
    version="1.0.0",
    install_requires=[
        "pyyaml>=6.0",
        # 其他依赖...
    ],
)
```

## 使用方法

### 1. 转换YAML规则文件

运行转换器：

```bash
python src/knowledge/yaml_to_python_converter.py
```

这会生成 `src/knowledge/knowledge_rules.py` 文件，包含所有规则。

### 2. 自动加载

`KnowledgeTranslator` 会自动：
1. 首先尝试从 `knowledge_rules.py` 加载（无需yaml）
2. 如果失败，尝试从YAML文件加载（需要yaml）

### 3. 更新规则

当YAML规则文件更新后，重新运行转换器：

```bash
python src/knowledge/yaml_to_python_converter.py
```

## 文件结构

```
src/knowledge/
├── knowledge_translator.py      # 规则转化器（支持两种加载方式）
├── yaml_to_python_converter.py  # YAML转Python转换器
└── knowledge_rules.py           # 转换后的规则（自动生成）

docs/knowledge/
├── rules_card_grouping.yaml     # 原始YAML规则文件
├── rules_passing_skills.yaml
├── rules_card_language.yaml
└── rules_card_interactions.yaml
```

## 优势

### 1. 完全独立

yf_v4不再依赖pyyaml，可以：
- 直接运行，无需安装依赖
- 部署到任何Python环境
- 避免依赖冲突

### 2. 性能提升

- **启动更快**：直接导入Python字典，无需解析YAML
- **运行时更快**：无需YAML解析开销

### 3. 向后兼容

- 如果Python模块不存在，自动回退到YAML加载
- 支持两种方式共存

## 工作流程

### 开发阶段

1. 编辑YAML规则文件（`docs/knowledge/*.yaml`）
2. 运行转换器生成Python模块
3. 测试规则是否正确加载

### 部署阶段

1. 运行转换器生成 `knowledge_rules.py`
2. 将 `knowledge_rules.py` 包含在部署包中
3. yf_v4可以直接运行，无需yaml模块

## 注意事项

### 1. 转换时机

- **开发时**：每次修改YAML文件后运行转换器
- **部署前**：确保运行转换器生成最新版本
- **CI/CD**：可以在构建流程中自动运行转换器

### 2. 版本控制

- `knowledge_rules.py` 是自动生成的，可以：
  - 提交到版本控制（推荐，确保一致性）
  - 或添加到 `.gitignore`（在构建时生成）

### 3. 调试

如果规则加载有问题：
1. 检查 `knowledge_rules.py` 是否正确生成
2. 检查规则格式是否正确
3. 查看 `KnowledgeTranslator` 的加载日志

## 验证

运行以下命令验证集成：

```bash
# 1. 转换YAML文件
python src/knowledge/yaml_to_python_converter.py

# 2. 测试规则加载
python -c "import sys; sys.path.insert(0, 'src'); from knowledge.knowledge_translator import KnowledgeTranslator; t = KnowledgeTranslator(); print(f'总规则数: {len(t.core_rules)}')"

# 3. 检查依赖（应该显示yaml可选）
python src/knowledge/dependency_check.py
```

## 总结

✅ **已实现**：YAML规则已转换为Python代码，yf_v4可以完全独立运行

✅ **向后兼容**：如果Python模块不存在，自动回退到YAML加载

✅ **性能提升**：直接导入，无需运行时解析

✅ **易于维护**：YAML文件作为源文件，Python代码自动生成

