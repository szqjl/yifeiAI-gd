# 优先级排序问题修复说明

## 问题描述

在测试 `KnowledgeEnhancedDecisionEngine` 时遇到错误：
```
'<' not supported between instances of 'dict' and 'dict'
```

## 问题原因

1. **优先级字段类型不一致**：某些规则的 `priority` 字段可能是字符串、字典或其他非数字类型
2. **条件评估中的类型比较**：在 `evaluate_condition` 方法中，当比较操作涉及字典或None值时出错
3. **函数评估中的类型问题**：在 `_evaluate_function` 方法中，`min`/`max`/`sum` 函数处理了不可比较的类型

## 解决方案

### 1. 创建安全的优先级获取函数

在 `knowledge_translator.py` 中添加了 `get_priority_value()` 函数：

```python
def get_priority_value(rule: dict) -> float:
    """安全地获取规则的优先级值"""
    priority = rule.get("priority", 0)
    if priority is None:
        return 0.0
    if isinstance(priority, (int, float)):
        return float(priority)
    if isinstance(priority, str):
        try:
            if priority.isdigit() or (priority.startswith('-') and priority[1:].isdigit()):
                return float(int(priority))
            return float(priority)
        except (ValueError, AttributeError):
            return 0.0
    return 0.0
```

### 2. 修复所有排序位置

将所有使用 `lambda x: x.get("priority", 0)` 的排序改为使用 `get_priority_value`：

- `_load_rules_from_files()` 方法
- `translate_rules()` 方法
- `add_rule()` 方法

### 3. 修复条件评估中的类型问题

在 `evaluate_condition()` 方法中：
- 添加 None 值检查
- 添加字典/列表类型检查
- 使用 try-except 处理类型不匹配

### 4. 修复函数评估中的类型问题

在 `_evaluate_function()` 方法中：
- `min`/`max` 函数：过滤掉不可比较的值
- `sum` 函数：只对数字求和

## 测试结果

修复后，测试6现在可以正常工作：

```
[测试6] 规则转化器集成测试
------------------------------------------------------------
   ✅ 规则转化器工作正常
   适用规则数: 5
   前3个规则:
     1. 队友保护-即将获胜 (priority: 10)
     2. 队友保护-即将获胜 (priority: 10)
     3. 复杂队友保护规则 (priority: 9)
```

## 相关文件

- `src/knowledge/knowledge_translator.py` - 规则转化器（已修复）
- `test_knowledge_enhanced_decision.py` - 测试脚本

## 注意事项

1. **优先级字段类型**：确保YAML规则文件中的 `priority` 字段是数字类型
2. **条件表达式**：确保条件表达式中的字段值和比较值都是可比较的类型
3. **函数参数**：使用函数调用时，确保参数解析后是可比较的类型

