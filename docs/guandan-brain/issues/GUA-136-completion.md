# GUA-136 完成定义：玩家剩牌估算增强（记忆模块 + 圈序出牌历史）→ @3 冲刺能力精确评估 + yf1 接力能力精确评估

> **状态**：draft（2026-07-08 待登记）
> **WF-12 锚点**：`game_records_v7/20260706222548831117 [yf1_v7]-[opponent_1_3]-[10]-[2].json` 步 **51/89**
> **关联**：[GUA-135-completion](GUA-135-completion.md) 双进优先级判定；GUA-052 记忆模块；GUA-131/132/133 C1/C2/C4 决策；GUA-134 C3/C5/C6 自闭合

---

## 0. 背景与动机

**GUA-135 双进优先级判定**（已落地）依赖三个核心数据：

| 数据 | GUA-135 实现 | 精确度问题 |
|------|--------------|-----------|
| **yf2 冲刺能力** | `_has_sprint_capability(hand)` ✓ | 精确（自己手牌） |
| **yf1 接力能力** | `_has_teammate_bomb_family()` + `_has_teammate_bigger_twt()` 粗估 | ⚠️ **记忆模块未深度利用** |
| **@3 冲刺能力** | `tracker.get_seat_cards_estimate()` 不存在 → 保守 False | ⚠️ **永远 False = 无法阻止 @3** |

**GUA-136 目标**：利用 `MemoryTracker`（GUA-052）已记录的 108 张牌全量追踪 + 排除法推断 + 圈序出牌历史，**精确估算 yf1/@3 的冲刺能力**（剩 2 手 = 炸弹 + 单手），让 GUA-135 双进优先级判定可执行「阻止 @3 拿第二」分支。

---

## 1. 现状（未增强）

### 1.1 `_estimate_player_remaining` 当前实现

```python
def _estimate_player_remaining(
    self, position: int, ec: Dict[str, Any], game_state: Dict[str, Any],
) -> int:
    """GUA-135：估算某玩家当前剩牌数（用于双进优先级判定）。"""
    enemies = ec.get("enemies", {}) or {}
    enemy_ctx = enemies.get(position, {}) or {}
    remaining = enemy_ctx.get("remaining")
    if isinstance(remaining, int) and remaining >= 0:
        return remaining
    return 0  # 兜底
```

**问题**：
- 只看 `enemy_ctx.remaining`（仅对手），不查队友
- 记忆模块完全未用
- 0 兜底 → GUA-135 yf1/@3 sprint 评估永远失败

### 1.2 GUA-135 `_is_double_second_priority_scenario` 中 sprint 评估

```python
yf1_sprint = False
tracker = game_state.get("_memory_tracker")
if tracker is not None:
    try:
        yf1_sprint = self._has_teammate_bomb_family(game_state, teammate_pos)
    except Exception:
        pass

at3_sprint = False
if tracker is not None:
    try:
        at3_hand = (tracker.get_seat_cards_estimate(enemy_pos)
                    if hasattr(tracker, "get_seat_cards_estimate") else None)
        if at3_hand:
            at3_sprint = self._has_sprint_capability(at3_hand)
    except Exception:
        pass
```

**问题**：
- `tracker.get_seat_cards_estimate` **不存在**（memory_tracker 没有此方法）
- → at3_sprint 永远 False
- yf1_sprint 走 `_has_teammate_bomb_family` 但该方法只判「是否有 bomb family」，**不判冲刺能力**

---

## 2. 增强目标

### 2.1 三个新增/增强接口

| 接口 | 作用 | 实现位置 |
|------|------|----------|
| `_estimate_player_remaining(position, ec, game_state)` | **增强**：优先 MemoryTracker.get_hand_count → enemy_ctx.remaining → 0 | `endgame_decide.py` 替换 |
| `_estimate_player_hand_cards(position, game_state)` | **新增**：推断某玩家手牌（基于排除法 + play_history） | `endgame_decide.py` 新增 |
| `_estimate_player_sprint_capability(position, game_state)` | **新增**：基于推断手牌判定冲刺能力 | `endgame_decide.py` 新增 |

### 2.2 MemoryTracker 复用接口

| 接口 | 来源 | 用途 |
|------|------|------|
| `tracker.get_hand_count(seat)` | `memory_tracker.py:398` | 精确剩牌数（已通过 record_hand_update 维护） |
| `tracker.get_inferred_opponent_types(seat)` | `memory_tracker.py:595` | 排除法推断对手手牌（需 enable_inference=True） |
| `tracker.play_history` | `memory_tracker.py:128` | 圈序出牌历史（list[dict]） |
| `tracker.get_opponent_bomb_risk(seat)` | `memory_tracker.py:609` | 对手炸弹概率（仅作辅助信号） |
| `tracker.card_state` | `memory_tracker.py:111` | 108 张牌全量分配（核心） |

### 2.3 推断算法

**`_estimate_player_hand_cards(position, game_state)`** 三层降级：

```
Layer 1: MemoryTracker.get_inferred_opponent_types(position)
  - 若返回非空 → 精确推断（基于 108 张牌全量追踪 + 排除法）
  - 队友 = (my_pos + 2) % 4，MemoryTracker 无独立方法，需手动遍历 card_state

Layer 2: 基于 play_history 推断
  - 累计某 seat 已出牌张数 = len(cards across history for seat)
  - 27 - 已出 = 估算手牌数（不含贡牌/抗贡）
  - 但无法推断具体牌型

Layer 3: 兜底返回空 list（让 GUA-135 走保守 False）
```

**手牌推断（精确版）**：

```python
def _estimate_player_hand_cards(self, position, game_state):
    tracker = game_state.get("_memory_tracker")
    if tracker is None:
        return []  # 无记忆模块 → 兜底
    # 遍历 card_state 找 position 标记的牌种
    hand_types = []
    if hasattr(tracker, "card_state"):
        for ct, copies in tracker.card_state.items():
            for c in copies:
                if c == position:
                    hand_types.append(ct)
                    break  # 同牌种有 2 张时只计 1 次
    # 去重 + 展开成实际牌数（每种最多 2 张）
    return self._expand_card_types(hand_types, tracker, position)
```

**`_expand_card_types`**：根据每牌种的副本分配，展开成具体牌列表（保留张数）。

---

## 3. 接口定义

### 3.1 增强 `_estimate_player_remaining`

```python
def _estimate_player_remaining(
    self, position: int, ec: Dict[str, Any], game_state: Dict[str, Any],
) -> int:
    """
    GUA-136：增强的剩牌数估算（记忆模块优先）。

    优先级：
      1. MemoryTracker.get_hand_count(position) — 精确（已通过 record_hand_update 维护）
      2. enemy_ctx.remaining — 兜底（仅对手）
      3. 0 — 未知

    返回：估算的剩牌数
    """
    tracker = game_state.get("_memory_tracker")
    if tracker is not None:
        try:
            count = tracker.get_hand_count(position)
            if isinstance(count, int) and count >= 0:
                return count
        except Exception:
            pass
    enemies = ec.get("enemies", {}) or {}
    enemy_ctx = enemies.get(position, {}) or {}
    remaining = enemy_ctx.get("remaining")
    if isinstance(remaining, int) and remaining >= 0:
        return remaining
    return 0
```

### 3.2 新增 `_estimate_player_hand_cards`

```python
def _estimate_player_hand_cards(
    self, position: int, game_state: Dict[str, Any],
) -> List[str]:
    """
    GUA-136：推断某玩家当前手牌（具体牌列表）。

    实现：
      - 遍历 MemoryTracker.card_state 找 position 标记的牌种
      - 展开为实际牌列表（每种最多 2 张）
      - 无记忆模块 → 返回 []

    返回：手牌列表（具体牌），可能为空
    """
    tracker = game_state.get("_memory_tracker")
    if tracker is None or not hasattr(tracker, "card_state"):
        return []
    try:
        result = []
        for ct, copies in tracker.card_state.items():
            own_count = sum(1 for c in copies if c == position)
            for _ in range(own_count):
                result.append(ct)
        return result
    except Exception:
        return []
```

### 3.3 新增 `_estimate_player_sprint_capability`

```python
def _estimate_player_sprint_capability(
    self, position: int, game_state: Dict[str, Any],
) -> bool:
    """
    GUA-136：判定某玩家（yf1 或 @3）是否具备冲刺能力。

    冲刺能力 = 剩 2 手 = 炸弹 + 单手（参见 GUA-135 §0）

    实现：
      - 推断手牌 → 应用 _has_sprint_capability 判定
      - 无推断 → 保守 False

    返回：True / False
    """
    hand_cards = self._estimate_player_hand_cards(position, game_state)
    if not hand_cards:
        return False
    return self._has_sprint_capability(hand_cards)
```

---

## 4. 调用流程更新

```
GUA-135 _is_double_second_priority_scenario:
  ├─ yf2 sprint = _has_sprint_capability(hand) ✓ (GUA-135)
  ├─ yf1 sprint = _estimate_player_sprint_capability(teammate_pos, gs) ★GUA-136
  ├─ @3 sprint  = _estimate_player_sprint_capability(enemy_pos, gs) ★GUA-136
  └─ yf1/@3 remaining = _estimate_player_remaining(pos, ec, gs) ★GUA-136

GUA-135 _q1_double_second_priority:
  ├─ C2/C4 trigger：判定 yf2 冲刺能力（走 _estimate_player_remaining 查 @3 剩牌）
  ├─ yf2_self_sprint trigger：判定 yf1 冲刺能力（决定 yf2 PASS 还是跟 TWT）
  ├─ yf1_sprint trigger：判定 yf1 bomb family（已有 _has_teammate_bomb_family）
  └─ sprint_race trigger：双方都 ≤ 6 张，判定 yf2 vs yf1 冲刺能力
```

---

## 5. 关键牌理

### 5.1 冲刺能力精确评估的价值

**GUA-135 sprint_race 场景**（双方都 ≤ 6 张）：

| yf2 sprint | yf1 sprint | GUA-136 决策 |
|-----------|-----------|--------------|
| ✓ | ✓ | yf2 自己拿第二（更激进，避免 yf1 失误） |
| ✓ | ✗ | yf2 自己拿第二 |
| ✗ | ✓ | yf1 拿第二，yf2 PASS 让道 |
| ✗ | ✗ | yf2 PASS 等待更优时机（保守） |

### 5.2 阻止 @3 拿第二的可行性

**@3 sprint 评估**：

```
@3 剩牌张数 ≤ 6
+ @3 推断手牌中是否含 ≥4 张同点（炸弹家族）
+ @3 推断手牌中除炸弹外 ≤ 5 张可组成单整牌型

→ @3 sprint = True（@3 能闭合头游第二）

GUA-135 决策：yf2 必须用 bomb family / 更大 TWT 拦截 @3 抢第二
```

### 5.3 记忆模块 enable_inference 的影响

- `enable_inference=True`（默认）+ `max_infer_depth=3` → `get_inferred_opponent_types` 可推断具体牌
- `enable_inference=False` → `get_inferred_opponent_types` 返回空，GUA-136 退化到 Layer 2（仅剩张数）

**降级策略**：GUA-136 必须容忍 enable_inference=False 的情况，回退到「仅剩张数」+ 「保守冲刺能力 False」。

---

## 6. 停手条件 / 完成定义

**GUA-136 关单须满足**：

1. ✅ `_estimate_player_remaining` 增强（记忆模块优先）已实现
2. ✅ `_estimate_player_hand_cards` 新增（推断具体手牌）
3. ✅ `_estimate_player_sprint_capability` 新增（冲刺能力判定）
4. ✅ GUA-135 `_is_double_second_priority_scenario` 调用新接口（替换原保守 False）
5. ✅ pytest：`tests/test_gua136_player_remaining_enhance.py` 全绿
6. ✅ 回归：GUA-131/132/133/134/135 + GUA-123 + GUA-122 仍绿
7. ✅ ITERATIONS 末追加：`v7-gua136-player-remaining-enhance-implemented`

**关联 GUA**：
- GUA-052：MemoryTracker（108 张牌全量追踪）
- GUA-135：双进优先级判定（依赖 yf1/@3 冲刺能力）
- GUA-131/132/133：C1/C2/C4 决策（已落地）
- GUA-134：C3/C5/C6 自闭合（已落地）
- WF-12：决策溯源

---

## 7. 不做 / 后续

**本 GUA 不做**：
- ❌ 排除法推断算法增强（依赖 max_infer_depth，默认 0 = 不推断）— 留 GUA-137
- ❌ MemoryTracker 性能优化（enable_inference=True 时推理耗时 > 50ms）— 留 GUA-138
- ❌ 贡牌/抗贡特殊处理 — 留 GUA-139

**后续 GUA**：
- **GUA-137**：`_estimate_player_hand_cards` 增强（基于 grouping_engine 推断整牌型而非单牌）
- **GUA-138**：MemoryTracker 推理性能优化（50ms 门槛 → 30ms）
- **GUA-139**：贡牌/抗贡阶段后手牌重建（早期阶段推断准确性）

---

## 8. 与 GUA-135 §4 对接

GUA-136 是 GUA-135 §4.1 `_q1_double_second_priority` 中三个判定函数的**数据源升级**：

| GUA-135 函数 | 当前数据源 | GUA-136 升级 |
|--------------|-----------|--------------|
| `_estimate_player_remaining` | enemy_ctx.remaining | MemoryTracker.get_hand_count 优先 |
| `_is_double_second_priority_scenario` yf1_sprint | `_has_teammate_bomb_family()` | `_estimate_player_sprint_capability()` |
| `_is_double_second_priority_scenario` @3_sprint | 永远 False | `_estimate_player_sprint_capability()` |

升级后，GUA-135 §4.1 的「情形 3 必须：阻止 @3 拿第二」分支首次可执行（原本 @3_sprint 永远 False，该分支永不命中）。

---

## 9. 不做 / 边界

- ❌ 不修改 MemoryTracker 本身（GUA-052 已 frozen）— GUA-136 是消费者
- ❌ 不修改 GUA-131/132/133/134 C1-C6 决策树 — 它们不依赖 yf1/@3 sprint 评估
- ❌ 不引入新的 feature vector — 仅复用 MemoryTracker.get_hand_count / card_state
- ❌ 不做完整排除法推断（max_infer_depth 默认 0）— 留 GUA-137

---

## 10. 交叉引用

- **GUA-052**：MemoryTracker（108 张牌全量追踪）
- **GUA-125 §0.5**：C1-C6 主表（闭合路径分类）
- **GUA-135**：双进优先级判定（依赖 yf1/@3 冲刺能力精确评估）
- **GUA-131/132/133**：C1/C2/C4 决策
- **GUA-134**：C3/C5/C6 自闭合
- **WF-12**：决策溯源
