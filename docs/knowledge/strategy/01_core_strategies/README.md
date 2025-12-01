# 核心策略库 (Core Strategies)

## 📖 说明

核心策略库包含代码中实际实现的核心策略逻辑，这些策略在 `knowledge_enhanced_decision.py` 的 `_apply_knowledge_rules()` 方法中实现。

## 🎯 策略分类

### 01_teammate_protection.md - 队友保护策略
**代码位置**: `knowledge_enhanced_decision.py` 策略1

**核心逻辑**：
- 队友控场时的保护（greater_pos == teammate_pos）
- 队友快走完时的保护（teammate_cards <= 2/3/5）
- 队友出大牌时的保护（card_value >= 14）
- 被动模式下的队友保护

**评分规则**：
- PASS: +150 (队友1-2张) / +120 (队友3-5张，大牌) / +100 (队友3-5张，默认)
- 出牌: -80 (队友1-2张) / -60 (队友3-5张，大牌) / -50 (队友3-5张，默认)

### 02_opponent_suppression.md - 对手压制策略
**代码位置**: `knowledge_enhanced_decision.py` 策略2

**核心逻辑**：
- 对手快走完时的压制（min_opponent_cards <= 3/4/8）
- 被动模式下的压制（检查是否能压制当前动作）
- 主动模式下的压制
- 对手控场时的打断

**评分规则**：
- 能压制: +150 (对手1-3张) / +120 (对手4-5张)
- 不能压制但出牌: +100 (对手1-3张) / +80 (对手4-5张)
- PASS: -40 (对手快走完时)

### 03_critical_rules.md - 关键规则（硬约束）
**代码位置**: `hybrid_decision_engine_v4.py` `_apply_critical_rules()`

**核心逻辑**：
- 队友保护规则（立即返回PASS）
- 对手压制规则（立即返回压制动作）
- 进贡保护规则

**特点**：
- 硬约束，触发后立即返回，不经过后续层
- 优先级最高

### 04_active_passive_mode.md - 主动/被动模式策略
**代码位置**: `knowledge_enhanced_decision.py` `is_active` 判断

**核心逻辑**：
- 主动模式（type == "active"）：鼓励出牌
- 被动模式（type != "active"）：根据情况判断
- 模式切换判断

## 📋 文件格式要求

每个策略文件应包含：
- YAML 元数据（title, type, category, tags, priority）
- 策略描述
- 适用条件
- 评分规则
- 代码对应关系
- 实战案例

详见：`docs/知识库格式化方案.md`

