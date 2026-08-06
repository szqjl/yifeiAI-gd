# GUA-206 完成定义

> **GUA-206**：残局 Q1 出完整同花顺/炸弹被判「拆核心」→ 强压敌炸被 PASS（组牌 H2 配子 SF 与平台真实牌 SF 牌面不同被误判）
> **登记**：2026-08-06
> **严重级别**：P1
> **关联**：GUA-199（拆核心打弱牌拦截，`_action_breaks_core_structure` 同源）、GUA-124（平台 actionList 未枚举 latent SF）、GUA-192（跟牌轮漏 SF 候选）、GUA-205（中局开炸）、`src/v/nn/features/grouping_engine.py`（`_score_power` 同花顺 +3 / 普通炸弹 +2）

---

## 1. 问题描述

### 1.1 复现

match `6a74198a27e7bf01db12e8e6`（2026-08-06 13:20，`logs/v8_vs_botzone_20260806_130855.log`）：

- V8 手牌 16 = `C3, C5, C6, D3, D6, D7, H2, H3×2, H4×2, S2, S3, S4, S5, SA`（初始 27 出过 D9 / Bomb K / HJ,DJ / HA,CA / HQ,SQ 后剩余）

**step 20**（13:20:45，4号出 `Bomb/9` 5星炸后剩 1 张报单）：

- actionList 仅 `{PASS:1, StraightFlush:2}`（5星炸只能同花顺/更大炸压）
- GUA-124 警告 `latent=[['SA', 'S2', 'S3', 'S4', 'H2']]`（组牌可见可压敌炸但平台 actionList 未枚举）
- `Q1 封锁拆整牌(StraightFlush) → PASS`，残局管线命中 PASS

**step 22**（13:20:50，2号出大王 `HR` 后剩 5 张）：

- actionList `{PASS:1, Bomb:2, StraightFlush:2}`，greater=`Single/R`
- `Q1 封锁拆整牌(Bomb) → PASS`

### 1.2 根因链

```
组牌引擎 best_plan（手牌16，curRank=2）：
  straight_flushes = [['SA','S2','S3','S4','H2']]   ← 用 H2 配子补黑桃5
  group_members[1] = ['SA','S2','S3','S4','H2']     ← SF 核心组
  group_members[3] = ['C5','S5']                    ← 真实 S5 被分进对子组
  group_type_map[1] = 'StraightFlush'

平台 actionList 枚举完整同花顺（真实牌）：
  ['StraightFlush','A',['SA','S2','S3','S4','S5']]  ← 用真实黑桃5

_action_breaks_core_structure（endgame_decide.py:3248-3286）：
  CORE_TYPES 含 'StraightFlush'、'Bomb'
  action_cards_set = {SA,S2,S3,S4,S5}
  SF 组 members_set  = {SA,S2,S3,S4,H2}
  overlap = {SA,S2,S3,S4}  !=  members_set → return True（误判拆核心）
  → Q1 封锁拆整牌(StraightFlush) → PASS
```

**本质**：组牌引擎优先组同花顺、用 H2 配子补 SF；平台 actionList 用真实牌组同一副同花顺。两张同花顺**牌力完全等价**（同为 A2345 黑桃同花顺），但 `_action_breaks_core_structure` 用 `set` 精确比较牌面，配子牌 `H2` 与真实牌 `S5` 一换 → overlap ≠ members_set → 误判「拆核心」→ 强压敌炸被 PASS。

### 1.3 为什么是问题

- **同花顺是炸弹的一种**，牌力关系为：**同花顺 > 5星炸 > 4星炸 > 其他牌型**（见 AGENTS「掼蛋牌型大小关系（强制）」；组牌引擎 `_score_power` 中同花顺 +3、普通炸弹 +2 已体现）。
- 出**完整**同花顺/炸弹 = 用核心整牌压制敌人（bomb_family 可跨型压杂牌，GUA-131），**绝不可能是「拆核心打弱牌」**。
- GUA-199 要拦的是「444+H2 拆 H2 打 22 对子」这类**把炸弹核心当弱牌打**的动作（action 是 `Pair` 等非炸弹型）。把「出完整 SF/Bomb」一起误拦 = 残局火力白送。

---

## 2. 修复方案

### 2.0 核心思路

`_action_breaks_core_structure` 开头对**完整炸弹类动作**（同花顺 / 炸弹）直接豁免：完整 SF/Bomb 本身就是最高等级核心整牌，出它们 = 用核心压敌，不可能破坏 core 结构。非炸弹类动作（Pair/Single/Straight/Trips/TWT 等）仍按原逻辑判定，GUA-199 拦截不受影响。

### 2.1 代码修改（`src/v/nn/endgame/endgame_decide.py`）

在 `_action_breaks_core_structure`（L3248）开头新增豁免：

```python
@staticmethod
def _action_breaks_core_structure(action, game_state):
    """检查出牌是否会破坏 core 整牌结构。
    ...
    """
    # GUA-206: 完整炸弹/同花顺本身就是最高等级核心整牌（同花顺 > 5星炸 > 4星炸，
    # 组牌引擎 _score_power 同花顺 +3、普通炸弹 +2 已体现该大小关系）。
    # 出完整炸弹类动作 = 用核心整牌压制敌人，绝非 GUA-199 要拦的「拆核心打弱牌」
    # （如 444+H2 拆 H2 打 22 对子，那类 action 是 Pair 等非炸弹型，不受豁免）。
    # 背景：组牌引擎优先组同花顺、用 H2 配子补 SF（[SA,S2,S3,S4,H2]），而平台
    # actionList 枚举真实牌 SF（[SA,S2,S3,S4,S5]）——两张同花顺牌面 set 不同，
    # 若不豁免会被误判「拆核心」→ 强压敌炸被 PASS（match=6a74198a step20/22）。
    if _is_bomb_like_action(action):
        return False
    group_members = game_state.get("_group_members")
    ...
```

### 2.2 为什么安全（不改破既有拦截）

| 场景 | action 类型 | 是否豁免 | 行为 |
|------|------------|---------|------|
| 完整同花顺（真实牌，step20） | `StraightFlush` | ✅ 豁免 | Q1 可压 5星炸 |
| 完整同花顺（H2 配子，step20 组牌版） | `StraightFlush` | ✅ 豁免 | 同上 |
| 完整炸弹（step22） | `Bomb` | ✅ 豁免 | Q1 可压大王 |
| GUA-199：444+H2 拆 H2 打 22 对子 | `Pair` | ❌ 不豁免 | 仍拦截 PASS |
| 拆三带二打普通顺子（Q3 最省压） | `Straight` | ❌ 不豁免 | 仍拦截 PASS |
| 拆核心打对子/单张（Q0/Q1） | `Pair`/`Single` | ❌ 不豁免 | 仍拦截 PASS |

判定依据 `_is_bomb_like_action`（L469-481）：声明类型为 `Bomb`/`StraightFlush`（含守卫 `get_action_type` 兜底）→ 豁免；Pair/Single/Straight/Trips/TWT 等一律不豁免。

### 2.3 与既有逻辑的边界

- **`_q1_block_enemy`（L1278-1293）**：Q1 返回候选后仍走 `_action_breaks_core_structure` 校验，豁免后完整 SF/Bomb 候选直接放行（不再强制换 PASS）。
- **`_q3_bomb_fallback`（L3172）**：Q3「最省压牌拆整牌 → PASS」针对的是 `_find_cheapest_press` 返回的普通牌型，若最省压是 Bomb 类（完整炸弹）→ 豁免，放行压制；非炸弹型最省压仍 PASS。
- **GUA-199（L3268-3274 注释场景）**：拦截对象 action 是 `Pair`（打 22 对子），不触发豁免，行为不变。
- **GUA-124（平台未枚举 latent）**：本修复只解决「actionList 已枚举、但被拆核心误判」的拦截；actionList 根本未枚举 latent SF 的平台侧问题仍由 GUA-124/192 体系追踪。

---

## 3. 验收

### 3.1 新 pytest（`tests/test_gua206_sf_bomb_exempt_break_core.py`，5 用例全绿）

| # | 用例 | 期望 |
|---|------|------|
| 1 | `test_full_straight_flush_real_cards_not_break`：完整同花顺（真实黑桃 A2345，与组牌 H2 配子版牌面不同） | 不判拆核心（False） |
| 2 | `test_full_straight_flush_wild_cards_not_break`：完整同花顺（H2 配子补黑桃5，与组牌一致） | 不判拆核心（False） |
| 3 | `test_full_bomb_not_break`：完整炸弹 | 不判拆核心（False） |
| 4 | `test_gua199_pair_break_still_blocked`：444+H2 拆 H2 打 22 对子（Pair） | 仍拦截（True） |
| 5 | `test_ordinary_straight_break_still_detected`：拆三带二核心打普通顺子 | 仍拦截（True） |

复现数据取自 match `6a74198a` step20 组牌产出：`group_members` SF 组 `['SA','S2','S3','S4','H2']`、真实 S5 分进对子组。

### 3.2 回归

- `pytest tests/test_gua069_weak_role_core_protection.py tests/test_gua066_no_lead_bomb.py tests/test_gua202_lead_feed_teammate.py tests/test_gua154_duplicate_card_cross_group.py tests/test_gua116_main_attack_lead.py`
- 59 通过；1 失败（`test_steel_plate_small_net_positive`）经 git stash 验证为**改动前已存在**、与本次无关。

### 3.3 实局/批跑

1. 重启 Botzone 监听（WF-14）加载新代码。
2. 复现场景（match `6a74198a` 同型：残局手牌含 H2 配子 SF + 完整炸弹，敌方出 5星炸/大王）应改为出 SF/Bomb 压敌，不再 PASS。
3. 净盘 V8 批跑验证队胜率 KPI 不回退（`v8-win-rate-history.md` 记录）。

---

## 4. 影响面

- 仅影响 `_action_breaks_core_structure` 对**完整炸弹类动作**的判定；非炸弹类（Pair/Single/Straight/Trips/TWT）拆核心判定完全不变。
- Q0/Q1/Q2/Q3 各阶段、中局/残局/领出各阶段共用此函数；豁免只放开「完整 SF/Bomb 出牌」，不新增动作类型、不触碰 banned_set / R10 / R11。
- 平台侧「actionList 未枚举 latent SF」仍归 GUA-124/192 体系，本修复不覆盖。
