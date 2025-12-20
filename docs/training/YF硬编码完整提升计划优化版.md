# YF硬编码完整提升计划

## 📋 计划概述

**制定时间**: 2025-12-17  
**最后更新**: 2025-12-17（调整策略方向）  
**目标**: 基于lalala决策机制分析，制定YF硬编码规则引擎的完整提升方案  
**原则**: 学习lalala优点但不抄袭，在lalala基础上实现创新和提升  
**预期成果**: 构建一套清晰、可操作、可扩充的硬编码决策系统

**重要决策**: 
- ⚠️ **机器学习测试结果**: 经过3周测试，机器学习方案未达到预期效果
- ✅ **策略调整**: 回归硬编码路线，专注硬编码规则引擎优化
- 🎯 **核心方向**: 通过精细化硬编码规则，实现AI决策质量的提升

---

## 🎯 核心设计理念

### 1. 架构设计原则

**lalala的启发**:
- ✅ 简单直接的架构：`rule_parse() → passive()/active() → 牌型专门方法`
- ✅ 清晰的阶段分离
- ✅ 每种牌型有专门处理方法

**YF的提升方向**:
- 🚀 **分层架构 + 模块化设计**: 在保持简单的同时，增加可扩展性
- 🚀 **策略模式 + 工厂模式**: 便于添加新策略和牌型处理
- 🚀 **配置化参数**: 关键阈值可配置，便于调优
- 🚀 **决策树 + 规则引擎**: 更灵活的规则组合

**YF新架构**:
```
RuleBasedDecisionEngine (主入口)
  ├── StageRouter (阶段路由) ⭐ 优化：阶段细分路由
  │   ├── 开局阶段处理器 (剩余牌数 > 20)
  │   │   ├── OpeningActiveHandler (开局主动出牌)
  │   │   └── OpeningPassiveHandler (开局被动出牌)
  │   ├── 中局前期处理器 (剩余牌数 15-20)
  │   │   ├── MidEarlyActiveHandler (中局前期主动出牌)
  │   │   └── MidEarlyPassiveHandler (中局前期被动出牌)
  │   ├── 中局后期处理器 (剩余牌数 10-15)
  │   │   ├── MidLateActiveHandler (中局后期主动出牌)
  │   │   └── MidLatePassiveHandler (中局后期被动出牌)
  │   ├── 残局前期处理器 (剩余牌数 5-10)
  │   │   ├── EndgameEarlyActiveHandler (残局前期主动出牌)
  │   │   └── EndgameEarlyPassiveHandler (残局前期被动出牌)
  │   ├── 残局后期处理器 (剩余牌数 ≤ 5)
  │   │   ├── EndgameLateActiveHandler (残局后期主动出牌)
  │   │   └── EndgameLatePassiveHandler (残局后期被动出牌)
  │   └── SpecialStageHandler (进贡/还贡)
  │
  ├── CardTypeHandlers (牌型处理器工厂)
  │   ├── SingleHandler
  │   ├── PairHandler
  │   ├── TripsHandler
  │   └── ... (8种牌型)
  │
  ├── StrategyEngine (策略引擎) ⭐ 新增
  │   ├── TeammateProtectionStrategy (队友保护)
  │   ├── HandStructureAnalyzer (手牌结构分析)
  │   └── PrioritySystem (优先级系统)
  │   ⚠️ 注意：残局策略（RushStrategy, DefendStrategy等）已整合到残局处理器内部
  │
  └── EvaluationSystem (评估系统)
      ├── CardValueSystem (牌值系统)
      ├── PowerEvaluator (牌力评估)
      └── ContextEvaluator (上下文评估)
```

### 2. 核心优势对比

| 方面 | lalala | YF当前 | YF提升后 |
|------|--------|--------|----------|
| **架构** | 简单直接 | 复杂多层 | 分层模块化 ⭐ |
| **阶段细分** | 无（统一处理） | 无 | 5阶段细分路由 ⭐⭐⭐ |
| **决策速度** | 中等 | 较慢 | 快速（减少5-10ms）⭐⭐⭐ |
| **可扩展性** | 低（硬编码） | 中（部分模块化） | 高（策略模式）⭐ |
| **残局处理** | 有（简单） | 无 | 有（增强版）⭐ |
| **手牌分析** | 深入 | 基础 | 深入+智能 ⭐ |
| **队友保护** | 清晰 | 不够明确 | 多策略组合 ⭐ |
| **优先级系统** | 固定 | 多因素评估 | 动态优先级 ⭐ |
| **参数调优** | 硬编码 | 部分配置 | 完全配置化 ⭐ |
| **决策可解释性** | 中 | 低 | 高（决策树）⭐ |

---

## 📊 提升路径规划

### 阶段一：架构重构与基础建设（2周）

#### 1.1 决策入口重构

**目标**: 建立清晰的阶段分离和路由机制

**实施步骤**:

1. **创建StageRouter（阶段路由器）** ⭐ 优化：阶段细分路由
   
   **优化说明**: 在路由层直接进行阶段细分，每个阶段有专门的处理器，优势：
   - 🚀 **决策路径更短**: 直接定位到专门处理器，减少判断层级（性能提升5-10ms）
   - 🚀 **策略更精准**: 每个阶段完全独立优化，无通用逻辑干扰
   - 🚀 **优化空间更大**: 可以针对每个阶段做深度优化和A/B测试
   - 🚀 **代码更专注**: 每个处理器只关注一个阶段，逻辑更清晰
   
   ```python
   class StageRouter:
       """阶段路由器（优化：阶段细分路由，提升决策质量和速度）"""
       
       def __init__(self, config: Dict):
           self.config = config
           # 初始化各阶段处理器（优化：直接路由到专门处理器）
           self.handlers = {
               # 开局阶段（剩余牌数 > 20）
               'opening_active': OpeningActiveHandler(config),
               'opening_passive': OpeningPassiveHandler(config),
               # 中局前期（剩余牌数 15-20）
               'mid_early_active': MidEarlyActiveHandler(config),
               'mid_early_passive': MidEarlyPassiveHandler(config),
               # 中局后期（剩余牌数 10-15）
               'mid_late_active': MidLateActiveHandler(config),
               'mid_late_passive': MidLatePassiveHandler(config),
               # 残局前期（剩余牌数 5-10）
               'endgame_early_active': EndgameEarlyActiveHandler(config),
               'endgame_early_passive': EndgameEarlyPassiveHandler(config),
               # 残局后期（剩余牌数 ≤ 5）
               'endgame_late_active': EndgameLateActiveHandler(config),
               'endgame_late_passive': EndgameLatePassiveHandler(config),
           }
           # 特殊阶段处理器
           self.tribute_handler = TributeHandler(config)
           self.back_handler = BackHandler(config)
       
       def route(self, message: Dict) -> int:
           """路由到对应阶段处理器（优化：直接路由，无额外判断）"""
           stage = message.get("stage", "play")
           my_remain = len(message.get("handCards", []))
           
           # 特殊阶段处理（进贡/还贡）
           if stage == "tribute":
               return self.tribute_handler.handle(message)
           elif stage == "back":
               return self.back_handler.handle(message)
           
           # 打牌阶段：根据剩余牌数和出牌类型直接路由
           if stage == "play":
               # 判断游戏阶段（优化：在路由层直接判断）
               game_phase = self._get_game_phase(my_remain)
               
               # 判断主动/被动出牌
               is_passive = self._is_passive_play(message)
               
               # 直接路由到专门处理器（优化：一步到位，无额外判断）
               handler_key = f"{game_phase}_{'passive' if is_passive else 'active'}"
               handler = self.handlers.get(handler_key)
               
               if handler:
                   return handler.handle(message)
           
           return 0
       
       def _get_game_phase(self, my_remain: int) -> str:
           """获取游戏阶段（优化：细分为5个阶段）"""
           if my_remain > 20:
               return "opening"        # 开局
           elif my_remain > 15:
               return "mid_early"      # 中局前期
           elif my_remain > 10:
               return "mid_late"       # 中局后期
           elif my_remain > 5:
               return "endgame_early"  # 残局前期
           else:
               return "endgame_late"   # 残局后期
       
       def _is_passive_play(self, message: Dict) -> bool:
           """判断是否为被动出牌"""
           cur_action = message.get("curAction")
           return cur_action is not None and len(cur_action) > 0
   ```

2. **创建各阶段处理器（优化：每个阶段独立处理器）**
   
   **优化说明**: 每个阶段有专门的处理器，可以完全针对该阶段优化策略，无需考虑其他阶段的逻辑。
   
   **基类定义**:
   ```python
   class BasePhaseHandler(ABC):
       """阶段处理器基类（优化：统一接口，减少代码重复）"""
       
       def __init__(self, config: Dict):
           self.config = config
           self.hand_analyzer = HandStructureAnalyzer()
           self.priority_system = PrioritySystem(config)
       
       @abstractmethod
       def handle(self, message: Dict) -> int:
           """处理出牌（子类实现）"""
           pass
       
       def _check_one_hand_complete(self, action_list: List, handcards: List) -> Optional[int]:
           """检查一手出完（所有阶段都可能需要，但实现可能不同）"""
           for i, action in enumerate(action_list):
               if len(action[2]) == len(handcards):
                   return i
           return None
   ```
   
   **开局阶段处理器示例**:
   ```python
   class OpeningActiveHandler(BasePhaseHandler):
       """开局主动出牌处理器（优化：专注于建立牌型结构）"""
       
       def handle(self, message: Dict) -> int:
           """开局策略：专注于建立牌型结构，不考虑快速出完"""
           action_list = message.get("actionList", [])
           handcards = message.get("handCards", [])
           
           # 开局不需要检查"一手出完"（优化：避免不必要的检查）
           # 开局策略：建立牌型结构
           return self._build_structure_strategy(message, action_list)
       
       def _build_structure_strategy(self, message: Dict, action_list: List) -> int:
           """建立牌型结构策略（开局专用）"""
           # 分析手牌结构
           hand_structure = self.hand_analyzer.analyze(
               message.get("handCards", []),
               message.get("curRank", "2")
           )
           
           # 开局优先级：小单张 → 三连对/钢板 → 顺子 → 三带二 → 三张 → 对子
           priority_order = ['small_single', 'threepair', 'straight', 
                           'three_with_two', 'trips', 'pair']
           
           for card_type in priority_order:
               candidates = [a for a in action_list if a[0] == card_type]
               if candidates:
                   return self._select_best_from_candidates(candidates, hand_structure)
           
           return 0
   ```
   
   **残局后期处理器示例**:
   ```python
   class EndgameLateActiveHandler(BasePhaseHandler):
       """残局后期主动出牌处理器（优化：专注于快速出完）"""
       
       def handle(self, message: Dict) -> int:
           """残局后期策略：快速出完，不考虑建立结构"""
           action_list = message.get("actionList", [])
           handcards = message.get("handCards", [])
           
           # 优先级1: 一手出完（残局最重要）
           one_hand_idx = self._check_one_hand_complete(action_list, handcards)
           if one_hand_idx is not None:
               return one_hand_idx
           
           # 优先级2: 出最大牌型（快速减少牌数）
           return self._select_largest_action(action_list)
       
       def _select_largest_action(self, action_list: List) -> int:
           """选择最大牌型（残局专用）"""
           largest_idx = 0
           largest_size = 0
           
           for i, action in enumerate(action_list):
               action_size = len(action[2])
               if action_size > largest_size:
                   largest_size = action_size
                   largest_idx = i
           
           return largest_idx
   ```
   
   **其他阶段处理器**:
   - `MidEarlyActiveHandler` / `MidEarlyPassiveHandler`: 中局前期处理器
   - `MidLateActiveHandler` / `MidLatePassiveHandler`: 中局后期处理器
   - `EndgameEarlyActiveHandler` / `EndgameEarlyPassiveHandler`: 残局前期处理器
   - `OpeningPassiveHandler` / `EndgameLatePassiveHandler`: 被动出牌处理器

3. **阶段处理器设计原则**
   
   **优化优势总结**:
   - ✅ **决策速度更快**: 减少5-10ms判断时间，直接定位到专门处理器
   - ✅ **策略更精准**: 每个阶段完全独立优化，无通用逻辑干扰
   - ✅ **代码更清晰**: 每个处理器只关注一个阶段，逻辑简单明了
   - ✅ **优化空间大**: 可以针对每个阶段做深度优化和A/B测试
   - ✅ **维护成本低**: 通过基类减少代码重复，保持架构清晰
   
   **各阶段策略重点**:
   - **开局** (>20): 建立牌型结构，观察对手，不急于出完
   - **中局前期** (15-20): 控制节奏，配合队友，开始考虑出完
   - **中局后期** (10-15): 积极出牌，配合队友，准备冲刺
   - **残局前期** (5-10): 快速出牌，保护队友，争取先手
   - **残局后期** (≤5): 全力冲刺，一手出完优先，快速结束

**验收标准**:
- [ ] StageRouter能正确识别所有5个游戏阶段
- [ ] 阶段路由准确率>99%（直接路由，无判断错误）
- [ ] 主动/被动出牌路由正确
- [ ] 各阶段处理器独立工作，策略互不干扰
- [ ] 决策时间<200ms（平均），<500ms（最大）
- [ ] 代码结构清晰，通过基类减少重复代码

---

#### 1.2 牌型处理器工厂重构

**目标**: 为每种牌型创建专门的处理方法，支持策略注入

**实施步骤**:

1. **定义CardTypeHandler接口**
   ```python
   class CardTypeHandler(ABC):
       """牌型处理器基类（提升：统一接口，支持策略注入）"""
       
       @abstractmethod
       def handle_passive(self, message: Dict, context: Dict) -> int:
           """处理被动出牌"""
           pass
       
       def handle_active(self, message: Dict, context: Dict) -> int:
           """处理主动出牌（可选）"""
           pass
       
       def analyze_structure(self, handcards: List, rank: str) -> Dict:
           """分析手牌结构（提升：统一的手牌分析接口）"""
           pass
   ```

2. **实现SingleHandler（单张处理器）**
   ```python
   class SingleHandler(CardTypeHandler):
       """单张处理器（学习lalala，但增强）"""
       
       def __init__(self, config: Dict):
           self.config = config
           self.teammate_protection = TeammateProtectionStrategy(config)
           self.hand_analyzer = HandStructureAnalyzer()
           self.priority_system = PrioritySystem()
       
       def handle_passive(self, message: Dict, context: Dict) -> int:
           """处理单张被动出牌（提升：更完善的逻辑）"""
           # 1. 手牌结构分析（lalala有，YF增强：更详细）
           hand_structure = self.hand_analyzer.analyze(
               message.get("handCards", []),
               message.get("curRank", "2")
           )
           
           # 2. 队友保护判断（lalala有，YF增强：多策略）
           if self.teammate_protection.should_protect(message, context):
               return 0  # PASS
           
           # 3. 优先级选择（lalala有，YF提升：动态优先级）
           candidates = self._get_candidates(message)
           return self.priority_system.select(
               candidates, 
               hand_structure, 
               context
           )
   ```

3. **实现其他牌型处理器**
   - PairHandler（对子）
   - TripsHandler（三张）
   - ThreeWithTwoHandler（三带二）
   - ThreePairHandler（三连对）
   - StraightHandler（顺子）
   - TwoTripsHandler（钢板）
   - BombHandler（炸弹）

**验收标准**:
- [ ] 所有8种牌型都有专门处理器
- [ ] 处理器接口统一，易于扩展
- [ ] 支持策略注入和配置化

---

#### 1.3 手牌结构分析器增强

**目标**: 实现比lalala更深入的手牌结构分析

**实施步骤**:

1. **创建HandStructureAnalyzer**
   ```python
   class HandStructureAnalyzer:
       """手牌结构分析器（提升：比lalala更深入）"""
       
       def analyze(self, handcards: List, rank: str) -> Dict:
           """分析手牌结构（提升：返回更详细的信息）"""
           structure = {
               # 基础信息（lalala有）
               'single_member': [],      # 单张成员
               'pair_member': [],        # 对子成员
               'trip_member': [],        # 三张成员
               'bomb_member': [],        # 炸弹成员
               'straight_member': [],    # 顺子成员
               
               # 增强信息（YF新增）
               'card_value_distribution': {},  # 牌值分布
               'combo_potential': {},          # 组合潜力
               'destructible_combos': [],      # 可破坏的组合
               'protected_combos': [],         # 受保护的组合
               'flexibility_score': 0.0,       # 灵活性评分
               'threat_level': 0.0,           # 威胁等级
           }
           
           # 分析各种牌型成员
           sorted_cards = self._combine_handcards(handcards, rank)
           structure['single_member'] = sorted_cards.get("Single", [])
           structure['pair_member'] = self._flatten(sorted_cards.get("Pair", []))
           structure['trip_member'] = self._flatten(sorted_cards.get("Trips", []))
           structure['bomb_member'] = self._flatten(sorted_cards.get("Bomb", []))
           structure['straight_member'] = self._extract_straight_members(sorted_cards)
           
           # 增强分析（YF新增）
           structure['card_value_distribution'] = self._analyze_value_distribution(handcards, rank)
           structure['combo_potential'] = self._analyze_combo_potential(sorted_cards)
           structure['destructible_combos'] = self._find_destructible_combos(sorted_cards)
           structure['protected_combos'] = self._find_protected_combos(sorted_cards)
           structure['flexibility_score'] = self._calculate_flexibility(structure)
           structure['threat_level'] = self._calculate_threat_level(structure)
           
           return structure
       
       def _analyze_combo_potential(self, sorted_cards: Dict) -> Dict:
           """分析组合潜力（YF新增：预测未来可能的组合）"""
           potential = {
               'can_form_pair': [],      # 可以形成对子的单张
               'can_form_trip': [],      # 可以形成三张的对子
               'can_form_straight': [],  # 可以形成顺子的牌
           }
           # 实现组合潜力分析逻辑
           return potential
   ```

**验收标准**:
- [ ] 手牌结构分析返回信息比lalala更详细
- [ ] 包含组合潜力、灵活性等高级指标
- [ ] 分析速度<50ms

---

### 阶段二：核心策略实现（2周）

#### 2.1 残局策略系统（残局处理器内部策略）

**目标**: 为残局处理器提供多种残局策略

**优化说明**: 
- ⚠️ **架构调整**: 在优化版中，不再使用统一的`EndgameHandler`
- ✅ **新架构**: 残局已细分为`EndgameEarlyHandler`和`EndgameLateHandler`
- ✅ **策略整合**: 残局策略（RushStrategy, DefendStrategy等）作为残局处理器的内部策略使用

**lalala的策略**:
- 当剩余牌数≤10时，调用`one_hand()`专门处理
- 简单的残局判断

**YF的提升**:
- 🚀 **多维度残局判断**: 不仅看自己，还看全局
- 🚀 **残局策略库**: 多种残局场景的策略（整合到残局处理器内部）
- 🚀 **动态策略选择**: 根据残局类型选择最佳策略

**实施步骤**:

1. **定义残局策略接口**
   ```python
   class EndgameStrategy(ABC):
       """残局策略基类（供残局处理器内部使用）"""
       
       @abstractmethod
       def execute(self, message: Dict) -> int:
           """执行残局策略"""
           pass
   ```

2. **实现残局策略类（供残局处理器使用）**
   ```python
   class RushStrategy(EndgameStrategy):
       """冲刺策略：快速出完牌"""
       
       def execute(self, message: Dict) -> int:
           """执行冲刺策略（提升：更智能的出牌顺序）"""
           action_list = message.get("actionList", [])
           handcards = message.get("handCards", [])
           
           # 优先级1: 一手出完
           for i, action in enumerate(action_list):
               if len(action[2]) == len(handcards):
                   return i
           
           # 优先级2: 出最大牌型（快速减少牌数）
           return self._select_largest_action(action_list)
   
   class DefendStrategy(EndgameStrategy):
       """防守策略：保护队友"""
       pass
   
   class CooperateStrategy(EndgameStrategy):
       """配合策略：配合队友"""
       pass
   
   class ControlStrategy(EndgameStrategy):
       """控制策略：控制节奏"""
       pass
   ```

3. **在残局处理器中使用策略**
   ```python
   class EndgameLateActiveHandler(BasePhaseHandler):
       """残局后期主动出牌处理器（优化：使用残局策略）"""
       
       def __init__(self, config: Dict):
           super().__init__(config)
           # 残局策略库（内部使用）
           self.strategies = {
               'rush': RushStrategy(),
               'defend': DefendStrategy(),
               'cooperate': CooperateStrategy(),
               'control': ControlStrategy(),
           }
       
       def handle(self, message: Dict) -> int:
           """处理残局后期（提升：智能策略选择）"""
           # 1. 识别残局类型
           endgame_type = self._classify_endgame(message)
           
           # 2. 选择最佳策略
           strategy = self.strategies.get(endgame_type, self.strategies['rush'])
           
           # 3. 执行策略
           return strategy.execute(message)
       
       def _classify_endgame(self, message: Dict) -> str:
           """残局分类（提升：多维度分类）"""
           my_remain = len(message.get("handCards", []))
           teammate_remain = self._get_teammate_remain(message)
           opponents_remain = self._get_opponents_remain(message)
           
           # 分类1: 冲刺型（自己牌少，需要快速出完）
           if my_remain <= 3 and max(opponents_remain) >= 8:
               return 'rush'
           
           # 分类2: 防守型（队友牌少，需要保护）
           if teammate_remain <= 3 and my_remain <= 5:
               return 'defend'
           
           # 分类3: 配合型（队友牌少，需要配合）
           if teammate_remain <= 5 and my_remain <= 5:
               return 'cooperate'
           
           # 分类4: 控制型（自己牌多，需要控制节奏）
           if my_remain <= 5 and sum(opponents_remain) <= 15:
               return 'control'
           
           return 'rush'  # 默认
   ```

**验收标准**:
- [ ] 残局策略类定义清晰，接口统一
- [ ] 残局处理器能正确选择和使用残局策略
- [ ] 残局策略执行成功率>80%
- [ ] 残局处理时间<100ms

---

#### 2.2 队友保护策略系统（TeammateProtectionStrategy）

**目标**: 实现比lalala更完善的队友保护逻辑

**lalala的策略**:
- 如果队友是最大动作者，且当前牌值很大，选择PASS
- 如果队友剩余牌数≤4，只出比当前牌大1的牌

**YF的提升**:
- 🚀 **多策略组合**: 多种保护策略的组合
- 🚀 **动态保护强度**: 根据情况调整保护强度
- 🚀 **保护成本评估**: 评估保护的成本和收益

**实施步骤**:

1. **创建TeammateProtectionStrategy**
   ```python
   class TeammateProtectionStrategy:
       """队友保护策略（提升：多策略组合）"""
       
       def __init__(self, config: Dict):
           self.config = config
           self.protection_rules = [
               HighValueProtectionRule(),      # 高牌值保护
               LowCardCountProtectionRule(),   # 低牌数保护
               CriticalStageProtectionRule(),  # 关键阶段保护
               ThreatAssessmentRule(),         # 威胁评估保护
           ]
       
       def should_protect(self, message: Dict, context: Dict) -> bool:
           """判断是否应该保护队友（提升：多规则组合）"""
           protection_score = 0.0
           
           # 综合所有保护规则
           for rule in self.protection_rules:
               score = rule.evaluate(message, context)
               protection_score += score
           
           # 动态阈值（提升：根据情况调整）
           threshold = self._get_dynamic_threshold(message, context)
           
           return protection_score >= threshold
       
       def get_protection_action(self, message: Dict, context: Dict) -> Optional[int]:
           """获取保护动作（提升：智能选择保护方式）"""
           if not self.should_protect(message, context):
               return None
           
           # 保护方式1: PASS（完全保护）
           if self._should_full_protect(message, context):
               return 0
           
           # 保护方式2: 出最小管牌（部分保护）
           if self._should_partial_protect(message, context):
               return self._find_minimal_action(message)
           
           return None
   ```

2. **实现保护规则**
   ```python
   class HighValueProtectionRule:
       """高牌值保护规则（学习lalala）"""
       
       def evaluate(self, message: Dict, context: Dict) -> float:
           """评估保护需求"""
           cur_action = message.get("curAction")
           greater_pos = message.get("greaterPos")
           my_pos = message.get("myPos", 0)
           teammate_pos = (my_pos + 2) % 4
           
           # 如果队友是最大动作者
           if greater_pos == teammate_pos:
               cur_val = self._get_card_value(cur_action)
               max_val = context.get("max_card_value", 15)
               
               # 当前牌值很大，需要保护
               if cur_val >= max_val or cur_val >= 15:
                   return 1.0  # 高保护需求
               elif cur_val >= max_val - 2:
                   return 0.5  # 中等保护需求
           
           return 0.0
   ```

**验收标准**:
- [ ] 队友保护准确率>90%
- [ ] 保护策略多样化，适应不同场景
- [ ] 保护成本评估准确

---

#### 2.3 优先级系统（PrioritySystem）

**目标**: 实现比lalala更灵活的优先级系统

**lalala的策略**:
- 主动出牌：一手出完 → 两手出完 → 单张（小）→ 三连对/钢板 → 顺子 → 三带二 → 三张 → 对子 → 单张
- 被动出牌：单张成员 + 大牌值 → 非炸弹成员 + 大牌值 → 放宽条件 → 使用等级牌 → 使用炸弹

**YF的提升**:
- 🚀 **动态优先级**: 根据上下文调整优先级
- 🚀 **多因素综合**: 综合考虑多个因素
- 🚀 **可配置优先级**: 优先级规则可配置

**实施步骤**:

1. **创建PrioritySystem**
   ```python
   class PrioritySystem:
       """优先级系统（提升：动态优先级）"""
       
       def __init__(self, config: Dict):
           self.config = config
           self.base_priority = self._load_base_priority(config)
           self.context_adjuster = ContextPriorityAdjuster()
       
       def select(self, candidates: List, hand_structure: Dict, context: Dict) -> int:
           """选择最佳动作（提升：动态优先级）"""
           # 1. 获取基础优先级
           base_scores = self._calculate_base_scores(candidates, hand_structure)
           
           # 2. 根据上下文调整（提升：动态调整）
           adjusted_scores = self.context_adjuster.adjust(
               base_scores, 
               context
           )
           
           # 3. 选择最高分
           best_idx = max(range(len(adjusted_scores)), 
                         key=lambda i: adjusted_scores[i])
           return best_idx
       
       def _load_base_priority(self, config: Dict) -> Dict:
           """加载基础优先级（提升：可配置）"""
           # 从配置文件加载，支持动态调整
           return config.get("priority_rules", {
               'active': {
                   'one_hand_complete': 1000,
                   'two_hand_complete': 900,
                   'small_single': 800,
                   'threepair': 700,
                   'straight': 600,
                   # ...
               },
               'passive': {
                   'single_member_large': 1000,
                   'non_bomb_large': 900,
                   'relaxed_condition': 800,
                   # ...
               }
           })
   ```

2. **实现上下文优先级调整器**
   ```python
   class ContextPriorityAdjuster:
       """上下文优先级调整器（YF新增：动态调整）"""
       
       def adjust(self, base_scores: List[float], context: Dict) -> List[float]:
           """根据上下文调整优先级"""
           adjusted = base_scores.copy()
           
           # 调整因子1: 下家牌数
           if context.get("next_player_remain", 0) == 1:
               # 下家只剩1张，降低单张优先级
               adjusted = self._reduce_single_priority(adjusted, context)
           
           # 调整因子2: PASS次数
           if context.get("pass_count", 0) >= 5:
               # PASS次数过多，提高出牌优先级
               adjusted = self._increase_play_priority(adjusted, context)
           
           # 调整因子3: 残局阶段
           if context.get("is_endgame", False):
               # 残局，调整优先级
               adjusted = self._adjust_endgame_priority(adjusted, context)
           
           return adjusted
   ```

**验收标准**:
- [ ] 优先级系统可配置
- [ ] 动态调整准确有效
- [ ] 优先级选择准确率>85%

---

#### 2.4 牌值系统（CardValueSystem）

**目标**: 实现统一的牌值评估系统

**lalala的策略**:
- 基础牌值：2-14（A）
- 等级牌值：15
- 大小王：16, 17
- JOKER：10000

**YF的提升**:
- 🚀 **上下文相关牌值**: 根据游戏阶段调整牌值
- 🚀 **相对牌值**: 考虑剩余牌库的牌值
- 🚀 **组合牌值**: 考虑牌的组合价值

**实施步骤**:

1. **创建CardValueSystem**
   ```python
   class CardValueSystem:
       """牌值系统（提升：上下文相关）"""
       
       def __init__(self, rank: str):
           self.rank = rank
           self.base_values = self._init_base_values()
           self.rank_card_value = 15
       
       def get_value(self, card: str, context: Dict = None) -> float:
           """获取牌值（提升：上下文相关）"""
           # 基础值
           base_value = self.base_values.get(card, 0)
           
           # 等级牌特殊处理
           if card == f'H{self.rank}':
               base_value = self.rank_card_value
           
           # 上下文调整（提升：动态调整）
           if context:
               base_value = self._adjust_by_context(base_value, card, context)
           
           return base_value
       
       def _adjust_by_context(self, base_value: float, card: str, context: Dict) -> float:
           """根据上下文调整牌值（YF新增）"""
           # 调整因子1: 剩余牌库
           max_remain_value = context.get("max_remain_value", 15)
           if base_value >= max_remain_value:
               # 是最大牌，增加价值
               base_value += 0.5
           
           # 调整因子2: 游戏阶段
           if context.get("is_endgame", False):
               # 残局，大牌价值更高
               if base_value >= 12:
                   base_value += 1.0
           
           return base_value
   ```

**验收标准**:
- [ ] 牌值系统统一且准确
- [ ] 上下文调整有效
- [ ] 牌值计算速度<10ms

---

### 阶段三：高级功能实现（2周）

#### 3.1 决策树系统

**目标**: 实现可解释的决策树，提升决策可解释性

**YF的创新**:
- 🚀 **决策树可视化**: 可以查看决策路径
- 🚀 **决策规则可配置**: 决策规则可配置和调整
- 🚀 **决策历史记录**: 记录决策历史，便于分析

**实施步骤**:

1. **创建DecisionTree**
   ```python
   class DecisionTree:
       """决策树（YF新增：提升可解释性）"""
       
       def __init__(self):
           self.root = DecisionNode("root")
           self.current_path = []
       
       def decide(self, message: Dict) -> Tuple[int, List[str]]:
           """决策并返回路径"""
           self.current_path = []
           action_idx = self._traverse(self.root, message)
           return action_idx, self.current_path.copy()
       
       def _traverse(self, node: DecisionNode, message: Dict) -> int:
           """遍历决策树"""
           self.current_path.append(node.name)
           
           # 检查条件
           if node.condition and not node.condition.evaluate(message):
               return 0
           
           # 叶子节点，返回动作
           if node.is_leaf():
               return node.action_idx
           
           # 遍历子节点
           for child in node.children:
               if child.condition.evaluate(message):
                   return self._traverse(child, message)
           
           return 0
   ```

---

#### 3.2 策略配置系统

**目标**: 实现完全配置化的策略系统

**YF的创新**:
- 🚀 **YAML配置**: 使用YAML文件配置策略
- 🚀 **热更新**: 支持运行时更新配置
- 🚀 **A/B测试**: 支持多套配置A/B测试

**实施步骤**:

1. **创建策略配置文件**
   ```yaml
   # strategy_config.yaml
   endgame:
     threshold: 10
     strategies:
       rush:
         enabled: true
         priority: 1.0
       defend:
         enabled: true
         priority: 0.8
   
   teammate_protection:
     rules:
       high_value:
         enabled: true
         threshold: 15
       low_card_count:
         enabled: true
         threshold: 4
   
   priority:
     active:
       one_hand_complete: 1000
       two_hand_complete: 900
       small_single: 800
     passive:
       single_member_large: 1000
       non_bomb_large: 900
   ```

2. **实现配置加载器**
   ```python
   class StrategyConfigLoader:
       """策略配置加载器（YF新增）"""
       
       def load(self, config_path: str) -> Dict:
           """加载配置文件"""
           with open(config_path, 'r', encoding='utf-8') as f:
               return yaml.safe_load(f)
       
       def hot_reload(self, config_path: str):
           """热更新配置"""
           new_config = self.load(config_path)
           # 更新运行时配置
           self._update_runtime_config(new_config)
   ```

---

#### 3.3 性能优化系统

**目标**: 确保决策速度满足实时要求

**YF的创新**:
- 🚀 **缓存机制**: 缓存常用计算结果
- 🚀 **并行计算**: 并行计算多个候选动作
- 🚀 **早期退出**: 找到足够好的动作就退出

**实施步骤**:

1. **实现缓存系统**
   ```python
   class DecisionCache:
       """决策缓存（YF新增：提升性能）"""
       
       def __init__(self, max_size: int = 1000):
           self.cache = {}
           self.max_size = max_size
       
       def get(self, key: str) -> Optional[Any]:
           """获取缓存"""
           return self.cache.get(key)
       
       def set(self, key: str, value: Any):
           """设置缓存"""
           if len(self.cache) >= self.max_size:
               # LRU淘汰
               self._evict_lru()
           self.cache[key] = value
   ```

---

## 📈 实施时间表

### 第1-2周：架构重构
- [ ] StageRouter实现
- [ ] ActivePlayHandler实现
- [ ] PassivePlayHandler实现
- [ ] CardTypeHandlerFactory重构
- [ ] 基础测试

### 第3-4周：核心策略
- [ ] 残局策略类实现（RushStrategy, DefendStrategy等）
- [ ] 残局处理器策略整合（EndgameEarlyHandler, EndgameLateHandler）
- [ ] TeammateProtectionStrategy实现
- [ ] PrioritySystem实现
- [ ] CardValueSystem实现
- [ ] HandStructureAnalyzer增强
- [ ] 策略测试

### 第5-6周：高级功能
- [ ] DecisionTree实现
- [ ] StrategyConfigLoader实现
- [ ] 性能优化
- [ ] 完整测试

### 第7-8周：优化与调优
- [ ] 参数调优
- [ ] 性能优化
- [ ] 完整测试
- [ ] 文档编写

---

## 🎯 关键提升点总结

### 相比lalala的提升

1. **架构设计** ⭐⭐⭐⭐⭐
   - lalala: 简单直接，但扩展性差
   - YF: 分层模块化，易于扩展和维护

2. **残局处理** ⭐⭐⭐⭐⭐
   - lalala: 简单判断（剩余牌数≤10）
   - YF: 阶段细分（残局前期/后期）+ 多维度判断 + 多种策略（整合到处理器内部）

3. **队友保护** ⭐⭐⭐⭐
   - lalala: 基础保护逻辑
   - YF: 多策略组合 + 动态保护强度

4. **优先级系统** ⭐⭐⭐⭐⭐
   - lalala: 固定优先级
   - YF: 动态优先级 + 可配置

5. **手牌分析** ⭐⭐⭐⭐
   - lalala: 深入分析
   - YF: 更深入 + 组合潜力分析

6. **可配置性** ⭐⭐⭐⭐⭐
   - lalala: 硬编码
   - YF: 完全配置化

7. **可解释性** ⭐⭐⭐⭐⭐
   - lalala: 中等
   - YF: 决策树 + 决策路径记录

8. **性能优化** ⭐⭐⭐⭐
   - lalala: 未优化
   - YF: 缓存 + 并行 + 早期退出

---

## 📝 验收标准

### 功能验收
- [ ] 所有阶段路由正确
- [ ] 所有牌型处理器正常工作
- [ ] 残局处理准确率>95%
- [ ] 队友保护准确率>90%
- [ ] 优先级选择准确率>85%

### 性能验收
- [ ] 决策时间<200ms（平均）
- [ ] 决策时间<500ms（最大）
- [ ] 内存占用<100MB

### 代码质量
- [ ] 代码覆盖率>80%
- [ ] 所有模块有单元测试
- [ ] 代码符合PEP8规范
- [ ] 有完整的文档

---

## 🔄 持续改进计划

### 短期（1-2月）- 硬编码优化
- 根据实战结果调整硬编码参数
- 优化决策速度（硬编码优化）
- 完善测试用例
- 细化各阶段硬编码策略
- 优化队友保护硬编码规则
- 完善残局硬编码策略

### 中期（3-6月）- 硬编码深化
- 增加更多硬编码策略规则
- 实现硬编码参数配置化（YAML配置）
- 硬编码规则A/B测试和调优
- 完善对手压制硬编码策略（如需要）
- 硬编码决策树优化

### 长期（6月+）- 硬编码系统化
- 构建完整的硬编码规则库
- 硬编码规则版本管理和回滚机制
- 硬编码规则效果评估系统
- 硬编码规则自动测试框架

**注意**: 
- ⚠️ 机器学习方案已暂停，当前专注硬编码路线
- ✅ 硬编码规则引擎是当前核心发展方向
- 📊 通过精细化硬编码规则，实现稳定可靠的决策质量

---

## 🚀 迭代升级方案（未来优化方向）

### 对手压制策略引擎（OpponentSuppressionStrategy）

**背景分析**:
- lalala中有分散的对手相关策略，但没有统一的对手压制引擎
- lalala的策略包括：
  - 根据对手牌数调整出牌优先级
  - 根据最大动作者牌数决定是否使用炸弹
  - 根据下家牌数选择牌型（避免被单张压制）

**YF优化方向**:
- 🚀 **统一对手压制策略引擎**: 整合分散的对手相关逻辑
- 🚀 **对手威胁评估系统**: 评估对手威胁等级
- 🚀 **对手压制策略库**: 多种压制策略（主动压制、被动压制、炸弹压制等）
- 🚀 **对手牌数分析系统**: 综合分析对手牌数分布，制定压制策略

**实施建议**:
```python
class OpponentSuppressionStrategy:
    """对手压制策略引擎（未来优化方向）"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.threat_analyzer = OpponentThreatAnalyzer()
        self.suppression_rules = [
            ActiveSuppressionRule(),      # 主动压制规则
            PassiveSuppressionRule(),     # 被动压制规则
            BombSuppressionRule(),        # 炸弹压制规则
            CardTypeSuppressionRule(),    # 牌型压制规则
        ]
    
    def should_suppress(self, message: Dict, context: Dict) -> bool:
        """判断是否应该压制对手"""
        # 评估对手威胁等级
        threat_level = self.threat_analyzer.analyze(message, context)
        
        # 根据威胁等级决定是否压制
        return threat_level >= self.config.get("suppression_threshold", 0.7)
    
    def get_suppression_action(self, message: Dict, context: Dict) -> Optional[int]:
        """获取压制动作"""
        # 综合所有压制规则，选择最佳压制动作
        pass
```

**优先级**: 中等（在核心功能稳定后实施）  
**预计实施时间**: 第9-10周（迭代升级阶段）

---

## 📚 参考资料

- lalala决策机制完整分析报告
- lalala决策机制详细分析文档（01-04）
- YF当前决策引擎代码
- 掼蛋游戏规则文档

---

**计划制定时间**: 2025-12-17  
**最后更新**: 2025-12-17（调整策略方向：专注硬编码）  
**计划状态**: 待实施  
**预计完成时间**: 8周  
**负责人**: 待分配

---

## ⚠️ 重要说明：硬编码优先策略

### 策略调整背景

**机器学习测试结果**（2025-12-17）:
- ❌ 经过3周测试，机器学习方案未达到预期效果
- ❌ 模型训练效果不稳定，决策质量提升有限
- ❌ 模型推理速度无法满足实时对战要求

**决策调整**:
- ✅ **回归硬编码路线**: 专注硬编码规则引擎优化
- ✅ **硬编码优先**: 所有优化方向以硬编码为核心
- ✅ **精细化规则**: 通过精细化硬编码规则，实现稳定可靠的决策质量

### 硬编码优势

1. **稳定性**: 硬编码规则稳定可靠，不受训练数据影响
2. **可解释性**: 规则清晰明确，易于理解和调试
3. **性能**: 决策速度快，满足实时对战要求
4. **可控性**: 规则可精确控制，便于调优和优化

### 当前重点

- 🎯 **阶段细分路由**: 实现5阶段细分路由系统
- 🎯 **策略引擎**: 完善队友保护、优先级等策略引擎
- 🎯 **规则优化**: 精细化各阶段硬编码规则
- 🎯 **参数调优**: 通过实战数据调优硬编码参数

### 未来方向

- 📊 硬编码规则库建设
- 📊 硬编码规则版本管理
- 📊 硬编码规则效果评估
- 📊 硬编码规则自动测试

**注意**: 机器学习相关方案已暂停，当前所有工作聚焦硬编码规则引擎优化。

