# 知识库目录结构

> **离线平台 / lalala 对局数据怎么读**（**平台局 ≠ 副**；`completed_games` 是局数；match_key/`total_rounds` 是副数）→ **[platform-data-interpretation.md](platform-data-interpretation.md)**（分析、批跑、迭代均适用）

## 📁 目录说明

本知识库按照**知识库格式化方案**和**决策流程架构**组织，分为三个层次：

### 1. Rules (规则知识) - 硬编码层
**位置**: `rules/`  
**实现方式**: 硬编码到 `GameRules` 类中  
**访问方式**: O(1) 直接调用  
**更新方式**: 代码修改

- `01_basic_rules/` - 基础规则（含 [06_game_flow.md](rules/01_basic_rules/06_game_flow.md) 进贡流程）
- `02_competition_rules/` - 比赛规则（实体赛：竞赛形式、计分、违规处理）

### 2. Strategy (策略知识) - 内存加载层
**位置**: `strategy/`  
**实现方式**: 程序启动时加载到内存  
**访问方式**: O(1) 内存访问  
**更新方式**: 重启程序或热更新

**优化后的结构**（基于策略分析和代码实现）：

- `01_core_strategies/` - **核心策略**（新增，基于代码实现）
  - `01_teammate_protection.md` - 队友保护策略
  - `02_opponent_suppression.md` - 对手压制策略
  - `03_critical_rules.md` - 关键规则（硬约束）
  - `04_active_passive_mode.md` - 主动/被动模式策略

- `02_role_strategies/` - **角色策略**
  - `01_main_attack/` - 主攻策略
  - `02_assist_attack/` - 助攻策略

- `03_card_strategies/` - **牌型策略**
  - `01_bomb_strategy.md` - 炸弹策略
  - `02_fire_matching.md` - 配火原则
  - `03_card_grouping.md` - 组牌策略

- `04_phase_strategies/` - **阶段策略**（新增）
  - `01_opening/` - 开局策略
  - `02_midgame/` - 中局策略
  - `03_endgame/` - 残局策略

- `05_common_strategy/` - **通用策略**
  - 位置分析、牌值评估、局势判断

### 3. Skills (技巧知识) - 按需查询层
**位置**: `skills/`（索引见 [skills/README.md](skills/README.md)）  
**实现方式**: 按需查询知识库文件，结果缓存  
**访问方式**: 首次 O(n) 查询，后续 O(1) 缓存访问  
**更新方式**: 知识库文件更新，缓存失效

- `01_foundation/` - 基础技巧（含 `03_basic_strategy`、`04_practice_tips`）
- `02_main_attack/` - 主攻技巧
- `03_assist_attack/` - 助攻技巧
- `04_common_skills/` - 通用技巧（配牌、出牌、记牌等）
- `05_psychology/` - 心理知识（心态、风格、配合默契）
- `06_advanced/` - 高级技巧
- `07_opening/` - 开局技巧
- `08_endgame/` - 残局技巧

## 🔗 与决策流程的对应关系

根据**决策流程重构TODO**，知识库在决策流程中的位置：

```
决策流程：
1. 关键规则检查（硬约束）→ 立即返回
   └─ 使用 Rules 知识库 + Strategy/01_core_strategies/03_critical_rules.md
2. 生成候选动作（Layer 1 + Layer 2）
   └─ Layer 1: YF (lalala) 策略
   └─ Layer 2: DecisionEngine
3. 知识增强评分（Layer 3）
   └─ 使用 Strategy/01_core_strategies/ 中的核心策略
   └─ 使用 Strategy/02_role_strategies/ 中的角色策略
   └─ 使用 Strategy/03_card_strategies/ 中的牌型策略
   └─ 使用 Strategy/04_phase_strategies/ 中的阶段策略
   └─ 使用 Skills 知识库进行技巧增强
4. 选择最优动作
```

## 📋 文件格式标准

所有知识库文件应遵循**知识库格式化方案**中的格式标准：

- YAML 元数据（title, type, category, tags, difficulty, priority, game_phase）
- 统一术语（使用平台标准变量名：Single, Pair, Bomb 等）
- 知识关联（前置知识、后续知识、相关知识）
- 代码对应关系（标注对应的代码位置）

详见：`docs/知识库格式化方案.md`

## 📊 优化说明

本次优化基于：
1. **策略对比分析.md** - lalala策略分析
2. **knowledge_enhanced_decision.py** - 实际代码中的策略实现
3. **hybrid_decision_engine_v4.py** - 决策流程架构

主要优化：
- 新增 `strategy/01_core_strategies/` 目录，对应代码中的核心策略实现
- 重构角色策略、牌型策略、阶段策略的目录结构
- 明确策略与代码的对应关系

详见：`docs/knowledge/STRUCTURE_OPTIMIZED.md`
