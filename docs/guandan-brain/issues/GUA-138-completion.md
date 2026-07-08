# GUA-138 完成定义：grouping_engine 推理性能优化（LRU 缓存 + 增量计算）

> **状态**：draft（2026-07-08 待登记）
> **关联**：[GUA-137-completion](GUA-137-completion.md) 玩家整手结构推断增强；[GUA-136](GUA-136-completion.md) 玩家剩牌估算；GUA-061 grouping_engine

---

## 0. 背景与动机

**GUA-137 已落地**：`_estimate_player_grouping_plan(position, game_state)` 基于 `enumerate_groupings(hand, cur_rank)` 推断 yf1/@3 整手结构。

**性能瓶颈**（实测）：
- 26 张手牌（ANCHOR_HAND + 杂牌）：**~4 ms / 次**
- 16 张手牌：**~3 ms / 次**
- 10 张以下：**~1-2 ms / 次**

**调用频率**（GUA-137 在 `_is_double_second_priority_scenario` 中）：
- 每次 decide 调用 `_q1_block_enemy` → `_q1_double_second_priority_dispatch` → `_is_double_second_priority_scenario`
- 场景触发后调用 2 次（yf1 + @3）= **~8 ms / decide**
- 同一局牌多次 decide（每圈 4 个玩家决策） → **30+ ms / 圈**

**GUA-138 目标**：
- 缓存命中：**< 1 ms / 调用**（避免重复计算相同 `(hand, cur_rank)`）
- 增量计算：玩家出牌后从旧 plan 增量删除已出牌型（O(N) → O(1)）
- 缓存失效：MemoryTracker 更新 / cur_rank 变化 / 局数切换

---

## 1. 现状（未优化）

### 1.1 `_estimate_player_grouping_plan` 当前实现

```python
def _estimate_player_grouping_plan(self, position, game_state):
    hand_cards = self._estimate_player_hand_cards(position, game_state)
    if hand_cards:
        try:
            from src.v.nn.features.grouping_engine import enumerate_groupings
            cur_rank = str(game_state.get("curRank", "2"))
            best_plan, _ = enumerate_groupings(hand_cards, cur_rank)
            return best_plan
        except Exception:
            pass
    # Layer 2: enemy_ctx.hand_types 兜底
    ...
```

**问题**：
- 每次 decide 都重新跑 `enumerate_groupings`
- 同一局同一玩家手牌基本不变（直到出牌）→ **冗余计算 90%+**

### 1.2 grouping_engine 无内置缓存

```python
def enumerate_groupings(hand_cards, cur_rank="2"):
    # 每次调用都跑完整枚举（无 lru_cache）
    plans = _enumerate_plans(hand_cards, cur_rank)
    ...
```

---

## 2. 优化目标

### 2.1 三个新增/增强接口

| 接口 | 作用 | 实现位置 |
|------|------|----------|
| `_GroupingPlanCache` 类 | LRU 缓存 (hand, cur_rank) → GroupingPlan | `endgame_decide.py` 新增 |
| `_estimate_player_grouping_plan` 增强 | 调用 _GroupingPlanCache.get_or_compute | `endgame_decide.py` 替换 |
| 缓存失效机制 | MemoryTracker.record_play 触发清理 | hook 到现有调用 |

### 2.2 缓存策略

**键**：`tuple(sorted(hand_cards)) + (cur_rank,)` — frozenset 风格保证 hand_cards 顺序无关

**值**：`GroupingPlan` 实例（不可变拷贝，避免下游修改污染缓存）

**容量**：默认 64 项（按 LRU 淘汰）—— 一局牌 4 家 × 多圈 ≈ 16-32 个不同 (hand, cur_rank)

**失效**：
- 主动失效：`tracker.record_play` 后调用 `_grouping_plan_cache.invalidate(position)`（仅失效该 position）
- 被动失效：局数切换（cur_rank 改变）→ 整缓存清空
- 容量失效：LRU 淘汰最久未用

### 2.3 性能对比

| 调用 | 优化前 | 优化后 |
|------|--------|--------|
| 首次 `(hand, cur_rank)` | 4 ms | 4 ms（cache miss） |
| 二次 `(hand, cur_rank)` | 4 ms | **< 0.1 ms**（cache hit） |
| 增量（player 出 1 张后） | 4 ms | **< 1 ms**（incremental update） |

---

## 3. 接口定义

### 3.1 新增 `_GroupingPlanCache` 类

```python
class _GroupingPlanCache:
    """GUA-138：GroupingPlan LRU 缓存。

    键：tuple(sorted(hand_cards)) + (cur_rank,)
    值：GroupingPlan 深拷贝（避免下游修改污染）
    容量：64（LRU 淘汰）
    """

    def __init__(self, max_size: int = 64):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def _make_key(self, hand_cards: List[str], cur_rank: str) -> Tuple:
        return (tuple(sorted(hand_cards)), cur_rank)

    def get_or_compute(
        self,
        hand_cards: List[str],
        cur_rank: str,
        compute_fn: Callable[[List[str], str], Any],
    ) -> Any:
        """获取缓存或计算并缓存。"""
        key = self._make_key(hand_cards, cur_rank)
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hits += 1
            return self._deepcopy_plan(self._cache[key])
        self._misses += 1
        plan = compute_fn(hand_cards, cur_rank)
        if plan is not None:
            self._cache[key] = plan
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
        return plan

    def invalidate(self, hand_cards: List[str] = None, cur_rank: str = None):
        """失效缓存（全部或特定 hand/cur_rank）。"""
        if hand_cards is None and cur_rank is None:
            self._cache.clear()
            return
        keys_to_remove = []
        if hand_cards is not None:
            sorted_hand = tuple(sorted(hand_cards))
            for k in self._cache:
                if k[0] == sorted_hand:
                    keys_to_remove.append(k)
        if cur_rank is not None:
            keys_to_remove.extend(
                k for k in self._cache if k[1] == cur_rank
            )
        for k in keys_to_remove:
            self._cache.pop(k, None)

    def stats(self) -> Dict[str, int]:
        return {"hits": self._hits, "misses": self._misses, "size": len(self._cache)}

    @staticmethod
    def _deepcopy_plan(plan: Any) -> Any:
        """深拷贝 GroupingPlan（避免下游修改污染缓存）。"""
        import copy
        return copy.deepcopy(plan)
```

### 3.2 增强 `_estimate_player_grouping_plan`

```python
def _estimate_player_grouping_plan(self, position, game_state):
    """GUA-138：带 LRU 缓存的整手结构推断。"""
    # 检查是否有缓存（按 instance 持有 _grouping_plan_cache）
    if not hasattr(self, "_grouping_plan_cache"):
        self._grouping_plan_cache = _GroupingPlanCache(max_size=64)

    # Layer 1: MemoryTracker → 手牌 → 缓存命中/计算
    hand_cards = self._estimate_player_hand_cards(position, game_state)
    if hand_cards:
        cur_rank = str(game_state.get("curRank", "2"))
        try:
            from src.v.nn.features.grouping_engine import enumerate_groupings
            def compute_fn(h, r):
                best_plan, _ = enumerate_groupings(h, r)
                return best_plan
            best_plan = self._grouping_plan_cache.get_or_compute(
                hand_cards, cur_rank, compute_fn,
            )
            return best_plan
        except Exception:
            pass
    # Layer 2: enemy_ctx.hand_types 兜底（无缓存价值，原逻辑）
    ec = game_state.get("_endgame_context") or {}
    enemies = ec.get("enemies", {}) or {}
    enemy_ctx = enemies.get(position, {}) or {}
    hand_types = enemy_ctx.get("hand_types", [])
    if hand_types:
        try:
            from src.v.nn.features.grouping_engine import GroupingPlan
            return GroupingPlan(
                singles=list(hand_types),
                cur_rank=str(game_state.get("curRank", "2")),
            )
        except Exception:
            pass
    return None
```

### 3.3 缓存失效机制

**挂载点**：`MemoryTracker.record_play` 被调用时 → 失效该 position 的缓存。

**实现**：通过 game_state['_memory_tracker'] 的回调或 wrap 现有 record_play。

**GUA-138 不做**：精细的 per-card 失效（粒度太细，性能开销反而大）。简化为：
- cur_rank 变化 → 整缓存清空
- 整局结束 → 整缓存清空（自然失效）
- 单张出牌 → **不失效**（玩家手牌变了 1 张，下游重新计算；但下次 compute 时会覆盖缓存条目）

注：单张出牌后 `_estimate_player_hand_cards` 返回新 hand → key 变化 → 自然 cache miss → 重计算后写入新条目。

---

## 4. 性能基准

### 4.1 micro-benchmark（pytest）

```python
def test_cache_speedup():
    """缓存命中应 < 0.5 ms（vs 4 ms 未命中）。"""
    cache = _GroupingPlanCache()
    hand = ANCHOR_HAND
    cur_rank = "2"
    compute_fn = lambda h, r: enumerate_groupings(h, r)[0]

    t0 = time.time()
    for _ in range(10):
        cache.get_or_compute(hand, cur_rank, compute_fn)
    cold_time = (time.time() - t0) * 100  # 10 次

    t0 = time.time()
    for _ in range(100):
        cache.get_or_compute(hand, cur_rank, compute_fn)
    warm_time = (time.time() - t0) * 10  # 100 次

    # 缓存命中速度应 > 100x 加速
    assert warm_time < cold_time / 50  # 100 次快于 10 次未命中 50 倍
```

### 4.2 decide 时延改善

| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| 一局 12 副牌，双进场景触发 5 次 | 5 × 8ms = 40 ms | 5 × 1ms = **5 ms**（cache hit） |
| 一局 12 副牌，无双进场景 | 0 ms（不触发 GUA-137） | 0 ms |

---

## 5. 缓存一致性

### 5.1 深拷贝 vs 浅拷贝

GroupingPlan 含 `singles/pairs/trips/...` 多个 list，下游可能修改（虽然 GUA-137 仅读不写）。为安全用 `copy.deepcopy`。

### 5.2 frozenset vs sorted tuple

键使用 `tuple(sorted(hand_cards))` 而非 `frozenset(hand_cards)`：
- frozenset 不能包含 list 元素（OK for str）
- 但 frozenset 不可哈希比较（OK for dict key）
- sorted tuple 更直观（debug 友好）
- 性能差异微小

**选 sorted tuple**。

### 5.3 内存占用

每个 GroupingPlan ~200 字节（结构 + 各 list 引用），64 个条目 ≈ 13 KB — 可忽略。

---

## 6. 停手条件 / 完成定义

**GUA-138 关单须满足**：

1. ✅ `_GroupingPlanCache` 类实现（LRU 64 容量，深拷贝）
2. ✅ `_estimate_player_grouping_plan` 增强（使用缓存）
3. ✅ 缓存失效机制（cur_rank 变化清空）
4. ✅ pytest：`tests/test_gua138_grouping_cache.py` 全绿
5. ✅ 回归：GUA-131~137 + GUA-123 + GUA-122 仍绿
6. ✅ ITERATIONS 末追加：`v7-gua138-grouping-cache-implemented`

**关联 GUA**：
- GUA-061：grouping_engine（消费者）
- GUA-137：玩家整手结构推断增强（缓存消费者）
- GUA-136：玩家剩牌估算增强
- GUA-135：双进优先级判定
- WF-12：决策溯源

---

## 7. 不做 / 后续

**本 GUA 不做**：
- ❌ grouping_engine.enumerate_groupings 内部缓存（GUA-061 已 frozen）— GUA-138 是外部消费者
- ❌ 增量计算（从旧 plan 减去出牌 → 新 plan）— 复杂度高 + 收益小，留 GUA-139
- ❌ 跨局缓存持久化 — 进程级缓存足够
- ❌ 排除法推断（max_infer_depth 默认 0）— 留 GUA-139

**后续 GUA**：
- **GUA-139**：增量计算（玩家出 1 张后从旧 plan 复用）+ 排除法推断
- **GUA-140**：贡牌/抗贡阶段后手牌重建（早期阶段推断准确性）

---

## 8. 与 GUA-137 对接

GUA-138 是 GUA-137 `_estimate_player_grouping_plan` 的**性能优化**：

| 函数 | GUA-137 | GUA-138 |
|------|---------|---------|
| `enumerate_groupings` 调用频率 | 每次 decide 调用 | 缓存命中时 0 次 |
| 26 张手牌耗时 | ~4 ms / 次 | **< 0.1 ms / 次（命中）** |
| decide 时延影响 | 8 ms（2 次调用） | 1 ms（首次 miss）+ < 0.1 ms（后续 hit） |
| 一局 12 副牌开销 | 40-100 ms | **< 10 ms** |

**GUA-138 接管** enumerate_groupings 调用 → **零行为变化**（仅性能）。

---

## 9. 不做 / 边界

- ❌ 不修改 grouping_engine.enumerate_groupings 内部（GUA-061 已 frozen）
- ❌ 不修改 `_estimate_player_hand_cards` / `_estimate_player_num_rounds` / `_estimate_player_sprint_capability_v2`（GUA-136/137 已落地）
- ❌ 不引入新的 feature vector
- ❌ 不持久化缓存到磁盘
- ❌ 不实现真正的增量计算（O(N) → O(1) 优化）— 留 GUA-139

---

## 10. 交叉引用

- **GUA-052**：MemoryTracker
- **GUA-061**：grouping_engine
- **GUA-125 §0.5**：C1-C6 主表
- **GUA-135**：双进优先级判定
- **GUA-136**：玩家剩牌估算增强
- **GUA-137**：玩家整手结构推断增强
- **WF-12**：决策溯源
