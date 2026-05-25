# M1 vs lalala：硬编码规则引擎对照分析

## 1. 定位对比

| | lalala | M1 |
|---|---|---|
| 来源 | 一等奖作品，`action.py` 1412行 | yifeGDBOT m1-dev 分支，6个文件 |
| 系列 | 未知（纯硬编码） | M系列（Hardcoded Rules），与V系列并列 |
| 入口 | `rule_parse()` 单入口 | `decide()` → `StageRouter` → Handler |

---

## 2. 被动出牌（管牌）

### lalala `passive()` 逻辑（`action.py:964-1019`）

```
passive():
  1. 建立牌值系统（rank_card=15, B=16, R=17）
  2. numofmy <= 10 → 调用 one_hand() 残局处理（最高优先级）
  3. 按 curAction[0] 分发到 Single/Pair/Trips/.../Bomb 共8个方法
```

**残局判断**：剩余牌数 ≤ 10，直接走 `one_hand()` 专门处理，不走常规牌型分发。

### M1 对应实现

M1 用阶段路由器代替了 lalala 的 if-elif 分发链：

| lalala | M1 |
|--------|-----|
| `numofmy <= 10` → `one_hand()` | `rest > 10` → `MidLateHandler`；`rest 6-10` → `EndgameEarlyHandler`；`rest <= 5` → `EndgameLateHandler` |
| 8个牌型方法 | `PrioritySystem.select()` 通用排序 |

**区别**：lalala 在 `passive()` 入口处用固定阈值（≤10）拦截残局；M1 用阶段路由器按剩余牌数分段（>15 / 10-15 / 6-10 / ≤5），每个阶段对应一个 Handler。

---

## 3. 主动出牌（首出）

### lalala `active()` 优先级（`action.py:1093-1183`）

```
1. 一手出完（handcards == len(action)）  ← 最高优先级
2. 两手出完（len(handcards) <= 12）
3. 小单张（单张值 < cur[0]=9，下家剩1张时不出）
4. 三连对/钢板（阈值 cur[1]=10, cur[2]=9）
5. 顺子（顺子最小值 < cur[4]=10）
6. 三带二 → rankthree() 评估
7. 三张 → rankone() 评估
8. 对子 → ranktwo() 评估
9. 单张兜底
```

**阈值数组** `cur = [9, 10, 9, 8, 10, 10, 2]` 定义了各牌型"能出的最大牌值"，超过则让掉。

### M1 对应实现（`OpeningActiveHandler.handle()`）

```
1. 扫描手牌最优组合（excess_singles）
2. 保护受限制造组合（protected_combinations）
3. PrioritySystem.select() 综合评分
4. 降级策略：按 power 分三档（≥6 / <6 / <5）
   - ≥6 或有王/级牌 → 出小单张
   - <6 → 对子先行
   - <5 → 优先钢板/三连对，不出单张
```

**关键差距**：M1 `OpeningActiveHandler` 注掉了"一手出完"检查（见 §4b）；lalala 还有"下家剩1张"特殊处理链——拆对子/出多张/出最大单张，M1 缺少这一层。

---

## 4. 单张管牌（被动出牌中最复杂的分支）

### lalala `Single()` 逻辑（`action.py:37-179`）

```
Single(curAction):
  # 提取所有人剩余牌数
  numofnext, numofgreaterPos, numoffri, numofmy, numofpre

  # 残局/关键阶段（下家≤4 或 上家剩1-3张）
  if numofnext <= 4 or (numofpre <= 3 and numofpre >= 1):
      if 队友是最大 and curVal >= max_val: return PASS  # 保护队友
      if 队友是最大 and curVal >= 15 and numofnext != 1: return PASS
      优先选：单张成员 + 牌值 >= max_val + 非等级牌
      次选：非炸弹成员 + max_val
      放宽：牌值 >= max_val-2
      考虑用炸弹

  # 队友是最大动作者
  elif 队友是最大:
      if curVal >= 14 or curVal >= max_val-2: return PASS
      elif 队友剩牌 <= 4:
          只出比当前大1的牌
      else: normal() 或 PASS

  # 对手是最大动作者
  else:
      normal() → special()（PASS次数过多时）→ 炸弹（条件触发）
```

**手牌结构分析**：调用 `combine_handcards()` 将手牌分解为 `single_member / pair_member / trip_member / bomb_member / straight_member`，避免出单张时破坏这些组合。

### M1 对应实现

M1 没有按牌型分发的 `Single()` 方法，单张管牌逻辑在 `MidEarlyPassiveHandler` 等 Handler 内，通过 `PrioritySystem` 通用评分：

```
TeammateProtectionStrategy.should_protect():
  - HighValueProtectionRule（队友出大牌，curVal >= max_val → 保护）
  - LowCardCountProtectionRule（队友剩牌少 → 保护）
  - CriticalStageProtectionRule（endgame 阶段 → 保护）
  - ThreatAssessmentRule（对手快走完 → 保护）
  - OpponentSprintWhenTeammateLeadsRule（对手冲关，队友领先 → 负分，减少让牌）
```

**关键差距**：lalala `Single()` 的手牌结构分析（识别单张/对子/炸弹/顺子成员，避免破坏组合）在 M1 中分散在 `HandStructureAnalyzer` 和 `OptimalCombinationScanner` 里，没有在单张管牌时针对性使用。

**lalala 额外回退机制**：`Single()` 根据 PASS 次数动态降级：
- `pass_num >= 5` 或 `my_pass_num >= 3` → 降级到 `special()`（从大到小选）
- `pass_num >= 7` 或 `my_pass_num >= 5` → 考虑使用炸弹

---

## 4b. 主动出牌：一手出完

lalala 在 `active()` 入口处有最高优先级判断：`actionList` 中任意动作包含全部手牌 → 直接返回该动作索引。

M1 的 `OpeningActiveHandler`（开局主动）**明确注掉了**此检查（`phase_handlers.py:73` 注释：`# 开局不需要检查"一手出完"`）。但 `EndgameEarlyActiveHandler` / `EndgameLateActiveHandler` 等其他 Handler 仍保留 `_check_one_hand_complete()` 调用。因此"缺少一手出完优先"**仅适用于开局主动**，残局阶段 Handler 不受此影响。

---

## 5. 队友保护逻辑对比

| 场景 | lalala | M1 |
|------|--------|-----|
| 队友出大牌，我有大牌 | 直接 PASS | `should_protect()` 阈值触发 |
| 队友剩牌 ≤ 4 | 只出大1的牌（精确控制） | `LowCardCountProtectionRule` 统一处理 |
| 队友出大牌但我也有大牌 | curVal≥14 或 curVal≥max_val-2 时仍 PASS（`Single():140-141`） | `should_protect()` 可能误触发 |
| 对手快冲关，队友领先 | 无 | `OpponentSprintWhenTeammateLeadsRule` 负分（-0.55） |

**GUA-022 根源**：`strategy_engine.py` 的队友保护规则组合（阈值 2.25）在"队友出大牌"时保护倾向过强，导致 M1 频繁 PASS 丢权。lalala 的队友保护更克制，只在特定条件下 PASS，没有"积累分数达到阈值"的机制。

---

## 6. 牌型分发 vs 通用评分

| | lalala | M1 |
|---|---|---|
| 被动出牌分发 | 按 `curAction[0]` 分发到8个方法 | `PrioritySystem.select()` 统一评分 |
| 主动出牌 | if-elif 优先级链 + `getlist()` 分析 | `OpeningActiveHandler` + 策略栈 |
| 残局 | `one_hand()` 阈值拦截 | Handler 分段 |
| 手牌分析 | `combine_handcards()` 统一入口 | `HandStructureAnalyzer` + `OptimalCombinationScanner` 分离 |

**trade-off**：lalala 的"一牌型一方法"更易于针对性调参，但每新增一种牌型逻辑就要改 `passive()`；M1 的通用评分更灵活，但评分函数本身变得复杂。

---

## 7. 战绩

| 对局数据 | 结果 |
|----------|------|
| 10局对战 lalala | M1 胜率 0（`victoryNum=[0,3,0,3]`） |
| PASS率 | yf1_m1 54.78%，yf2_m1 55.70% |
| 问题 PASS（有非 PASS 仍 PASS） | yf1_m1: 7次，yf2_m1: 10次 |

---

## 9. 规则层面：M1 缺失或不足的规则

### 9.1 完全缺失的规则

| 规则 | lalala 实现位置 | M1 状态 |
|------|----------------|---------|
| **队友剩牌≤4，只出"刚好大1"的牌** | `Single():144-153`：精确控制 `card_val == curVal+1` | ❌ 无，`should_protect()` 整段 PASS |
| **PASS次数→策略降级** | `pass_num≥5 → special()`，`≥7 → bomb`（`Single():174-193`） | ❌ 无，`pass_num` 未参与被动出牌决策 |
| **主动出牌"下家剩1张"完整处理链**（拆对子/出多张/出最大单张） | `active():156-182` | ⚠️ 仅降低单张优先级（`strategy_engine.py:382`），无拆对子逻辑 |

### 9.2 有但不完整的规则

| 规则 | lalala | M1 |
|------|--------|-----|
| **单张成员识别**（避免拆 bomb/straight） | `normal()/special()` 在 `Single()` 内精确识别 | ⚠️ `HandStructureAnalyzer` 存在，但单张管牌时未针对性调用 |
| **两手出完** | 精确匹配 `len(i)+len(j)==len(handcards)` | ⚠️ 宽松近似 `>=70%`（`strategy_engine.py:503`） |

### 9.3 核心结论

M1 和 lalala 的差距不在于"缺规则"，而在于 **规则嵌入方式的差异**：

- lalala：规则硬编码在专用路径里（`Single`/`Pair`/`Trips` 各有专职），调用时机精确可控
- M1：规则分散在可配置的组件里（`HandStructureAnalyzer` / `PrioritySystem` / `should_protect`），但调用时机不对——最典型的问题是 GUA-022：`should_protect()` 把"队友保护"封装成可积累的分数，缺少 lalala `Single()` 里那种精确的"只出大1"边界控制，导致保护过度

---

## 10. 技术路径对比：规则的嵌入方式

### 10.1 两种架构的核心差异

| 维度 | lalala | M1 |
|------|--------|-----|
| 代码组织 | 单文件 `action.py`，~1400行 | 6+ 文件分散，总计 ~3000+ 行 |
| 入口分发 | `rule_parse()` → if-elif 硬分发 | `decide()` → `StageRouter` 路由表 |
| 规则嵌入位置 | 各牌型方法内部（Single/Pair/Trips...） | 共享组件（PrioritySystem/should_protect/HandAnalyzer） |
| 规则粒度 | 精确条件：`card_val == curVal+1` | 可配置分数：`protection_score >= threshold` |
| 手牌结构分析 | 内嵌在各牌型方法里 | 提取为独立组件但调用时机不对 |

---

### 10.2 关键差距：GUA-022 的技术根源

**lalala 的队友保护**（`Single():144-153`）：
```python
elif (myPos+2)%4 == greaterPos:  # 队友是最大
    if numoffri <= 4:
        for action in single_actionList:
            if card_val[action[1]] == curVal + 1:  # 精确：只出大1
                return action_index
```
- 精确边界：队友剩牌 ≤ 4 时，只考虑"刚好大1"的选项
- 没有积累分数、没有阈值
- 调用路径固定，`single_actionList` 过滤完只剩符合条件的选择

**M1 的队友保护**（`strategy_engine.py:79-85`）：
```python
def should_protect(self, message, context):
    protection_score = 0.0
    for rule in self.protection_rules:
        score = rule.evaluate(message, context)
        protection_score += score       # 积累
    threshold = self._get_dynamic_threshold(...)
    return protection_score >= threshold  # 阈值判断
```
- 多规则分数累加，结果依赖阈值配置
- **黑盒性**：`protection_score=0.8`、`threshold=2.25` 在哪些情况下触发 PASS，无法直接读懂
- GUA-022 根因：多个 0.x 的小分数加起来超过 2.25，但没有 lalala "队友剩牌≤4"那种精确边界控制

**lalala 的手牌结构分析**（`Single():49-68`）：
```python
sorted_cards, bomb_info = combine_handcards(handcards, rank_card[-1], card_val)
single_member = sorted_cards["Single"]
bomb_member = []
for bomb in sorted_cards["Bomb"]: bomb_member += bomb
# 精确识别成员类型，避免破坏组合
for action in single_actionList:
    if action[2][0] not in bomb_member: ...
```
在 `Single()` 内部直接调用 `combine_handcards()`，识别后立即在选牌逻辑中使用。

**M1 的手牌结构分析**：提取为 `HandStructureAnalyzer`，但各 Handler 调用的是 `PrioritySystem.select()` ——通用评分里没有专门针对"管单张时不能破坏 bomb_member"的硬约束。

---

### 10.3 为什么 lalala 的路径更优

**可预测性**：lalala 的每条规则都能在 10 行以内看懂；M1 的 `should_protect()` 依赖 5 个 rule 的分数积累，加上动态 threshold，没有人能说清楚第 3 局为什么 PASS 了。

**调参精度**：lalala 改"队友剩牌≤4，只出大1"只需要改一个数字；M1 改队友保护强度需要调 5 个 rule 的权重 + threshold，且改动效果不可预测。

**调用时机**：lalala 的规则就在决策路径上，没有"组件 A → 组件 B → 组件 C"的调用链；M1 的规则经过 Handler → PrioritySystem → 候选过滤 → 评分，链条长且耦合松。

**可测试性**：lalala 每个方法可以独立跑单元测试；M1 的 `should_protect()` 依赖完整的 `message + context`，测试用例构造复杂。

---

### 10.4 M1 的架构问题

M1 试图把"硬编码规则"变成"可配置的组件"，但这个抽象层次不对：

| lalala 做得好的 | M1 对应的抽象错位 |
|----------------|----------------|
| 精确边界条件 | `protection_score >= threshold` 模糊了边界 |
| 牌型专用逻辑 | `PrioritySystem` 通用评分，丢失牌型语义 |
| 规则内嵌在决策路径 | `HandStructureAnalyzer` 组件化后调用时机丢失 |
| PASS次数→策略降级 | M1 被动出牌完全没有 PASS 次数参与决策 |

M1 的"共享组件"架构适合数据驱动的 V 系列（训练出来的权重），但不适合规则驱动的 M1——把精确的 if-then 规则抽象成可配置组件，本身就是信息损失。

---

### 10.5 如何追赶

**短期（不改架构）**：
1. 补齐 §9.1 完全缺失的规则——在 `MidEarlyPassiveHandler` 内实现"队友剩牌≤4，只出大1"的精确逻辑
2. 恢复 `OpeningActiveHandler` 的一手出完检查
3. PASS 次数引入被动出牌决策（参考 `Single():174-193`）

**中期（微调架构）**：
4. 在 `SinglePassiveHandler`（若存在）中内嵌 `combine_handcards()` 的等价逻辑，类似 lalala
5. `should_protect()` 替换为精确条件分支，去掉分数积累机制

**长期（架构重构）**：
6. 参考 lalala 的"一牌型一方法"，为 M1 的每种被动牌型（单张/对子/三张/三带二/顺子）实现专用 Handler，而不是用 `PrioritySystem` 通用评分
7. `strategy_engine.py` 中的 5 个 rule 抽象，可以折叠回 Handler 内部，成为精确的条件分支

**核心原则**：M1 的模块化架构对 V 系列有意义，对硬编码规则的 M1 是过度设计。规则越精确，越不应该抽象成组件。

1. **队友保护过于激进**：`should_protect()` 阈值机制导致频繁让牌丢权；lalala 用精确条件（队友剩牌≤4时只出大1）替代了阈值积累
2. **开局主动缺少一手出完检查**：M1 `OpeningActiveHandler` 注掉了 `_check_one_hand_complete()`（`phase_handlers.py:73`）；残局阶段 Handler 不受影响
3. **单张管牌缺少手牌结构分析**：lalala `Single()` 精确识别成员类型避免破坏组合，M1 用通用组件但针对性不足
4. **牌型分发 vs 通用评分**：lalala 的 if-elif 链更直白可调，M1 的评分函数黑盒难调
5. **PASS次数未参与被动出牌决策**：lalala `Single()` 用 `pass_num` 动态降级（special→bomb），M1 的被动出牌无此机制
6. **主动出牌下家剩1张处理链不完整**：M1 仅降低单张优先级，缺少 lalala 的"拆对子/出多张"逻辑
