# 知识库目录结构说明

## 📂 完整目录树

```
docs/knowledge/
├── README.md                          # 知识库总说明
├── STRUCTURE.md                       # 本文件：目录结构说明
├── 术语统一规范.md                    # 术语统一标准
├── 知识库冲突检查报告.md              # 冲突检查报告
│
├── rules/                             # 规则知识库（硬编码层）
│   ├── 01_basic_rules/                # 基础规则
│   │   ├── 01_game_introduction.md    # 游戏介绍
│   │   ├── 02_quick_start.md          # 快速入门
│   │   ├── 04_card_types_guide.md     # 牌型指南
│   │   ├── 05_card_distribution.md    # 牌张分配
│   │   ├── 06_game_flow.md            # 游戏流程与进贡
│   │   ├── 07_upgrade_rules.md        # 升级规则
│   │   └── 08_basic_concepts.md       # 基本概念（术语）
│   │   # 入门策略/练习 → skills/01_foundation/03、04
│   │
│   └── 02_competition_rules/          # 实体赛规则
│       ├── 01_competition_format.md   # 竞赛形式
│       ├── 02_scoring.md              # 计分规则
│       └── 03_violation_handling.md   # 违规处理
│
├── strategy/                          # 策略知识库（内存加载层）
│   ├── README.md                      # 策略库说明
│   ├── 01_main_attack/                # 主攻策略
│   ├── 02_assist_attack/              # 助攻策略
│   ├── 03_common_strategy/            # 通用策略
│   ├── 04_card_grouping/              # 组牌策略
│   └── 05_fire_matching/              # 配火原则
│
└── skills/                            # 技巧知识库（按需查询层）
    ├── 01_foundation/                 # 基础技巧
    │   ├── 01_basic_principles.md
    │   ├── 02_strategy_overview.md
    │   ├── 03_basic_strategy.md     # 入门策略
    │   └── 04_practice_tips.md      # 练习建议
    ├── 02_main_attack/                # 主攻技巧
    ├── 03_assist_attack/              # 助攻技巧
    ├── 04_common_skills/              # 通用技巧
    │   ├── 01_pair_skills.md          # 对子技巧
    │   ├── 02_card_language.md        # 牌语
    │   ├── 03_card_interactions.md    # 牌型相生相克
    │   ├── 04_calculation_skills.md   # 算牌技巧
    │   ├── 05_memory_skills.md        # 记牌技巧
    │   ├── 06_red_heart_usage.md      # 红桃配运用
    │   ├── 07_two_trips_skills.md     # 钢板技巧
    │   ├── 08_straight_skills.md       # 顺子技巧
    │   ├── 09_three_pair_skills.md    # 三连对技巧
    │   ├── 10_three_with_two_skills.md # 三带二技巧
    │   ├── 11_trips_skills.md         # 三张技巧
    │   └── card_types/                # 牌型相关
    │
    ├── 05_psychology/                 # 心理知识
    ├── 06_advanced/                  # 高级技巧
    ├── 07_opening/                    # 开局技巧
    │   ├── 01_opening_interpretation.md # 首发解读
    │   └── 04_card_grouping_skills.md   # 组牌技巧
    │
    └── 08_endgame/                    # 残局技巧
```

## 🎯 三层架构说明

### 1. Rules (规则知识) - 硬编码层
- **实现位置**: `src/game/game_rules.py` 或类似文件
- **访问方式**: O(1) 直接调用
- **更新方式**: 代码修改
- **特点**: 最高准确性，整合多个源文档，消除重复和交叉

### 2. Strategy (策略知识) - 内存加载层
- **实现位置**: `src/knowledge/strategy_library.py` (待创建)
- **访问方式**: O(1) 内存访问
- **更新方式**: 重启程序或热更新
- **特点**: 程序启动时加载，快速访问

### 3. Skills (技巧知识) - 按需查询层
- **实现位置**: `src/knowledge/knowledge_retriever.py` (待创建)
- **访问方式**: 首次 O(n) 查询，后续 O(1) 缓存访问
- **更新方式**: 知识库文件更新，缓存失效
- **特点**: 按需查询，结果缓存

## 🔗 与决策流程的对应

根据**决策流程重构TODO**：

```
决策流程：
1. 关键规则检查（硬约束）→ 立即返回
   └─ 使用 Rules 知识库
   
2. 生成候选动作（Layer 1 + Layer 2）
   └─ Layer 1: YF (lalala) 策略
   └─ Layer 2: DecisionEngine
   
3. 知识增强评分（Layer 3）
   └─ 使用 Strategy 和 Skills 知识库
   └─ 对候选动作进行加分/减分
   
4. 选择最优动作
```

## 📋 文件命名规范

- 使用数字前缀排序：`01_`, `02_`, `03_`...
- 使用下划线分隔：`card_types.md`
- 使用小写字母和数字
- 中文文件名使用UTF-8编码

## 📝 文件格式标准

所有知识库文件应遵循 `docs/知识库格式化方案.md` 中的格式标准：

- YAML 元数据头部
- 统一术语（平台标准变量名）
- 知识关联（前置、后续、相关）
- 游戏阶段标注（opening/midgame/endgame）

详见：`docs/知识库格式化方案.md`

