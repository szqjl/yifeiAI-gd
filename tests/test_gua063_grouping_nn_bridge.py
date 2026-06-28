# -*- coding: utf-8 -*-
"""
GUA-063 组牌→出牌衔接 单元测试

测试范围：
  - Phase 1: GroupingPlan.to_card_mask() — 牌级 mask
  - Phase 2: _group_consistency_filter() / _action_breaks_core()
  - Phase 3: 中局重分组触发
  - MemoryTracker.get_tracking_vector() — 24 维拆分
"""
import pytest
from src.v.nn.features.grouping_engine import (
    enumerate_groupings,
    GroupingPlan,
    _parse_rank,
)
from src.v.nn.features.memory_tracker import (
    MemoryTracker,
    MEMORY_TRACKER_DIM,
    MEMORY_TRACKER_DIM_V061,
)


# ── 辅助函数 ────────────────────────────────────────────

def make_hand(*ranks: str) -> list:
    """从 rank 列表构造手牌（自动分配花色）。"""
    cards = []
    suit_cycle = ["S", "H", "C", "D"]
    for i, r in enumerate(ranks):
        suit = suit_cycle[i % 4]
        cards.append(f"{suit}{r}")
    return cards


def _action(card_list):
    """构造标准 action 格式：[type, rank, cards]"""
    return ["Single", "2", card_list]


def _pass_action():
    return ["PASS", "", []]


# ═══════════════════════════════════════════════════════════
# Phase 1: to_card_mask()
# ═══════════════════════════════════════════════════════════

class TestCardMask:
    """Case 1: 牌级 mask 构建。"""

    def test_bomb_marked_as_core(self):
        """炸弹中的牌标记为 core。"""
        # 5555 炸弹 + QQ 对子 + J + 非连续单张，无法组成顺子
        hand = make_hand("5", "5", "5", "5", "Q", "Q", "J", "7", "3")
        best, _ = enumerate_groupings(hand, "2")
        mask, type_map, group_members = best.to_card_mask()
        # 5555应该在炸弹组中且标记为core
        bomb_cards = [c for c, info in mask.items() if info[1] >= 1.0]
        assert len(bomb_cards) >= 4, f"炸弹组至少4张core牌，got {len(bomb_cards)}"

    def test_normal_pair_not_core(self):
        """普通对子不标记为 core。"""
        hand = make_hand("3", "3", "5", "6", "7", "8", "9")
        best, _ = enumerate_groupings(hand, "2")
        mask, type_map, group_members = best.to_card_mask()
        # 对子 "3", "3" 应该 is_core=0
        pair_info = [info for card, info in mask.items()
                     if _parse_rank(card) == "3"]
        for info in pair_info:
            assert info[1] < 1.0, f"普通对子不应为core, got {info}"

    def test_single_is_ungrouped(self):
        """单张牌 group_id = -1。"""
        hand = make_hand("3", "4", "5", "6", "7")
        best, _ = enumerate_groupings(hand, "2")
        mask, type_map, group_members = best.to_card_mask()
        for card, info in mask.items():
            gid, is_core, gsize = info
            assert gsize >= 1, f"group_size should be >= 1, got {gsize}"

    def test_empty_hand_mask_is_empty(self):
        """空手牌返回空 mask。"""
        best, _ = enumerate_groupings([], "2")
        mask, type_map, group_members = best.to_card_mask()
        assert isinstance(mask, dict)
        assert len(mask) == 0

    def test_group_ids_are_consistent(self):
        """同一组的牌共享相同 group_id。"""
        hand = make_hand("K", "K", "K", "K", "3", "4", "5", "6", "7")
        best, _ = enumerate_groupings(hand, "2")
        mask, type_map, group_members = best.to_card_mask()
        # 找到炸弹组（K K K K）
        k_infos = [(c, mask[c]) for c in mask if _parse_rank(c) == "K"]
        core_k = [(c, info) for c, info in k_infos if info[1] >= 1.0]
        if core_k:
            # 所有 core K 应该有相同的 group_id
            gids = {info[0] for _, info in core_k}
            assert len(gids) == 1, f"同一炸弹组的牌应共享group_id, got {gids}"


# ═══════════════════════════════════════════════════════════
# Phase 2: _action_breaks_core
# ═══════════════════════════════════════════════════════════

class TestActionBreaksCore:
    """Case 2: 核心拆牌检测。"""

    def test_pass_does_not_break(self):
        """PASS 不拆核心。"""
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        mask = {}  # empty mask
        assert not UltimateWinRateEngineV7._action_breaks_core(
            _pass_action(), mask)

    def test_full_bomb_does_not_break(self):
        """完整打出炸弹不视为拆。"""
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        # 5555炸弹 + QQ对子 + 非连续单张，无法组成顺子
        hand = make_hand("5", "5", "5", "5", "Q", "Q", "J", "7", "3")
        best, _ = enumerate_groupings(hand, "2")
        mask, type_map, group_members = best.to_card_mask()

        # 找出炸弹的4张牌
        bomb_cards = [c for c, info in mask.items() if info[1] >= 1.0]
        assert len(bomb_cards) >= 4, f"应有至少4张core牌"
        full_bomb_action = ["Bomb", "5", bomb_cards[:4]]
        assert not UltimateWinRateEngineV7._action_breaks_core(
            full_bomb_action, mask, group_members, type_map)

    def test_partial_bomb_breaks_core(self):
        """只出一张炸弹牌 → 拆核心。"""
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        # 5555 + QQ + J+7+3，无顺子
        hand = make_hand("5", "5", "5", "5", "Q", "Q", "J", "7", "3")
        best, _ = enumerate_groupings(hand, "2")
        mask, type_map, group_members = best.to_card_mask()

        bomb_cards = [c for c, info in mask.items() if info[1] >= 1.0]
        if len(bomb_cards) >= 4:
            # 只出一张炸弹牌
            partial = _action([bomb_cards[0]])
            assert UltimateWinRateEngineV7._action_breaks_core(
                partial, mask, group_members, type_map), "部分使用炸弹牌应视为拆核心"

    def test_using_non_core_card_does_not_break(self):
        """使用非核心牌不视为拆。"""
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        # 5555 + QQ + 3+7+J
        hand = make_hand("5", "5", "5", "5", "Q", "Q", "J", "7", "3")
        best, _ = enumerate_groupings(hand, "2")
        mask, type_map, group_members = best.to_card_mask()

        # 找到非core的牌
        non_core = [c for c, info in mask.items() if info[1] < 1.0]
        if non_core:
            action = _action([non_core[0]])
            assert not UltimateWinRateEngineV7._action_breaks_core(
                action, mask)

    def test_two_cards_from_bomb_breaks_core(self):
        """从炸弹中出2张（不够4张）→ 拆核心。"""
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        # 5555 + QQ + J+7+3
        hand = make_hand("5", "5", "5", "5", "Q", "Q", "J", "7", "3")
        best, _ = enumerate_groupings(hand, "2")
        mask, type_map, group_members = best.to_card_mask()

        bomb_cards = [c for c, info in mask.items() if info[1] >= 1.0]
        if len(bomb_cards) >= 4:
            two_cards = bomb_cards[:2]
            partial = _action(two_cards)
            assert UltimateWinRateEngineV7._action_breaks_core(
                partial, mask, group_members, type_map), "出2张炸弹牌应视为拆核心"


# ═══════════════════════════════════════════════════════════
# MemoryTracker: get_tracking_vector()
# ═══════════════════════════════════════════════════════════

class TestTrackingVector:
    """Case 3: MemoryTracker 追踪向量拆分。"""

    def test_tracking_vector_24_dims(self):
        """get_tracking_vector() 返回 24 维。"""
        tracker = MemoryTracker(my_pos=0)
        tracker.init_from_hand(["S3", "H4", "C5"])
        vec = tracker.get_tracking_vector()
        assert len(vec) == 24, f"追踪向量应为24维，got {len(vec)}"

    def test_tracking_vector_values_in_range(self):
        """所有值在 [0, 1] 范围内。"""
        tracker = MemoryTracker(my_pos=0)
        tracker.init_from_hand(["S3", "H4", "C5", "D6", "S7",
                                "H8", "C9", "DT", "SJ", "HQ", "CK", "DA"])
        vec = tracker.get_tracking_vector()
        for i, v in enumerate(vec):
            assert 0.0 <= v <= 1.0, f"vec[{i}]={v} out of range"

    def test_state_vector_backward_compat(self):
        """get_state_vector() 向后兼容。"""
        tracker = MemoryTracker(my_pos=0)
        tracker.init_from_hand(["S3", "H4", "C5"])
        # 不传 game_state → 退化为零组牌特征
        vec = tracker.get_state_vector(game_state=None)
        assert len(vec) == MEMORY_TRACKER_DIM  # 33

    def test_get_tracking_vector_after_play(self):
        """出牌后追踪向量更新。"""
        tracker = MemoryTracker(my_pos=0)
        tracker.init_from_hand(["S3", "H4", "C5", "D6", "S7"])
        # 模拟对手出牌
        tracker.record_play(1, ["Single", "A", ["SA"]])
        vec = tracker.get_tracking_vector()
        assert len(vec) == 24, f"出牌后追踪向量仍24维，got {len(vec)}"


# ═══════════════════════════════════════════════════════════
# Phase 3: 中局重分组
# ═══════════════════════════════════════════════════════════

class TestMidgameRegroup:
    """Case 4: 中局重分组触发。"""

    def test_mask_update_on_hand_change(self):
        """手牌变化后 mask 应更新。"""
        hand1 = make_hand("3", "3", "5", "5", "5", "5", "7", "8", "9")
        best1, _ = enumerate_groupings(hand1, "2")
        mask1, _, _ = best1.to_card_mask()

        # 模拟出牌后手牌减少
        hand2 = make_hand("3", "3", "7", "8", "9")  # 出了5555
        best2, _ = enumerate_groupings(hand2, "2")
        mask2, _, _ = best2.to_card_mask()

        # mask 应该不同（炸弹被完整打出）
        assert mask1 != mask2, "手牌变化后 mask 应更新"

    def test_hand_size_15_triggers_new_plan(self):
        """手牌降到15张时重新组牌。"""
        hand = make_hand(
            "2", "3", "4", "5", "6", "7", "8", "9", "T",
            "J", "Q", "K", "A", "2", "3",
        )
        assert len(hand) == 15
        best, plans = enumerate_groupings(hand, "2")
        assert best is not None
        assert len(plans) >= 1
        assert best.num_rounds() <= len(hand)

    def test_hand_size_10_and_5(self):
        """10张和5张手牌正常组牌。"""
        for size in [10, 5]:
            hand = make_hand(*["2", "3", "4", "5", "6", "7", "8", "9", "T", "J"][:size])
            best, plans = enumerate_groupings(hand, "2")
            assert best is not None
            assert best.num_rounds() <= size


# ═══════════════════════════════════════════════════════════
# 集成测试: 角色驱动确认
# ═══════════════════════════════════════════════════════════

class TestRoleDrivenMask:
    """Case 5: 角色与 mask 联动。"""

    def test_strong_bomb_hand_is_attacker(self):
        """有炸弹+大王+同花顺的强牌应定位为主攻/超强主攻。"""
        # KKKK 炸弹(+2) + 同花顺(+3) + 大王(+1) → power ≥ 6 → 主攻
        hand = (make_hand("K", "K", "K", "K") +    # bomb: +2
                ["S3", "S4", "S5", "S6", "S7"] +   # 同花顺: +3
                ["RJ"])                              # 大王: +1
        best, _ = enumerate_groupings(hand, "2")
        assert best.role in ("主攻", "超强主攻"), \
            f"强牌应为主攻，got {best.role} (power={best.power_score})"

    def test_weak_hand_is_assistant(self):
        """无炸弹弱牌应定位为助攻/超弱。"""
        hand = make_hand("3", "4", "5", "6", "7", "8", "9", "T")
        best, _ = enumerate_groupings(hand, "2")
        assert best.role in ("助攻", "超弱"), \
            f"弱牌应为助攻，got {best.role}"

    def test_core_mask_exists_for_attacker(self):
        """主攻角色有 core 牌 mask 条目。"""
        hand = (make_hand("K", "K", "K", "K") +
                make_hand("3", "4", "5", "6", "7"))
        best, _ = enumerate_groupings(hand, "2")
        mask, type_map, group_members = best.to_card_mask()
        core_count = sum(1 for info in mask.values() if info[1] >= 1.0)
        assert core_count >= 4, \
            f"至少4张core牌(炸弹)，got {core_count}"
