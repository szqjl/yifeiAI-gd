# 知识库目录结构（优化版）

## 📊 优化依据

根据以下分析优化目录结构：
1. **策略对比分析.md** - lalala策略分析
2. **knowledge_enhanced_decision.py** - 实际代码中的策略实现
3. **hybrid_decision_engine_v4.py** - 决策流程架构
4. **知识库格式化方案.md** - 格式化标准

## 🎯 核心策略分类（基于代码实现）

从代码中提取的核心策略：

### 1. 队友保护策略 (Teammate Protection)
- 队友控场时的保护
- 队友快走完时的保护
- 队友出大牌时的保护
- 被动模式下的队友保护

### 2. 对手压制策略 (Opponent Suppression)
- 对手快走完时的压制
- 被动模式下的压制
- 主动模式下的压制
- 对手控场时的打断

### 3. 关键规则 (Critical Rules)
- 硬约束规则（立即返回）
- 队友保护规则
- 对手压制规则
- 进贡保护规则

### 4. 牌型策略 (Card Type Strategy)
- 炸弹使用策略
- 配火原则
- 组牌策略
- 牌型优先级

### 5. 阶段策略 (Phase Strategy)
- 开局策略
- 中局策略
- 残局策略

## 📂 优化后的目录结构

```
docs/knowledge/
├── README.md                          # 知识库总说明
├── STRUCTURE.md                       # 原目录结构说明
├── STRUCTURE_OPTIMIZED.md             # 本文件：优化版结构说明
├── 术语统一规范.md                    # 术语统一标准
├── 知识库冲突检查报告.md              # 冲突检查报告
│
├── rules/                             # 规则知识库（硬编码层）
│   ├── 01_basic_rules/                # 基础规则
│   │   ├── 01_card_types.md           # 牌型定义（需创建）
│   │   ├── 02_card_distribution.md    # 牌张分配
│   │   ├── 03_game_flow.md            # 游戏流程
│   │   ├── 04_upgrade_rules.md        # 升级规则
│   │   ├── 05_game_introduction.md    # 游戏介绍
│   │   ├── 06_basic_concepts.md       # 基本概念
│   │   ├── 07_quick_start.md          # 快速入门
│   │   └── 08_basic_strategy.md       # 基础策略
│   │
│   ├── 02_competition_rules/          # 比赛规则
│   │   ├── 01_competition_format.md   # 竞赛形式
│   │   ├── 02_scoring.md              # 计分规则
│   │   └── 03_violation_handling.md   # 违规处理
│   │
│   └── 03_advanced_rules/             # 高级规则
│       ├── 01_tribute_rules.md        # 进贡规则
│       └── 02_reporting_rules.md      # 报牌规则
│
├── strategy/                          # 策略知识库（内存加载层）
│   ├── README.md                      # 策略库说明
│   │
│   ├── 01_core_strategies/            # 核心策略（新增，基于代码实现）
│   │   ├── 01_teammate_protection.md  # 队友保护策略
│   │   │   ├── 队友控场保护
│   │   │   ├── 队友快走完保护
│   │   │   ├── 队友出大牌保护
│   │   │   └── 被动模式队友保护
│   │   │
│   │   ├── 02_opponent_suppression.md # 对手压制策略
│   │   │   ├── 对手快走完压制
│   │   │   ├── 被动模式压制
│   │   │   ├── 主动模式压制
│   │   │   └── 对手控场打断
│   │   │
│   │   ├── 03_critical_rules.md      # 关键规则（硬约束）
│   │   │   ├── 队友保护规则（立即返回）
│   │   │   ├── 对手压制规则（立即返回）
│   │   │   └── 进贡保护规则
│   │   │
│   │   └── 04_active_passive_mode.md # 主动/被动模式策略
│   │       ├── 主动模式策略
│   │       ├── 被动模式策略
│   │       └── 模式切换判断
│   │
│   ├── 02_role_strategies/            # 角色策略（重构）
│   │   ├── 01_main_attack/            # 主攻策略
│   │   │   ├── 头游争夺
│   │   │   ├── 牌路控制
│   │   │   └── 出牌时机
│   │   │
│   │   └── 02_assist_attack/          # 助攻策略
│   │       ├── 队友保护
│   │       ├── 传牌技巧
│   │       └── 角色转换
│   │
│   ├── 03_card_strategies/            # 牌型策略（重构）
│   │   ├── 01_bomb_strategy.md        # 炸弹策略
│   │   │   ├── 炸弹使用时机
│   │   │   ├── 炸弹优先级
│   │   │   └── 炸弹保留原则
│   │   │
│   │   ├── 02_fire_matching.md        # 配火原则
│   │   │   ├── 配火时机
│   │   │   ├── 配火优先级
│   │   │   └── 配火策略
│   │   │
│   │   └── 03_card_grouping.md       # 组牌策略
│   │       ├── 组牌原则
│   │       ├── 优先级排序
│   │       └── 优化策略
│   │
│   ├── 04_phase_strategies/          # 阶段策略（新增）
│   │   ├── 01_opening/                # 开局策略
│   │   │   ├── 01_opening_teammate_cooperation.md  # 开局队友配合（越级打牌问题）
│   │   │   └── ...
│   │   ├── 02_midgame/                # 中局策略
│   │   └── 03_endgame/                # 残局策略
│   │
│   └── 05_common_strategy/            # 通用策略
│       ├── 01_position_analysis.md   # 位置分析
│       ├── 02_card_value_evaluation.md # 牌值评估
│       └── 03_situation_judgment.md  # 局势判断
│
└── skills/                            # 技巧知识库（按需查询层）
    ├── 01_foundation/                 # 基础技巧
    ├── 02_main_attack/                # 主攻技巧
    ├── 03_assist_attack/              # 助攻技巧
    ├── 04_common_skills/              # 通用技巧
    │   ├── 01_pair_skills.md          # 对子技巧
    │   ├── 02_card_language.md         # 牌语
    │   ├── 03_card_interactions.md     # 牌型相生相克
    │   ├── 04_calculation_skills.md    # 算牌技巧
    │   ├── 05_memory_skills.md         # 记牌技巧
    │   ├── 06_red_heart_usage.md       # 红桃配运用
    │   ├── 07_two_trips_skills.md      # 钢板技巧
    │   ├── 08_straight_skills.md       # 顺子技巧
    │   ├── 09_three_pair_skills.md     # 三连对技巧
    │   ├── 10_three_with_two_skills.md # 三带二技巧
    │   └── 11_trips_skills.md          # 三张技巧
    │
    ├── 05_psychology/                 # 心理知识
    ├── 06_advanced/                   # 高级技巧
    ├── 07_opening/                    # 开局技巧
    └── 08_endgame/                    # 残局技巧
```

## 🔄 主要优化点

### 1. 新增 `strategy/01_core_strategies/` 目录
**原因**：代码中实现的核心策略（队友保护、对手压制）应该独立成目录

**内容**：
- `01_teammate_protection.md` - 队友保护策略（多种情况）
- `02_opponent_suppression.md` - 对手压制策略（多种情况）
- `03_critical_rules.md` - 关键规则（硬约束）
- `04_active_passive_mode.md` - 主动/被动模式策略

### 2. 重构 `strategy/02_role_strategies/` 目录
**原因**：将主攻/助攻策略从技巧库中分离，作为策略库的一部分

**内容**：
- `01_main_attack/` - 主攻策略（头游争夺、牌路控制）
- `02_assist_attack/` - 助攻策略（队友保护、传牌）

### 3. 重构 `strategy/03_card_strategies/` 目录
**原因**：牌型相关策略应该集中管理

**内容**：
- `01_bomb_strategy.md` - 炸弹策略
- `02_fire_matching.md` - 配火原则
- `03_card_grouping.md` - 组牌策略

### 4. 新增 `strategy/04_phase_strategies/` 目录
**原因**：不同游戏阶段的策略应该独立管理

**内容**：
- `01_opening/` - 开局策略
- `02_midgame/` - 中局策略
- `03_endgame/` - 残局策略

### 5. 优化 `strategy/05_common_strategy/` 目录
**原因**：通用策略应该包含位置分析、牌值评估等基础能力

## 📋 与代码实现的对应关系

| 代码实现 | 知识库位置 | 说明 |
|---------|-----------|------|
| `_apply_knowledge_rules()` 中的队友保护逻辑 | `strategy/01_core_strategies/01_teammate_protection.md` | 策略1：队友保护 |
| `_apply_knowledge_rules()` 中的对手压制逻辑 | `strategy/01_core_strategies/02_opponent_suppression.md` | 策略2：对手压制 |
| `_apply_critical_rules()` 中的关键规则 | `strategy/01_core_strategies/03_critical_rules.md` | 关键规则层 |
| `is_active` 判断逻辑 | `strategy/01_core_strategies/04_active_passive_mode.md` | 主动/被动模式 |

## 🎯 使用建议

1. **核心策略优先**：先完善 `strategy/01_core_strategies/` 中的策略
2. **代码对应**：每个策略文件应该对应代码中的具体实现
3. **格式统一**：遵循 `docs/知识库格式化方案.md` 的格式标准
4. **术语统一**：使用平台标准变量名（Single, Pair, Bomb 等）

