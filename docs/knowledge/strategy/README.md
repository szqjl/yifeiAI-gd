# 策略知识库 (Strategy Library)

## 📖 说明

策略知识库对应**决策流程架构**中的"策略库 (Strategy Library)"，实现方式为**内存加载层**。

- **加载时机**: 程序启动时加载到内存
- **访问方式**: O(1) 内存访问
- **更新方式**: 重启程序或热更新

## 📁 目录结构（优化版）

### 01_core_strategies/ - 核心策略 ⭐
**基于代码实现的核心策略**，对应 `knowledge_enhanced_decision.py` 中的策略逻辑。

- `01_teammate_protection.md` - 队友保护策略
  - 代码位置: `_apply_knowledge_rules()` 策略1
  - 包含：队友控场保护、队友快走完保护、队友出大牌保护等
  
- `02_opponent_suppression.md` - 对手压制策略
  - 代码位置: `_apply_knowledge_rules()` 策略2
  - 包含：对手快走完压制、被动模式压制、主动模式压制等
  
- `03_critical_rules.md` - 关键规则（硬约束）
  - 代码位置: `hybrid_decision_engine_v4.py` `_apply_critical_rules()`
  - 特点：硬约束，触发后立即返回，不经过后续层
  
- `04_active_passive_mode.md` - 主动/被动模式策略
  - 代码位置: `_apply_knowledge_rules()` `is_active` 判断
  - 包含：主动模式策略、被动模式策略、模式切换判断

### 02_role_strategies/ - 角色策略
根据角色（主攻/助攻）的不同策略。

- `01_main_attack/` - 主攻策略
  - 头游争夺
  - 牌路控制
  - 出牌时机

- `02_assist_attack/` - 助攻策略
  - 队友保护
  - 传牌技巧
  - 角色转换

### 03_card_strategies/ - 牌型策略
牌型相关的策略和原则。

- `01_bomb_strategy.md` - 炸弹策略
  - 炸弹使用时机
  - 炸弹优先级
  - 炸弹保留原则

- `02_fire_matching.md` - 配火原则
  - 配火时机
  - 配火优先级
  - 配火策略

- `03_card_grouping.md` - 组牌策略
  - 组牌原则
  - 优先级排序
  - 优化策略

### 04_phase_strategies/ - 阶段策略
不同游戏阶段的策略。

- `01_opening/` - 开局策略
  - 起手牌分析
  - 首攻选择
  - 初期布局

- `02_midgame/` - 中局策略
  - 中局控制
  - 牌路调整
  - 局势判断

- `03_endgame/` - 残局策略
  - 残局冲刺
  - 听牌技巧
  - 防守策略

### 05_common_strategy/ - 通用策略
适用于所有角色的通用策略。

- `01_position_analysis.md` - 位置分析
  - 位置关系计算
  - 队友/对手识别
  - 位置优势分析

- `02_card_value_evaluation.md` - 牌值评估
  - 牌值转换
  - 牌力评估
  - 牌值比较

- `03_situation_judgment.md` - 局势判断
  - 局势分析
  - 风险评估
  - 决策依据

## 🔗 与决策流程的关系

策略知识库在 **Layer 3 (KnowledgeEnhancedDecision)** 中使用，对候选动作进行评分增强。

**核心策略**（`01_core_strategies/`）直接对应代码实现，是知识库的核心部分。

## 📋 文件格式要求

所有策略文件应遵循 `docs/知识库格式化方案.md` 中的格式标准：

- YAML 元数据（title, type, category, tags, priority, game_phase）
- 策略描述
- 适用条件
- 评分规则
- 代码对应关系（标注对应的代码位置）
- 实战案例

## 🎯 使用优先级

1. **核心策略优先**：先完善 `01_core_strategies/` 中的策略
2. **代码对应**：每个策略文件应该对应代码中的具体实现
3. **格式统一**：遵循格式化方案的格式标准
4. **术语统一**：使用平台标准变量名（Single, Pair, Bomb 等）
