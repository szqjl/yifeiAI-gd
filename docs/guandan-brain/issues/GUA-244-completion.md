# GUA-244 残局「池推理 → 对子/单决策」接线方案

> 登记：2026-08-15 · 状态：方案已定，待实施
> 对局：match `6a8003e60fbd680d7c754f20`（2026-08-15 14:15）
> 日志：`logs/v8_vs_botzone_20260815_141037.log` L188 / L201-203

## 一、问题定义

V8=player2 手牌 10 = `D5 C6 66 77 + TWT(AAA+JJ)`，自领出，主敌 p1 剩 2、p3 剩 6、队友 p0 剩 7（numofplayers=`[7,2,10,6]`）。

决策链（日志实证）：
1. `14:15:15#2` Q1 封锁 `idx=10 type=ThreeWithTwo` → TWT(AAA+JJ) 锁敌（L188，**正确**——p1 两牌凑不成炸弹，必接不住）。
2. `14:15:16` Q1 封锁 `idx=3 type=Single` → 领出 `C6`（L201-203，**败因**）→ p1 用**级牌 D2** 接走、再 S8 走完 → 头游，V8 末游，scores=[0,3,0,3]。

**为什么选了 C6 而不是 66/77**（`_q1_enemy_critical_lead_special`，L3060）：
```
structured = 对子 [66, 77]
  ├─ _select_two_turn_sprint_structure → None（4 手 ≠ 2 手）
  ├─ _select_enemy_one_locking_structure → Pair/66
  └─ GUA-220 gate：best_lock 是 Pair → _q1_downseat_two_single_first(singles)
        → 下家 p3 剩 6 ≠ 2 → 返回 None（GUA-220 只护下家，危险敌人 p1 是侧位）
  ↓
safe_single = _select_enemy_one_safe_single(singles) → Single/C6
  └─ _seat_may_hold_single_above(p1, '6', ...)
        → 依赖 tracker.card_state（MemoryTracker 每 request 只重放当前圈，整场牌谱从未进入）
        → card_state 为空 → 返回 False → C6 被误判「外部无压制安全单」
```

**根因**：残局的「单 vs 对」决策完全建立在**空的记忆**上。`_seat_may_hold_single_above` 想回答「p1 手里有没有牌压 C6」，但手里有没有牌它根本不知道（MemoryTracker 失忆），于是默认安全 → 低单送进 2 张敌人。

## 二、池真相（干净解析器实证）

从日志重建目标时刻各席已出（与「决策:」行交叉校验，解析器已出=决策行并集，一致）：

| 席 | 已出 | 剩余 |
|----|------|------|
| p0 队友 | 20 | 7 |
| p1 主敌 | 25 | **2** |
| p2 V8 | 17（含 Bomb/Q） | 10（目标时刻手牌） |
| p3 敌 | 21 | 6 |

剩余池 15 张（108 ints − 全席已出 − V8 当前手牌，name 级每名 2 副本）：

```
C8  CA CA  CK  CT  D2  D5  D7  DK  DQ  H8  HJ  S5  S8  SQ
rank: 2×1(级牌D2)  5×2  7×1  8×3  T×1  J×1  Q×2  K×2  A×2
```

p1 两张（C(15,2)=105 组合）：
- 持对子：55/88/QQ/KK/AA 共 **7/105 = 6.7%**
- 持 >66 对子：88/QQ/KK/AA 共 **6/105 = 5.7%**；持 >77 对子同 **6/105 = 5.7%**
- 至少 1 张 >5 或级牌（压 D5/C6）：**104/105 = 99.0%**

**结论：出单被 p1 接走的概率 99%，出对子被 p1 接走仅 5.7% —— 对子先于单约 17× 安全。** 数据同时解释了实际败因：池中有未出的级牌 D2，任何低单（C6）都必然被级牌压。

## 三、接线方案（四段）

### A. 数据接线：adapter 注入剩余池

`src/communication/botzone_adapter.py`

1. **新增 `_compute_remaining_pool`**（放 `_compute_numofplayers` L1258 旁）：

```python
def _compute_remaining_pool(self, game: "BotzoneGameState",
                            hand_cards: List[str]) -> List[str]:
    """GUA-244：name 级剩余池 = 108 ints − 各席已出 − 当前手牌。

    Botzone 每副 27 张、每张牌名 2 副本（int i 与 i+54 同牌名）。
    返回展开的牌名列表（按 rank 升序）；供引擎/残局决策做对手残牌构成推理。
    """
    from collections import Counter
    played: Counter = Counter()
    for seat in range(4):
        for i in game.played_cards.get(seat, set()):
            if 0 <= i <= 107:
                played[bz_to_v8_card(i)] += 1
    hand: Counter = Counter(hand_cards or [])
    pool = []
    for name in _POOL_NAME_ORDER:          # S2..CA + SB/HR 全 54 名
        cnt = 2 - hand.get(name, 0) - played.get(name, 0)
        pool.extend([name] * max(0, cnt))
    return pool
```

2. **game_state 注入**（L1856-1875 构造处加一个字段）：

```python
"remainingPool": self._compute_remaining_pool(game, hand_cards),
```

> 数据源 `game.played_cards` 已由 `_accumulate_played_cards`（L1251）整场累计，仅需一个字段传下去，零新采集。

### B. 引擎注入 + 校验

`src/v/nn/ultimate_win_rate_engine_v7.py`

1. `decide()` L588（`_inject_numofplayers` 之后）追加调用：

```python
self._inject_numofplayers(game_state)
self._inject_remaining_pool(game_state)   # GUA-244
```

2. **新增 `_inject_remaining_pool`**（放 `_inject_numofplayers` L1602 旁）：

```python
def _inject_remaining_pool(self, game_state: Dict[str, Any]) -> None:
    """GUA-244：注入 name 级剩余池 → game_state['_remaining_pool_cards']。

    一致性校验（防污染，校验失败自动回退 None，决策层走原逻辑）：
      1. 池总张数 == 其余三家 numofplayers 之和（池 = 对手残牌全集）
      2. 每张牌名 ≤ 2 副本（两副牌约束）
    v1006 线无 remainingPool 字段 → 校验失败 → None，行为不变。
    """
    pool = game_state.get("remainingPool")
    if not isinstance(pool, list) or not pool:
        game_state["_remaining_pool_cards"] = None
        return
    try:
        from collections import Counter
        cnt = Counter(pool)
        if any(c > 2 for c in cnt.values()):
            raise ValueError("副本数 >2")
        nop = game_state.get("numofplayers", [27, 27, 27, 27])
        my_pos = game_state.get("myPos", self.player_id)
        others = sum(nop) - len(game_state.get("handCards", []) or [])
        if len(pool) != others:
            raise ValueError(f"池张数 {len(pool)} != 对手剩余 {others}")
        game_state["_remaining_pool"] = dict(cnt)
        game_state["_remaining_pool_cards"] = sorted(pool)
    except Exception:
        game_state["_remaining_pool_cards"] = None
```

> 校验失败静默回退，保证 v1006 线与池异常时零回归。

### C. 决策层：池风险 + 对子/单编排

`src/v/nn/endgame/endgame_decide.py`

1. **新增两个概率 helper**（放 `_select_enemy_one_safe_single` L3744 附近）：

```python
GUA244_SINGLE_RISK = 0.7   # 单被接风险阈值
GUA244_PAIR_RISK = 0.3     # 对子被接风险阈值
GUA244_ENUM_POOL_MAX = 18  # 精确枚举上限：池 ≤18 张
GUA244_ENUM_SEAT_MAX = 6   # 且该席剩 ≤6 张

def _pool_single_beat_risk(self, game_state, seat, card_rank):
    """P(该席剩余牌含 ≥1 张能压 card_rank 单张，含级牌)。
    池 ≤18 且 seat 剩余 ≤6 → 精确 C(n,k) 枚举；否则按池 rank 计数边际近似。"""
    pool = game_state.get("_remaining_pool_cards")
    if not pool:
        return None
    nop = game_state.get("numofplayers", [27, 27, 27, 27])
    rem = nop[seat] if len(nop) > seat else 27
    if rem <= 0:
        return 0.0
    cur_rank = str(game_state.get("curRank", "2"))
    beaters = [c for c in pool if self._pool_card_beats_single(c, card_rank, cur_rank)]
    n_beat, n_pool = len(beaters), len(pool)
    if rem > n_pool:
        return 1.0
    if n_pool <= GUA244_ENUM_POOL_MAX and rem <= GUA244_ENUM_SEAT_MAX:
        from math import comb
        return 1.0 - comb(n_pool - n_beat, rem) / comb(n_pool, rem)
    # 边际近似：至少 1 张来自可压子集
    return 1.0 - ((n_pool - n_beat) / n_pool) ** rem

def _pool_pair_beat_risk(self, game_state, seat, pair_rank):
    """P(该席剩余牌含 >pair_rank 对子)。枚举内精确，否则边际近似。"""
    ...  # 对称实现：池中每 rank 剩余≥2 的可成对 rank，>pair_rank 的成对组合数 / C(n,rem)

def _pool_card_beats_single(self, card, target_rank, cur_rank):
    """HR/SB 恒压；级牌压非级牌；否则按 rank 序。对齐 _rank_beats_same_type 语义。"""
    ...
```

2. **`_seat_may_hold_single_above`（L3959）池优先**——安全单判定的真源替换：

```python
pool = game_state.get("_remaining_pool_cards")
if pool:
    nop = game_state.get("numofplayers", [27, 27, 27, 27])
    if nop[seat] if len(nop) > seat else 27 <= 0:
        return False
    # 池中是否存在能压 target_rank 且可被该席持有的牌
    return any(self._pool_card_beats_single(c, target_rank, cur_rank)
               for c in pool)
# ── 原 MemoryTracker 路径（无池时回退，保持 v1006 行为）──
```

3. **`_q1_enemy_critical_lead_special`（L3060）GUA-220 gate 加池护栏**：

```python
if get_action_type(best_lock[1]) == ACTION_TYPE_PAIR:
    # GUA-244：危险敌人（非下家）侧位/对家剩 2 张时，
    # 单先于对会把低单送进 ~99% 被接局面（match 6a8003e6 C6 被级牌 D2 接走）。
    if self._pool_blocks_single_first(game_state, main_enemy, singles):
        return best_lock          # 直接出对子锁，不拆单
    downseat_single = self._q1_downseat_two_single_first(singles, game_state, ec)
    if downseat_single is not None:
        return downseat_single
return best_lock

def _pool_blocks_single_first(self, game_state, main_enemy, singles) -> bool:
    pool = game_state.get("_remaining_pool_cards")
    if not pool or not singles:
        return False
    rem = int(main_enemy.get("remaining", 27) or 27)
    if rem not in (1, 2, 3):
        return False
    lowest_single = min(_get_cards(a)[0] for _, a in singles if _get_cards(a))
    lowest_rank = get_card_rank(lowest_single)
    single_risk = self._pool_single_beat_risk(game_state, main_enemy_pos(game_state), lowest_rank)
    if single_risk is None or single_risk < GUA244_SINGLE_RISK:
        return False
    return True
```

4. **新增 `_q1_pool_pair_first_special`**（对子先于整牌/单，插在 `_q1_block_enemy` L2070 `_q1_enemy_critical_lead_special` **之前**调用）：

```python
def _q1_pool_pair_first_special(self, game_state, candidates, ec,
                                main_pos, main_enemy):
    """GUA-244：领出 + 主敌剩 ≤3 + 池存在 + 本方多对+低单无回手 +
    池风险「单 99% 被接 / 对 5.7% 被接」→ 先出最高对子（对子先于单/整牌）。

    场景：手 TWT(AAA+JJ) + 66 + 77 + D5 + C6，主敌 p1 剩 2。
    TWT 锁敌后 V8 领出权延续，正确顺序应为 77 → 66 → TWT → D5 → C6；
    原路径锁敌后直接出单 C6 送 p1 级牌 D2 接走。
    """
    if not GUARD_TOOLS_OK:
        return None
    my_pos = ec.get("my_pos", game_state.get("myPos", 0))
    if not self._is_my_q1_lead_turn(game_state, my_pos):
        return None
    rem = int(main_enemy.get("remaining", 27) or 27)
    if rem not in (1, 2, 3):
        return None
    pool = game_state.get("_remaining_pool_cards")
    if not pool:
        return None

    hand_cards = list(game_state.get("handCards", []) or [])
    hands, pair_groups = self._count_hand_structure(hand_cards, game_state)
    if pair_groups < 2 or hands < 4:
        return None

    # 找最高对子候选（不拆炸）
    pairs = [(i, a) for i, a in candidates
             if _get_cards(a) and len(_get_cards(a)) == 2
             and get_action_type(a) == ACTION_TYPE_PAIR
             and not self._is_bomb_destroying_action(a, hand_cards, game_state)]
    if not pairs:
        return None

    # 池风险门：单被接风险高 + 对子被接风险低
    lowest_rank = ...   # 手牌最低单（无大单回手 → 单被接必丢权）
    single_risk = self._pool_single_beat_risk(game_state, main_pos, lowest_rank)
    pair_risk = self._pool_pair_beat_risk(game_state, main_pos,
                                          get_card_rank(_get_cards(pairs[0][1])[0]))
    if single_risk is None or pair_risk is None:
        return None
    if single_risk < GUA244_SINGLE_RISK or pair_risk >= GUA244_PAIR_RISK:
        return None

    best = max(pairs, key=lambda it: get_card_value(_get_cards(it[1])[0],
                                                     str(game_state.get("curRank", "2"))))
    logger.info("Q1 池推理对子优先(GUA-244): idx=%d type=Pair rank=%s "
                "single_risk=%.2f pair_risk=%.2f",
                best[0], get_action_rank(best[1]), single_risk, pair_risk)
    return best
```

调用点（`_q1_block_enemy`，L2070 前）：

```python
pool_pair_first = self._q1_pool_pair_first_special(
    game_state, non_banned_candidates, ec, main_pos, main_enemy,
)
if pool_pair_first is not None:
    return pool_pair_first
```

> **效果对比（match 6a8003e6）**：#16 不再锁 TWT，先出 77 → p1 接不住（对子被接仅 5.7%）→ 后续 66、TWT、D5、C6 顺延；即便 D5/C6 终归要被接，也已把低单压到最后，翻车窗口从 #17 提前引爆变为最后两手的低概率事件（99%→5.7% 起步）。

### D. 阈值与常量

| 常量 | 值 | 含义 |
|------|-----|------|
| `GUA244_SINGLE_RISK` | 0.7 | 单被主敌接走的池风险 ≥ 0.7 → 触发护栏 |
| `GUA244_PAIR_RISK` | 0.3 | 对子被主敌接走的池风险 < 0.3 → 允许对子优先 |
| `GUA244_ENUM_POOL_MAX` | 18 | 池 ≤18 张做精确 C(n,k) 枚举 |
| `GUA244_ENUM_SEAT_MAX` | 6 | 该席剩余 ≤6 张时枚举（C(18,6)=18564，单次毫秒级） |

## 四、测试（`tests/test_gua244_pool_pair_single_decision.py`，待新增）

Fixture 用 match 6a8003e6 真实数据：hand = `[D5,C6,H6,H7,S7,DA,HA,SA,SJ,SJ]`、numofplayers=`[7,2,10,6]`、pool = 上文 15 张、main_enemy=p1(rem=2)。

| # | 用例 | 断言 |
|---|------|------|
| 1 | `_pool_single_beat_risk(p1, '6')` | ≈ 104/105 = 0.9905 |
| 2 | `_pool_pair_beat_risk(p1, '6'/'7')` | = 6/105 ≈ 0.0571 |
| 3 | `_q1_pool_pair_first_special` 触发 | 返回 `Pair/7`（77 先于 TWT/单） |
| 4 | 无 remainingPool | 回退原 TWT 锁敌，不回归 |
| 5 | 低风险池（全 ≤5 低牌） | 不触发，维持原锁敌 |
| 6 | `_seat_may_hold_single_above(p1,'6')` 池路径 | True（池有 D2/7/8…） |
| 7 | 集成：复现 #17（TWT 出后剩 D5 C6 66 77 领出） | 决策从 `Single/C6` 变为 `Pair/7` |

回归：`test_gua220/239/240/241/243 + -k "endgame"` 全量；改动集失败数须与基线一致（无新增）。

## 五、实施顺序

1. **A+B**（adapter + 引擎注入）：纯增量，无行为变化 → 可单独验收（池注入正确、校验失败回退）。
2. **C3**（GUA-220 gate 池护栏）：最小改动，直接命中 #17 败因（`Single/C6`→`Pair/66`）。
3. **C4**（`_q1_pool_pair_first_special`）：编排级修复，命中 #16 起手顺序（`TWT`→`77`）。
4. **测试 + 回归**。
5. **实局验证**：WF-14 重启监听；遇 match 6a8003e6 同构场景（主敌 2 张 + 本方多对+低单+整牌锁）观测出牌顺序；批跑记录 `v8-win-rate-history.md` 环比。

## 六、边界与风险

- **v1006 线不受影响**：yf1_v5.py 等无 `remainingPool` 字段 → `_inject_remaining_pool` 校验失败 → `_remaining_pool_cards=None` → 决策层全部回退原逻辑（行为零变化）。
- **池污染防护**：副本数>2 / 总张数≠对手剩余 → 校验失败回退；`_accumulate_played_cards` 用 int-set 去重，跨 request history 重叠安全（实测交叉校验通过）。
- **枚举规模**：池 >18 或该席 >6 → 边际近似（决策参考，不阻塞主路径）。
- **内部字段**：`_remaining_pool` / `_remaining_pool_cards` / `remainingPool` 均为引擎内部键，不进 platform actionList、不影响组牌引擎。
- **语义边界**：池给出的是「对手残牌的可能性集」，不是确定性——护栏只改变「对子/单/整牌」的**编排顺序**，不改牌力排序与 banned 语义。

## 七、关联

- GUA-220：下家剩 2 张单先于对（`_q1_downseat_two_single_first`）——本 issue 为其补**池风险护栏**，且扩展到侧位/对家危险敌人。
- GUA-239：单试探留整牌（同属「单 vs 整牌」编排），其 H7 拆 SF 试探的前提是有大王回手；GUA-244 在**无回手**时走对子优先。
- GUA-078 / GUA-170：numofplayers 真源（publicInfo.rest），本方案池一致性校验依赖它。
- GUA-072：规则记牌信念（`_belief`），与池互为补充（池是确定性残牌全集，belief 是概率推断）。
