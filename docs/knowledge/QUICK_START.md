# 知识库功能快速启动指南

## ⚠️ 重要：环境依赖

知识库功能**需要** `pyyaml` 模块才能完整运行。

### 检查依赖

运行以下命令检查依赖状态：

```bash
python src/knowledge/dependency_check.py
```

### 安装依赖

如果缺少依赖，运行：

```bash
pip install -r requirements.txt
```

或仅安装yaml：

```bash
pip install pyyaml
```

## 功能可用性

### ✅ 完整功能（yaml已安装）

- ✅ 5条内置规则
- ✅ 29条动态规则（从YAML文件加载）
- ✅ 完整Markdown元数据解析
- ✅ 所有知识检索功能

### ⚠️ 受限功能（yaml未安装）

- ✅ 5条内置规则（可用）
- ❌ 29条动态规则（不可用）
- ⚠️ Markdown元数据解析受限

**影响**：AI决策质量会显著下降，因为缺少了29条重要的策略规则。

## 验证安装

安装后验证：

```bash
python -c "import yaml; print('PyYAML version:', yaml.__version__)"
```

应该输出类似：`PyYAML version: 6.0.3`

## 相关文档

- [INSTALL_DEPENDENCIES.md](../development/INSTALL_DEPENDENCIES.md) - 详细安装指南
- `YAML_DEPENDENCY_ANALYSIS.md` - 依赖影响分析
- `TEST_GUIDE.md` - 测试指南

