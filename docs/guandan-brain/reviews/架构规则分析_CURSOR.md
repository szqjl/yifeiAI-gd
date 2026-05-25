# Cursor 评审：架构规则分析.md

> 评审时间：2026-05-21
> 评审依据：必须逐个读指令里列出的7个文件

---

## 一、调用链层数验证

### 1.1 lalala "3层"说法验证

**文档声称**：`rule_parse() ← 唯一入口（L1354）→ passive() → 具体方法`，调用深度3层

**原文验证**：

- `action.py:1354` - `rule_parse()`确实是唯一入口
- `action.py:1358` - 判断`msg["greaterPos"] != mypos`进入被动
- `action.py:1369-1370` - 调用`self.passive(...)`
- `action.py:964` - `def passive(...)` 定义
- `action.py:981-986` - 关键：`if numofmy <= 10: actIndex = one_hand(...)` 精确残局拦截
- `action.py:988-1019` - 按`curAction[0]`分发到Single/Pair/Trips等

**判定：✅ 准确**
- 3层：`rule_parse()` → `passive()` / `active()` → `Single()`/`Pair()`等
- L981-986的`one_hand()`拦截是文档未提及的第4层（但属于条件分支，不是固定路径）

---

### 1.2 M1 从 `decide()` 到出牌实际层数

**文档声称**：调用深度5层+（decide → Router → Handler → PrioritySystem → should_protect）

**原文验证**：

| 层次 | 文件位置 | 调用链 |
|------|----------|--------|
| 1 | `rule_based_decision_engine_m1.py:158` | `decide()` |
| 2 | `rule_based_decision_engine_m1.py:195` | `self.router.route(message)` |
| 3 | `stage_router.py:493` | `handler.handle(message)` |
| 4 | `phase_handlers.py:50` (OpeningActiveHandler) | `handle()` → `_build_structure_strategy()` → `self.priority_system.select()` |
| 5 | `strategy_engine.py:425` | `PrioritySystem.select()` |
| 6 | `strategy_engine.py:431` | `_calculate_base_scores()` |
| 7 | `strategy_engine.py:467` | 分数计算 |

**判定：✅ 基本准确，但实际上是7层而非5层+**
- 如果算上`should_protect()`的调用（strategy_engine.py:196），实际是8层
- 文档保守地说"5层+"是合理的，因为PrioritySystem内部调用不一定是必经路径

---

## 二、分数积累 vs 精确 if-then 验证

### 2.1 lalala 源码里有没有"分数积累"？

**验证结果：主要使用精确 if-then，但有部分近似逻辑**

**精确条件判断（action.py）**：
```python
# L81-85
if numofnext <= 4 or (numofpre <= 3 and numofpre>=1):
    if (myPos+2)%4 == greaterPos and curVal >= max_val:
        return 0
```
→ 精确整数比较

**精确残局匹配（utils.py:369-411）**：
```python
def one_hand(numofmy,numofnext,actionList,...):
    if numofmy == len(action[2]):  # L392
        return tag
```
→ 精确匹配，不是有牌率

**choose_bomb()（utils.py:297-367）**：
```python
bomb_res.append((index, new_card_val[action[1]] + (l - 4) * 16+prior))
```
→ 有分数计算，但这是在炸弹选择时的优先级排序，不是"分数积累决策"

**判定：✅ 文档准确**
- lalala确实主要用精确if-then
- "分数积累"主要存在于M1的`should_protect()`，lalala无此机制

---

### 2.2 M1 的 `should_protect()` 用的是什么机制？

**文档声称**：`should_protect()` 用5条规则分数累加（L467-540）

**原文验证**：
- `strategy_engine.py:196-211` - `should_protect()` 方法
- L198-206：遍历`self.protection_rules`（5个规则），累加score
- L209：动态阈值 `threshold = self._get_dynamic_threshold()`
- L211：`return protection_score >= threshold`

```python
protection_score = 0.0
for rule in self.protection_rules:
    score = rule.evaluate(message, context)
    protection_score += score
return protection_score >= threshold
```

**判定：✅ 准确**

5个规则定义在 L188-194：
1. `HighValueProtectionRule()`
2. `LowCardCountProtectionRule()`
3. `CriticalStageProtectionRule()`
4. `ThreatAssessmentRule()`
5. `OpponentSprintWhenTeammateLeadsRule()` (GUA-022)

---

## 三、lalala 三件套验证

### 3.1 `choose_bomb()` 验证

**文档声称**：存在choose_bomb()最小代价算法

**原文验证**：
- `utils.py:297` - `def choose_bomb(...)`
- L297-367：完整实现，含级牌加成、同花顺特殊处理
- action.py多处调用：L101, L168, L173, L247等

**判定：✅ 准确**

---

### 3.2 `one_hand()` 验证

**文档声称**：被动处理中 `numofmy≤10` 时优先调用 one_hand() 精确残局匹配

**原文验证**：
- `utils.py:369` - `def one_hand(...)`
- `action.py:981-986`：
```python
numofmy = numofplayers[myPos]
if numofmy <= 10:
    actIndex = one_hand(numofmy,numofnext,actionList,myPos,greaterPos,7,
             restcards,card_value_s2v,rank_card)
    if actIndex!=-1:
        return actIndex
```

**判定：✅ 准确**

---

### 3.3 `passive()` 入口残局拦截验证

**文档声称**：passive()是残局拦截入口

**原文验证**：
- `action.py:964` - `def passive(...)` 是被动出牌总入口
- L977-986 - curAction[0]=="PASS"特殊处理 + one_hand()残局拦截

**判定：✅ 准确**

---

## 四、"lalala 更优"结论验证

### 4.1 结论是否过于笼统？

**文档声称**：对硬编码规则引擎来说，lalala 的方式更优

**分析**：
- 文档确实指明了对"硬编码规则引擎"这个维度
- 但表格中（L100-107）列出了6个维度，有混淆"更优"语境之嫌

**问题1**：`调用链深度 3层 vs 5层+`——这是架构设计选择，不是非此即彼的优劣
**问题2**：L107注明"GUA-022 根因"——说明M1的问题有具体bug，不是一概而论

**判定：⚠️ 基本准确，但有绝对化倾向**
- 结论限定了"对硬编码规则引擎来说"，这是合理的
- 但"更优"的表述方式容易被解读为全面优于，而实际只是某些维度

---

## 五、P0 任务清单验证

### 5.1 P0任务是否有双CLI review出处？

**P0任务列表（L148-149）**：
1. P0：`combine_handcards` + `choose_bomb`
2. P0：context 补齐 `pass_num`/`numofnext`/`numofgreaterPos`

**验证结果**：
- 文档L148-149列出了P0任务，但没有引用"双CLI review"的出处
- 指令要求验证是否有"双CLI review"的出处

**问题**：文档中未找到"双CLI review"的具体引用位置
- opencode评审（L134-154）和cursor评审（L157-169）是同一次评审的两个视角，不是两个独立的CLI review

**判定：🔴 出处存疑**
- "双CLI review"说法在文档中无明确引用
- 建议补充引用来源或更正表述

---

## 六、错误与遗漏

### 6.1 发现的错误

| # | 问题 | 严重度 | 位置 |
|---|------|--------|------|
| 1 | 调用链层数：M1实际是7-8层，文档说"5层+"偏保守但可接受 | 低 | L40 |
| 2 | "双CLI review"无明确出处引用 | 中 | L148-149 |
| 3 | L107 "GUA-022 根因"标注位置不准确——根因是阈值参数问题，不是分数积累本身 | 中 | L107 |

### 6.2 遗漏

| # | 遗漏项 | 说明 |
|---|--------|------|
| 1 | lalala的`one_hand()`实际有条件分支（numofmy<=10），不是无条件拦截 | action.py:981 |
| 2 | M1的`should_protect()`有动态阈值机制（strategy_engine.py:231-246），不是固定2.25 | 文档未提及 |
| 3 | lalala的`choose_bomb()`有同花顺特殊处理（utils.py:357-361），M1无等价实现 | 文档L145有提及但不够明确 |

---

## 七、自评认真程度

**🔥🔥🔥🔥（非常认真）**

**验证方法**：
1. ✅ 逐个读取7个源文件
2. ✅ 每个验证点都有原文引用+行号
3. ✅ 发现3处需要澄清的问题
4. ⚠️ 部分验证受文件截断影响（phase_handlers.py 2773行，action.py 1411行）

**置信度**：中高
- 核心验证点（调用链、三件套、should_protect机制）已核实
- 部分细节（如各Handler的完整handle逻辑）因代码量大仅做抽样验证

---

## 八、综合结论

| 验证项 | 判定 | 说明 |
|--------|------|------|
| lalala 3层调用链 | ✅ 准确 | rule_parse → passive/active → Single/Pair等 |
| M1 5层+调用链 | ✅ 基本准确 | 实际7-8层，保守说5层+可接受 |
| lalala精确if-then | ✅ 准确 | 确认无分数积累机制 |
| should_protect()分数累加 | ✅ 准确 | 5规则累加+动态阈值 |
| 三件套完整性 | ✅ 准确 | choose_bomb/one_hand/passive均存在 |
| "更优"结论 | ⚠️ 基本准确 | 有绝对化倾向，但限定了语境 |
| P0双CLI review出处 | 🔴 存疑 | 未找到明确引用 |

**建议**：文档质量较高，主要需澄清"双CLI review"的出处引用，以及补充M1动态阈值机制。  
