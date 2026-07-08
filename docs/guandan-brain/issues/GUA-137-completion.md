# GUA-137 完成定义：玩家整手结构推断增强（grouping_engine）→ yf1/@3 冲刺能力精确 + 整牌型评估

> **状态**：draft（2026-07-08 待登记）
> **WF-12 锚点**：`game_records_v7/20260706222548831117 [yf1_v7]-[opponent_1_3]-[10]-[2].json` 步 **51/89**
> **关联**：[GUA-136-completion](GUA-136-completion.md) 玩家剩牌估算；[GUA-135-completion](GUA-135-completion.md) 双进优先级判定；GUA-052 记忆模块；GUA-061 grouping_engine

---

## 0. 背景与动机

**GUA-136 已落地**：基于 `MemoryTracker.card_state` 推断 yf1/@3 具体手牌（含每张牌的副本归属），然后应用 `_has_sprint_capability` 判定冲刺能力。

**GUA-136 局限**：
- `_has_sprint_capability` 只看「≥4 张同点 + 剩余 ≤ 5 张」的粗粒度判定
- 不识别 **整牌型结构**（顺子 / 三连对 / 三带二 / 钢板 / 同花顺）→ 误判 yf1 是否能闭合冲刺
- 不识别 **手数**（num_rounds）→ 无法精确判断 yf1 出完需要几圈

**GUA-137 目标**：用 `grouping_engine.enumerate_groupings(hand_cards, cur_rank)` 把推断出的手牌 → 整手结构（singles/pairs/trips/bombs/straights/...），让 GUA-135 双进优先级判定能识别：
- yf1 是否能闭合冲刺（不只是「剩 2 手」，还要「整牌型闭合」）
- yf1 / @3 整手手数（num_rounds）→ 精确判断「yf2 PASS 等 yf1 闭合」 vs 「yf2 跟牌夺权」
- yf1/@3 是否含炸弹家族（bombs + straight_flushes）→ 威胁评估

---

## 1. 现状（GUA-136 局限）

### 1.1 `_has_sprint_capability` 当前实现

```python
def _has_sprint_capability(self, hand_cards):
    """判定手牌是否具备冲刺能力（剩 2 手 = 炸弹 + 单手）。"""
    ranks = Counter(get_card_rank(c) for c in hand_cards)
    max_count = max(ranks.values()) if ranks else 0
    if max_count < 4:
        return False  # 无炸弹
    remaining_after_bomb = len(hand_cards) - max_count
    if remaining_after_bomb > 5:
        return False  # 单手 > 5 张
    if remaining_after_bomb == 0:
        return False  # 整手只是炸弹
    return True
```

**问题**：
- 「剩 2 手 = 炸弹 + 单手」判定过于简化
- 例：4 张同点 + 4 张顺子 → 算 2 手吗？取决于顺子能否独立出
- 例：6J + 333+22 + 单张 → GUA-136 算 2 手（剩 6 张 > 5 → False），但实际是 3 整手，可「6J → 三带二 → 单」三手清空

### 1.2 GUA-136 `_estimate_player_sprint_capability` 调用链

```
_estimate_player_sprint_capability(pos, gs)
  └─ _estimate_player_hand_cards(pos, gs)        # 推断手牌
       └─ MemoryTracker.card_state                # 单牌级推断
  └─ _has_sprint_capability(hand_cards)           # 粗粒度判定
```

**缺失环节**：手牌 → **整手结构**（按牌型分组）→ 「出完需要几圈」+ 「能否冲刺闭合」。

---

## 2. 增强目标

### 2.1 三个新增接口

| 接口 | 作用 | 实现位置 |
|------|------|----------|
| `_estimate_player_grouping_plan(position, game_state)` | 推断 yf1/@3 整手结构（GroupingPlan） | `endgame_decide.py` 新增 |
| `_estimate_player_num_rounds(position, game_state)` | 推断出完需要几圈（num_rounds） | `endgame_decide.py` 新增 |
| `_estimate_player_sprint_capability_v2(position, game_state)` | 冲刺能力精确判定（基于 grouping_plan） | `endgame_decide.py` 替换 GUA-136 旧版 |

### 2.2 推断算法

**`_estimate_player_grouping_plan`** 三层降级：

```
Layer 1: MemoryTracker.card_state → 手牌列表 → enumerate_groupings(hand, cur_rank)
  - 返回 best_plan（评分最高的组牌方案）
  - 包含 singles/pairs/trips/bombs/straights/straight_flushes/three_pairs/three_with_twos/steel_plates

Layer 2: MemoryTracker 不可用 但 enemy_ctx.hand_types 存在（上游已推断）
  - 构造虚拟 GroupingPlan（仅含 singles/pairs/trips）

Layer 3: 兜底返回 None（让 GUA-135 走保守 False）
```

**`num_rounds` 判定**：

```python
plan = _estimate_player_grouping_plan(position, gs)
if plan is None:
    return 0  # 未知
return plan.num_rounds()  # 出完所有牌所需轮数
```

**`_estimate_player_sprint_capability_v2`** 算法：

```python
plan = _estimate_player_grouping_plan(position, gs)
if plan is None:
    return False

# 冲刺能力定义（精确版）：
#   - 手数 ≤ 2（出完 ≤ 2 圈）
#   - 至少 1 个 bomb family（bombs + straight_flushes）
#   - 不要求「剩 2 手 = 炸弹 + 单手」的严格结构

num_rounds = plan.num_rounds()
has_bomb_family = len(plan.bombs) > 0 or len(plan.straight_flushes) > 0

return num_rounds <= 2 and has_bomb_family
```

**为什么不只检查 num_rounds == 2？**
- 6J + 单张 → num_rounds=2 但 has_bomb_family=True → 冲刺 ✓
- 三带二 + 单张 → num_rounds=2 但 has_bomb_family=False → **不是冲刺**（这是「一手清空」或「二游」，不是「冲刺闭合」）
- 6J + 333+22 + 单张 → num_rounds=3 但 GUA-125 sprint 是 6J+任意≤5 张（≤2 圈）→ **不是冲刺**（3 圈闭合不可冲刺）

---

## 3. 接口定义

### 3.1 新增 `_estimate_player_grouping_plan`

```python
def _estimate_player_grouping_plan(
    self, position: int, game_state: Dict[str, Any],
) -> Optional[object]:
    """
    GUA-137：推断 yf1/@3 整手结构（GroupingPlan）。

    实现：
      - Layer 1：MemoryTracker.card_state → 手牌列表 → enumerate_groupings
      - Layer 2：enemy_ctx.hand_types 构造虚拟 plan
      - Layer 3：返回 None

    返回：GroupingPlan 实例（来自 grouping_engine）或 None
    """
    # 1. 推断手牌
    hand_cards = self._estimate_player_hand_cards(position, game_state)
    if hand_cards:
        try:
            from src.v.nn.features.grouping_engine import enumerate_groupings
            cur_rank = str(game_state.get("curRank", "2"))
            best_plan, _ = enumerate_groupings(hand_cards, cur_rank)
            return best_plan
        except Exception:
            pass
    # 2. 兜底：enemy_ctx.hand_types（若存在）
    ec = game_state.get("_endgame_context") or {}
    enemy_ctx = ec.get("enemies", {}).get(position, {}) or {}
    hand_types = enemy_ctx.get("hand_types", [])
    if hand_types:
        # 构造虚拟 plan（仅含 singles）
        from src.v.nn.features.grouping_engine import GroupingPlan
        return GroupingPlan(singles=list(hand_types), cur_rank=str(game_state.get("curRank", "2")))
    return None
```

### 3.2 新增 `_estimate_player_num_rounds`

```python
def _estimate_player_num_rounds(
    self, position: int, game_state: Dict[str, Any],
) -> int:
    """
    GUA-137：推断 yf1/@3 出完所有牌需要几圈（num_rounds）。

    返回：圈数（0 表示未知）
    """
    plan = self._estimate_player_grouping_plan(position, game_state)
    if plan is None:
        return 0
    try:
        return plan.num_rounds()
    except Exception:
        return 0
```

### 3.3 增强 `_estimate_player_sprint_capability`

**保留 GUA-136 旧实现 + 新增 v2 版本**：

```python
def _estimate_player_sprint_capability(
    self, position: int, game_state: Dict[str, Any],
) -> bool:
    """
    GUA-137：冲刺能力精确判定（基于 grouping_plan）。

    算法：
      - 推断整手 plan → num_rounds + has_bomb_family
      - 冲刺能力 = num_rounds ≤ 2 AND has_bomb_family

    返回：True / False
    """
    plan = self._estimate_player_grouping_plan(position, game_state)
    if plan is None:
        # GUA-136 兜底：单牌级推断
        return self._estimate_player_sprint_capability_legacy(position, game_state)
    num_rounds = plan.num_rounds()
    has_bomb_family = len(plan.bombs) > 0 or len(plan.straight_flushes) > 0
    return num_rounds <= 2 and has_bomb_family
```

`_estimate_player_sprint_capability_legacy` 即 GUA-136 旧实现（保留作回退）。

---

## 4. 关键判定表

### 4.1 yf1/@3 冲刺能力（GUA-137 精确版）

| 整手结构示例 | num_rounds | has_bomb_family | GUA-137 判定 | GUA-136 判定 |
|--------------|-----------|----------------|--------------|--------------|
| 6J + 22（2 张对） | 2 | ✓ | ✓ sprint | ✓ sprint |
| 6J + 单张 + 单张 | 3 | ✓ | ✗（3 圈） | ✓ sprint（误判） |
| 4×8 + 22 + 单 | 3 | ✓ | ✗（3 圈） | ✓ sprint（误判） |
| 5×7 + 5×8（同点 5 张可当炸弹） | 2 | ✓ | ✓ sprint | ✓ sprint |
| 三带二 + 单 | 2 | ✗ | ✗（非冲刺） | ✓ sprint（误判） |
| 顺子 5 + 单 | 2 | ✗ | ✗（非冲刺） | ✗ 无炸弹 |
| 顺子 5 + 6J | 2 | ✓ | ✓ sprint | ✓ sprint |
| 6J + 333+22 + 8 | 3 | ✓ | ✗（3 圈闭合） | ✓ sprint（误判） |
| 4 张炸 + 5 张三带二 | 2 | ✓ | ✓ sprint | ✓ sprint |

**GUA-137 优势**：
- 「6J + 单张 + 单张」= 3 圈闭合 → 不是 sprint（只有 2 圈接力才是）
- 「三带二 + 单」= 2 圈但无炸弹 → 不是 sprint（只是一手清空）
- 「6J + 顺子 5」= 2 圈 + bomb family → 是 sprint ✓

### 4.2 GUA-135 双进优先级判定增强

**场景：sprint_race（双方都 ≤ 6 张）**

| yf2 plan | yf1 plan | GUA-137 决策 |
|----------|----------|--------------|
| num_rounds=2, bomb ✓ | num_rounds=3 | yf2 自己拿第二（更激进） |
| num_rounds=2, bomb ✓ | num_rounds=2, bomb ✓ | yf2 自己拿第二（避免 yf1 失误） |
| num_rounds=3 | num_rounds=2, bomb ✓ | yf1 拿第二，yf2 PASS 让道 |
| num_rounds=3 | num_rounds=3 | yf2 PASS 等待（保守） |

---

## 5. 性能考量

### 5.1 `enumerate_groupings` 性能

- 26 张手牌的精确枚举：~10-50ms（GUA-063 测试基准）
- 10 张以下手牌：< 5ms
- GUA-137 调用频率：仅在 GUA-135 场景触发时（双进优先级判定）→ **每次 decide 调用最多 2 次**（yf1 + @3）

### 5.2 缓存策略

**可选**：`_estimate_player_grouping_plan` 结果可缓存到 `_grouping_plan_cache[position]`，仅在 MemoryTracker 更新时失效。

**GUA-137 不做**：缓存由 GUA-138 性能优化负责。

---

## 6. 停手条件 / 完成定义

**GUA-137 关单须满足**：

1. ✅ `_estimate_player_grouping_plan` 新增（基于 enumerate_groupings）
2. ✅ `_estimate_player_num_rounds` 新增
3. ✅ `_estimate_player_sprint_capability` 升级（v2 基于 plan，保留 legacy 回退）
4. ✅ GUA-135 sprint_race / yf2_self_sprint 触发判定更精确
5. ✅ pytest：`tests/test_gua137_grouping_enhance.py` 全绿
6. ✅ 回归：GUA-131~136 + GUA-123 + GUA-122 仍绿
7. ✅ ITERATIONS 末追加：`v7-gua137-grouping-enhance-implemented`

**关联 GUA**：
- GUA-052：MemoryTracker
- GUA-061：grouping_engine（24 维特征）
- GUA-063：grouping_engine card_mask
- GUA-135：双进优先级判定（依赖 yf1/@3 sprint 能力）
- GUA-136：玩家剩牌估算增强（基础数据源）
- WF-12：决策溯源

---

## 7. 不做 / 后续

**本 GUA 不做**：
- ❌ grouping_engine 性能优化（26 张手牌 10-50ms）— 留 GUA-138
- ❌ `_estimate_player_grouping_plan` 缓存策略 — 留 GUA-138
- ❌ 排除法推断具体牌型（如 yf1 必有 6J + 某顺子）— 留 GUA-139
- ❌ 贡牌/抗贡后手牌重建 — 留 GUA-140

**后续 GUA**：
- **GUA-138**：grouping_engine 推理性能优化（缓存 + 增量计算）
- **GUA-139**：yf1/@3 排除法推断（基于已知出牌推断可能手牌范围）
- **GUA-140**：贡牌/抗贡阶段后手牌重建（早期阶段推断准确性）

---

## 8. 与 GUA-136 对接

GUA-137 是 GUA-136 `_estimate_player_sprint_capability` 的**算法升级**：

| 函数 | GUA-136 | GUA-137 |
|------|---------|---------|
| 数据源 | MemoryTracker.card_state（单牌级） | MemoryTracker.card_state + grouping_engine（结构级） |
| 冲刺判定 | 「≥4 张同点 + 剩 ≤ 5 张」粗粒度 | 「num_rounds ≤ 2 AND has_bomb_family」精确 |
| 误判风险 | 高（6J+单+单 误判 sprint） | 低（按整牌型拆分手数） |
| 性能 | O(N) | O(N) + O(枚举) ≈ 5-10ms |

**GUA-137 接管 sprint 判定**，GUA-136 旧实现保留为 `legacy` 兜底（无 grouping_engine 时）。

---

## 9. 不做 / 边界

- ❌ 不修改 grouping_engine 本身（GUA-061 已 frozen）— GUA-137 是消费者
- ❌ 不修改 GUA-131/132/133/134 C1-C6 决策树
- ❌ 不修改 GUA-135 双进优先级判定逻辑（仅升级数据源）
- ❌ 不引入新的 feature vector

---

## 10. 交叉引用

- **GUA-052**：MemoryTracker（108 张牌全量追踪）
- **GUA-061**：grouping_engine（24 维特征 + enumerate_groupings）
- **GUA-125 §0.5**：C1-C6 主表 + sprint 定义
- **GUA-135**：双进优先级判定
- **GUA-136**：玩家剩牌估算增强
- **GUA-131/132/133**：C1/C2/C4 决策
- **GUA-134**：C3/C5/C6 自闭合
- **WF-12**：决策溯源
