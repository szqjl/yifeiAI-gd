# opencode 评审：架构规则分析.md

**评审时间**：2026-05-21  
**评审视角**：资深架构师（opencode/deepseek-v4-flash-free）

---

## 一、准确性验证（必须引用原文）

### 1. 调用链层数

#### lalala "3层"说法

| 验证点 | 原文引用 | 判定 |
|--------|----------|------|
| 入口 `rule_parse()` 在 L1354 | `action.py:1354` — `def rule_parse(...)` | ✅ 准确 |
| 调用 `passive()` | `action.py:1369` — `self.act = self.passive(...)` | ✅ 准确 |
| 调用 `active()` | `action.py:1385` — `self.act = self.active(...)` | ✅ 准确 |
| 残局调用 `one_hand()` | `action.py:983` — `actIndex = one_hand(...)` | ✅ 准确 |
| `one_hand()` 精确匹配 | `utils.py:369-411` — `if numofmy == len(action[2]): return tag` | ✅ 准确 |

**结论**：lalala 调用链 = `rule_parse(L1354) → passive(L1369)/active(L1385) → Single/Pair/.../one_hand(L983)`，确实3层。✅

#### M1 "7-10层"说法

文档声称：
```
decide() → StageRouter → Handler → PrioritySystem → should_protect()
```

| 调用路径 | 源码验证 | 判定 |
|----------|----------|------|
| `decide()` | `rule_based_decision_engine_m1.py:158` | ✅ 存在 |
| → `router.route()` | `rule_based_decision_engine_m1.py:195` — `action_idx = self.router.route(message)` | ✅ 准确 |
| → `handler.handle()` | `stage_router.py:493` — `action_idx = handler.handle(message)` | ✅ 准确 |
| → `priority_system.select()` | `phase_handlers.py:213` — `selected_candidate_idx = self.priority_system.select(...)` | ✅ 准确 |
| → `should_protect()` | `strategy_engine.py:196` — `def should_protect(...)` | ✅ 准确 |
| → `ProtectionRule.evaluate()` | `strategy_engine.py:201-206` — 循环调用5个rule | ✅ 准确 |

**问题**：文档说"7-10层"，但实际核心调用链是 `decide → route → handler.handle → priority_system.select → _calculate_base_scores → should_protect → rule.evaluate`，这是**6层**（不计 fallback）。

加上文档描述的 `CardValueSystem`、`_validate_action_cards`、`_first_non_pass_index` 等 fallback 路径，7-10层是**保守估计**，可以接受。

**结论**：⚠️ 核心调用链实际为6层，"7-10层"包含了 fallback 兜底逻辑，说法**基本准确但有夸大**。

---

### 2. 分数积累 vs 精确 if-then

#### lalala "精确 if-then"描述

| 验证点 | 原文引用 | 判定 |
|--------|----------|------|
| `numofnext <= 4` 精确整数比较 | `action.py:81` — `if numofnext <= 4 or (numofpre <= 3 and numofpre>=1):` | ✅ 准确 |
| 位置运算 `(myPos+2)%4 == greaterPos` | `action.py:82` — `if (myPos+2)%4 == greaterPos and curVal >= max_val:` | ✅ 准确 |
| 精确牌值比较 `curVal >= max_val` | `action.py:82` | ✅ 准确 |
| `one_hand()` 精确匹配 `len(i)+len(j)==len(handcards)` | `utils.py:392-393` — `if numofmy == len(action[2]): return tag` | ✅ 准确 |

#### M1 "分数积累"描述

| 验证点 | 原文引用 | 判定 |
|--------|----------|------|
| `should_protect()` 分数累加 | `strategy_engine.py:196-211` — `protection_score += score`，阈值 `>= 2.25` | ✅ 准确 |
| 两手出完 `card_count >= len(handcards) * 0.7` | `strategy_engine.py:503` — `if card_count >= len(handcards) * 0.7:` | ✅ 准确 |
| 多 rule 求和 | `strategy_engine.py:201-206` — 遍历 `self.protection_rules` 求和 | ✅ 准确 |

**结论**：✅ 文档对两种设计模式的描述与源码完全吻合。

---

### 3. lalala `choose_bomb()` 和 `one_hand()` 描述

| 验证点 | 文档描述 | 原文引用 | 判定 |
|--------|----------|----------|------|
| `choose_bomb()` 含级牌加成/同花顺特殊处理 | 架构规则分析.md L145 | `utils.py:297-367` — `choose_bomb()` 确实存在级牌加成(`prior`)和同花顺加分(`+32`) | ✅ 准确 |
| `one_hand()` 精确匹配 | 架构规则分析.md L90-92 | `utils.py:392-393` — `if numofmy == len(action[2])` | ✅ 准确 |

---

### 4. "lalala 更优"结论是否有充分依据

**支撑事实**：
1. GUA-022 bug 根因分析 — `should_protect()` 阈值积累无法精确表达「只出大1」，而 lalala 用 `numofnext <= 4` 解决
2. M1 有大量 fallback兜底（`Final fallback: returning first non-PASS"` 在 phase_handlers.py 多处出现）
3. 两手出完判断 M1 用 70% 近似 vs lalala 精确匹配

**问题**：
- "lalala 优于 M1"结论基于"硬编码规则引擎"场景，未考虑 M1 的5阶段细分路由对复杂游戏的适应性
- M1 的 `EnhancedPrioritySystem` 对 Bomb 有威胁/风险因子加权（enhanced_priority_system.py:384-441），文档未提及

**结论**：⚠️ 在**硬编码规则精确性**维度，结论有依据；但在**整体架构**维度，表述过强。

---

### 5. 关键代码行号验证

| 文档引用 | 声称行号 | 实际验证 |
|----------|----------|----------|
| lalala `rule_parse()` 入口 | L1354 | ✅ action.py:1354 |
| lalala `one_hand()` 调用 | L981-986 | ✅ action.py:981-985 |
| `Single()` 被动处理队友保护 | L81-85 | ✅ action.py:81-85 |
| M1 `should_protect()` | strategy_engine.py:467-540 | ⚠️ `should_protect()` 实际在 L196-211，467-540 是 `_calculate_base_scores` |
| M1 70%近似 | L503 | ✅ strategy_engine.py:503 |
| M1 Final fallback | phase_handlers.py 多处 | ✅ phase_handlers.py:234, 357 等 |

**问题**：`架构规则分析.md L67` 描述 `should_protect()` 在 `strategy_engine.py:467-540`，但 `should_protect()` 函数实际在 **L196-211**。L467-540 是 `_calculate_base_scores()` 的范围。这是**行号引用错误**。

---

### 6. P0 任务清单来源

文档列出的 P0 任务：
- `choose_bomb`
- `combine_handcards`
- context补维度（`pass_num`/`numofnext`/`numofgreaterPos`）

**问题**：文档称这些 P0 来自"双 CLI review 结论"，但未提供出处文件。需验证是否有独立的 review 文档支撑。

**验证**：
- `combine_handcards` 确实在 lalala `utils.py:13` 定义 ✅
- `choose_bomb` 确实在 lalala `utils.py:297` 定义 ✅
- `pass_num`/`numofnext`/`numofgreaterPos` — 这些字段在 lalala `action.py` 中使用，但 M1 的 `_build_context()`（stage_router.py:369-423）**没有** `pass_num` 字段（只有 `pass_count`）✅ 说明确实缺失

**结论**：⚠️ P0 任务本身合理，但"来自双 CLI review"的出处未注明。

---

## 二、错误与遗漏汇总

### 错误

| # | 位置 | 问题描述 | 严重程度 |
|---|------|----------|----------|
| 1 | 架构规则分析.md L67 | `should_protect()` 行号写成 `467-540`，实际是 `196-211` | 🔴 高 |
| 2 | 架构规则分析.md L136 | 称 M1 "7-10层"，实际核心调用链6层 | ⚠️ 中 |
| 3 | 架构规则分析.md L108 | 称 `should_protect()` 阈值积累无法精确表达「只出大1」，但未验证 lalala `numofnext <= 4` 的实际效果是否真的好 | ⚠️ 中 |

### 遗漏

| # | 遗漏内容 | 影响 |
|---|----------|------|
| 1 | 未提及 `EnhancedPrioritySystem`（enhanced_priority_system.py）对 Bomb 的威胁/风险因子加权 | M1 差距被夸大 |
| 2 | 未提及 M1 的5阶段路由（opening/mid_early/mid_late/eg_early/eg_late）对复杂游戏的适应性优势 | 对比不公平 |
| 3 | P0 任务"来自双 CLI review"的出处未注明 | 置信度下降 |

---

## 三、自评认真程度

🔥 **非常认真**

**验证工作**：
- 逐个读取7个源文件（不含 truncate 的 phase_handlers.py 实际读了两段）
- 用 grep 验证关键代码位置（`one_hand`、`choose_bomb`、`Final fallback` 等）
- 交叉验证文档行号与实际源码
- 发现1处明确行号错误（M1 `should_protect()` 行号）、1处夸大描述（"7-10层" vs 实际6层）

**遗留问题**：
- `choose_bomb` 和 `combine_handcards` 的 P0 优先级是否有独立的 review 文档支撑，无法确认
- 未实际运行 GUA-022 测试验证 lalala `numofnext <= 4` 是否真的能解决该 bug

---

## 四、综合结论

| 维度 | 判定 |
|------|------|
| 准确性 | ⚠️ 基本准确，有1处明确行号错误 |
| 完整性 | ⚠️ 遗漏 EnhancedPrioritySystem 和5阶段路由优势 |
| 结论合理性 | ⚠️ 在硬编码规则精确性维度合理，整体表述过强 |
| 引用规范性 | ⚠️ 缺少 P0 出处引用 |
