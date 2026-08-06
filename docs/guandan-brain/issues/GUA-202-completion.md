# GUA-202 完成定义

> **GUA-202**：敌方报单领出时 Q1 `_q1_enemy_critical_lead_special` 整牌锁敌抢跑，队友剩 2 张却不出对子（Q2 送牌永远到不了）
> **登记**：2026-08-06
> **严重级别**：P1
> **关联**：GUA-189（Q2 喂牌排序 + P1-P4 领出喂牌）、GUA-117（assist_prefer 单一真源）、GUA-190（敌方报单炸弹封死）、`src/v/nn/endgame/endgame_decide.py`（残局管线 L1247-1273、`_q1_enemy_critical_lead_special` L2264-2319、`_select_enemy_one_locking_structure` L2458-2479、`_q1_structure_priority` L735-747）、`src/v/nn/assist_prefer_table.py`

---

## 1. 问题描述

### 1.1 复现

match `6a73e53d27e7bf01db12c646`（2026-08-06 09:37:43，`logs/v8_vs_botzone_20260806_092556.log` [255] 领出轮）：

- V8 领出（上手自己 Trips/J），手牌 11 = `S3` + `888`(S8,C8,C8) + `99`(D9,H9) + `TTT`(DT,DT,ST) + `AA`(HA,SA)，actionList len=29 含 **6 种 Pair**
- 队友 player2 剩 **2 张**（`is_close` 成立，`assist_prefer=["Pair"]`）
- 敌方 player1 剩 9 张、player3 剩 1 张（报单）

实际决策（日志 264 行）：`Q1 封锁敌方: idx=18 type=ThreeWithTwo` → 出 `['S8','C8','C8','D9','H9']`（888+99），**未送对子**。

### 1.2 根因链

```
残局管线（endgame_decide.py:1227-1273）：
  Q0.5 一手清 → Q0 自己冲刺 → Q1 封锁敌方(enemies 非空即抢跑) → Q2 助攻队友(is_close) → Q3 炸弹兜底

本局：
  Q1 命中（P1/P3 均 ≤10 入残局区）
  └─ Q1 内主敌 = player3（剩 1 张，endgame_rule[1]=("极高",["最大单张"],[])）
     ├─ recommended 分支（L1704）【优先级低】
     └─ _q1_enemy_critical_lead_special（L1694，位于 recommended 之前）★命中
        ├─ remaining==1 ✓，_is_my_q1_lead_turn ✓
        ├─ structured 候选（整牌）优先于单/对（L2283-2311）
        │  └─ _select_enemy_one_locking_structure（L2458-2479）
        │     └─ key=(_q1_structure_priority, bomb_destroy, -张数, 牌力)
        │        → ThreeWithTwo=1 最高 → 选中 888+99
        └─ 直接 return → Q2 送对子永远到不了
```

**本质**：Q1 内「敌方报单 + 我领出」整牌锁敌特判，没有「队友也 close 时应优先送牌」的检查。`recommended_types=["最大单张"]` 是**非直接原因**（该分支优先级低于 critical_lead_special）。

### 1.3 为什么是问题

- 队友剩 2 张 = 极可能对子，送对子（`99` 或 `AA`）让队友一手接走 → 队友头游（我方赢）。
- 实际出 888+99 TWT：队友 2 张接不住 TWT，P1 有 9 张可能捡牌，V8 被迫再战，机会损失。
- **注**：整牌锁敌本身是防御性正确行为（防 P3 报单接牌头游），故 P1 而非 P0。

---

## 2. 修复方案（方案①：Q1 领出轮队友 close 优先送牌）

### 2.1 新增特判方法 `_q1_lead_feed_teammate_special`

在 `_q1_block_enemy` 中，**位于 `_q1_enemy_critical_lead_special`（L1694）之前**插入调用：

```python
# ④.5d GUA-202：我方领出 + 队友 close → 优先送牌（防整牌锁敌抢跑）
lead_feed = self._q1_lead_feed_teammate_special(
    game_state, non_banned_candidates, ec,
)
if lead_feed is not None:
    return lead_feed
```

方法实现（示意）：

```python
def _q1_lead_feed_teammate_special(
    self,
    game_state: Dict[str, Any],
    candidates: List[Tuple[int, List]],
    ec: Dict[str, Any],
) -> Optional[Tuple[int, List]]:
    """GUA-202：我方领出轮 + 队友 is_close → 优先按 assist_prefer 送牌。

    仅当满足以下全部条件才送（否则放行给整牌锁敌）：
      1. 本回合是自由领出（_is_my_q1_lead_turn）
      2. 队友 is_close（1-5 张）
      3. 送牌候选不拆我方核心整牌结构（不拆弹、不拆 TWT/Trips core）
      4. 送牌候选在 assist_prefer 内且非 banned
    """
    if not GUARD_TOOLS_OK:
        return None

    my_pos = ec.get("my_pos", game_state.get("myPos", 0))
    if not self._is_my_q1_lead_turn(game_state, my_pos):
        return None

    teammate = ec.get("teammate", {})
    if not teammate.get("is_close"):
        return None

    assist_prefer = teammate.get("assist_prefer", [])
    if not assist_prefer:
        return None

    # 送牌候选 = assist_prefer 内且不拆核心结构的合法动作
    feed_candidates: List[Tuple[int, List]] = []
    hand_cards = list(game_state.get("handCards", []) or [])
    for idx, act in candidates:
        try:
            atype = get_action_type(act)
        except Exception:
            continue
        if atype == ACTION_TYPE_PASS:
            continue
        if atype not in assist_prefer:
            continue
        if self._is_bomb_destroying_action(act, hand_cards):
            continue
        if atype in ("Bomb", "StraightFlush", "JokerBomb"):
            continue
        feed_candidates.append((idx, act))

    if not feed_candidates:
        return None

    # 队友报单(1张)时：若下家/关键敌可能接走大单 → 不送（防截胡）
    remaining = int(teammate.get("remaining", 0) or 0)
    if remaining == 1:
        safe = self._select_enemy_one_safe_single(feed_candidates, game_state, ec)
        if safe is None:
            return None
        return safe

    # 复用 Q2 的 prefer 排序：回收优先 → 取最优
    cur_rank = str(game_state.get("curRank", "2"))
    ordered = _sort_by_recapture_first(feed_candidates, hand_cards, cur_rank)
    if not ordered:
        return None
    logger.info(
        "Q1 领出送队友(GUA-202): idx=%d type=%s",
        ordered[0][0], get_action_type(ordered[0][1]),
    )
    return ordered[0]
```

### 2.2 安全约束设计（关键）

| 约束 | 理由 | 实现 |
|------|------|------|
| **仅自由领出** | 跟牌轮送牌会被 P1/P3 压，Q2/既有逻辑已覆盖 | `_is_my_q1_lead_turn` |
| **仅队友 close** | 队友不近时送牌无意义 | `teammate.is_close` |
| **不拆核心结构** | 送牌不能拆 888/TTT 等 core 组，否则后续失手 | `_is_bomb_destroying_action` |
| **不送炸** | 炸弹是回手/锁敌资源，不可用于喂牌 | 显式排除 Bomb/SF/JokerBomb |
| **队友报单时安全单过滤** | 送单张可能被敌方截胡，须确认当前无外部压制 | `_select_enemy_one_safe_single` |
| **候选须在 non_banned 内** | 不违反 Q1 banned 语义 | 直接复用 `non_banned_candidates` |

### 2.3 与既有逻辑的边界

- **Q0/Q0.5 优先不变**：若手牌能一手清 / 自己冲刺，仍先走 Q0.5/Q0（管线 L1227-1245），本特判只在落到 Q1 后才生效。
- **`_q1_hold_teammate_max_control`（L1983）不受影响**：那是「队友已控牌时 Q1 不让道」，本特判是「我领出时主动送」，场景互补。
- **`_q1_enemy_critical_lead_special` 仍保留**：仅当送牌不成立（如无 safe single / 无 prefer 候选 / 拆核）时才轮到整牌锁敌。若队友 2 张、我方有对子不拆核 → 送对子优先；若送牌候选全部拆核或不存在 → 回退整牌锁敌（保持 GUA-183/190 防御语义）。
- **Q2 仍保留**：本特判只覆盖 Q1 抢跑场景；Q1 未命中时 Q2 照旧。两处共用 `pick_assist_feed_by_prefer` / `_sort_by_recapture_first`，排序语义一致。

---

## 3. 验收

### 3.1 新 pytest（`tests/test_gua202_lead_feed_teammate.py`）

| # | 用例 | 期望 |
|---|------|------|
| 1 | 复现局：领出 + 队友 2 张 + 手 `S3,888,99,TTT,AA` + actionList 含 6 Pair | `_q1_block_enemy` 返回 Pair（99 或 AA，回收优先），非 ThreeWithTwo |
| 2 | 同手牌但队友 6 张（非 close） | 不触发送牌，回退 `_q1_enemy_critical_lead_special`（出 TWT 888+99） |
| 3 | 队友 2 张但领出候选全是拆核（如只剩 Pair 由 TWT 拆出） | 不送牌，回退整牌锁敌 |
| 4 | 队友报单(1张) + 手有安全单 | 送安全小单 |
| 5 | 队友报单(1张) + 唯一单张会被敌压制 | 不送，回退锁敌/强单 |
| 6 | 跟牌轮（非领出）队友 2 张 | 不触发（走 Q1/Q2 原有逻辑） |
| 7 | 领出 + 队友 2 张 + 手有 Pair 但该 Pair 为 `_action_breaks_core_structure` | 拦截为 PASS 或不送（保持拆核保护） |
| 8 | 回归：原 GUA-190 场景（跟牌压单开炸）仍开炸 | `_q1_block_enemy` 仍 Bomb |

### 3.2 回归

- `pytest tests/test_botzone_adapter.py tests/test_gua078_endgame_tracker_decide_entry.py tests/test_gua091_*.py tests/test_gua112_finish_now_banned_exempt.py tests/test_gua189_*.py tests/test_gua190_enemy_one_bomb_lock.py tests/test_gua116_main_attack_lead.py tests/test_gua117_assist_prefer_pipeline.py`
- 目标全绿；预存失败（`test_steel_plate_small_net_positive` 等）确认与本次无关。

### 3.3 实局/批跑

1. 重启 Botzone 监听（WF-14）加载新代码。
2. 复现场景（手 888+99+TTT+AA、队友 2 张、V8 领出）应改为出 Pair 送队友。
3. 净盘 V8 批跑验证队胜率 KPI 不回退。

---

## 4. 影响面

- 仅影响 **Q1 领出轮 + 队友 close + 有安全送牌候选** 的场景；跟牌轮、Q0/Q0.5、Q2、Q3 路径不变。
- 不触碰 banned_set / protected_types 语义（直接复用 non_banned_candidates）。
- 不新增动作类型或协议字段。
