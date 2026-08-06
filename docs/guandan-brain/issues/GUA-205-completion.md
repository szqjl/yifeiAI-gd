# GUA-205 完成定义

> **GUA-205**：超强手牌（多炸）中局主动进攻开炸/抢攻意识不强烈：GUA-091 中局 PASS 意图接管，全程不主动开炸
> **登记**：2026-08-06
> **严重级别**：P1
> **关联**：GUA-091（`_recommend_play_mid` 中局统一入口）、GUA-102（sprint_fire 主动点火，`_maybe_recommend_sprint_fire_bomb`）、GUA-204（同局「领出拆炸」）、R11（`_r11_bomb_throttle_check` 改炸节流）、`src/v/nn/features/grouping_engine.py`（`determine_role` 超强主攻 ≥7）

---

## 1. 问题描述

### 1.1 复现

match `6a740a2427e7bf01db12df05`（2026-08-06 12:14:42→12:15:04 中局，`logs/v8_vs_botzone_20260806_110540.log`）：

- V8 手牌 20 = 5×7 星炸 + 4×K 炸 + A2345 同花顺 + 顺子 + 散 Q，组牌引擎 `role=超强主攻`（`bombs=2`+SF）
- 12:14:42→12:15:03 **连续 8 次决策全 PASS**，意图：`mid_no_same_type_pass`/`mid_preserve_teammate_lane`/`mid_trade_min_press`(出 SQ)/`mid_yield_teammate_control`/`mid_preserve_teammate_lane`/Q3 炸弹兜底 idx=0/`mid_yield_teammate_control`/`mid_no_same_type_pass`——**无一次开炸抢攻**
- 直到 12:15:04 队友 done 接风领出才被迫出手（此处撞 GUA-204）
- 终局 scores=[3,0,3,0] 赢，但靠队友接风

### 1.2 根因链

```
GUA-091 `_stage_mid_dispatch`（ultimate_win_rate_engine_v7.py:4383-4645）：

  is_teammate（队友出牌，L4464-4475）
    └─ 无条件 PASS（mid_yield_teammate_control / mid_preserve_teammate_lane）
       → 不评估自己超强手牌该不该抢权 ← 支线1

  is_upper / is_lower（敌方出牌，L4520-4643）
    ├─ _recommend_min/max_press_impl（同型压）→ 无同型可压时
    ├─ mid_bomb_cutoff（L4562-4571 / L4624-4632）★唯一开炸口
    │  └─ 硬绑 critical_enemy_remaining <= 3（敌方报单临界）
    │     → 中局敌剩 4+ 张时 can_bomb 即使 True 也永不开炸 ← 支线2
    ├─ mid_counter_enemy_bomb（L4580）仅限敌方已出 Bomb/SF 且敌 ≤5 张
    └─ mid_no_same_type_pass（默认 PASS）

R11 `_r11_bomb_throttle_check`（L5374-5453）：
  上家：第一圈让道 PASS、第二圈同型才允许改炸
  下家：仅 Single 做全局抑制牌检查，非 Single 直接 (False, "暂不让道改炸")
```

**本质**：R11 的 `can_bomb` 能力在 GUA-091 中局几乎未获调用机会；炸弹只在「敌方报单临界」被动触发，**无「超强手牌中局主动开炸抢攻」意图**。

### 1.3 为什么是问题

- 超强手牌（多炸）核心战略价值 = 抢领出权 / 打节奏 / 提前冲刺。全程让道把火力白送。
- 中局早开炸能拿领出权，后续按己方结构打 → 压缩敌方整牌（尤其敌方剩 4-8 张未报单时）。
- 等到敌方报单临界（≤3）才炸，往往已把主动权和牌型优势让光。

---

## 2. 修复方案（两条支线）

### 2.0 核心思路

在 `_stage_mid_dispatch` 的 `is_teammate` / `is_upper` / `is_lower` 分支顶部增加 **「超强主攻主动开炸」特判**，复用既有开炸基元（`_recommend_bomb_from_mask`、R11），不新增动作类型/协议字段。触发门槛 = **手牌 `bombs≥3` 或 role=超强主攻**。

新增方法 `_mid_aggressive_bomb_special`，在 `_stage_mid_dispatch` 内三处调用点插入：

```python
# 支线1：队友出牌但队友不 close → 允许自己抢攻开炸
if is_teammate:
    aggressive = self._mid_aggressive_bomb_special(
        game_state, card_mask, hand_cards, cur_rank,
        greater_action=greater_action,
        greater_type=greater_type,
        greater_rank=greater_rank,
        teammate_pos=teammate_pos,
        is_teammate=True,
    )
    if aggressive:
        return aggressive
    # 原 PASS 逻辑保持不变
    ...

# 支线2（is_upper 分支，位于 mid_bomb_cutoff 之后 / mid_counter_enemy_bomb 之前）：
aggressive = self._mid_aggressive_bomb_special(
    game_state, card_mask, hand_cards, cur_rank,
    greater_action=greater_action,
    greater_type=greater_type,
    greater_rank=greater_rank,
    teammate_pos=teammate_pos,
    is_teammate=False,
)
if aggressive:
    return aggressive
```

### 2.1 新增方法 `_mid_aggressive_bomb_special`

```python
def _mid_aggressive_bomb_special(
    self,
    game_state: Dict[str, Any],
    card_mask: Dict[str, tuple],
    hand_cards: List[str],
    cur_rank: str,
    *,
    greater_action: List[Any],
    greater_type: str,
    greater_rank: str,
    teammate_pos: int,
    is_teammate: bool,
) -> Optional[Dict[str, Any]]:
    """GUA-205：超强主攻中局主动开炸抢攻。

    触发前提（全局）：
      1. 手牌炸弹族数量 bombs>=3，或 role=超强主攻
      2. 存在可选炸弹（_recommend_bomb_from_mask 非空）

    支线1（is_teammate=True，队友出牌）：
      额外要求队友剩牌 > 4（不 close）——队友不 close 意味着未进入
      送牌/冲刺临界，自己超强手牌有权抢攻开炸。

    支线2（is_teammate=False，敌方出牌）：
      额外要求：
        a. greater 是普通牌型（非 Bomb/SF，R11 已拦对手出炸场景）
        b. 敌方非报单临界（critical_enemy_remaining > 3）——
           报单临界仍交给原 mid_bomb_cutoff 精确处理
        c. teammate_cover_confidence < 0.5（队友也接不住，一圈无人接）
        d. 开炸价值达标（_mid_aggressive_value_check）
    """
```

### 2.2 开炸价值检查 `_mid_aggressive_value_check`

支线2 需要「开炸后能拿领出权 + 后续有冲刺结构」，避免乱炸：

```python
def _mid_aggressive_value_check(
    self,
    game_state: Dict[str, Any],
    card_mask: Dict[str, tuple],
    hand_cards: List[str],
    cur_rank: str,
    *,
    teammate_pos: int,
) -> bool:
    """GUA-205：开炸价值判断。

    同时满足才算有开炸价值：
      1. 本手含 ≥3 炸弹族（bomb_count>=3）或 role=超强主攻（外层已保证）
      2. enemy_bomb_risk_max < 0.5（敌方反炸风险不失控）
      3. 手牌总张数 > 3（非只剩炸弹等收尾阶段）
    """
```

设计要点：
- **不加全局黑名单**：不按牌型白名单限制 greater_type，普通牌型（Single/Pair/Trips/TWT/Straight/ThreePair/TwoTrips）均可触发；Bomb/SF 由 R11 前置拦截。
- **不新造意图名**：返回用 `_with_intent(bomb, "mid_aggressive_bomb")`，与 R11 的 `mid_bomb_cutoff` 并列。
- **回手策略**：炸后拿领出权，下一手自然走 `is_lead → recommend_main_attack_lead`，其已实现「出对方可能没有的牌型 / 本方有回手能力的牌型」（`docs/knowledge/skills/04_common_skills/03_card_interactions.md`：顺子 vs TWT 相克、Trips vs Pair、对子留回手等）。GUA-205 只补「愿意开炸」这一环。

### 2.3 安全约束设计（关键）

| 约束 | 理由 | 实现 |
|------|------|------|
| **bombs≥3 或 role=超强主攻** | 普通手牌不允许中局乱炸（R11 已管被动临界炸） | 外层前提 |
| **队友不 close 才抢攻（支线1）** | 队友 close（≤4）时抢攻破坏送牌/冲刺，仍让队友走 | `_remaining(teammate_pos) > 4` |
| **敌方非报单临界（支线2）** | 报单临界（≤3）已有 mid_bomb_cutoff 精确炸，避免重复 | `critical_enemy_remaining > 3` |
| **队友也接不住（支线2）** | 一圈无人接（V8 无同型 + 队友 cover 低）才值得花炸弹 | `teammate_cover_confidence < 0.5` |
| **敌方反炸风险不失控** | 敌方重炸（≥0.5）时开炸等于送权 | `enemy_bomb_risk_max < 0.5` |
| **R11 仍保留** | 超强主攻在临界场景仍走 R11 上家两圈逻辑，不绕过 | 特判插在 mid_bomb_cutoff 之后 |

### 2.4 与既有逻辑的边界

- **`mid_bomb_cutoff`（L4562/4624）不删**：报单临界（`critical_enemy_remaining<=3`）仍由原逻辑精确炸，本特判只补「中局 4+ 张」的早炸。
- **`sprint_fire_ready`（L4509-4518）不冲突**：那是「整牌冲刺态」点火（≤12 张、散牌≤2），本特判是「超强手牌中局」抢攻（手多也能炸）。
- **`mid_counter_enemy_bomb`（L4580）不冲突**：那是「敌方已出炸」的反炸，本特判是「敌方出普通牌型」的主动炸。
- **支线1 只在队友不 close 时放行**：队友 close 场景保持无条件让道（`mid_preserve_teammate_lane` / `mid_yield_teammate_control` 原样）。

---

## 3. 验收

### 3.1 新 pytest（`tests/test_gua205_mid_aggressive_bomb.py`）

| # | 用例 | 期望 |
|---|------|------|
| 1 | 支线1：role=超强主攻 + 队友出牌 + 队友 15 张（不 close）+ 手有炸弹 | 返回 Bomb，intent=`mid_aggressive_bomb` |
| 2 | 支线1 负例：role=超强主攻 + 队友出牌 + 队友 3 张（close） | 不炸，保持 PASS（mid_yield_teammate_control） |
| 3 | 支线1 负例：role=主攻 + bombs=1（非超强）+ 队友 15 张 | 不炸，保持 PASS |
| 4 | 支线2：bombs=3 + 敌剩 6 张（>3 非临界）+ 队友 cover 低 + greater=Pair | 返回 Bomb，intent=`mid_aggressive_bomb` |
| 5 | 支线2 负例：敌剩 2 张（报单临界） | 不触发特判，走原 mid_bomb_cutoff 路径 |
| 6 | 支线2 负例：teammate_cover_confidence=0.9（队友能接） | 不炸，PASS |
| 7 | 支线2 负例：enemy_bomb_risk_max=0.8（敌方反炸失控） | 不炸，PASS |
| 8 | 支线2 负例：bombs=1 且 role=主攻 | 不炸，PASS（mid_no_same_type_pass） |
| 9 | 回归：超强主攻 + 上家第一圈（R11 让道）仍让道 | 不触发特判，走 R11 让道 PASS |
| 10 | 回归：sprint_fire_ready 场景仍走 `_maybe_recommend_sprint_fire_bomb` | 不受新特判影响 |

### 3.2 回归

- `pytest tests/test_gua091_stage_mid_dispatch.py tests/test_gua066_no_lead_bomb.py tests/test_gua123_counter_enemy_bomb.py tests/test_gua072_joker_heuristic_mid.py`
- 目标全绿；预存失败（`test_steel_plate_small_net_positive` 等）确认与本次无关。

### 3.3 实局/批跑

1. 重启 Botzone 监听（WF-14）加载新代码。
2. 复现场景（match `6a740a2427e7bf01db12df05` 同型手牌、中局敌方剩 4-8 张出普通牌型）应改为主动开炸抢攻。
3. 净盘 V8 批跑验证队胜率 KPI 不回退（`v8-win-rate-history.md` 记录）。

---

## 4. 影响面

- 仅影响 **stage_2 中局 + 超强手牌（bombs≥3 或 role=超强主攻）** 的分支；助攻/超弱、残局、领出、报单临界路径不变。
- 不新增动作类型或协议字段；不触碰 banned_set / R10 领出禁炸。
- 支线1 仅放宽「队友不 close」时的抢攻；支线2 仅补「非报单临界」的主动炸，R11 与 mid_bomb_cutoff 均保留。
