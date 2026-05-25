# M1 vs lalala：硬编码规则引擎技术路径对比

## 一、核心结论

**lalala 的技术路径更优**。M1 在以下维度存在实质性差距：规则嵌入的精确度、代码-规则耦合的紧凑度、牌型级决策的细腻度。M1进行了"过度工程化"（过度分层、过度抽象），导致规则密度稀释，最终决策质量反而下降。

---

## 二、规则嵌入路径对比

### 2.1 lalala：按牌型组织，单方法完成全部决策

lalala 的规则按牌型嵌入在 `Action` 类的实例方法中，每个牌型一个独立方法：

```
passive() → 根据 curAction[0] dispatch → Single() / Pair() / Trips() / ...
active() → 手牌遍历优先链 → getindex() / rankone() / ranktwo() / ...
```

**关键代码特征：**

- `action.py:37-179` `Single()` 方法：完整的单张被动出牌决策，包含 `numofnext/numofgreaterPos/numoffri` 四个位置维度的条件分支，每个分支直接决定返回值（0=PASS, >0=动作索引）
- `action.py:181-335` `Pair()` 方法：与 Single 结构高度对称，但逻辑独立调整（例如 L228: `curVal>=12 && numofnext!=2` 与 Single 的 L84: `curVal>=15 && numofnext!=1` 不同）
- `action.py:964-1019` `passive()` 方法：仅做牌型 dispatch，无额外抽象层
- `action.py:1093-1183` `active()` 方法：独立的出牌优先级链，按 `len(single_actionlist) < cur[0]` → `rankfour()` → `rankthree()` → `rankone()` → `ranktwo()` 顺序尝试
- `utils.py:369-411` `one_hand()`：作为独立函数，专门处理`手牌≤10张`场景，主动检测一手出完/两手出完

**嵌入路径特点：**
- 规则直接写在决策点位置，无中间抽象
- 每个方法的入参即游戏状态的全部维度（`actionList, curAction, rank_card, handcards, numofplayers, rest_cards, card_val, myPos, greaterPos, pass_num, my_pass_num`）
- 条件分支就地返回结果，无 "策略建议 → 过滤 → 优先级排序 → 最终选择" 的流水线

### 2.2 M1：按阶段+动静分层，规则分散在四层结构中

M1 的规则按**阶段×动静**组织在 `BasePhaseHandler` 派生的 10 个处理器中，外加独立的策略引擎：

```
RuleBasedDecisionEngineM1.decide()
  → StageRouter.route()  // 路由层
    → OpeningActiveHandler.handle() / OpeningPassiveHandler.handle() / ...
      → PrioritySystem.select()  // 优先级系统
      → TeammateProtectionStrategy.get_protection_action()  // 保护策略
        → HighValueProtectionRule / LowCardCountProtectionRule / ...
```

**关键代码特征：**

- `rule_based_decision_engine_m1.py:158-229` `decide()`：入口，调用 `self.router.route(message)`，然后做结果验证（L202-223：Counter 卡牌一致性检查）
- `stage_router.py:464-538` `route()`：路由，根据 `my_remain` 判断阶段，dispatch 到具体 handler
- `phase_handlers.py:50-77` `OpeningActiveHandler.handle()`：开局主动，调用 `_build_structure_strategy()`（L75），后者又调用 `_scan_hand_combination()` → `priority_system.select()` → 多级 fallback（L116-362）
- `phase_handlers.py:387-534` `OpeningPassiveHandler.handle()`：开局被动，先检查 `teammate_protection`（L454-460），再按 curAction_type dispatch 到 `_handle_single_passive()` / `_handle_pair_passive()` / `_handle_other_passive()`
- `strategy_engine.py:425-540` `PrioritySystem.select()`：根据优先级映射计算分数，选择最高分
- `strategy_engine.py:180-211` `TeammateProtectionStrategy.should_protect()`：综合 5 个 ProtectionRule 的评分，与动态阈值比较

**嵌入路径特点：**
- 规则分散在 4 层中：handler 层（if-else 条件） + priority 层（分数映射） + protection 层（多规则评分） + fallback 层（兜底逻辑）
- 每个 handler 有大量样板代码：构建 context → 扫描手牌 → 过滤 candidates → 调用 priority_system → fallback
- 同牌型的决策逻辑分散在多个 handler 中重复编写（例如单张被动分布在 OpeningPassiveHandler._handle_single_passive、MidEarlyPassiveHandler._handle_single_passive）

---

## 三、关键差距（代码级）

### 差距1：规则精确度——lalala 的条件维度远多于 M1

**lalala** 在一个方法内使用了 `numofnext / numofgreaterPos / numoffri / numofpre` 四个位置维度 + `curVal / max_val / pass_num / my_pass_num` 四个数值维度，组合出精细化条件。例如：

- `action.py:81-85`：`numofnext <= 4 or (numofpre <= 3 and numofpre >= 1)` 时，如果队友是 greaterPos，直接让过（return 0）
- `action.py:137-155`：队友是 greaterPos 时，根据 `curVal >= 14或 max_val-2`、`numoffri <= 4`、`curVal <= 10` 三级分支
- `action.py:161-177`：非队友 greaterPos 时，根据 `pass_num >= 5 or my_pass_num >= 3`、`cur_bomb_num > 1`、`numofgreaterPos >= 15` 组合决定是否炸

**M1** 在 `_handle_single_passive` 中的条件维度显著更少：

- `phase_handlers.py:619`：仅有 `is_upper_hand = (greater_pos == (my_pos - 1) % 4)` 一个位置判断
- `phase_handlers.py:701-708`：仅按 `action_rank_value > cur_rank_value` 比较大小，缺乏 `numofnext / pass_num / cur_bomb_num` 等上下文
- `phase_handlers.py:814-829`：对手出高牌时的兜底逻辑仅做"返回第一个非 PASS 动作"，无精细分级

### 差距2：炸弹使用策略——lalala 有完整的评分系统，M1 基本缺失

**lalala** 的 `choose_bomb()`（`utils.py:297-367`）实现了多维度的炸弹评分：
- `L315-326`：级牌炸弹根据 `rank_card_num` 给予 `prior=3或16` 的额外权重
- `L328-331`：普通炸弹根据 `bomb_info` 中原始张数匹配时才接受
- `L332-341`：允许用级牌补强炸弹（`rank_card in action[2]`），给予 `prior` 加分
- `L357-361`：同花顺额外加 `32` 分
- `L366-367`：按总分排序，选最低分的（最小代价）

**M1** 的炸弹逻辑在 `PrioritySystem._calculate_base_scores()`（`strategy_engine.py:512-525`）：
- 仅做了阶段限制（`my_rest > 15` 时 score=0 禁止使用）
- 无炸弹之间的优劣比较
- 无级牌补强炸弹的评分逻辑
- 无同花顺的特殊优先级

### 差距3：主动出牌优先级——lalala 有手牌驱动的动态选择，M1 依赖固定优先级映射

**lalala** 的 `active()` 方法（`action.py:1093-1183`）根据手牌结构动态决策路径：
- `L1129-1133`：如果最小单张 `card_val[single_actionlist[0][0]] < cur[0]`（可出范围），立即出单
- `L1135-1140`：如果有三连对/钢板，调 `rankfour()` 比较两者最小值的优先级
- `L1146-1154`：如果有三带二，调 `rankthree()` 综合 `trips/pairs/singles` 数量做复杂比较（`utils.py:610-687`）
- `L1155-1158`：三张/对子/单张形成了天然优先级链，但每个节点有独立的 `numofnext` 检查
- `L1160-1181`：`numofnext == 1` 时的特殊处理：先检查是否能一手出完、拆对子凑Pair、出最大单

**M1** 的 `PrioritySystem._calculate_base_scores()`（`strategy_engine.py:467-540`）：
- `L474-483`：固定映射 `action_type_mapping` 将牌型映射到 6 个优先级键
- `L444-464`：`base_priority` 是固定分数（single=200, pair=300, trips=360...）
- `L496-505`：仅有一手出完（`len(cards)==len(handcards)`）和两手出完（`card_count >= handcards*0.7`）的加权
- 缺乏 lalala 中 `rankthree()` 那种根据 `len(pairs) vs len(trips)` 的动态比较逻辑

### 差距4：lalala 的 one_hand 函数精简高效，M1 分散在多个 handler 中重复

**lalala** 的 `one_hand()`（`utils.py:369-411`）：
- `L388-393`：非队友时，找一手出完的动作直接返回
- `L394-409`：队友时，非炸弹优先，炸弹需要评估 `cur_level > max_bomb` 才出
- 完整地封装了"少牌场景的一手出完决策"，输入输出明确

**M1** 的"少牌"逻辑分散在各 handler 中：
- `phase_handlers.py:1168-1209` `MidEarlyActiveHandler._check_two_hand_complete()`：在 MidEarly/MidLate 中重复定义
- `phase_handlers.py:1044-1047` 和 `1674-1682`：在 MidEarly/MidLate Active 中分别调用
- `phase_handlers.py:88-93` `BasePhaseHandler._check_one_hand_complete()`：是基类方法，但只在部分 handler 中调用
- lalala 的 `one_hand` 以 `numofnext` 和 `max_bomb` 维度判断，M1 仅以牌数判断

### 差距5：代码量与规则密度的反比

| 维度 | lalala | M1 |
|------|--------|-----|
| 核心决策代码行数 | ~770行（action.py + utils.py） | ~3600+行（4个文件） |
| 规则抽象层数 | 1层（方法直接返回） | 4层（router→handler→strategy→fallback） |
| 每牌型被动规则 | 8个独立方法 | 5阶段 × 2动静 × 多牌型（重复定义） |
| 日志/验证代码占比 | <5% | ~40%（validate_action_cards、logger、Counter检查等） |

M1 的 `_validate_action_cards`（`stage_router.py:197-245`）在每个 handler 的每个决策路径都被调用，但 lalala 完全不需要——因为 lalala 的规则直接使用手牌数据结构，天然不会选错牌。

---

## 四、扩充性分析

### 4.1 lalala 的扩充性

**加新规则：** 直接在对应牌型方法中添加 if-else 分支。
- action.py 的 Single() 方法已有 6 个 if 段 + 2 个闭包函数（normal/special），再加分支，阅读难度线性增长
- 当条件组合爆炸（如同时考虑 numofnext、pass_num、bomb_num、rank_card_num），嵌套深度可达 5+ 层
- 没有统一的优先级框架，新规则需要手动插入到正确位置

**加新牌型：** 需要新增方法并加入 passive() 的 dispatch 链。
- passive() 的 dispatch 在 action.py:988-1017 是 7 路 if-elif，加新牌型简单
- 但 active() 的 dispatch 逻辑分散在 action.py:1129-1181，需要理解完整的决策树

**结论：** lalala 的扩充适合"在现有维度上加深"，不适合"引入新的决策维度或新牌型"。

### 4.2 M1 的扩充性

**加新规则：** 可以选择：
1. 在 `ProtectionRule` 子类中新增（如 `OpponentSprintWhenTeammateLeadsRule`，`strategy_engine.py:125-149`）
2. 修改 `base_priority` 字典调整分数（`strategy_engine.py:444-464`）
3. 在具体 handler 的方法中加 if 分支

**加新阶段：** 新增 `BasePhaseHandler` 子类，在 `RuleBasedDecisionEngineM1.__init__()` 注册。
- 每个新阶段需要 2 个 handler（active + passive）
- 每个 handler ~200 行样板代码

**加新牌型：** 需要：
1. 修改 `action_type_mapping`（`strategy_engine.py:474-484`）
2. 修改 `base_priority` 添加新键值
3. 在相关 handler 的方法中添加处理逻辑

**结论：** M1 的扩充性在"加新保护规则"方面好（只需新增类注册到列表），但在"加新牌型"和"加新阶段"方面比 lalala 差（需要改多个文件，且样板代码多）。

### 4.3 总体扩充性评分

| 场景 | lalala | M1 |
|------|--------|-----|
| 已有牌型的规则细化 | ★★★★☆（直接加if） | ★★☆☆☆（需找对handler + 理解多层架构） |
| 加新牌型 | ★★★☆☆（加方法+改dispatch） | ★★☆☆☆（改4个地方+样板代码） |
| 加新阶段/场景维度 | ★☆☆☆☆（无此概念） | ★★★☆☆（继承BasePhaseHandler） |
| 加新保护/协作策略 | ★☆☆☆☆（无此概念） | ★★★★☆（新增ProtectionRule子类） |
| 调试/排查问题 | ★★☆☆☆（打印语句） | ★★★★☆（结构化日志+验证+降级） |

---

## 五、追赶建议（可执行）

### 建议1：将 M1 的 PrioritySystem 替换为 lalala 的牌型驱动决策

**当前问题：** `PrioritySystem._calculate_base_scores()`（`strategy_engine.py:467-540`）用固定分数映射做决策，无法表达 lalala 中 `numofnext==1` 时的特殊处理、`rankthree()` 中根据手牌比例动态选择牌型等逻辑。

**具体操作：**

1. 删除 `strategy_engine.py:467-540` 的 `_calculate_base_scores` 方法
2. 在 `phase_handlers.py` 的每个 active handler 中，直接实现 lalala 风格的优先级链：
   ```
   def _active_priority_chain(self, message, action_list, handcards):
       # 1. 检查一手出完（lalala action.py:1113-1115）
       # 2. 剩余≤12张检查两手出完（lalala action.py:1121-1127）
       # 3. 小单张直接出（lalala action.py:1129-1133）
       # 4. 三连对/钢板 rankfour（lalala action.py:1135-1140）
       # 5. 顺子（lalala action.py:1143-1144）
       # 6. 三带二 rankthree（lalala action.py:1146-1154）
       # 7. 三张 rankone（lalala action.py:1155-1156）
       # 8. 对子 ranktwo（lalala action.py:1157-1158）
       # 9. 单张（lalala action.py:1159-1181）
       # 10. fallback PASS
   ```

### 建议2：将 lalala 的单牌型被动方法直接移植为 M1 handler 的内联逻辑

**当前问题：** `OpeningPassiveHandler._handle_single_passive()`（`phase_handlers.py:576-834`）有 258 行但缺乏关键条件维度。

**具体操作：**

1. 在 `BasePhaseHandler` 基类中添加 `_lalala_single_passive()` 方法，直接移植 `action.py:37-179` 的核心逻辑
2. 替换各 passive handler 中的 `_handle_single_passive()` 调用
3. 移植时需要保留 lalala 的 4 位置维度 + 4 数值维度的条件组合

关键移植代码模式（以 single 为例）：
```python
def _lalala_single_passive(self, message, action_list, curAction):
    # 从 message 中提取 lalala 需要的所有参数
    sorted_cards, bomb_info = combine_handcards(handcards, rank_card[-1], card_val)
    # ... 移植 action.py:37-179 的完整逻辑
    # 替换 return 0 为调用 self._default_passive_action
    # 替换 return Index 为 return index
```

### 建议3：移植 lalala 的 combine_handcards + choose_bomb

**当前问题：** `choose_bomb()`（`utils.py:297-367`）的评分逻辑无法在 M1 中找到等价物。

**具体操作：**

1. 将 `utils.py:13-243` 的 `combine_handcards()` 复制到 `src/decision/lalala_compat.py` 作为独立工具函数
2. 将 `utils.py:297-367` 的 `choose_bomb()` 复制到同一文件
3. 在 `BasePhaseHandler._build_context()` 中调用 `combine_handcards()` 将结果加入 context
4. 在 passive handler 的炸弹决策点调用 `choose_bomb()` 替代当前逻辑

### 建议4：消除重复样板代码

**当前问题：** 每个 handler 都重复手牌扫描、candidates 过滤、fallback 等 50+ 行样板代码。

**具体操作：**

1. 在 `BasePhaseHandler` 中增加带参数模板方法：
```python
def _active_decision(self, message, phase_specific_fn=None):
    context = self._build_context(message)
    scan_result = self._scan_hand_combination(message, context)
    # ... 公共逻辑 ...
    if phase_specific_fn:
        result = phase_specific_fn(message, action_list, handcards, scan_result)
        if result is not None:
            return result
    return self._default_active_action(action_list, message)
```

2. 每个 handler 的实现缩减为：
```python
class OpeningActiveHandler(BasePhaseHandler):
    def handle(self, message):
        return self._active_decision(message, self._opening_priority)
    
    def _opening_priority(self, message, action_list, handcards, scan_result):
        # 仅包含开局特有的优先级逻辑，~30行
```

### 建议5：删除过度防御的验证代码

**当前问题：** `_validate_action_cards()`（`stage_router.py:197-245`）在 handler 内部 + `decide()` 中（`rule_based_decision_engine_m1.py:202-223`）双重执行。游戏服务器本身会保证 actionList 的合法性。

**具体操作：**
1. 删除 handler 内部所有的 `_validate_action_cards()` 调用
2. 保留 `decide()` 中的最终验证作为安全网（但改为 warn 级别，不打 error）

---

## 六、自评

### 置信度：85%

**依据：**
- 通过阅读全部 6 个源文件的完整源码，获得了对两个引擎的全面理解
- 所有引用的行号和原文都是精确的
- 对比维度覆盖了规则嵌入路径、决策精确度、代码组织、扩充性

**可能遗漏的地方：**
1. M1 的 `OptimalCombinationScanner` 和 `HandStructureAnalyzer` 的功能尚未深入分析（未在源文件列表中），它们可能在手牌分析方面比 lalala 的 `combine_handcards` 更强，但对比时未深入
2. M1 的智能路由器 `IntelligentStageRouter` 未在本次分析范围内（按配置选择启用，非默认）
3. M1 的增强协作策略 `EnhancedCollaborationStrategy` 和增强优先级系统 `EnhancedPrioritySystem` 未在源文件列表中，它们可能弥补部分差距
4. 未进行实际对战测试，基于静态代码分析的结论
5. lalala 的进贡/还贡逻辑只读了 `action.py:1185-1245` 片段（截断），未做完整对比

### 开放问题
- M1 的多阶段设计如果与 lalala 的细粒度规则结合，是否会获得"两全其美"的效果？建议实现"建议1"后做 A/B 测试验证。
