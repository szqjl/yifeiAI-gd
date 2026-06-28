# -*- coding: utf-8 -*-
"""
card_mask group_members multiset 真源 — 4~8 星炸与重复牌串

覆盖 handoff 2026-06-21：Dict[str,tuple] 同 key 覆盖导致
五星/六星/七星/八星炸及双 SQ 四 Q 炸诊断与拆 core 误判。
"""
import pytest

from src.v.nn.features.grouping_engine import GroupingPlan, enumerate_groupings
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _bomb_hand(rank: str, count: int, *, pad_rank: str = "3") -> list:
    """构造 count 张同点炸弹 + 若干垫牌（允许重复花色 key）。"""
    suits = ["S", "H", "C", "D", "S", "H", "C", "S"]
    bomb = [f"{suits[i]}{rank}" for i in range(count)]
    pad = [f"D{pad_rank}", f"C{pad_rank}"]
    return bomb + pad


def _plan_with_bomb(rank: str, count: int) -> tuple:
    hand = _bomb_hand(rank, count)
    plan = GroupingPlan()
    plan.bombs = [hand[:count]]
    plan.singles = hand[count:]
    return plan.to_card_mask()


class TestGroupMembersMultiset:
    """group_members 保留重复牌串，mask 键可少于实际张数。"""

    @pytest.mark.parametrize("rank,count,label", [
        ("10", 5, "五星炸"),
        ("J", 6, "六星炸"),
        ("7", 7, "七星炸"),
        ("9", 8, "八星炸"),
    ])
    def test_star_bomb_member_count(self, rank, count, label):
        mask, type_map, group_members = _plan_with_bomb(rank, count)
        bomb_gid = next(gid for gid, t in type_map.items() if t == "bomb")
        members = group_members[bomb_gid]
        assert len(members) == count, f"{label}: group_members 应有 {count} 张"
        assert type_map[bomb_gid] == "bomb"
        # mask 因重复 key 可能少于 count，但 gsize 仍应正确
        sample = mask[members[0]]
        assert sample[2] == count

    def test_four_q_with_duplicate_sq(self):
        """四 Q 炸含双 SQ：group_members 4 张，mask 仅 3 key。"""
        hand = ["SQ", "SQ", "HQ", "DQ", "S3"]
        plan = GroupingPlan()
        plan.bombs = [["SQ", "SQ", "HQ", "DQ"]]
        plan.singles = ["S3"]
        mask, type_map, group_members = plan.to_card_mask()
        bomb_gid = next(gid for gid, t in type_map.items() if t == "bomb")
        assert len(group_members[bomb_gid]) == 4
        assert len([c for c in mask if c.endswith("Q") or c == "SQ"]) <= 3
        assert group_members[bomb_gid].count("SQ") == 2


class TestBrokenCoreStarBombs:
    """部分拆 5~8 星炸应判 broken；整炸打出不拆。"""

    @pytest.mark.parametrize("rank,count", [
        ("10", 5),
        ("J", 6),
        ("7", 7),
        ("9", 8),
    ])
    def test_partial_star_bomb_breaks_core(self, rank, count):
        mask, type_map, group_members = _plan_with_bomb(rank, count)
        bomb_gid = next(gid for gid, t in type_map.items() if t == "bomb")
        cards = group_members[bomb_gid]

        full = ["Bomb", rank if rank != "10" else "T", list(cards)]
        assert UltimateWinRateEngineV7._get_broken_core_type(
            full, mask, type_map, group_members) is None

        partial = ["Single", rank if rank != "10" else "T", [cards[0]]]
        assert UltimateWinRateEngineV7._get_broken_core_type(
            partial, mask, type_map, group_members) == "bomb"

        two = ["Pair", rank if rank != "10" else "T", cards[:2]]
        assert UltimateWinRateEngineV7._get_broken_core_type(
            two, mask, type_map, group_members) == "bomb"

    def test_duplicate_sq_partial_breaks_four_q(self):
        hand = ["SQ", "SQ", "HQ", "DQ"]
        plan = GroupingPlan()
        plan.bombs = [hand]
        mask, type_map, group_members = plan.to_card_mask()

        partial = ["Single", "Q", ["SQ"]]
        assert UltimateWinRateEngineV7._get_broken_core_type(
            partial, mask, type_map, group_members) == "bomb"

        full = ["Bomb", "Q", hand]
        assert UltimateWinRateEngineV7._get_broken_core_type(
            full, mask, type_map, group_members) is None


class TestBasicClassifyStarBombs:
    """降级路径 _basic_classify 同样产出完整 group_members。"""

    @pytest.mark.parametrize("rank,count", [
        ("10", 5),
        ("J", 6),
        ("7", 7),
        ("9", 8),
    ])
    def test_basic_classify_bomb_size(self, rank, count):
        hand = _bomb_hand(rank, count)
        mask, type_map, group_members = UltimateWinRateEngineV7._basic_classify(
            hand, "2")
        bomb_gid = next(gid for gid, t in type_map.items() if t == "bomb")
        assert len(group_members[bomb_gid]) == count


class TestRecommendBombFromMask:
    """炸弹推荐应读到完整 5~8 张，而非 mask 去重后的张数。"""

    @pytest.mark.parametrize("rank,count", [
        ("10", 5),
        ("J", 6),
        ("7", 7),
        ("9", 8),
    ])
    def test_recommend_bomb_size(self, rank, count):
        mask, type_map, group_members = _plan_with_bomb(rank, count)
        engine = UltimateWinRateEngineV7(player_id=0)
        engine._group_type_map = type_map
        engine._group_members = group_members
        rec = engine._recommend_bomb_from_mask(mask, "2")
        assert rec is not None
        assert len(rec["cards"]) == count
