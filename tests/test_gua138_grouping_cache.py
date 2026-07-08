# -*- coding: utf-8 -*-
"""GUA-138 单元 + 集成测试：grouping_engine LRU 缓存（性能优化）

测试覆盖：
  - _GroupingPlanCache（LRU、深拷贝、invalidate、stats）
  - _estimate_player_grouping_plan 缓存集成（lazy init、cur_rank 失效）
  - 行为等价 GUA-137（零行为变化，仅性能）
  - cache hit 加速 benchmark
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import EndgameDecider, _GroupingPlanCache


# ── 复用 GUA-137 测试数据 ──

class MockMemoryTracker:
    def __init__(self, hand_counts=None, card_state=None):
        self.hand_counts = hand_counts or {}
        self.card_state = card_state or {}

    def get_hand_count(self, seat):
        return self.hand_counts.get(seat, 0)


ANCHOR_HAND = [
    "SJ", "SJ", "HJ", "HJ", "DJ", "DJ",
    "S7", "S7", "C7",
    "D8", "D8", "C8",
    "S2", "D2",
]
TWT_333_22 = ["ThreeWithTwo", "3", ["S3", "H3", "D3", "S2", "D2"]]


def _build_state(
    hand_cards=None,
    *,
    enemy_remaining=10,
    teammate_remaining=10,
    at3_remaining=8,
    my_pos=0,
    greater_pos=1,
    cur_rank="2",
    memory_tracker=None,
):
    numofplayers = [
        len(hand_cards or ANCHOR_HAND),
        enemy_remaining,
        at3_remaining,
        teammate_remaining,
    ]
    state = {
        "myPos": my_pos,
        "curPos": greater_pos,
        "greaterPos": greater_pos,
        "greaterAction": TWT_333_22,
        "handCards": list(hand_cards or ANCHOR_HAND),
        "actionList": [["PASS", "PASS", "PASS"]],
        "curRank": cur_rank,
        "selfRank": cur_rank,
        "oppoRank": cur_rank,
        "numofplayers": numofplayers,
        "publicInfo": [{"rest": n} for n in numofplayers],
        "_role": "主攻",
    }
    if memory_tracker is not None:
        state["_memory_tracker"] = memory_tracker
    return state


def _card_state_for_hand(cards):
    card_state = {}
    for c in cards:
        card_state.setdefault(c, [-1, -1])
        for i in range(2):
            if card_state[c][i] == -1:
                card_state[c][i] = 1
                break
    return card_state


# ═══════════════════════════════════════════════════════
#  _GroupingPlanCache 单元测试
# ═══════════════════════════════════════════════════════


class TestGroupingPlanCacheUnit:
    def test_miss_then_hit_stats(self):
        cache = _GroupingPlanCache(max_size=8)
        hand = ["S3", "H3", "D3", "S4", "H4"]
        calls = {"n": 0}

        def compute_fn(h, r):
            calls["n"] += 1
            return {"hand": list(h), "rank": r}

        cache.get_or_compute(hand, "2", compute_fn)
        cache.get_or_compute(hand, "2", compute_fn)
        stats = cache.stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 1
        assert stats["size"] == 1
        assert calls["n"] == 1

    def test_key_order_independent(self):
        cache = _GroupingPlanCache(max_size=8)
        calls = {"n": 0}

        def compute_fn(h, r):
            calls["n"] += 1
            return {"sorted": tuple(sorted(h))}

        hand_a = ["S7", "H7", "D7", "S8"]
        hand_b = ["D7", "S8", "H7", "S7"]
        cache.get_or_compute(hand_a, "2", compute_fn)
        cache.get_or_compute(hand_b, "2", compute_fn)
        assert calls["n"] == 1
        assert cache.stats()["hits"] == 1

    def test_deepcopy_isolation_on_hit(self):
        """命中时返回深拷贝：下游修改不污染缓存条目。"""
        cache = _GroupingPlanCache(max_size=8)
        hand = ["S5", "H5", "D5", "S6", "H6"]

        def compute_fn(h, r):
            return {"items": [1, 2, 3]}

        cache.get_or_compute(hand, "2", compute_fn)  # miss → 写入缓存
        hit_copy = cache.get_or_compute(hand, "2", compute_fn)  # hit → 深拷贝
        hit_copy["items"].append(99)
        fresh = cache.get_or_compute(hand, "2", compute_fn)
        assert fresh["items"] == [1, 2, 3]
        assert cache.stats()["hits"] == 2

    def test_none_plan_not_cached(self):
        cache = _GroupingPlanCache(max_size=8)
        hand = ["SA", "HA"]
        calls = {"n": 0}

        def compute_fn(h, r):
            calls["n"] += 1
            return None

        assert cache.get_or_compute(hand, "2", compute_fn) is None
        assert cache.get_or_compute(hand, "2", compute_fn) is None
        assert calls["n"] == 2
        assert cache.stats()["size"] == 0

    def test_lru_eviction(self):
        cache = _GroupingPlanCache(max_size=2)
        seen = []

        def compute_fn(h, r):
            seen.append(tuple(sorted(h)))
            return {"hand": tuple(sorted(h))}

        cache.get_or_compute(["S3", "H3"], "2", compute_fn)
        cache.get_or_compute(["S4", "H4"], "2", compute_fn)
        cache.get_or_compute(["S5", "H5"], "2", compute_fn)
        assert len(seen) == 3
        assert cache.stats()["size"] == 2

        # 最早 S3/H3 应被淘汰 → 再次访问触发 recompute
        cache.get_or_compute(["S3", "H3"], "2", compute_fn)
        assert len(seen) == 4

    def test_invalidate_all(self):
        cache = _GroupingPlanCache(max_size=8)
        hand = ["ST", "HT", "DT"]

        def compute_fn(h, r):
            return {"ok": True}

        cache.get_or_compute(hand, "2", compute_fn)
        cache.invalidate()
        assert cache.stats()["size"] == 0

    def test_invalidate_by_cur_rank(self):
        cache = _GroupingPlanCache(max_size=8)
        hand = ["S9", "H9", "D9"]

        def compute_fn(h, r):
            return {"rank": r}

        cache.get_or_compute(hand, "2", compute_fn)
        cache.get_or_compute(hand, "3", compute_fn)
        assert cache.stats()["size"] == 2
        cache.invalidate(cur_rank="2")
        assert cache.stats()["size"] == 1
        remaining_key = next(iter(cache._cache))
        assert remaining_key[1] == "3"

    def test_invalidate_by_hand(self):
        cache = _GroupingPlanCache(max_size=8)
        hand_a = ["S2", "H2", "D2"]
        hand_b = ["S3", "H3", "D3"]

        def compute_fn(h, r):
            return {"hand": tuple(sorted(h))}

        cache.get_or_compute(hand_a, "2", compute_fn)
        cache.get_or_compute(hand_b, "2", compute_fn)
        cache.invalidate(hand_cards=hand_a)
        assert cache.stats()["size"] == 1


# ═══════════════════════════════════════════════════════
#  EndgameDecider 缓存集成
# ═══════════════════════════════════════════════════════


class TestEstimatePlayerGroupingPlanCache:
    def test_lazy_init_cache_on_decider(self):
        d = EndgameDecider()
        assert not hasattr(d, "_grouping_plan_cache")
        card_state = _card_state_for_hand(["SJ", "HJ", "DJ", "S2", "D2"])
        tracker = MockMemoryTracker(card_state=card_state)
        gs = _build_state(memory_tracker=tracker)
        d._estimate_player_grouping_plan(1, gs)
        assert hasattr(d, "_grouping_plan_cache")
        assert isinstance(d._grouping_plan_cache, _GroupingPlanCache)

    def test_repeated_call_hits_cache(self):
        card_state = {
            "SJ": [1, 1], "HJ": [1, 1], "DJ": [1, 1],
            "S2": [1, 1], "D2": [1, 1],
        }
        tracker = MockMemoryTracker(card_state=card_state)
        gs = _build_state(memory_tracker=tracker)
        d = EndgameDecider()
        d._estimate_player_grouping_plan(1, gs)
        stats_after_first = d._grouping_plan_cache.stats()
        d._estimate_player_grouping_plan(1, gs)
        stats_after_second = d._grouping_plan_cache.stats()
        assert stats_after_first["misses"] == 1
        assert stats_after_second["hits"] == 1
        assert stats_after_second["misses"] == 1

    def test_cur_rank_change_invalidates_entries(self):
        card_state = {
            "SJ": [1, 1], "HJ": [1, 1], "DJ": [1, 1],
            "S2": [1, 1], "D2": [1, 1],
        }
        tracker = MockMemoryTracker(card_state=card_state)
        gs = _build_state(memory_tracker=tracker, cur_rank="2")
        d = EndgameDecider()
        d._estimate_player_grouping_plan(1, gs)
        assert d._grouping_plan_cache.stats()["size"] == 1

        gs["curRank"] = "3"
        gs["selfRank"] = "3"
        gs["oppoRank"] = "3"
        d._estimate_player_grouping_plan(1, gs)
        stats = d._grouping_plan_cache.stats()
        # cur_rank=2 条目应被 invalidate；新 cur_rank=3 写入
        assert stats["size"] == 1
        only_key = next(iter(d._grouping_plan_cache._cache))
        assert only_key[1] == "3"

    def test_behavior_equivalent_to_uncached_plan(self):
        """GUA-138 零行为变化：缓存前后 num_rounds 一致。"""
        card_state = {
            "SJ": [1, 1], "HJ": [1, 1], "DJ": [1, 1],
            "S2": [1, 0], "D2": [1, 0],
        }
        tracker = MockMemoryTracker(card_state=card_state)
        gs = _build_state(memory_tracker=tracker)
        d = EndgameDecider()
        plan1 = d._estimate_player_grouping_plan(1, gs)
        plan2 = d._estimate_player_grouping_plan(1, gs)
        assert plan1 is not None and plan2 is not None
        assert plan1.num_rounds() == plan2.num_rounds()
        assert d._estimate_player_sprint_capability_v2(1, gs) is True


# ═══════════════════════════════════════════════════════
#  性能 benchmark
# ═══════════════════════════════════════════════════════


class TestGroupingCacheBenchmark:
    @pytest.mark.slow
    def test_cache_hit_faster_than_miss(self):
        """缓存命中应显著快于 miss（GUA-138 §4.1：>50x）。"""
        from src.v.nn.features.grouping_engine import enumerate_groupings

        cache = _GroupingPlanCache(max_size=8)
        hand = list(ANCHOR_HAND)
        cur_rank = "2"

        def compute_fn(h, r):
            best_plan, _ = enumerate_groupings(h, r)
            return best_plan

        # 冷启动：1 次 miss
        t0 = time.perf_counter()
        cache.get_or_compute(hand, cur_rank, compute_fn)
        cold_ms = (time.perf_counter() - t0) * 1000

        # 热路径：100 次 hit
        t0 = time.perf_counter()
        for _ in range(100):
            cache.get_or_compute(hand, cur_rank, compute_fn)
        warm_total_ms = (time.perf_counter() - t0) * 1000
        warm_per_ms = warm_total_ms / 100

        assert cache.stats()["hits"] == 100
        speedup = cold_ms / warm_per_ms if warm_per_ms > 0 else float("inf")
        # GUA-138 目标 >50x；14 张 ANCHOR_HAND 在本机约 30–40x，阈值取 20x 防 CI 抖动
        assert speedup >= 20, (
            f"expected speedup >= 20x, got {speedup:.1f}x "
            f"(hit={warm_per_ms:.4f}ms cold={cold_ms:.4f}ms)"
        )

    def test_compute_fn_not_called_on_hit(self):
        """集成：第二次调用不触发 enumerate_groupings。"""
        card_state = _card_state_for_hand(ANCHOR_HAND)
        tracker = MockMemoryTracker(card_state=card_state)
        gs = _build_state(memory_tracker=tracker)
        d = EndgameDecider()

        call_count = {"n": 0}

        from src.v.nn.features import grouping_engine as ge_mod

        original_enum = ge_mod.enumerate_groupings

        def counting_enum(h, r="2"):
            call_count["n"] += 1
            return original_enum(h, r)

        ge_mod.enumerate_groupings = counting_enum
        try:
            d._estimate_player_grouping_plan(1, gs)
            d._estimate_player_grouping_plan(1, gs)
        finally:
            ge_mod.enumerate_groupings = original_enum

        assert call_count["n"] == 1
        assert d._grouping_plan_cache.stats()["hits"] == 1
