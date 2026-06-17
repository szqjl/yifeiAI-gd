# YAML依赖问题修复说明

## 问题描述

运行测试时遇到 `No module named 'yaml'` 错误。

## 解决方案

### 1. 代码已实现优雅降级

代码已经实现了优雅降级机制，即使没有安装 PyYAML，系统仍然可以工作：

- **KnowledgeLoader**: 如果 yaml 模块不可用，会使用简单的键值对解析器 (`_parse_simple_frontmatter`)
- **KnowledgeTranslator**: 如果 yaml 模块不可用，YAML 规则文件加载功能会被禁用，但内置规则仍然可用

### 2. 安装 PyYAML（推荐）

为了完整功能，建议安装 PyYAML：

```bash
# 方法1：使用 requirements.txt
pip install -r requirements.txt

# 方法2：仅安装 PyYAML
pip install pyyaml

# 方法3：指定版本
pip install pyyaml>=6.0
```

### 3. 验证安装

```bash
python -c "import yaml; print('PyYAML version:', yaml.__version__)"
```

## 测试结果

即使没有安装 PyYAML，测试仍然可以运行：

```
Warning: PyYAML is not installed. YAML frontmatter parsing will be disabled.
Loaded 32 knowledge items.
✅ 初始化成功
   知识加载器: 已加载
   规则转化器: 已加载
```

## 功能影响

### 无 PyYAML 时的限制

1. **YAML frontmatter 解析**: 使用简单解析器，可能无法处理复杂的 YAML 结构
2. **YAML 规则文件加载**: 无法从 YAML 文件加载规则，只能使用内置规则

### 有 PyYAML 时的完整功能

1. ✅ 完整的 YAML frontmatter 解析
2. ✅ 从 YAML 文件动态加载规则
3. ✅ 支持复杂的 YAML 结构

## 相关文件

- `src/knowledge/knowledge_loader.py` - 已实现优雅降级
- `src/knowledge/knowledge_translator.py` - 已实现优雅降级
- `requirements.txt` - 包含 `pyyaml>=6.0`
- [INSTALL_DEPENDENCIES.md](../development/INSTALL_DEPENDENCIES.md) - 依赖安装指南

## 建议

虽然代码可以在没有 PyYAML 的情况下运行，但**强烈建议安装 PyYAML** 以获得完整功能。

