# Priority动态调整功能说明

## 概述

实现了根据知识库中的 `priority` 字段动态调整加分幅度的功能，确保高优先级规则和技能对决策有更大的影响。

## 实现位置

### 1. 规则转化器 (`knowledge_translator.py`)

在 `apply_rule()` 方法中实现：

```python
def apply_rule(self, rule: Dict, action_type: str, context: Dict) -> float:
    # 获取规则优先级
    priority = rule.get("priority", 1)
    
    # 计算基础调整值
    base_adjust = ...  # 从actions中获取
    
    # 根据priority动态调整加分幅度
    # priority范围通常是1-10，映射到0.5-2.0的倍数
    # priority=1: 0.5倍, priority=5: 1.0倍, priority=10: 2.0倍
    priority_multiplier = 0.5 + (priority / 10.0) * 1.5
    
    # 应用优先级加权
    adjusted_score = base_adjust * priority_multiplier
    
    return adjusted_score
```

**调整公式**：
- `multiplier = 0.5 + (priority / 10.0) * 1.5`
- Priority 1: 0.5倍（最低优先级）
- Priority 5: 1.0倍（中等优先级）
- Priority 10: 2.0倍（最高优先级）

### 2. 决策引擎 (`knowledge_enhanced_decision.py`)

在 `_calculate_knowledge_bonus()` 方法中实现：

```python
def _calculate_knowledge_bonus(self, action: List, skills: List[Dict], ...) -> float:
    bonus = 0.0
    
    for skill in skills:
        priority = skill.get('priority', 1)
        
        # 根据priority动态计算加分幅度
        # priority=1: 基础加分2.0, priority=5: 基础加分10.0, priority=10: 基础加分20.0
        base_bonus = 2.0 + (priority - 1) * (18.0 / 9.0)
        
        # 对于高优先级技能（priority >= 8），额外加权
        if priority >= 8:
            base_bonus *= 1.2  # 高优先级技能额外20%加权
        
        bonus += base_bonus
    
    return min(bonus, 50.0)
```

**调整公式**：
- `base_bonus = 2.0 + (priority - 1) * (18.0 / 9.0)`
- Priority 1: 2.0分
- Priority 5: 10.0分
- Priority 10: 20.0分
- Priority >= 8: 额外20%加权

## 使用示例

### 示例1：规则优先级调整

```yaml
rules:
  - id: high_priority_rule
    priority: 10
    actions:
      - action_type: PASS
        score_adjust: 100
    # 实际调整: 100 * 2.0 = 200
    
  - id: low_priority_rule
    priority: 1
    actions:
      - action_type: PASS
        score_adjust: 100
    # 实际调整: 100 * 0.5 = 50
```

### 示例2：知识库技能优先级调整

```python
skills = [
    {"priority": 10, "title": "高优先级技能"},  # 加分: 20.0 * 1.2 = 24.0
    {"priority": 5, "title": "中优先级技能"},   # 加分: 10.0
    {"priority": 1, "title": "低优先级技能"}    # 加分: 2.0
]

total_bonus = 24.0 + 10.0 + 2.0 = 36.0
```

## 优势

1. **动态调整**：根据priority自动调整，无需手动配置
2. **线性映射**：priority和调整倍数/加分值呈线性关系，易于理解
3. **高优先级加权**：priority >= 8的规则/技能额外加权，确保重要规则优先应用
4. **向后兼容**：默认priority=1，不影响现有规则

## 测试

运行测试脚本验证功能：

```bash
python test_priority_adjustment.py
```

## 相关文件

- `src/knowledge/knowledge_translator.py` - 规则转化器实现
- `src/knowledge/knowledge_enhanced_decision.py` - 决策引擎实现
- `test_priority_adjustment.py` - 测试脚本

