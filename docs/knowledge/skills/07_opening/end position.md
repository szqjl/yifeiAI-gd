# 残局预处理模块设计

> **文档别名**：**残局管线设计**（V7 Endgame Pipeline Design）
> **Wiki**：已摄入 → [[end-position-design-summary]]、[[endgame-pipeline]]（真源路径见 `sources` 字段）
> **模块名**：`EndgamePreprocessor`
> **落盘位置**：`src/v/nn/endgame/endgame_preprocessor.py`
> **注入点**：V7 `decide()` 入口，`_inject_numofplayers` 之后，GUA-075 主路径之前
> **设计日期**：2025-06-21（管线订正 2026-06-01：MemoryTracker 须在 ② 之前）

---

> **残局管线使命**：四人中任何一人进入残局（≤10 张）后，让 V7 知道**该炸谁、该封谁、该送谁、什么时候该自己走**。

## 一、核心设计决策

### 1.1 「对手」定义：仅敌方两家，不含队友

**「对手」= 敌方两家** = `(myPos+1)%4`（下家）+ `(myPos+3)%4`（上家）。队友（`(myPos+2)%4`）不是对手，不纳入封锁对象。

残局管线按四家角色分别处理：

| 角色 | pos 公式 | 进入 ≤10 时的策略 |
|------|----------|-------------------|
| **敌方对手** | `(myPos+1)%4`, `(myPos+3)%4` | **封锁**：查 `endgame_rule` + `BAOSHU_RULE`，注入 `banned_types` / `baoshu.never_play` |
| **队友** | `(myPos+2)%4` | **助攻**：创造机会让队友走（送牌/喂牌/帮压），不封锁 |
| **自己** | `myPos` | **能走直接走**（两手整牌 → 冲刺），走不了时助攻队友 |

| 敌方剩牌 | 判定 | V7 对应逻辑 |
|----------|------|------------|
| ≤10 | 残局警戒区 → 封锁激活 | 与自己手牌 ≤10 触发中局重组对齐 |
| ≤4 | 紧急/报牌区 → BAOSHU 封锁 | V7 已有 `opp_in_danger(≤4)` 急眼逻辑 |
| 1 | 听牌封锁 → 禁单张 | — |

### 1.2 预处理器不做什么

| 不做 | 原因 |
|------|------|
| 不修改 `actionList` | 纯上下文注入，`banned_types` 硬排除由 `decide()` 在预处理器之后、Guard 之前执行（方案 A） |
| 不直接过滤/选中 action | 预处理器只标记"该做什么/不该做什么"，不操作 actionList |
| 不覆盖已有 Guard | 标记上下文，Guard 自行读取；R11 在残局激活时退让 |
| **不新建剩牌跟踪** | V7 已有 `game_state["numofplayers"]`（GUA-065），直接复用 |

### 1.3 注入的 `_endgame_context` 结构

```python
game_state["_endgame_context"] = {
    "is_active": bool,          # 是否有任何玩家 ≤10 张（触发残局管线）
    "numofplayers": [int,...],  # 4家剩牌快照
    "my_pos": int,              # 自己位置
    "enemies": {                # 敌方两家（仅进入警戒区 ≤10 时填充）
        opp_pos: {
            "remaining": int,           # 剩牌数
            "danger_level": str,        # 极高/高/中高/中/低
            "recommended_types": [...], # V7牌型名列表（如 Single, Pair, ThreeWithTwo…）
            "banned_types": [...],      # V7牌型名列表
            "baoshu": {                 # 仅 ≤4 张时有值
                "likely_hand": str,     # 可能牌型描述
                "block_with": [...],    # 封锁应出牌型（V7名）
                "never_play": [...],    # 禁出牌型（V7名）
            }
        }
    },
    "teammate": {               # 队友（仅 ≤10 张时填充，助攻用）
        "remaining": int,       # 剩牌数
        "is_close": bool,       # 队友接近头游（≤4）
        "assist_prefer": [...], # 推荐送什么牌型帮队友（如喂对子/三不带）
    },
    "self": {                   # 自己残局状态
        "remaining": int,       # 自己剩牌数
        "has_two_clean_hands": bool,  # 两手整牌可冲刺
        "has_bomb": bool,       # 是否有炸弹可用
        "should_sprint": bool,  # 应该抢头游
    },
}
```

### 1.4 文档名 → V7 牌型枚举映射

| 文档中文名 | V7 `ACTION_TYPE_*` 枚举 |
|-----------|------------------------|
| 单张 / 小单 / 大单张 / 最大单张 | `Single` |
| 对子 | `Pair` |
| 三张 / 三同张 / 三不带 | `Trips` |
| 3带2 / 三带二 | `ThreeWithTwo` |
| 顺子 / 长顺子 | `Straight` |
| 钢板 | `TwoTrips` |
| 连对 / 三连对 | `ThreePair` |
| 炸弹 | `Bomb` / `StraightFlush` |
| 长组合牌 | `Straight` + `ThreePair` + `TwoTrips` |

### 1.5 设计问题四：endgame_rule 推荐/禁止牌型 → actionList 映射

> **原问题**：文档返回的是抽象牌型名（"大单张"、"三带二"、"钢板"），但 V7 的 actionList 是具体的 `[['S2'], ['H3','D3'], ...]` 列表。是否需要一个"牌型名 → actionList 过滤"的映射层？还是复用已有工具？

**答案：不需要新建映射层。** V7 已有完备的工具链将抽象牌型名映射到具体 action，零新文件开销。

#### 子问题 1：怎么写映射层？

**不写。** 直接复用 V7 现有工具，`endgame_rule` 的推荐/禁止牌型按两步链路即可命中 actionList 中的具体牌：

```
endgame_rule["大单张"] → _map_types(["大单张"]) → ["Single"] → actionList 中 get_action_type==Single 且 value≥K 的 action
endgame_rule["三带二"] → _map_types(["三带二"]) → ["ThreeWithTwo"] → actionList 中 get_action_type==ThreeWithTwo 的 action
endgame_rule["钢板"]   → _map_types(["钢板"])   → ["TwoTrips"]     → actionList 中 get_action_type==TwoTrips 的 action
endgame_rule["长组合牌"]→ _map_types(["长组合牌"])→["Straight","ThreePair","TwoTrips"] → actionList 中任一匹配
```

**`_map_types` 桥接方法**（预处理器内部，~15 行）：

```python
_SHAPE_NAME_TO_ACTION_TYPES = {
    "单张":      ["Single"],      "大单张":  ["Single"],   # 大单张需进一步 check value≥K
    "最大单张":   ["Single"],       "小单":    ["Single"],   # 小单张需 check value<K
    "对子":      ["Pair"],
    "三张":      ["Trips"],        "三同张":  ["Trips"],    "三不带":   ["Trips"],
    "3带2":      ["ThreeWithTwo"], "三带二":  ["ThreeWithTwo"],
    "顺子":      ["Straight"],     "长顺子":  ["Straight"],
    "钢板":      ["TwoTrips"],
    "连对":      ["ThreePair"],    "三连对":  ["ThreePair"],
    "长组合牌":   ["Straight", "ThreePair", "TwoTrips"],
    "炸弹":      ["Bomb", "StraightFlush"],
    "零散单":    ["Single"],        # 泛指散牌单张
    "零散单、对子、三不带": ["Single", "Pair", "Trips"],
    "所有普通单张": ["Single"],      # 含大小单张全部
}

def _map_types(self, chinese_names: list) -> list:
    """中文牌型名 → V7 ACTION_TYPE 枚举名列表"""
    result = []
    for name in chinese_names:
        result.extend(self._SHAPE_NAME_TO_ACTION_TYPES.get(name, []))
    return list(set(result))  # 去重
```

#### 子问题 2：是否复用 grouptype_map 或 card_mask？

**复用 `get_action_type(act)`，不走 grouptype_map / card_mask。**

| 工具 | 位置 | 输入 | 输出 | 用途 |
|------|------|------|------|------|
| `get_action_type(act)` | `v7_guards.py` | `[['S2']]` / `['H3','D3']` | `"Single"` / `"Pair"` / ... | 将 actionList 中每条 act 分类为牌型枚举 |
| `get_card_value(card, cur_rank)` | `v7_guards.py` | `"SA"` | `12`（A=12, K=11, SB=13, HR=14） | 单张的具体强度 |
| `CARD_RANK_ORDER` | `v7_guards.py` | `"A"` | `12` | rank → 数值映射（2=0 … A=12） |

> **为什么不走 grouptype_map？** grouptype_map 描述的是**手牌**的组牌方案（"9999 是炸"），而 actionList 是**本轮可选出牌**（"出 ['S2'] 是单张"）。两个域不同，`get_action_type(act)` 才是 actionList 的正确分类器。

#### 子问题 3：大单张需要全局牌记忆 —— 是否复用 MemoryTracker？

**是，复用 MemoryTracker + `_count_remaining_suppressors`。**

「大单张」= K 及以上单张。`get_card_value` 给出的是静态牌值（不随牌局剩余变化），但在残局场景下"最大单张"还受全局牌记忆影响：

- 残局预处理器调用 `_count_remaining_suppressors(tracker, "K", cur_rank)` 检查 K 还剩余几张
- 当 K 以上几乎打光时，"大单张"阈值做 K→Q→J 三级阶梯降级
- 大单张判定：`get_action_type==Single 且 val ≥ 当前动态阈值`
- 小单张判定：`get_action_type==Single 且 val < CARD_RANK_ORDER["K"]`

**完整过滤链路**（以推荐"大单张"为例）：
1. `_map_types(["大单张"])` → `["Single"]`
2. 遍历 actionList，`get_action_type(act)==Single` 且排除小单张
3. 用 `_resolve_big_single_threshold(tracker, cur_rank)` 取动态阈值，过滤不够大的单张
4. 返回符合条件的 action 列表

### 1.6 设计问题五：残局规则 vs Guard 的优先级

> **原问题**：对手剩 1 张，文档说"禁出所有单张"，但 R08"送队友"可能推荐出最小单张——残局封锁和送队友冲突时谁优先？R03"被动不PASS"强制出牌，但残局规则说"此时不应出牌"——残局是最高优先级还是平等竞争？

**答案：残局管线为最高优先级，凌驾于所有 Guard 之上。**

| 冲突场景 | Guard 原行为 | 残局规则 | 裁决 |
|----------|-------------|---------|------|
| 对手剩 1 张 vs R08 送队友 | R08 推荐出最小单张喂队友 | BAOSHU_RULE[1]：禁出所有单张 | **残局胜**：锁定 R08，不出单张 |
| 对手剩 1 张 vs R03 被动不PASS | R03 强制出牌压过 | 残局推荐：三带二/钢板锁死 | **残局胜**：R03 退让，按残局推荐走 |
| 对手剩 2 张 vs R02 顺子优先 | R02 推荐出长顺子 | endgame_rule[2]：禁对子 | **残局胜**：R02 退让，不出对子 |
| 对手 ≤10 张 vs R11 抑制炸弹 | R11 建议等待不炸 | 两手整牌 → 冲刺炸 | **残局胜**：R11 退让，残局管线决策 |

**优先级链**：
```
残局管线（banned_types 硬禁止 / recommended_types 硬推荐）
  > GUA-075 推荐引擎（在残局约束内排序加权）
  > R01-R14 Guard（残局激活时退让，仅做合法性兜底）
  > heuristic 回退
```

**实现方式**：不是靠优先级数字排序，而是靠 **`banned_types` 硬排除**。`decide()` 在预处理器注入 `_endgame_context` 之后、Guard 链之前，读取 `enemies[*].banned_types` 直接过滤 `actionList`——被禁牌型一刀切掉，下游 Guard / GUA-075 根本看不到它们。同理，`baoshu.never_play` 是更严的子集封锁。

### 1.7 设计问题七：「对手」定义与队友/自己的残局角色

> **原问题**：残局管线中「对手」指谁？队友进入残局区时是否也纳入封锁？自己剩牌情况如何影响残局决策？

**答案：对手 = 敌方两家（pos+1, pos+3），队友（pos+2）走助攻管线，自己走冲刺/助攻判断。**

#### 子问题 1：敌方对手 → 封锁管线

敌方两家 ≤10 张时，走 `endgame_rule` + `BAOSHU_RULE` 封锁管线。规则保持不变——`banned_types` / `baoshu.never_play` 只对敌方注入，不对队友生效。

```python
ENEMY_POSITIONS = [(myPos + 1) % 4, (myPos + 3) % 4]
```

#### 子问题 2：队友进入残局 → 助攻管线

队友 ≤10 张时，策略反转——不是封锁而是助攻：

| 队友剩牌 | 最可能手牌 | 投喂策略 |
|:--:|------|------|
| **1 张** | 单张 | 直接投喂 1 张（单张），让队友垫走 |
| **2 张** | 对子 | 投喂对子，让队友对子走完 |
| **3 张** | 三同张 | **优先投喂三张**：若队友 PASS → 降级投喂 2 张（对子）→ 若再 PASS → 投喂 1 张（单张） |
| **4 张** | 炸弹 或 两个对子 | **优先投喂对子**：对子是最安全的投喂（是两个对子则接走，是炸弹则至少消耗一张） |
| **5 张** | 顺子 或 三带二 | 投喂顺子 / 三带二 |
| 6-10 张 | — | 投喂对子优先，正常助攻，不必强喂 |

```python
def _assist_prefer_for(remaining: int) -> list:
    """队友剩 N 张时，精确投喂牌型（按优先序）"""
    if remaining == 1:      return ["Single"]
    elif remaining == 2:    return ["Pair"]
    elif remaining == 3:    return ["Trips", "Pair", "Single"]   # 三张→降级对子→降级单张
    elif remaining == 4:    return ["Pair"]                       # 优先对子（防炸弹/两个对子）
    elif remaining == 5:    return ["Straight", "ThreeWithTwo"]   # 顺子/三带二
    elif remaining <= 10:   return ["Pair"]                       # 6-10 对子优先
    else:                   return []
```

#### 子问题 3：自己残局 → 冲刺优先，走不了助攻

自己 ≤10 张时按以下优先级：

| 条件 | 策略 | 说明 |
|------|------|------|
| 两手整牌 + 有炸弹 | **直接冲刺抢头游** | Q1 最高优先级，出最大整炸 |
| 两手整牌，无炸弹但有顺序 | **走牌路线** | 按顺序出，不停留 |
| 非两手整牌 | **不强行走** | 转助攻队友，封锁敌人 |
| 无论何种情况 | **不走时助攻队友** | 自己能走就走，走不了帮队友 |

```python
def _should_sprint(game_state: dict) -> bool:
    """自己是否应该冲刺抢头游"""
    return _has_two_clean_hands(game_state) and _has_bomb(game_state)
```

### 1.8 设计问题八：banned_types 硬排除的具体实现位置

> **原问题**：文档说"在 Guard 链最前端做硬过滤"，但没有指定具体落点。方案 A（`decide()` 中一刀切）、方案 B（新增 R15 Guard）、方案 C（各 Guard 自行读取），选哪个？

**答案：选方案 A，`decide()` 中预处理器之后、Guard 之前一刀切。**

#### 为什么方案 A

| 方案 | 实现位置 | 结论 |
|------|---------|------|
| **A** | `decide()` 中，预处理器之后、Guard 之前过滤 `actionList` | ✅ **采纳** |
| B | 新增专用 Guard（R15 残局过滤器） | ❌ `banned_types` 是硬排除不是软加权，Guard 无意义 |
| C | 各 Guard 自行读取 `banned_types` | ❌ 分散易遗漏 |

方案 A 的核心优势：
- `banned_types` 是**硬排除**（永不出），放在 Guard 链里意义不大——Guard 是"举荐/拦截"逻辑
- 一刀切后下游 Guard 和 GUA-075 根本看不到被禁牌型，不会出现"某 Guard 推荐了 banned 牌型，另一个 Guard 拦截"的冲突
- 代码位置明确，就是一个 `actionList = [a for a in actionList if get_action_type(a) not in banned_set]`

#### 与 is_active 触发面的关系

`is_active` 由任何一家 ≤10 张触发，但 `banned_types` 硬排除**仅作用于敌方**：

```python
# decide() 中，预处理器之后
if game_state["_endgame_context"]["is_active"]:
    # 收集所有敌人的 banned_types + baoshu.never_play
    banned_set = set()
    for enemy_ctx in game_state["_endgame_context"]["enemies"].values():
        remaining = enemy_ctx["remaining"]
        banned_set.update(enemy_ctx.get("banned_types", []))
        if "baoshu" in enemy_ctx:
            # baoshu.never_play 也经过牌数过滤（>N 张的牌型不写入）
            banned_set.update(enemy_ctx["baoshu"].get("never_play", []))
    if banned_set:
        actionList = [a for a in actionList if get_action_type(a) not in banned_set]
```

当 `is_active` 由自己或队友 ≤10 张触发（敌方均 >10 张）时，`enemies` 为空 → `banned_set` 为空 → `actionList` 不变 → 走冲刺/助攻路径。

### 1.9 设计问题九：banned_types 硬排除后 actionList 为空怎么办

> **原问题**：对手剩 1 张 → 禁所有单张。手上全单张+无炸弹，硬排除后 actionList 为空，主动方又不能 PASS，怎么办？

**答案：三级兜底，炸弹永不被禁，极限时打级牌以下最大单张。**

#### 为什么炸弹永不被禁

`BAOSHU_RULE` 中炸弹始终在 `block_with` 中，从不在 `never_play` 中。`endgame_rule` 的 `banned_types` 也不含 `Bomb` / `StraightFlush`。**banned_set 永不含炸弹**——有炸就能出，不会 empty。

#### 三级降级路径

```
decide() 中 banned_types 硬排除后:
  actionList 非空？
    ├─ Yes → 正常走 Q0~Q3
    └─ No  → 进入降级
             ↓
    L1: 检查是否有炸弹可用
      ├─ 有炸 → 出炸（走 Q3 should_bomb），炸永不被禁
      └─ 无炸 → L2
             ↓
    L2: 是否被动跟牌（greaterPos != myPos）？
      ├─ Yes → PASS（最安全兜底，不强制出牌送死）
      └─ No（主动方，必须出牌） → L3
             ↓
    L3: 放宽 banned_types，保留 baoshu.never_play 硬禁
      ├─ 回到原始 actionList
      ├─ 仅用 baoshu.never_play 硬排除（放松 endgame_rule 的 banned_types）
      ├─ 筛选级牌（curRank）以下的牌
      └─ 按牌值从大到小出（例：Q > J > T > 9 …）
```

#### L3 出牌逻辑

```python
def _l3_fallback(actionList, baoshu_never_play, cur_rank):
    """极限降级：无炸 + 主动方 + 全被禁 → 打级牌以下最大牌"""
    # 仅保留 baoshu.never_play 硬禁
    never_set = set(baoshu_never_play)
    candidates = [a for a in actionList if get_action_type(a) not in never_set]

    # 筛选级牌以下
    rank_value = CARD_RANK_ORDER[cur_rank]
    below_rank = [a for a in candidates
                  if all(get_card_value(c) < rank_value for c in a[0])]

    if below_rank:
        return sorted(below_rank, key=lambda a: get_card_value(a[0]), reverse=True)
    else:
        return candidates  # 没牌了，全出
```

#### 触发概率极低

L3 需同时满足：敌人报单 + 自己无炸 + 自己是主动方 + 手牌全单张。属极端边缘，走"最小损失"即可。

---

### 1.10 设计问题十：敌方两人同时进入残局 — 排序与冲突裁决

> **原问题**：下家剩 3 张 + 上家剩 8 张同时 ≤10。谁更危险？banned_types 取谁？recommended_types 冲突怎么办？

**答案：下家优先（位置 + 剩牌 + baoshu），banned_types 取并集，recommended 主目标优先但避所有禁令。**

#### 子问题 1：危险度排序（四级键）

```python
def _enemy_danger_key(enemy_pos, remaining, danger_level, has_baoshu):
    """危险度排序键：越小越危险"""
    # ① 剩牌数（越少越危险）
    # ② 位置：下家 > 上家（下家接你后面出手，上家有队友管）
    # ③ 是否有 baoshu
    # ④ danger_level 序数
    pos_score = 0 if enemy_pos == (myPos + 1) % 4 else 1  # 下家=0, 上家=1
    danger_map = {"极高": 0, "高": 1, "中高": 2, "中": 3, "低": 4}
    return (remaining, pos_score, 0 if has_baoshu else 1, danger_map.get(danger_level, 5))
```

| 排序键 | 说明 |
|--------|------|
| ① `remaining` | 剩牌越少越危险，报单 > 报双 > … |
| ② 位置 | **下家 > 上家**：下家紧接你后面出手，上家有队友（pos+2）管 |
| ③ `has_baoshu` | ≤4 有报牌逻辑，更危险 |
| ④ `danger_level` | 极高 > 高 > 中高 > 中 > 低 |

#### 子问题 2：banned_types 取并集

不能只看最危险敌人——次危险的也不能放。

```
下家 3 张 banned = [Trips]（三带二已被 _ACTION_TYPE_CARD_COUNT 过滤，5张>3张，不写入）
上家 8 张 banned = [Single, Pair, Trips]

banned_set = UNION = {Single, Pair, Trips}
```

#### 子问题 3：recommended_types 冲突裁决

优先满足主封锁目标（排序第一的敌人）的 `recommended`，但**必须在所有敌人的 `banned` 之外**。

```
主目标(下家3张) recommended = [Pair, Single(大)]
次目标(上家8张) recommended = [Straight]
banned_set = {Single, Pair, Trips}

→ 主目标推荐 [Pair, Single大] 全在 banned 中
→ 降级看次目标推荐 Straight，不在 banned 中 ✅
→ 出顺子
```

**冲突裁决链**：主目标 recommended → 过 banned_set 滤 → 有剩则出 / 无剩看次目标 → 再滤 → 仍无剩走 Q9 降级。

---

### 1.11 设计问题十一：手中只有被禁牌型该怎么办

> **原问题**：上家 8 张禁 `["小单", "对子", "三不带"]`，但自己手中只有单张、对子牌型了，全被禁，怎么办？

**答案：走 Q9 的 L3 降级——放宽禁令，仅保留 `baoshu.never_play` 硬禁，打级牌以下从大到小。**

#### 走法

```
手中只有 单张 + 对子 → banned_set = {Single, Pair, Trips}
→ 硬排后 actionList 为空
→ Q9 L1: 检查炸弹 → 无炸
→ Q9 L2: 是否被动跟牌？→ 若是，PASS；若否（主动方），进入 L3
→ L3: 仅保留 baoshu.never_play 硬禁（上家 8 张无报牌 → never_play 为空）
  → 恢复全部单张 + 对子
  → 打级牌以下从大到小
    例 curRank=2 → K > Q > J > T > 9 > … → 出级牌以下最大单张
```

#### 不存在死锁

L3 的设计目的就是应对这种情况——放宽禁令，保底出一张损失最小的牌。`baoshu.never_play` 是最后一道防线（敌人报牌时的致命牌型仍然禁），但 `endgame_rule` 的封锁在无牌可出时可以松绑。

---

### 1.12 设计问题十二：R11 在残局激活时怎么退让

> **原问题**：文档说"R11 在残局激活时退让"，但退让到什么程度？完全停摆 / 部分退让 / 仅调参？

**答案：先走"部分退让"，观察效果，效果不行再尝试完全退让或仅节流退让。**

#### 三种退让级别

| 级别 | R11 行为 | Q3 行为 | 当前 |
|:----:|----------|---------|:----:|
| 完全退让 | R11 不执行 | Q3 `should_bomb` 独揽炸决策 | 备选 |
| **部分退让** | R11 计算 `pass_num`/`curVal`/`numofgreaterPos`，产出 `should_bomb` 建议 | Q3 综合 R11 建议 + `endgame_rule.should_bomb` 最终裁决 | ✅ **当前** |
| 仅节流退让 | R11 正常跑，仅降低炸阈值 | Q3 不插手 | 备选 |

#### 部分退让的具体行为

```python
# decide() 中，残局激活时
if _endgame_context["is_active"]:
    # R11 仍然运行，产出建议
    r11_suggestion = R11.evaluate(game_state, actionList)
    # r11_suggestion = {"should_bomb": bool, "confidence": float, "reason": str}

    # Q3 综合裁决
    endgame_bomb_advice = _endgame_context["enemies"][main_enemy].get("should_bomb", False)

    # 裁决逻辑：任一方建议炸就炸
    final_should_bomb = r11_suggestion["should_bomb"] or endgame_bomb_advice

    # 但若 R11 明确不建议且 confidence 高（>0.8），覆盖 Q3
    if r11_suggestion["confidence"] > 0.8 and not r11_suggestion["should_bomb"]:
        final_should_bomb = False  # R11 高置信说不炸，尊重
```

#### 为什么选部分退让

- **R11 有缺陷但不是完全没用**：虽然缺全局牌记忆，但 `pass_num`/`curVal`/`numofgreaterPos` 仍提供有价值的统计信号
- **Q3 有残局信息但不是万能**：Q3 知道敌人报牌但不知道场上压制情况
- **两者互补**：R11 看压制力 → Q3 看残局紧迫度 → 互不冲突时取并集，冲突时 R11 高置信赢
- **先跑效果，数据说话**：效果不行再切完全退让或仅节流

#### 过渡策略

```python
# 配置开关，便于 A/B 测试
R11_ENDGAME_MODE = "partial"  # "full_cede" | "partial" | "threshold_only"
```

批跑对比三种模式的效果后，选最优固定。

---

### 1.13 设计问题十三：Q1 封锁与 Q2 助攻的同牌数冲突

> **原问题**（修正后）：敌人和队友剩牌数相同时（各 5 张 / 各 2 张 / 各 1 张），同一牌型既可能送队友也可能喂敌人，怎么裁决？

**答案：当前不裁决。留待记忆管线完善后再开发。**

#### 修正前提

原提问场景"下家 3 张 vs 队友 5 张"是伪冲突——3 张敌人无法压制 5 张三带二，`_ACTION_TYPE_CARD_COUNT` 过滤已处理，不存在选择困难。

#### 真正的难题：同牌数冲突

| 敌人 | 队友 | 困境 |
|:----:|:----:|------|
| 5张 | 5张 | 三带二 / 顺子 同时适用于双方，出牌方向不明 |
| 2张 | 2张 | 都可能吃对子，也可能都是单张 |
| 1张 | 1张 | 都是单张，一张牌可能放走敌人或帮队友 |

**对人来说也是难题。** 不靠记忆模块（出了哪些牌、各家还剩什么）无解。

#### 当前处理策略

在记忆管线（Memory Pipeline）上线前，遇到同牌数冲突时：

```
if 敌人.remaining == 队友.remaining:
    # 无法区分 → 保守策略
    → 优先封锁敌人（Q1 > Q2），宁可保守不放
```

这是有损但安全的默认行为——不漏可能放走敌人，代价是可能延误队友。

#### 记忆管线的未来能力

| 能力 | 解决的问题 |
|------|-----------|
| 跟踪各点数剩余张数 | "大王出过没"、"级牌还剩几张" |
| 推断敌人手牌倾向 | "下家 2 张大概率对子，因为前面单J他都没接" |
| 推断队友手牌倾向 | "队友 1 张，前面出了小王，剩的可能是大王" |
| 同牌数冲突裁决 | 有推断依据后，选择有利方向出牌 |

**状态：暂不开发，已知局限，等记忆管线就绪后回头补。**

---

### 1.14 设计问题十四：GUA-075 在残局中是否需要按 `recommended_types` 加权

> **原问题**：文档说"GUA-075 按 recommended_types 做排序加权"，但到 GUA-075 这里时 banned_types 已一刀切、Q1 已先走过推荐牌型，剩余的都是中性牌，加权有意义吗？

**答案：先不加权，纯靠 NN 赢率排序，看批跑效果再决策。**

#### 为什么不加权

```
Q0 自己冲刺 → 直接出牌，不到 GUA-075
Q1 封锁敌人 → 先按 recommended_types 出，找到直接出
              → 找不到才走 Q2，此时 actionList 里没有推荐牌型了
Q2 助攻队友 → 按 assist_prefer 出，找到直接出
              → 找不到才走 Q3
Q3 炸弹/常规 → 到这里 GUA-075，所剩都是"既不推荐也不禁止"的中性牌
```

**GUA-075 看到的 actionList 已被过滤干净**：推荐牌型被 Q1/Q2 优先消耗，禁止牌型被一刀切。剩下的中性牌加系数意义不大——没有"更推荐"的，也没有"更不推荐"的。

#### 两种方案

| 方案 | 做法 | 当前 |
|:----:|------|:----:|
| **不加权** | GUA-075 纯 NN 赢率排序，残局不加任何系数 | ✅ **当前** |
| 加权 | GUA-075 做 `基础分 × 推荐系数 × 惩罚系数` | 备选 |

#### 什么时候需要加权

如果批跑发现以下情况，再回头加系数：
- Q1 推荐牌型和中性牌之间 NN 赢率相近，常选错方向
- Q3 残局炸弹决策（should_bomb）和 NN 赢率冲突，需要一个系数调和
- 级牌在残局中过频繁被优先打出（NN 觉得级牌值大，但残局出级牌可能危险）

#### 配置开关

```python
GUA075_ENDGAME_WEIGHTED = False  # 当前关闭，需要时打开
```

---

### 1.15 设计问题十五：Q1 `recommended_types` 多个推荐牌型时按什么顺序选

> **原问题**：上家 8 张，`endgame_rule[8]` → `recommended = ["长顺子", "钢板", "三连对"]`。你手里三条推荐都有——先出哪个？

**答案：有回收的优先，无回收按张数多优先。**

#### 排序规则

```
① 检查手中是否有同一牌型的"回收对"（低段+高段同牌型）
   → 有回收 → 出低段，即使被对手压，高段可反压回收出牌权
② 无回收 → 按出牌张数降序排列
   → 同张数的按牌力值排序
③ 兜底 → 任选
```

**回收规则适用于所有可压制的牌型**，不限于顺子：

| 牌型 | 回收示例 | 逻辑 |
|------|---------|------|
| 单张 | 手里有 J、K 两张单张推荐 → 先出 J | 对手压 Q → K 回收 |
| 对子 | 手里有 77、QQ 两对推荐 → 先出 77 | 对手压 JJ → QQ 回收 |
| 三张 | 手里有 444、888 两组推荐 → 先出 444 | 对手压 666 → 888 回收 |
| 三带二 | 手里有 333+55、KKK+88 两组推荐 → 先出 333+55 | 对手压 777+99 → KKK+88 回收 |
| 三连对 | 手里有 556677、991010JJ 两组推荐 → 先出 556677 | 对手压 778899 → 991010JJ 回收 |
| 顺子 | 手里有 2-6、9-K 两组推荐 → 先出 2-6 | 对手压 7-J → 9-K 回收 |

#### 伪代码

```python
def _sort_recommended_actions(actions, hand_cards):
    """按回收优先 → 张数多优先排序"""
    def has_recapture(act):
        """判断此牌型在手牌中是否有更高段回收"""
        act_type = get_action_type(act)
        act_cards = act["cards"]
        remaining = [c for c in hand_cards if c not in act_cards]
        # 找同牌型、更高段（顶点更大）的回收
        for r_act in generate_actions(remaining, act_type):
            if max_card_value(r_act["cards"]) > max_card_value(act_cards):
                return True
        return False

    # 有回收的排前面
    return sorted(actions, key=lambda a: (
        not has_recapture(a),  # False(有回收)排前面
        -len(a["cards"]),      # 张数多优先
    ))
```

#### 为什么不是"出牌力最强的"

| 策略 | 风险 |
|------|------|
| 出牌力最强（如 9-K 顺子） | 一次性消耗最强牌，被对手更高顺子压了就没回收了 |
| 出有回收的低段（2-6 后 9-K） | **两层防线**：低段诱敌，高段回收，比一次性耗最强牌更稳 |

掼蛋残局核心是**出牌权**——有回收意味着输了这手还能回来，是更安全的打法。

#### 复用：领出牌阶段分两种场景

回收优先作为通用出牌原则，在领出牌阶段分**残局**和**非残局**两种情况：

##### 残局领出：按级牌以下从大到小

```
下家进入残局（如报单 1 张）→ banned_types 禁了你其他牌型
  → 你只能出"单张"
  → 没有回收可选（只有一种牌型）
  → 按级牌以下从大到小出
  例 curRank=2 → K > Q > J > T > 9 > …
```

**逻辑**：残局下牌型被限制，出牌选择少，直接出级牌以下最大的，不给敌人喘息机会。

##### 非残局领出：回收优先，从低段出

```
对手未进残局（均 >10 张）→ 牌型未受限
  → 你有回收对：如单 Q + 单 K
  → 出倒数第二小或最小的可回收牌段
  例 手里单张有 3, 7, Q, K → 出 Q（低段）留 K（高段回收）
  而不是出 3（虽最小但无回收）
```

**逻辑**：非残局不急于消耗最大牌，低段诱敌、高段回收更安全。优先出**有回收的低段**，无回收时再按最小消耗出。

##### 对比总结

| 场景 | 牌型自由度 | 出牌策略 | 例 |
|------|:--:|------|------|
| 残局领出 | 受限（banned_types） | 级牌以下从大到小 | 报单时出 K → Q → J |
| 非残局领出 | 不受限 | 回收优先：有回收的低段 | 单 Q（低段）→ 留 K（回收） |

---

### 1.16 设计问题十六：Q0 自己冲刺（两手整牌+有炸）时，出牌顺序是先炸还是先整？

> **原问题**：文档说 Q0 = "两手整牌 + 有炸 → 出最大整炸，抢头游"。但出牌顺序（先炸后整 vs 先整后炸）没有明确。

**答案：按出牌权 + 对手残局状态动态选择。**

#### 完整决策表

| 出牌权 | 对手残局状态 | 额外条件 | 策略 |
|:--:|:--:|------|------|
| **在我手** | 未进入残局 | — | **先整后炸**：出整牌开路，保留炸弹回收 |
| **在我手** | 已进入残局 | 敌人剩余数 = 整牌张数 且 整牌顶点 ≤ K | **先炸后整** ⚠️ 防止对手直接顺走获头游 |
| **在我手** | 已进入残局 | 敌人剩余数 ≠ 整牌张数 或 整牌顶点 > K | **先整后炸**：对手吃不掉你的高段整牌 |
| **不在我手** | 未进入残局 | — | **不急于炸**：让对手出一手，可能出到你的整牌牌型，用整牌压制后净胜炸弹，留待对手进入残局后开炸 |
| **不在我手** | 已进入残局 | — | **必须先炸后整**：用炸弹夺回出牌权 → 出整牌走完 |

#### 为什么"先整后炸"是常态

```
我手有出牌权，8 张：同花顺(♥3♥4♥5♥6♥7) + AAAA炸
→ 先出同花顺 → 对手：被顺子压了，出不了同花顺压你，只能炸或 PASS
  ├─ 对手 PASS → 你剩 4 张 AAAA → 炸弹直接走 → 头游
  └─ 对手炸你 → 你 AAAA 反炸 → 出牌权在手 → 头游
```

**逻辑**：你有炸弹兜底，不怕对手炸你的第一手整牌。先出整牌还能试探对手底牌——对手不炸说明可能没炸或舍不得炸。

#### 为什么"敌残局+同张数+低段"时要切换为先炸

```
我手有出牌权，9 张：5头炸(55551) + 三带二(KKK+88)
对手剩 5 张（残局），你的三带二正好 5 张，顶点 K
→ 如果你先出 KKK+88 → 对手正好有 AAA+22 三带二 → 直接压你 → 对手头游
→ 所以 **先炸后整**：55551 炸开路 → 出牌权确保 → 出 KKK+88 走完
```

**判据**：`敌人剩余数 == 整牌张数 and 整牌顶点 ≤ K` → 风险太高，先炸保底。顶点 > K（如 AAA+22）则对手难压，可先整后炸。

#### 出牌权不在我手时为什么"不急于炸"

```
对手领出（你被动跟牌），对手未进入残局（剩 12 张）
你剩 7 张：4444炸 + 三带二(777+99)
→ 不急于炸，PASS 或跟一手单张
→ 对手第二轮正好出三带二 888+JJ → 你用 777+99 压制
→ 净胜炸弹 4444 留着，等对手进残局后开炸锁死
```

**逻辑**：炸弹是稀缺资源，对手未进残局时开炸浪费。让对手出一手，说不定正好出你的整牌牌型，等于白赚一轮。

#### 伪代码

```python
def _q0_spirit_order(game_state, actions, endgame_context):
    """Q0 自己冲刺：两手整牌+有炸，决定出牌顺序"""
    is_my_turn = (game_state["curPos"] == myPos)
    enemy_in_endgame = any(
        e["remaining"] <= 10 for e in endgame_context["enemies"]
    )

    if is_my_turn:
        if not enemy_in_endgame:
            return "整牌优先"  # 先整后炸
        # 敌人已进残局 → 检查同张数风险
        for e in endgame_context["enemies"]:
            if e["remaining"] <= 10:
                for act in actions:
                    if (get_card_count(act) == e["remaining"]
                        and max_card_value(act) <= CARD_RANK_ORDER["K"]):
                        return "炸弹优先"  # 风险高，先炸
        return "整牌优先"  # 敌人吃不掉，先整
    else:
        # 出牌权不在我手
        if enemy_in_endgame:
            return "必须炸"  # 先炸后整，夺回出牌权
        else:
            return "等待"  # 不急于炸，让对手出
```

---

### 1.17 设计问题十七：Q2 助攻队友时，`assist_prefer` 多牌型排序规则

> **原问题**：Q2 只有 `_assist_prefer_for(remaining)` 返回牌型列表，没有排序规则。队友剩 3 张时，单张和对子都有，先出哪个？

**答案：与 Q1 相同，按回收优先排序。**

#### Q1 与 Q2 排序统一

| 管道 | 目标 | 排序规则 |
|:--:|------|------|
| Q1 封锁敌人 | 不让敌人走 | 回收优先 → 张数多优先 |
| Q2 助攻队友 | 让队友走 | **回收优先 → 张数多优先**（同 Q1） |

#### 为什么助攻也用回收优先

```
队友剩 3 张，你有单 Q + 单 K（同牌型回收对）
→ 先出单 Q（低段诱敌）
  ├─ 敌人压 A → 你 K 回收出牌权 → 再出一张助攻队友
  └─ 敌人 PASS → 队友接走 Q → 队友走完了，你 K 还在手
```

**逻辑**：助攻的目标是帮队友走，但你自己的出牌权也重要——有回收意味着你能多助攻一轮。保留回收 = 保留助攻能力。

#### 排序函数复用

```python
# Q1 和 Q2 共用同一排序函数
def _sort_by_recapture_first(actions, hand_cards):
    """回收优先 → 张数多优先（Q1/Q2 通用）"""
    return sorted(actions, key=lambda a: (
        not has_recapture(a, hand_cards),  # 有回收排前面
        -len(get_cards(a)),                 # 张数多优先
    ))
```

Q1 走 `_filter_by_recommended_types()` + `_sort_by_recapture_first()`
Q2 走 `_filter_by_assist_prefer()` + `_sort_by_recapture_first()`

均为同一排序核心。

---

### 1.18 设计问题十八：Q3 `should_bomb()` 的 `can_clear` 和 `will_lose` 判定标准

> **原问题**：决策表有了，但 `can_clear`（炸完能走）和 `will_lose`（不炸必输）两个核心判据没有定义。

**答案：`can_clear` 用组牌引擎判剩余手数；`will_lose` 看敌人剩牌是否为致命张数（5/3/2/1），但 4 张走「炸不压四」规则（有例外）。**

#### `can_clear`：炸完剩余牌能否一轮走完

```
炸完剩余牌 = 手牌总数 - 炸弹张数
→ 组牌引擎对剩余牌分组
→ 剩余手数 ≤ 1 → can_clear = True
→ 剩余手数 ≥ 2 → can_clear = False
```

**例外**：剩余牌本身是炸弹（如 5头炸后剩 4头炸，4头炸一手走完）→ 也算 `can_clear = True`。

#### `will_lose`：敌人是否极可能一手走完

敌人剩牌为以下**致命张数**时，不炸敌人就赢了：

| 敌人剩余 | 对应一手牌型 | 为什么致命 |
|:--:|------|------|
| **1 张** | 单张 | 任意单张直接头游 |
| **2 张** | 对子 | 任意对子直接头游 |
| **3 张** | 三同张 | 任意三同张一手走完 |
| **5 张** | 三带二 / 顺子 / 同花顺 | 一手 5 张整牌直接走完 |

> 注：3 张三同张不一定有，但敌人剩 3 张时有相当概率是一手三同张，风险不可忽视，因此纳入致命张数。

#### 🚫 4 张规则：炸不压四（火不打四）

| 敌人剩余 | 规则 | 原因 |
|:--:|------|------|
| **4 张** | 一般**不炸** | 敌人 4 张极可能是炸弹——炸弹压炸弹没有意义，你炸了牌权在敌人手 |

**但有两个例外可以冲刺**：

| 例外条件 | 策略 | 场景 |
|----------|------|------|
| ① 自己只剩两手牌（其中一手是炸）+ 出牌权在我手 | **可冲刺**：炸开路 → 另一手走完 | 你有 9 张：炸弹 + 一手整牌 |
| ② 炸弹牌力 ≥ J | **仍可压制冲刺** | J 以上炸弹牌力足够，不怕敌人更大炸弹反压的概率更低 |

```
炸不压四总结：
  ├─ 一般 → 不炸（敌人 4 张是炸弹，炸了牌权归敌）
  ├─ 自己两手牌 + 可冲刺 → 可以炸（冲刺头游优先）
  └─ 炸弹 ≥ J → 仍可炸（牌力足够压制风险）
```

**判据**：

```
下家或上家敌人剩余 ∈ {1, 2, 3, 5} → will_lose = True
敌人剩余 = 4 且（自己两手牌 or 炸弹 ≥ J）→ will_lose = True（可冲刺）
敌人剩余 = 4 且 不满足例外 → will_lose = False（炸不压四）
否则 → will_lose = False
```

#### 完整决策逻辑

```python
def should_bomb(bomb_action, hand_cards, enemies):
    """Q3 兜底炸弹决策"""
    # 炸完剩余牌
    remaining = [c for c in hand_cards if c not in bomb_action["cards"]]

    # can_clear：剩余牌能否一手走完
    remaining_hands = count_hands(remaining)  # 组牌引擎
    can_clear = (remaining_hands <= 1) or is_bomb(remaining)

    # will_lose：敌人是否致命张数
    fatal_counts = {1, 2, 3, 5}
    will_lose = any(
        e["remaining"] in fatal_counts
        for e in enemies
        if e["remaining"] <= 10
    )
    # 炸不压四例外：敌人剩4张 + (自己两手牌 or 炸弹≥J) → 可冲刺
    if not will_lose:
        enemy_has_4 = any(e["remaining"] == 4 for e in enemies if e["remaining"] <= 10)
        remaining_after_bomb = len(remaining)
        bomb_val = max_card_value(bomb_action["cards"])
        my_two_hands = (remaining_after_bomb > 0 and count_hands(remaining) <= 1)
        bomb_ge_J = (bomb_val >= CARD_RANK_ORDER["J"])
        if enemy_has_4 and (my_two_hands or bomb_ge_J):
            will_lose = True  # 可冲刺头游

    # 决策表
    if can_clear and will_lose:
        return True   # 炸完能走 + 不炸必输 → 果断炸
    if can_clear and not will_lose:
        return False  # 能走但非必须 → 观察
    if not can_clear and will_lose:
        return False  # 必输但炸也走不掉 → 留给对家
    return False      # 都不满足 → 绝对不能炸
```

> 与原来决策表完全一致，仅补充了判据计算逻辑。

---

### 1.19 设计问题十九：Q3 兜底「走常规牌型」的具体策略

> **原问题**：Q3 两个分支（有炸弹但不炸 / 无炸弹）都通向"走常规牌型"，但没有定义具体策略。

**答案：分主动领出和被动跟牌两种情况。此规则不只是残局兜底——同样适用于开局阶段和中期阶段。**

#### 主动领出（出牌权在我手）：非残局回收优先

与问题十五规则一致，按**非残局领出**策略：牌型不受限 → 回收优先（有回收的低段→高段回收出牌权）。

#### 被动跟牌（出牌权不在我手）：看牌力角色

| 牌力角色 | 跟牌策略 | 目的 |
|:--:|------|------|
| **助攻 / 弱牌力** | **小跟** | 尽快出掉手中的小牌、弱牌，不消耗大牌 |
| **主攻 / 强牌力** | **大跟压制** | 压制对手出牌权 + 投喂队友需要的牌型 |

##### 牌力角色判定

```
牌力 = 0.5×牌力分 + 0.3×手数分 + 0.1×回收分 + 0.1×灵活分
主攻阈值: 牌力 ≥ 5（或牌力分 ≥ 5）
助攻阈值: 牌力 < 5

优先级: 队友角色优先 → 队友是主攻则你是助攻，反之亦然
```

##### 为什么助攻小跟、主攻大跟

| 角色 | 策略 | 逻辑 |
|:--:|------|------|
| 助攻 | 小跟 | 你不是主角，尽快清小牌、弱牌，为队友腾出空间。跟牌略大于当前即可，不额外消耗大牌资源 |
| 主攻 | 大跟 | 你是主角，需要夺取出牌权。大跟压制对手后 → 领出牌型 → 投喂队友需要的牌型（assist_prefer），队友接走你继续压 |

##### 伪代码

```python
def _regular_play(game_state, teammate_context=None):
    """通用出牌策略：主动领出→回收优先 / 被动跟牌→看牌力角色

    适用阶段：开局 / 中期 / 残局（Q3 兜底通用）
    """
    is_my_turn = (game_state["curPos"] == game_state["myPos"])

    if is_my_turn:
        # 主动领出 → 非残局回收优先
        return _sort_by_recapture_first(actions, hand_cards)

    else:
        # 被动跟牌 → 看牌力角色
        power = get_hand_power(hand_cards)  # 牌力分
        if power >= 5:
            # 主攻：大跟压制 → 抢出牌权 → 投喂队友
            return _suppress_and_feed(actions, teammate_context)
        else:
            # 助攻：小跟 → 尽快出小牌弱牌
            return _minimal_follow(actions, current_action)
```

> **通用规则**：此策略不只用于 Q3 残局兜底，同样适用于开局阶段和中期阶段的常规出牌。主动领出走回收优先，被动跟牌看牌力角色决定大跟还是小跟。

---

### 1.20 设计问题二十：baoshu 封锁优先级与 block_with 走不通时的降级路径

> **原问题**：Q1 中 baoshu 的 `block_with` 和 endgame_rule 的 `recommended_types` 是什么关系？block_with 走不通时降级到哪？

**答案：残局阶段阈值 ≤10（非 ≤4），baoshu 是封锁线的强化子集；block_with 是推荐封锁牌型，走不通时出任意非 banned 牌型即可——不必同牌型压制。**

#### 两个关键纠正

| 纠正 | 错误 | 正确 |
|:--:|------|------|
| **残局阈值** | 封锁优先仅敌人 ≤4 触发 | 封锁优先 = 敌人 ≤**10** 就触发（Q1 入口即 `is_active`）。≤4 是 baoshu 子规则——在 ≤10 封锁基础上叠加更强禁令 |
| **block_with 是推荐非限制** | 只能在 block_with 列表里选 | `block_with` 是**优先推荐的封锁牌型**。走不通时，出**任意非 banned 牌型**即可。不是同牌型不能压制 |

#### block_with 走不通的具体场景

```
敌人报单(1张)：
  banned_types = ["单张"]                                      ← 一刀切
  baoshu.block_with = ["三带二", "钢板", "连对", "顺子", "炸弹"]  ← 推荐封锁牌型
  endgame_rule.recommended = ["最大单张"]                        ← 已被 banned

你手里：无三带二/钢板/顺子/炸弹，只有对子 QQ、JJ
→ block_with 走不通
→ banned 中无 "对子"
→ 直接出对子！"不是同牌型不能压制"——对子也能封锁敌人
```

#### 伪代码

```python
def _q1_blockade(actions, banned_set, block_with_types):
    """Q1 封锁优先：先用推荐封锁牌型，走不通则用任意非 banned 牌型

    核心原则：不需要同牌型才能压制。任何能维持出牌权的牌型都是有效的封锁。
    """
    # ① 优先在 block_with 推荐牌型中选
    for a in actions:
        if get_action_type(a) in block_with_types:
            return a  # 最优封锁

    # ② block_with 走不通 → 出任意非 banned 牌型
    for a in actions:
        if get_action_type(a) not in banned_set:
            return a  # 对子也能封锁

    # ③ 极限降级：全被禁 → 走 Q9 L3
    return _l3_fallback(actions, baoshu_never_play, cur_rank)
```

> **关键原则**：封锁不是只能出三带二/钢板/顺子。只要能抢到出牌权、不让敌人有机会出牌，任何牌型都是封锁。对子 QQ、JJ 一样能压住敌人不让其走单张。

---

### 1.21 设计问题二十一：Q2 assist_prefer 精确投喂表

> **原问题**：Q2 只说了"按 assist_prefer 出牌助攻队友"，没有定义每种剩牌数该投喂什么牌型。

**答案：按队友剩牌数精确匹配最可能手牌，投喂对应牌型。3 张有降级路径。**

#### 投喂原则

**核心思路**：猜队友最可能的手牌 → 出他能接的牌型 → 他接走你就继续帮压。

| 队友剩牌 | 最可能手牌 | 投喂牌型 | 优先级 |
|:--:|------|------|:--:|
| **1 张** | 单张 | 单张 | 直接喂走 |
| **2 张** | 对子 | 对子 | 直接喂走 |
| **3 张** | 三同张 | 三张 → 对子 → 单张 | **降级**：队友 PASS 则换更小的牌型再喂 |
| **4 张** | 炸弹 / 两个对子 | 对子 | 最安全：是对子接走，是炸弹也消耗 |
| **5 张** | 顺子 / 三带二 | 顺子、三带二 | 匹配最常见 5 张牌型 |
| 6-10 张 | — | 对子优先 | 正常助攻，不必强喂 |

#### 3 张降级路径（关键设计）

```
出牌权在我手 → 投喂三张
  ├─ 队友接走 ✅ → 继续帮压
  └─ 队友 PASS ❌ → 不是三同张！
        ├─ 投喂对子
        │    ├─ 队友接走 ✅ → 剩 1 张单张，下轮喂单张
        │    └─ 队友 PASS ❌ → 不是对子！
        └─ 投喂单张（最后手段）
```

> **降级原理**：队友剩 3 张时，如果不是三同张（可能是 1+2 或 3 散张），投喂三张他接不了 → PASS 暴露信息 → 换对子 → 再 PASS 换单张。每降一级，你就缩小了他可能手牌的范围。

#### 伪代码

```python
def _assist_prefer_for(remaining: int) -> list:
    """队友剩 N 张时，精确投喂牌型（按优先序）"""
    if remaining == 1:
        return ["Single"]                      # 直接喂走
    elif remaining == 2:
        return ["Pair"]                        # 直接喂走
    elif remaining == 3:
        return ["Trips", "Pair", "Single"]     # 三张 → 降级对子 → 降级单张
    elif remaining == 4:
        return ["Pair"]                        # 优先对子（防炸弹/两个对子）
    elif remaining == 5:
        return ["Straight", "ThreeWithTwo"]    # 顺子/三带二
    elif remaining <= 10:
        return ["Pair"]                        # 6-10 对子优先
    else:
        return []

def _q2_feed_teammate(actions, assist_prefer, game_state):
    """Q2 助攻：按 assist_prefer 顺序尝试投喂"""
    for pref_type in assist_prefer:
        candidates = [a for a in actions if get_action_type(a) == pref_type]
        if candidates:
            return _sort_by_recapture_first(candidates, hand_cards)[0]
    # assist_prefer 全部走不通 → Q3
    return None
```

> **与 Q1 排序共用**：找到候选牌型后，仍走 `_sort_by_recapture_first()` 回收优先排序（同 Q1/Q15/Q17）。

---

### 1.22 设计问题二十二：残局被动跟牌时 R03 与 banned_types 的退让规则

> **原问题**：残局被动跟牌轮，banned_types 禁掉了唯一能压的牌型时，R03 说"不能 PASS"，banned_types 说"不能出"，冲突了怎么办？

**答案：冲突不存在。不同牌型不能压制（除炸弹），只需判断当前轮牌型是否匹配敌人致命牌型。**

#### 核心原则

**不同牌型不能互相压制（炸弹除外）**。所以"banned_types 挡住了跟牌"实际是个伪命题——如果当前轮出的是对子，敌人致命牌型是单张，你本来就不用压也压不了。

#### 场景举例

```
局面：
  你（pos 0）：剩 5 张 [K♠, Q♥, 8♠, 8♦, 3♣]
  下家敌人（pos 1）：剩 1 张（报单！致命牌型 = 单张）
  上家敌人（pos 3）：出一对 99
  → 轮到你了

分析：
  当前轮牌型 = 对子
  敌人致命牌型 = 单张
  单张 压不了 对子 → 下家必 PASS
  → 你 PASS 安全，下家接不走
```

| 当前轮牌型 | 敌人致命牌型 | 是否匹配 | 策略 |
|:--:|:--:|:--:|------|
| 对子 | 单张（剩 1 张） | ❌ 不匹配 | **PASS 安全**——敌人接不走，让队友处理 |
| 单张 | 单张（剩 1 张） | ✅ 匹配 | **必须压**——用手牌最大单张压，压不住也没办法 |
| 三带二 | 单张（剩 1 张） | ❌ 不匹配 | **PASS 安全** |
| 顺子 | 顺子（剩 5 张） | ✅ 匹配 | **必须压**——用最大顺子压 |
| 任意 | 对子（剩 2 张） | 仅对子匹配 | 对子轮必须压，非对子轮 PASS 安全 |

#### 为什么压了反而更危险

```
上家出对子 99 → 你用 QQ 压住获得出牌权
→ 你手里只剩 [K♠, Q♥, 8♠, 8♦, 3♣] → 必须出牌
→ 三张散牌只有单张可出 → 下家敌人趁机垫走头游！
```

> **你压了对子获得出牌权 → 出牌权在手就得清手牌 → 手里只剩单张 → 正好送下家走。PASS 让队友处理才是正道。**

#### 伪代码

```python
def _r03_endgame_retreat(
    cur_action_type: str,        # 当前轮牌型
    enemy_deadly_type: str,      # 敌人致命牌型（从 baoshu/endgame_rule 推断）
    can_follow: list,            # 能跟牌的候选动作
    can_pass: bool,              # 是否可以 PASS（主动轮 False）
):
    """残局被动跟牌时的 R03 退让规则

    核心：不同牌型不能压制，所以 banned_types 挡不住时才需要决策。
    关键判断是「当前轮牌型 == 敌人致命牌型吗」。
    """
    # ① 当前轮牌型与敌人致命牌型不同 → 敌人压不了，PASS 安全
    if cur_action_type != enemy_deadly_type:
        if can_pass:
            return "PASS"   # 安全放行，让队友处理
        else:
            # 主动轮无法 PASS → 正常出牌（敌人本就接不走，出啥都行）
            return None  # 走正常管线

    # ② 牌型匹配！敌人能用致命牌型压 → 必须跟牌
    if can_follow:
        # 用手牌最大能压的牌去压，压不住也没办法
        return max(can_follow, key=lambda a: _card_value(a))
    else:
        # 跟不了 → 只能 PASS
        return "PASS"  # 没办法，压不住
```

> **记忆口诀**：**牌型不同 → PASS 安全**（敌人接不走）；**牌型相同 → 必须压**（用最大的压，压不住认栽）。

---

### 1.23 设计问题二十三：残局接管与非残局交接时的状态切换

> **原问题**：残局模式（`is_active=True`）什么时候开启、什么时候退出？敌人头游后封锁目标怎么处理？跨副牌是否残留状态？

**答案：三个自动切换，无需手动干预。**

#### 切换一：进入残局（敌人 11→10）

```
第 7 轮：numofplayers = [18, 11, 20, 16]  → is_active = False，正常出牌
第 8 轮：pos1 出 1 张，numofplayers = [18, 10, 20, 16]
  → 预处理器检测到 pos1 = 10 ≤ 10
  → is_active = True   ← 自动切换
  → enemies = {pos1: {remaining:10, danger_level:"low"}}
  → 决策管线立刻走 Q0→Q1→Q2→Q3 残局路径
```

**要点**：预处理器每轮运行，读到 `numofplayers` 有任何人 ≤10 就翻 `True`。不存在"半轮还在用旧管线"的竞态——本轮决策用的就是本轮的 `is_active`。

#### 切换二：敌人头游 → 封锁目标自动清空

```
第 15 轮：numofplayers = [10, 3, 14, 16]
  is_active = True
  enemies = {pos1: {remaining:3, danger_level:"critical", baoshu触发}}
  banned_types = ["单张", "对子"]

第 16 轮：pos1 出完最后 3 张 → 头游，离场
  → 第 17 轮预处理器：
    numofplayers = [8, 0, 12, 14]    ← pos1=0，已头游
    is_active = True                  ← 仍然 True（自己 8 张）
    enemies = {}                      ← 空了！pos3=14 > 10，不在残局区

  → 管线路由：
    ┌─ Q0: self.remaining=8 → 冲刺优先，抢二游/三游
    └─ Q1: enemies 为空 → 跳过封锁。敌人头游了就不存在了，防什么？防空气。
```

> **敌人头游 = 敌人不存在了**，不需要封锁一个已经离场的玩家。`enemies` 变空是正确行为。

#### 切换三：每副牌独立重置

```
第 1 副牌结束：我方头游+二游，敌人剩 5 张和 8 张，is_active=True
第 2 副牌开始：所有人 27 张 → is_active 重置为 False
```

> 副牌之间不继承残局状态。新一副牌所有人都 27 张起手，`numofplayers=[27,27,27,27]`，不可能触发 `is_active`。

#### `is_active` 的单向性

```
本副牌内：is_active 一旦翻 True → 不会翻回 False
原因：手牌只减不增，numofplayers 只会变小，不存在"从 ≤10 涨回 >10"
唯一的 False→True 切换发生在进入残局那一刻
唯一的 True→False 重置发生在新一副牌开始
```

#### 完整时间线

```
副牌开始 ──────────────────────────────────────────→ 副牌结束
  │                                                    │
  │ is_active = False                                  │
  │ 正常出牌管线                                        │
  │                                                    │
  │ ── 第 N 轮：敌人从 11→10 ──                       │
  │ is_active = True（自动切换）                        │
  │ Q0冲刺 > Q1封锁 > Q2助攻 > Q3兜底                   │
  │                                                    │
  │ ── 第 M 轮：敌人头游离场 ──                         │
  │ enemies 变空，Q1 跳过，Q0冲刺优先                    │
  │                                                    │
  │ ── 副牌结束 ──                                     │
  │                                                    │
下一副牌：is_active = False（重置）                      │
```

---

### 1.24 设计问题二十四：endgame_rule 的 banned_types 按剩余牌型推理动态查表

> **原问题**：banned_types 是否需要根据 baoshu 动态调整？每个 remaining 的值怎么定？

**答案：查表即调整。预处理器按 `remaining` 键查 endgame_rule，不同 remaining 返回不同的 banned_types。关键是每个 remaining 的 banned 必须基于"敌人最可能有什么牌型"的推理。**

#### 禁止推理的基本原则

| 敌人剩牌 | 最可能牌型 | 致命喂牌 | 为什么 |
|:--:|------|------|------|
| **6 张** | 5+1（炸弹+单张）或 4+2（炸弹+对子） | **禁单张、禁对子** | 单张会被 5+1 垫走首张；对子会被 4+2 接走 |
| **5 张** | 4+1（炸弹+单张） | **禁单张** | 出单张敌人垫走，剩炸弹直接炸出走完 |
| **4 张** | 炸弹 或 两个对子 | **禁对子** | 两个对子接走→走完。单张威胁不大（炸弹出不了单张）。**优先 PASS** |
| **3 张** | 1+2（单+对）或三同张 | **禁单张、禁三不带** | 单张被 1+2 垫走首张；三不带被三同张直接接走 |
| **2 张** | 对子 | **禁对子** | 接走→头游 |
| **1 张** | 单张 | **禁单张** | 一刀切 |

#### 完整 endgame_rule 表（已按问题二十四修正）

| remaining | 危险 | recommended | banned | 推理 |
|:--:|:--:|------|------|------|
| **10-7** | 低 | 长组合牌 | `[]` | 刚进入警戒区，暂不硬禁 |
| **6** | 中 | 三不带 | **`["单张", "对子"]`** | 5+1/4+2 双模式，两个致命喂牌都禁 |
| **5** | 中 | 对子, 三不带, 大单张 | **`["单张"]`** | 4+1 模式，只禁单张（对子没威胁） |
| **4** | 中高 | 大单张, 顺子 | **`["对子"]`** | 炸弹或两个对子，禁对子；**优先 PASS** |
| **3** | 高 | 单张, 对子 | **`["单张", "三不带"]`** | 1+2 或三同张，两种可能都防 |
| **2** | 高 | 单张 | `["对子"]` | 对子直接走完 |
| **1** | 极高 | 最大单张 | `["单张"]` | 一刀切 |

#### 动态查表即调整

```python
# 预处理器每轮运行，自动动态
remaining = numofplayers[enemy_pos]

# ① 查 endgame_rule 表
rule = ENDGAME_RULE[remaining]
banned = rule["banned_types"]        # 自动按 remaining 匹配，无需手写 if-else

# ② ≤4 时叠加上 baoshu 的子规则
if remaining <= 4:
    baoshu = BAOSHU_RULE[remaining]
    banned = list(set(banned + baoshu["never_play"]))
    # 例：remaining=3 → endgame["单张","三不带"] + baoshu["三同张","三不带"]
    #     → banned = ["单张", "三不带", "三同张"]

# ③ 过滤：敌人剩 N 张 → 只能出 ≤N 张的牌型
banned = [t for t in banned if _ACTION_TYPE_CARD_COUNT.get(t, 99) <= remaining]
```

> **关键认识**：不需要"动态调整"逻辑——`remaining` 本身就是键，查表即动态。banned_types 的值随敌人剩牌减少逐步收紧，从 10 张的 `[]` 逐渐收紧到 1 张的 `["单张"]`。

### 1.25 设计问题二十五：Q0「两手整牌」的精确判定

> **原问题**：组牌引擎返回的手数到底怎么算？炸+对+对+单是几手？炸完后剩几张算两手整牌？

**答案：组牌引擎的 `grouptype_map` 返回的是天然牌型组数，每个组 = 一手。**

#### 核心定义

> **两手整牌 = 手牌拆分后总共 2 组——两轮就能走完。**

- **一手**（Wiki）：玩家一次出牌动作所打出的那组牌，最小出牌决策单元
- **手数**（Wiki）：手牌拆分完后形成的一手牌组数，即 `sum(grouptype_map.values())`
- **两手整牌**：手数 = 2，手牌刚好拆成两个组，两轮出完

#### 手数判定

```
例1：KKKK + KK + 88 + 3
  grouptype_map = {炸:1, 对:2, 单:1}  → 1+2+1 = 4手
  ≠两手整牌，不能冲刺

例2：先出 KKKK 炸完
  剩 KK + 88 + 3 → grouptype_map = {对:2, 单:1} → 2+1 = 3手
  ≠两手整牌，仍需 3 手才能走完（对+对+单 = 三个独立的组）

例3：KKKK + 88
  grouptype_map = {炸:1, 对:1}  → 1+1 = 2手 ✅ 两手整牌！
  先出 KKKK → 剩 88 → 下轮对子走完
```

> **关键**：组牌引擎返回的手数 = 每个牌型组一手。对+对+单是 3 手（三个组），不是 2 手。炸弹本身也是一手——炸弹不"合并"其他牌型。

#### 两手整牌的严格条件

```python
def is_two_clean_hands(grouptype_map: dict) -> bool:
    # 两手整牌：总共 ≤2 个牌型组
    total_groups = sum(grouptype_map.values())
    return total_groups <= 2
```

| 手牌 | grouptype_map | 组数 | 两手整牌？ |
|------|------|:--:|:--:|
| QQQQ + KK + 88 + 3 | 炸1对2单1 | 4 | ❌ |
| KKKK + 88 | 炸1对1 | 2 | ✅ |
| 789TJQK + 22 | 顺1对1 | 2 | ✅ |
| KK + 88 + 33 | 对3 | 3 | ❌ |
| 4444 + 5 | 炸1单1 | 2 | ✅ |
| AA + KK + QQ + JJ | 对4 | 4 | ❌ |

> **两句口诀**：**组数 ≤2 就是两手整牌**——管你炸弹还是普通牌型，几个组就几手。

---

### 1.26 设计问题二十六：残局 R10 领出禁炸退让

> **原问题**：残局冲刺时 R10 说"领出不能炸"，但你是两手整牌（如 KKKK+88），先出炸弹就赢了——R10 和残局管线谁说了算？

**答案：进入残局阶段，以残局管线为准。R10 退让，和 R11 冲突解决一致。**

#### 为什么残局管线优先

```
场景：你 6 张，有出牌权
  手牌：KKKK + 88  → 两手整牌！

  正常管线：R10 硬禁领出炸弹 → KKKK 被过滤
            → 只能出 88 → 剩 KKKK
            → 下轮要炸还得等一圈拿到出牌权 → 敌人可能先走

  残局管线：is_active = True → Q0 冲刺判断
            → 两手整牌 → should_sprint = True
            → R10 退让 → KKKK 可以出
            → 先出 KKKK → 剩 88 → 下轮对子头游
```

#### 冲突解决优先级

| 优先级 | 规则 | 生效条件 |
|:--:|------|------|
| **1（最高）** | 残局管线（Q0冲刺） | `is_active == True` |
| 2 | R11 炸决策（被动不能炸时的退让） | 残局冲刺 + 压不住时 |
| 3 | R10 领出禁炸 | 非残局模式 |
| 4 | 其他 Guard 规则 | 正常模式 |

```python
def _resolve_r10_in_endgame(action, context):
    # 残局模式下 R10 退让
    if context.get("is_active") and context.get("should_sprint"):
        # 残局冲刺 → R10 退让，允许领出炸弹
        return True  # 通过
    # 非残局 → R10 正常生效，禁领出炸弹
    return not is_lead_bomb(action)
```

> **原则**：**残局冲刺 > R11 退让 > R10 禁领出**。进入残局后一切让路给冲刺——能走不等人。

**与 R11 冲突解决的对比**：

| | R11（被动炸决策） | R10（领出禁炸） |
|------|------|------|
| **非残局** | 正常 M3 三段节流 | 硬禁领出炸弹 |
| **残局冲刺** | 退让——Pass 太多 or 压不住时炸 | 退让——两手整牌直出炸 |
| **原则** | 残局管线优先 | 残局管线优先 |

> **一句话**：**进入残局，以残局管线为准。R10/R11 都退让。**

### 1.27 设计问题二十七：4 张"优先 PASS"在主动轮的降级策略

> **原问题**：敌人 4 张时规则说"优先 PASS"，但主动领出轮无法 PASS。此时出什么？

**答案：按 recommended_types 降级出牌，走不通时走 L3 降级。能冲刺时放宽 banned 限制。**

#### 为什么主动轮不能用"优先 PASS"

```
敌人 4 张 → endgame_rule[4] → 优先 PASS
原因：4 张可能是炸弹，硬压可能撞枪口；PASS 让队友试探。

但主动轮你拿到了出牌权，PASS 即弃权——规则不允许。
→ 必须出牌，按降级路径走。
```

#### 四个典型场景

##### 场景 A：有顺子出顺子（封锁最优）

```
你手牌：AKQJT + 55 + 4 → {顺1,对1,单1} = 3手
主动轮，敌人 4 张
banned=["对子"] → 55 排除
recommended=["大单张", "顺子"] → AKQJT 可用
→ 出顺子 AKQJT！敌人 4 张接不了顺子（4 < 5），安全封锁
```

> 4 张接不了顺子（不是同牌型且张数不够），不存在压制关系。比 PASS 更好——PASS 是让敌人出牌，出顺子是你封锁。

##### 场景 B：只有对子+单张，没长牌（单张兜底）

```
你手牌：AA + KK + 88 + 3 → {对3,单1} = 4手
主动轮，敌人 4 张
banned=["对子"] → 对子全被排除
recommended=["大单张","顺子"] → 无顺子，只剩单张
→ 出 3（单张威胁不大：炸弹出不了单张，两个对子也出不了单张）
```

> 单张对 4 张敌人无害——敌人的 4 张不管是什么牌型都接不了单张（炸弹不能拆，两个对子不是单张）。

##### 场景 C：有炸弹（炸不压四 + 冲刺判断）

```
你手牌：4444 + 88 + 3 → {炸1,对1,单1} = 3手
主动轮，敌人 4 张
banned=["对子"] → 88 排除
should_sprint? → 3手 > 2 → 不冲刺
"炸不压四"：敌人 4 张极可能也是炸弹 → 不硬炸
→ 出 3（单张安全），炸弹留作后手
```

> 如果 should_sprint（比如 4444+88 两手整牌），则 R10 退让 → 出 4444 炸 + 下轮 88 走完。

##### 场景 D：只剩对子，全被 banned（触发降级）

```
你手牌：AA + KK → {对2} = 2手（两手整牌！）
主动轮，敌人 4 张
banned=["对子"] → 对子全被封！actionList 为空！

降级路径：
  L1：banned 硬排除后 actionList 为空 → 触发降级
  L2：不能 PASS（主动轮）→ 不可用
  L3：放宽 banned——你是两手整牌应该冲刺
      判断：should_sprint == True（组数=2 ≤2）
      → 忽略 banned 限制，出 AA
      风险：敌人如果是两个对子 → 接走 AA → 剩对子走完
      但：如果 AA > 敌人最大对 → 压住拿回牌权 → 下轮 KK 走完
```

> **场景 D 揭示的规则**：**能冲刺时 banned 降级**。两手整牌该走就走，banned 不挡冲刺路径。

#### 完整降级决策树（4 张主动轮）

```python
def _decide_4card_active_round(context, actionList):
    # 4 张敌人 + 主动轮的降级出牌

    # ① 先 banned 硬排除
    banned_set = context.get("banned_set", set())
    safe_actions = [a for a in actionList if get_action_type(a) not in banned_set]

    if safe_actions:
        # 有安全牌型 → 按 recommended 优先
        recommended = context.get("recommended_types", [])
        for rectype in recommended:
            candidates = [a for a in safe_actions if get_action_type(a) == rectype]
            if candidates:
                return select_best(candidates)
        # recommended 都走不通 → 任意非 banned 牌型
        return select_best(safe_actions)

    # ② 全被 banned → 降级
    if context.get("should_sprint"):
        # 两手整牌 → 放宽 banned，能走直走
        return select_best(actionList)  # 忽略 banned
    else:
        # 不能冲刺 → L3 仅保留 baoshu.never_play 硬禁
        baoshu_never = context.get("baoshu_never_play", [])
        relaxed = [a for a in actionList if get_action_type(a) not in baoshu_never]
        if relaxed:
            return select_best(relaxed)
        # 极限：全被 baoshu 禁 → 出最大单张保底
        return max(actionList, key=card_value)
```

> **核心原则**：**有安全牌走安全牌 → 全被禁能冲刺走冲刺 → 不能冲刺走 L3 降级**。

---

## 二、numofplayers 与 GUA-065（残局触发真源）

```python
game_state["numofplayers"] = [p0_remaining, p1_remaining, p2_remaining, p3_remaining]
```

**数据源优先级**（`_inject_numofplayers` 写入顺序）：
1. `MemoryTracker.hand_counts` — 从出牌流水推算；**须在 decide 入口初始化**（不可仅 NN lazy init）
2. `publicInfo[i].rest` — act 消息平台真源，同步进 Tracker 后写入
3. `handCards` — 仅自己位置（`numofplayers[myPos]` 以此纠偏）
4. 回退 27 — 对手未知时估算为初始牌数

**残局预处理器的读取方式**（区分敌方/队友/自己）：

```python
numofplayers = game_state.get("numofplayers", [27, 27, 27, 27])
my_pos = game_state["myPos"]
teammate_pos = (my_pos + 2) % 4

# ① 敌方两家（封锁对象）
enemy_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]
for opp_pos in enemy_positions:
    remaining = numofplayers[opp_pos]
    if 1 <= remaining <= 10:
        # 查 endgame_rule → 注入 banned_types / baoshu 封锁
        ...
    # 敌人 > 10 张 → 不在警戒区，不注入

# ② 队友（助攻对象）
mate_remaining = numofplayers[teammate_pos]
if 1 <= mate_remaining <= 10:
    # 队友进入残局区 → 助攻模式，不封锁
    context["teammate"] = {
        "remaining": mate_remaining,
        "is_close": mate_remaining <= 4,
        "assist_prefer": _assist_prefer_for(mate_remaining),
    }

# ③ 自己（冲刺/助攻判断）
self_remaining = numofplayers[my_pos]
context["self"] = {
    "remaining": self_remaining,
    "has_two_clean_hands": _has_two_clean_hands(game_state),
    "has_bomb": _has_bomb(game_state),
    "should_sprint": _should_sprint(game_state),
}
```

| 对照 | 实际对战 | V7 实现 |
|------|---------|--------|
| **敌方**剩 10 张 | 报牌 1 次（口头声明） | `numofplayers[enemy_pos] == 10` → 残局警戒区激活，封锁管线 |
| **敌方**剩 4 张 | 高危险/报牌临界 | `numofplayers[enemy_pos] <= 4` → BAOSHU_RULE 触发 |
| **敌方**剩 1 张 | 听牌/报单 | `numofplayers[enemy_pos] == 1` → 封锁禁单张 |
| **队友**剩牌 ≤10 | 配合决策 | `numofplayers[teammate_pos]` → 助攻模式，送牌喂牌帮压 |
| **自己**剩牌 | 冲刺/助攻判断 | `numofplayers[myPos]` → 能走直走，走不了助攻队友 |

> **结论**：`is_active` 由任何一家 ≤10 张触发。敌方走封锁管线（`endgame_rule` + `BAOSHU_RULE` → `banned_types`），队友走助攻管线，自己走冲刺/助攻判断。`banned_types` 硬排除在 `decide()` 中一刀切，仅作用于敌方。

---

## 三、三大知识块

### 3.1 endgame_rule：剩 N 张 → 危险/推荐/禁止

- **落盘**：预处理器直接注入 `recommended_types` / `banned_types`
- **作用**：下游 Guard 或 GUA-075 推荐引擎读取，作为出牌偏好/排除依据

```python
endgame_rule = {
    # remaining: (danger_level, recommended_types, banned_types)
    # banned 根据敌人可能牌型推断，防致命喂牌
    1:  ("极高", ["最大单张"],           ["单张"]),                                    # 听牌！出单张敌人直接走
    2:  ("高",   ["单张"],               ["对子"]),                                    # 对子直接走完
    3:  ("高",   ["单张", "对子"],        ["单张", "三不带"]),                           # 防1+2垫走首张 + 防三同张直接接走
    4:  ("中高", ["大单张", "顺子"],       ["对子"]),                                    # 可能是炸弹/两个对子，禁对子；单张威胁不大。优先PASS
    5:  ("中",   ["对子", "三不带", "大单张"], ["单张"]),                                  # 可能是4+1（炸弹+单张），禁单张防垫走
    6:  ("中",   ["三不带"],             ["单张", "对子"]),                              # 可能是5+1(炸弹+单张)或4+2(炸弹+对子)，都禁
    7:  ("低",   ["长顺子", "钢板", "三连对"], []),                                     # TBD: 7张组合多，暂不硬禁
    8:  ("低",   ["长顺子", "钢板", "三连对"], []),                                     # TBD
    9:  ("低",   ["长组合牌"],            []),                                         # TBD
    10: ("低",   ["长组合牌"],            []),                                         # 刚进入警戒区，不硬禁
}
max_end_card = 10  # 残局临界手牌数
```

### 3.2 BAOSHU_RULE：报单/报双封锁

- **落盘**：预处理器注入 `baoshu` 子表（仅 `remaining ≤ 4` 触发）
- **触发源**：`numofplayers[opp_pos] ≤ 4`（V7 已有精确剩牌跟踪，无需代理）

```python
BAOSHU_RULE = {
    1: ("单张(听牌)", ["三带二", "钢板", "连对", "顺子", "炸弹"],  ["单张"]),
    2: ("对子",       ["三带二", "钢板", "连对", "顺子", "炸弹", "三同张"], ["对子"]),
    3: ("三同张",     ["对子", "单张", "钢板", "连对", "顺子", "炸弹"], ["三同张", "三不带"]),  # 禁三不带防三同张接走；3张打不了5张的三带二，移除
    4: ("炸弹/四张",   ["对子", "三带二", "钢板", "连对", "顺子", "炸弹"], ["对子"]),          # 优先PASS；对子最危险（防两个对子），单张威胁不大
}
```

> **通用过滤**：注入 `banned_types` / `baoshu.never_play` 时，必须过滤掉敌人剩牌数无法出的牌型。敌人剩 N 张 → 只能出 ≤N 张的牌型（Single=1, Pair=2, Trips=3, ThreeWithTwo=5, Straight≥5, TwoTrips=6, ThreePair≥6, Bomb≥4, StraightFlush≥5），>N 张的牌型**不出现在 banned 中**。

```python
# 牌型 → 所需张数
_ACTION_TYPE_CARD_COUNT = {
    "Single": 1, "Pair": 2, "Trips": 3, "ThreeWithTwo": 5,
    "Straight": 5, "TwoTrips": 6, "ThreePair": 6,
    "Bomb": 4, "StraightFlush": 5,
}
# 过滤：仅保留敌人能出的牌型
banned_types = [t for t in raw_banned if _ACTION_TYPE_CARD_COUNT.get(t, 99) <= remaining]
```

### 3.3 残局炸弹决策：以残局管线推荐为主，R11 退让

核心原则：**进入残局后，残局管线（预处理器注入的 `_endgame_context`）的推荐决策为第一优先级，R11 全局抑制检查应退让**。

#### 3.3.1 为什么残局管线必须主导炸弹决策

R11 的设计哲学是"等别人压"——检查全局抑制牌剩余、上家让道——这在中局是合理的保守策略。但残局不同：

- 对手 ≤10 张 → 每一轮都可能决定头游归属
- 等一圈可能就送对手走了
- 残局管线的 `recommended_types` / `banned_types` / `baoshu` 已经给出了完整的出牌方向

**R11 在残局时的退让**：当 `_endgame_context.is_active == True`，R11 不应主动过滤炸弹，而应交由残局管线决策。

#### 3.3.2 残局内的炸弹场景与决策

残局管线覆盖以下炸弹相关场景，决策均由 `_endgame_context` 驱动：

| 场景 | 触发条件 | 决策（残局管线推荐） | 优先级 |
|------|----------|---------------------|--------|
| **自己冲刺抢头游** | `self.should_sprint`（两手整牌+有炸） | 出最大整炸（P-H02 解禁），不受任何封锁约束 | Q0 最高 |
| **防对手冲刺** | 敌人 ≤4 张 + 危险等级高 | 炸拦截（R3 防冲刺炸，残局管线确认） | Q1 |
| **报单封锁** | 敌人 =1 张 | 禁出单张，出三带二/钢板锁死 | Q1 |
| **助攻队友** | `teammate.is_close`（队友 ≤4 张） | 出最大牌帮队友压住，送队友能吃下的牌型 | Q2 |
| **非冲刺兜底** | 非上述场景但有炸弹 | should_bomb() 确认「炸完能走+不炸必输」 | Q3 |

#### 3.3.3 「两手整牌」的定义与判定

> **两手整牌**：自己剩余手牌恰好组成 2 个完整牌型，1-2 轮即可清空手牌。

**判定逻辑**（基于 `grouptype_map`）：
- 统计手牌中被组牌引擎标记为整牌型（`Bomb`/`StraightFlush`/`ThreeWithTwo`/`Straight`/`TwoTrips`/`ThreePair`/`Pair`）的组数
- 加上未消耗的散牌数（每种散牌算 1 手）
- 总手数 ≤ 2 → 判定为两手整牌

**典型场景**：剩 9 张 = 5 头炸（5张）+ 三带二（5张含炸弹 overlay 1 张 → 实际 9 张 = 2 手）。炸弹炸完，剩一手三带二直接走完。

#### 3.3.4 should_bomb() — 残局管线内的工具方法

- **位置**：不放入预处理器，作为 `EndgamePreprocessor` 的静态工具方法
- **调用时机**：残局管线在非冲刺场景（两手整牌 / 防冲刺 以外）时，用 `should_bomb()` 做兜底确认

**决策表**（`remaining = my_hand_size - bomb_size`）：

| 炸完能走 (`can_clear \| remaining≤5`) | 不炸必输 (`will_lose`) | 决策 | 含义 |
|:---:|:---:|------|------|
| ✅ | ✅ | **炸** | 炸完能走 + 不炸必输 → 果断炸 |
| ✅ | ❌ | 不炸 | 炸完能走但非必须 → 观察对家 |
| ❌ | ✅ | 不炸 | 不炸必输但炸也走不掉 → 留给对家 |
| ❌ | ❌ | 不炸 | 炸不走+不会输 → 绝对不能炸 |

---

## 四、预处理器逻辑流程

`EndgamePreprocessor` 是一个轻量注入器，不做决策，只注入 `_endgame_context`：

**第一步：四家角色路由**

1. 读取 `game_state["numofplayers"]`（GUA-065 已注入）
2. 计算 `my_pos` / `teammate_pos` / `enemy_positions`
3. **敌方**：遍历 `enemy_positions`，若 `1 ≤ remaining ≤ 10` → 查 `endgame_rule[remaining]` 填充封锁上下文（`danger_level` / `banned_types` / `recommended_types`）；若 `remaining ≤ 4` → 额外填充 `baoshu` 子表
4. **队友**：若 `1 ≤ teammate_remaining ≤ 10` → 填充 `teammate` 助攻上下文（`is_close` / `assist_prefer`）
5. **自己**：填充 `self` 上下文（`has_two_clean_hands` / `has_bomb` / `should_sprint`）
6. `context["is_active"] = any(numofplayers[p] <= 10 for p in range(4))`（任何一家 ≤10 张时激活残局管线）
7. `game_state["_endgame_context"] = context`，返回 game_state

**第二步：is_active 判定口径（触发面 + 硬排除面分离）**

`is_active` **由任何一家 ≤10 张触发**（含自己、队友、敌方），但 `banned_types` 硬排除**仅作用于敌方**：

| 触发场景 | `is_active` | `banned_types` 硬排除 |
|----------|:----------:|:---------------------:|
| 敌方 ≤10 张 | ✅ | **生效**（按 enemies 的 banned_types 过滤 actionList） |
| 队友 ≤10 张（敌方均 >10） | ✅ | 不生效（enemies 为空，无 banned_types 可排） |
| 自己 ≤10 张（其他均 >10） | ✅ | 不生效（enemies 为空） |

这样设计的好处：残局管线统一由 `is_active` 开关控制，`decide()` 只读一个 bool 就知道是否走残局路径，但具体的封锁/助攻/冲刺策略由 `enemies` / `teammate` / `self` 子表分别驱动。

> **注意**：预处理器不修改 `actionList`。`banned_types` / `baoshu.never_play` 的硬排除由 `decide()` 在预处理器之后、Guard 之前执行（见 [[#六、残局管线决策流程]]）。

---

## 五、与 V7 决策管线的关系

```
decide(game_state):
  ① 组牌引擎（grouping_engine）
  ①b MemoryTracker 初始化 + 同步（decide 入口，GUA-078）
      - history/recentPlays 增量回放 → hand_counts
      - publicInfo[i].rest 平台真源覆盖（对齐 M3 GUA-028）
  ② _inject_numofplayers          ← 优先读 MemoryTracker.hand_counts
  ③ 接风记忆
  ④ game_state["_memory_tracker"] 注入（供 R11 / 大单张阈值等）
  ★ EndgamePreprocessor.preprocess()   ← 注入 _endgame_context
  ⑤ GUA-075 _recommend_play（推荐法主路径）
  回退路径: Guard（v7_guards）→ NN → heuristic
```

> **实现订正（2026-06-01）**：原稿将 MemoryTracker 写在 ② 之后，与 §二 数据源优先级矛盾——`MemoryTracker.hand_counts` 必须先于 `_inject_numofplayers` 就绪，否则残局 `enemies` 为空（47750 步62 yf1 有 K 炸却 PASS 根因）。NN 特征路径 lazy init 不足；**decide 入口同步**为真源要求。

**残局优先级硬规则**：按场景分流：

```
第一优先级 ★ 自己冲刺
  └─ self.should_sprint == True → 出最大整炸抢头游，不等任何人
  └─ 此路径不受 banned_types 约束（自己走比封锁更重要）

第二优先级 ★ 封锁敌方（is_active == True）
  └─ enemies 中按四级键排序取最危险（remaining → 下家优先 → baoshu → danger_level）
  └─ decide() 中 banned_types 硬排除 actionList → 被禁牌型一刀切

第三优先级 ★ 助攻队友（teammate.is_close == True）
  └─ 按 assist_prefer 出队友容易接的牌型
  └─ 宁可自己吃一轮也要帮队友走

第四优先级    Guard R01-R14（残局激活时退让）
  └─ 仅做合法性兜底（不出圈/不拆核心牌）

第五优先级    heuristic 回退
```

**各 Guard 在残局时的行为**：

| Guard | 正常行为 | 残局激活时 |
|-------|---------|-----------|
| R08 送队友 | 推荐出最小单张喂队友 | **退让**：若对手剩 1 张（banned_types 含 Single），不出单张；队友助攻时复用 R08 行为 |
| R03 被动不PASS | 强制出牌压过 | **退让**：若 banned_types 含当前推荐牌型，走残局推荐替代 |
| R11 全局抑制 | 等待不炸 | **退让**：残局管线自行决策炸弹（自己冲刺 / 封锁敌人） |
| R01 不出圈 | 拦截非法牌型 | **保留**：始终兜底 |
| card_mask 核心保护 | 禁止拆炸弹核心牌 | **保留**：始终兜底 |

---

## 六、残局管线决策流程（_endgame_context 主导）

```
前置: _endgame_context 注入完毕
       ↓
decide() 读取 _endgame_context
  ↓
┌─────────────────────────────────────────────────────┐
│  残局场景判定（按优先序）                              │
│                                                       │
│  Q0: 自己冲刺？（self.should_sprint）                  │
│    ├─ Yes → 出最大整炸抢头游（不等 R11）               │
│    │         不受 banned_types 约束，自己走 > 封锁敌人    │
│    │        → 直接返回                                │
│    └─ No  → Q1                                        │
│                                                       │
│  Q1: 有敌人进入残局区？（is_active == True）            │
│    ├─ Yes → 取最危险敌人（排序列：remaining>位置>baoshu>danger_level）│
│    │         【第零步】banned_types / baoshu.never_play │
│    │                   硬排除 actionList               │
│    │    ├─ 封锁优先（敌人 ≤10，含 ≤4 时 baoshu 强化）    │
│    │    ├─ 推荐牌型可走 → 按 recommended_types 出       │
│    │    └─ 推荐牌型走不通 → Q2                          │
│    └─ No  → Q2                                        │
│                                                       │
│  Q2: 队友接近头游？（teammate.is_close）                │
│    ├─ Yes → 按 assist_prefer 出牌助攻队友               │
│    │         （宁可自己吃一轮也要帮队友走）               │
│    └─ No  → Q3                                        │
│                                                       │
│  Q3: 有炸弹可选？（非冲刺/封锁/助攻场景）               │
│    ├─ Yes → should_bomb() 确认                         │
│    └─ No  → 按 recommended_types / banned_types        │
│              走常规牌型                                │
└─────────────────────────────────────────────────────┘
  ↓
R11 在此部分退让：_endgame_context.is_active → 产出 should_bomb 建议，与 Q3 综合裁决
  ↓
【方案 A】banned_types 已在 decide() 中一刀切过滤 actionList
  → Guard / GUA-075 只看到过滤后的 actionList，无需额外感知 banned_types
GUA-075 按 _endgame_context.enemies[*].recommended_types 做排序加权
```

**关键设计**：
1. **角色路由**：敌方 → 封锁管线；队友 → 助攻管线；自己 → 冲刺优先，走不了助攻
2. **`is_active` 任何一家 ≤10 触发，`banned_types` 仅作用于敌方**：自己/队友触发残局时不硬排 actionList
3. **方案 A**：`banned_types` 硬排除在 `decide()` 中、预处理器之后、Guard 之前一刀切
4. **自己冲刺最高优**：即使敌人剩 1 张，自己两手整牌也能抢头游——「能走先走，不走再守」
5. **残局场景判定全部收敛在 `_endgame_context` 内**，R11 等通用 Guard 在残局激活时退让

---

## 七、设计校验清单

- [x] `is_endgame(enemy_card_num)` → `is_opponent_in_endgame_zone(remaining)`，语义精确
- [x] 阈值 10 与 V7 自己手牌 ≤10 中局触发对齐，逻辑自洽
- [x] BAOSHU_RULE 触发源为 `numofplayers[opp_pos] ≤ 4`，复用 V7 已有精确剩牌跟踪
- [x] `should_bomb()` 不放入预处理器，保留为静态工具方法
- [x] 不修改 actionList，纯上下文注入，下游自主决策
- [x] 与 V7 已有 `opp_in_danger(≤4)` 急眼逻辑不冲突——≤10 是更宽的警戒超集
- [x] 牌型中文名已映射到 V7 `ACTION_TYPE_*` 枚举
- [x] 残局管线主导：`_endgame_context.is_active` → 残局推荐优先，R11 退让不主动过滤炸弹
- [x] 两手整牌冲刺归属于残局管线内部场景，不是独立于残局之外的 R6 规则
- [x] 残局场景判定收敛在 `_endgame_context` 内：两手整牌 → 防冲刺 → should_bomb 兜底
- [x] 对手报牌状态 = `numofplayers` 读数，不需新建剩牌跟踪
- [x] 【问题四·子问题1】不写新映射层，`_map_types()`（~15行）桥接中文名→V7 ACTION_TYPE 枚举
- [x] 【问题四·子问题2】走 `get_action_type(act)` 分类 actionList，不走 grouptype_map（域不同）
- [x] 【问题四·子问题3】大单张 = K及以上 Single，用 `get_card_value` + `CARD_RANK_ORDER["K"]` 静态判
- [x] 【问题四·子问题3】MemoryTracker 复用：`_resolve_big_single_threshold()` K→Q→J 三级动态降级
- [x] 完整过滤链路 `_filter_by_recommended_types()` 已设计，含大小单张区分 + 动态阈值应用
- [x] 【问题五】残局管线凌驾所有 Guard：冲突时 banned_types 硬排除优先，R08/R03/R11 退让
- [x] 【问题五】优先级链：残局 banned 硬排除 > recommended 软加权 > Guard 合法性兜底 > heuristic
- [x] 【问题五】非靠数字排序，靠 `decide()` 中 banned_types 硬排除 actionList 实现
- [x] 【问题六】知识融入残局管线，删除文档中冗余原型方法代码（类定义/方法体/测试用例）
- [x] 【问题六】保留规则数据（`_SHAPE_NAME_TO_ACTION_TYPES`/`endgame_rule`/`BAOSHU_RULE`）和决策表
- [x] 【问题七·子问题1】「对手」= 敌方两家 `ENEMY_POSITIONS = [(myPos+1)%4, (myPos+3)%4]`，封锁管线不变
- [x] 【问题七·子问题2】队友 ≤10 张 → 助攻管线：`assist_prefer` 送队友能吃下的牌型，不封锁
- [x] 【问题七·子问题3】自己 ≤10 张 → `self.should_sprint` 最高优先（两手整牌+有炸→抢头游），走不了助攻队友
- [x] `_endgame_context` 结构已扩展：`opponents`→`enemies` + 新增 `teammate` / `self` 三区
- [x] `is_active` 任何一家 ≤10 张触发（非仅敌方），`banned_types` 硬排除仅作用于敌方
- [x] 决策优先级：Q0 自己冲刺 > Q1 封锁敌人 > Q2 助攻队友 > Q3 炸弹兜底
- [x] 敌方多人进入残局 → 四级排序键：remaining > 位置(下家更危险) > baoshu > danger_level
- [x] 【问题十】banned_types 取并集（两位敌人的 banned 合并），不能只看主目标
- [x] 【问题十】recommended 冲突：主目标优先，但必须过 banned_set 滤，无剩降级看次目标
- [x] 【问题十】_ACTION_TYPE_CARD_COUNT 过滤：敌人剩 N 张 → banned_types 只保留 ≤N 张的牌型
- [x] BAOSHU_RULE[3] never_play 移除"三带二"（3张敌人打不了5张牌型）
- [x] 【问题十一】手中只有被禁牌型 → 走 Q9 L3，放宽禁令仅保留 baoshu.never_play，打级牌以下从大到小
- [x] 【问题十一】不存在死锁——L3 保底出一张损失最小的牌
- [x] 【问题十二】R11 部分退让：产出 should_bomb 建议给 Q3 综合裁决
- [x] 【问题十二】裁决逻辑：任一方建议炸则炸；R11 高置信(>0.8)说不炸则覆盖 Q3
- [x] 【问题十二】`R11_ENDGAME_MODE` 配置开关：`partial`（当前）/ `full_cede` / `threshold_only`
- [x] 【问题十三】Q1 vs Q2 同牌数冲突暂不开发，留待记忆管线（Memory Pipeline）
- [x] 【问题十三】当前保守策略：同牌数 → Q1 封锁优先，宁可不放敌人
- [x] 【问题十四】GUA-075 残局不加权，纯 NN 赢率排序，看效果再决定
- [x] 【问题十四】`GUA075_ENDGAME_WEIGHTED = False` 配置开关
- [x] 【问题十五】Q1 recommended 多牌型排序：有回收的优先（低段诱敌，高段回收出牌权——适用单张/对子/三张/三带二/三连对/顺子）
- [x] 【问题十五】无回收按张数多优先，同张数按牌力值排序
- [x] 【问题十五】回收优先同样复用于领出牌阶段（通用出牌原则）
- [x] 【问题十五】残局领出：牌型受限 → 级牌以下从大到小；非残局领出：不受限 → 回收优先（有回收的低段）
- [x] 【问题十六】Q0 冲刺出牌顺序：按出牌权 + 对手残局状态 + 整牌顶点/张数动态选先炸或先整
- [x] 【问题十六】出牌权在我手+敌未进残局 → 先整后炸；敌进残局+同张数+低段(≤K) → 先炸后整
- [x] 【问题十六】出牌权不在我手+敌未进残局 → 不急于炸，让对手出一手可能赚牌型；敌进残局 → 必须先炸
- [x] 【问题十七】Q2 assist_prefer 排序与 Q1 统一：回收优先 → 张数多优先，共用 `_sort_by_recapture_first()`
- [x] 【问题十七】保留回收 = 保留助攻能力（敌人压低段→高段回收→再助攻一轮）
- [x] 【问题二十一】Q2 精确投喂表：1张→单张 / 2张→对子 / 3张→三张→对子→单张(降级) / 4张→对子 / 5张→顺子+三带二
- [x] 【问题二十一】3 张降级路径：投喂三张→PASS→投喂对子→PASS→投喂单张，逐级缩小可能牌型
- [x] 【问题二十一】`_assist_prefer_for()` 重写为精确匹配（不再用 ≤ 宽松区间）
- [x] 【问题二十二】R03 残局退让规则：当前轮牌型 ≠ 敌人致命牌型 → PASS 安全（不同牌型不能压制）→ 让队友处理
- [x] 【问题二十二】R03 残局退让规则：当前轮牌型 == 敌人致命牌型 → 必须压（用最大牌压，压不住认栽）
- [x] 【问题二十二】伪代码 `_r03_endgame_retreat()`：牌型不同 PASS → 牌型相同最大牌压
- [x] 【问题二十三】切换一：进入残局自动切换（11→10，预处理器每轮读 numofplayers，当轮立刻生效）
- [x] 【问题二十三】切换二：敌人头游自动清空封锁目标（enemies 变空，Q1 跳过——敌人都下场了防空气）
- [x] 【问题二十三】切换三：每副牌独立重置（新副牌 27 张起手，is_active 回到 False）
- [x] 【问题二十三】is_active 单向性：本副牌内 True 不翻回 False（手牌只减不增）
- [x] 【问题二十四】endgame_rule banned_types 修正：6张→[单张,对子] / 5张→[单张] / 4张→[对子,优先PASS] / 3张→[单张,三不带]
- [x] 【问题二十四】BAOSHU_RULE 同步：4张 never_play=[对子]、block_with 加入对子；3张 never_play 加入三不带
- [x] 【问题二十四】ban 推理链：基于"敌人最可能牌型"反推致命喂牌（如6=5+1/4+2→禁单张+对子）
- [x] 【问题二十四】查表即动态调整：remaining 是键，不手写 if-else
- [x] 【问题二十五】两手整牌判定：组数 = sum(grouptype_map.values())，≤2 即两手整牌
- [x] 【问题二十五】对+对+单 = 3手（三个独立组），不是 2 手；炸弹一手不合并其他牌型
- [x] 【问题二十五】两手整牌示例表：KKKK+88(2手✅) / KK+88+33(3手❌) / 4444+5(2手✅)
- [x] 【问题二十六】残局 R10 领出禁炸退让：is_active + should_sprint → R10 退让，允许领出炸弹
- [x] 【问题二十六】冲突优先级：残局冲刺(1) > R11退让(2) > R10禁领出(3)
- [x] 【问题二十六】进入残局以残局管线为准，R10/R11 都退让——和 R11 冲突解决一致
- [x] 【问题二十七】4张主动轮降级：有顺子出顺子(封锁) > 无长牌出单张(安全) > 有炸炸不压四 > 全被禁两手整牌冲刺无视banned
- [x] 【问题二十七】伪代码 _decide_4card_active_round()：安全牌走推荐 → 全被禁能冲刺放宽banned → 不能冲刺走L3
- [x] 【问题二十七】核心原则：有安全牌走安全牌 → 全被禁能冲刺走冲刺 → 不能冲刺走 L3 降级
- [x] 【问题十八】`can_clear`：组牌引擎判剩余手数 ≤1 或剩余牌是炸弹 → True
- [x] 【问题十八】`will_lose`：敌人剩余 ∈ {1, 2, 3, 5} 致命张数（一手牌直接走）→ True
- [x] 【问题十八】4 张规则：炸不压四（火不打四）——敌人 4 张极可能炸弹，一般不炸
- [x] 【问题十八】炸不压四例外：自己两手牌可冲刺 OR 炸弹 ≥ J 仍可压制冲刺
- [x] 【问题十九】Q3 兜底主动领出：非残局回收优先（有回收的低段→高段回收出牌权）
- [x] 【问题十九】Q3 兜底被动跟牌：看牌力角色——助攻小跟清弱牌，主攻大跟压制+投喂队友
- [x] 【问题十九】此规则为通用出牌策略，同样适用于开局阶段和中期阶段
- [x] 【问题二十】残局封锁阈值 = ≤10（与 is_active 统一），≤4 是 baoshu 子规则强化，非封锁触发条件
- [x] 【问题二十】block_with 是推荐封锁牌型（非限制），走不通时出任意非 banned 牌型即可——不是同牌型也能压制
- [x] 【问题二十】伪代码：先 block_with 推荐 → 再任意非 banned → 极限走 Q9 L3
- [x] 【问题八·方案A】`banned_types` 硬排除在 `decide()` 中、预处理器之后、Guard 之前一刀切
- [x] 【问题八·方案A】伪代码：`actionList = [a for a in actionList if get_action_type(a) not in banned_set]`
- [x] 【问题八·方案A】`banned_set` 合并 enemies 的 `banned_types` + `baoshu.never_play`，enemies 为空则不排
- [x] 【问题九】三级降级：L1 有炸出炸 > L2 被动 PASS > L3 放宽为仅 baoshu.never_play 硬禁，打级牌以下从大到小
- [x] 【问题九】炸弹永不在 banned_set 中（BAOSHU_RULE block_with 含炸弹，never_play 不含）

---

## 八、参考场景

### 8.1 策略参考（设计调研）

| 场景 | 来源 | 核心教训 |
|------|------|---------|
| intermediate_01「炸弹时机」 | guandan.nullkit.com | 上家出顺子→你有4个8→PASS，让下家去压 |
| beginner_09「报单后怎么防」 | guandan.nullkit.com | 下家报单剩单2→出三带二锁死 |
| intermediate_04「堵下家的路」 | guandan.nullkit.com | 下家报双剩对Q→出钢板锁死 |

### 8.2 文档边界：设计调研 vs 调试发现

> 本文档由 Agent **一口气二十余轮设计问答**沉淀（见 §七「问题四～二十七」等），在**策略、数据结构、Guard 退让、Q0→Q3 分派**上覆盖面已较全。
> 但有一类缺陷**静态设计审不出来**，必须靠牌谱回放、断点、`pytest` 或批跑才能暴露——属于**管线集成 / 数据源 / 激活条件**，而非规则表写错。

| 类别 | 典型表现 | 本仓实例 |
|------|----------|----------|
| **注入顺序** | 文档 §二 与 §五 文字一致，实现却 lazy init 在错误路径 | GUA-078：`MemoryTracker` 须在 ② `_inject_numofplayers` 之前（decide 入口 ①b） |
| **数据源缺失** | 策略正确，但 `numofplayers` 全 27 → `enemies={}` → 残局未激活 | 47750 步62：yf1 有 K 炸却 PASS；notify 录制 `publicInfo=[]`，live act 需 `publicInfo.rest` |
| **Guard 抢先** | Q1 逻辑无误，但未进残局时 R11 仍「对手 Bomb → 不跟」 | 同上根因链：激活失败 → 走 GUA-075/R11 而非 Q1 封锁炸 |
| **子规则副作用** | `banned Single` 在 numof 正确时误滤封锁用大单 | 步64 类场景（与步62 不同 bug，待单独修） |

**分工**：§一～§七 回答「**上下文正确时**该怎么打」；§8.2 + 牌谱回归回答「**decide() 入口是否真有这份上下文**」。改策略前先看残局是否 `is_active`；改集成后必须用 `tests/test_gua078_*` 与真实 replay 步号复验。
