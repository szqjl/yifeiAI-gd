# 依赖安装指南

## 问题

如果遇到 `No module named 'yaml'` 错误，说明缺少 PyYAML 依赖。

## 解决方案

### 方法1：使用 requirements.txt 安装（推荐）

```bash
pip install -r requirements.txt
```

这会安装所有依赖，包括：
- `pyyaml>=6.0` - YAML解析库
- `psutil>=5.9.0` - 进程监控
- `pytest>=7.0.0` - 单元测试框架
- 其他依赖

### 方法2：仅安装 PyYAML

```bash
pip install pyyaml
```

或者指定版本：

```bash
pip install pyyaml>=6.0
```

### 方法3：使用 conda（如果使用 conda 环境）

```bash
conda install pyyaml
```

## 验证安装

安装完成后，可以验证：

```bash
python -c "import yaml; print('PyYAML version:', yaml.__version__)"
```

## ✅ 新方案：YAML已集成到yf_v4

**好消息**：yf_v4现在**不需要yaml模块**即可使用所有知识库功能！

### 实现方式

1. **YAML转Python代码**：所有YAML规则文件已转换为Python代码
2. **自动生成**：`src/knowledge/knowledge_rules.py` 包含39条规则
3. **智能加载**：优先从Python模块加载，无需yaml依赖

### 优势

- ✅ **完全独立**：无需安装pyyaml
- ✅ **性能更好**：直接导入，无需解析
- ✅ **向后兼容**：如果Python模块不存在，自动回退到YAML加载

### 更新规则

当YAML规则文件更新后，运行：

```bash
python src/knowledge/yaml_to_python_converter.py
```

## 优雅降级（保留，作为备选）

代码仍然实现了优雅降级机制：

1. **KnowledgeLoader**: 如果 yaml 模块不可用，会使用简单的键值对解析
2. **KnowledgeTranslator**: 
   - **优先**：从Python模块加载（无需yaml）
   - **回退**：如果Python模块不存在，从YAML文件加载（需要yaml）

### ⚠️ 重要提示（仅当Python模块不存在时）

**如果yaml模块不可用且Python模块不存在，知识库功能会受限**：

- ✅ **可用**：5条内置规则（核心策略）
- ❌ **不可用**：39条动态规则（从YAML文件加载）
- ⚠️ **受限**：Markdown文件的复杂元数据解析

**解决方案**：运行转换器生成Python模块，或安装PyYAML。

## 依赖检查工具

运行以下命令检查依赖状态：

```bash
python -m src.knowledge.dependency_check
```

或直接运行：

```bash
python src/knowledge/dependency_check.py
```

## 相关文件

- `requirements.txt` - 项目依赖列表（已包含pyyaml>=6.0）
- `src/knowledge/knowledge_loader.py` - 知识加载器（已支持优雅降级）
- `src/knowledge/knowledge_translator.py` - 规则转化器（已支持优雅降级）
- `src/knowledge/dependency_check.py` - 依赖检查工具（新增）
- `docs/knowledge/YAML_DEPENDENCY_ANALYSIS.md` - 详细影响分析（新增）

