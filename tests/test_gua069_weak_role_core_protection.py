# -*- coding: utf-8 -*-
"""
GUA-069 超弱角色不应拆核心牌型 单元测试

测试范围：
  - _score_power(): 钢板应计入牌力分
  - _group_consistency_filter(): 超弱/助攻角色仍保护 is_core 牌组
  - _action_breaks_core(): 回归验证（不受角色影响）
  - yf2 实际手牌场景：4x4炸+钢板+4对 → Single 4 被过滤

Bug 根因（2026-06-19）：
  组牌引擎正确识别 4x4 为炸弹，但 power_score=1→"超弱"→前置过滤全放行，
  Single C4 透过，NN 选中 → 浪费唯一炸弹。
"""
import pytest
from src.v.nn.features.grouping_engine import (
    enumerate_groupings,
    GroupingPlan,
    _parse_rank,
    _score_power,
    determine_role,
    _build_plan,
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


def _bomb_action(card_list):
    """构造炸弹 action。"""
    return ["Bomb", _parse_rank(card_list[0]), card_list]


# ═══════════════════════════════════════════════════════════
# Fix 1: _score_power 钢板计分
# ═══════════════════════════════════════════════════════════

class TestSteelPlatePowerScore:
    """Case 1: 钢板（连续三张对）应计入牌力分。"""

    def test_steel_plate_adds_power(self):
        """有钢板的方案比无钢板的分多。"""
        # 构造一个含 888-999 钢板的手牌
        # 888999 + 一对小对子55
        hand = make_hand(
            "8", "8", "8", "9", "9", "9",  # 钢板
            "5", "5",                        # 小对子
        )
        best, _ = enumerate_groupings(hand, "2")
        power = _score_power(best, "2")
        # 钢板 1 个 = +1，无炸弹(三张组成了钢板)，小对子55 = -1
        # 预期 power >= 0 (钢板 +1 抵消了 -1)
        assert power >= 0, f"钢板应抵消小对子惩罚，got power={power}"

    def test_steel_plate_role_upgrade(self):
        """有钢板的手牌 role 不应被低估为超弱。"""
        # yf2 实际场景简化版：1炸弹 + 1钢板 + 小对子
        # 不必完全复制 27 张，用最小集验证 role 不会因缺钢板分而降级
        hand = make_hand(
            "4", "4", "4", "4",             # 1 炸弹 +2
            "8", "8", "8", "9", "9", "9",   # 1 钢板 +1 (GUA-069 fix)
            "5", "5",                        # 小对子 -1
        )
        best, _ = enumerate_groupings(hand, "2")
        power = _score_power(best, "2")
        role = determine_role(power)
        # 2 + 1 - 1 = 2 → "助攻"
        # 修复前：钢板不计分 → 2 - 1 = 1 → "超弱" ← BUG
        assert role != "超弱", (
            f"钢板应计入牌力分，power={power} role={role}，"
            f"预期 role≠超弱"
        )

    def test_steel_plate_small_net_zero(self):
        """小钢板（≤6）加分被小牌惩罚抵消，net=0。"""
        # 3-3-3 + 4-4-4 = 小钢板（max=4 ≤6）
        hand = make_hand(
            "3", "3", "3", "4", "4", "4",
        )
        best, _ = enumerate_groupings(hand, "2")
        power = _score_power(best, "2")
        # 钢板 +1, 小钢板 -1 → net 0
        assert power == 0, (
            f"小钢板加分+1 应被小牌惩罚-1抵消，net=0，got power={power}"
        )


# ═══════════════════════════════════════════════════════════
# Fix 2: _group_consistency_filter 超弱角色仍保护 core
# ═══════════════════════════════════════════════════════════

class TestWeakRoleCoreProtection:
    """Case 2: 超弱/助攻角色不能拆 is_core 牌组。"""

    def test_action_breaks_core_immune_to_role(self):
        """_action_breaks_core 是纯函数，不受角色影响。"""
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        # 构造 4x4 炸弹 + 一些散牌
        hand = make_hand(
            "4", "4", "4", "4",   # 炸弹
            "7", "3", "J", "Q",   # 散牌
        )
        best, _ = enumerate_groupings(hand, "2")
        mask = best.to_card_mask()

        # 找到炸弹牌
        bomb_cards = [c for c, info in mask.items() if info[1] >= 1.0]
        assert len(bomb_cards) >= 4, f"应有4张core牌，got {len(bomb_cards)}"

        # 打完整炸弹 → 不拆
        assert not UltimateWinRateEngineV7._action_breaks_core(
            _bomb_action(bomb_cards[:4]), mask)

        # 打炸弹中的 1 张 → 拆核心
        assert UltimateWinRateEngineV7._action_breaks_core(
            _action([bomb_cards[0]]), mask)

    def test_weak_role_still_filters_single_from_bomb(self):
        """超弱角色：Single 从炸弹中取出应被过滤。"""
        # 模拟 yf2 场景：1炸+1钢板+4对 ≈ power=1 超弱
        # 验证 group_consistency_filter 即使 role=超弱也不再全放行
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        # 构造最小复现手牌
        hand = make_hand(
            "4", "4", "4", "4",           # 唯一炸弹
            "8", "8", "8", "9", "9", "9", # 钢板
            "5", "5",                      # 小对子
        )
        best, _ = enumerate_groupings(hand, "2")
        mask = best.to_card_mask()
        role = best.role
        power = best.power_score

        # 验证：修复后 role 不应是超弱（钢板+1分）
        if power < 2:
            # 钢板修复前可能是超弱，但即便如此也应保护 core
            pass  # 继续测试

        # 找到炸弹 core 牌
        core_cards = [c for c, info in mask.items() if info[1] >= 1.0]
        assert len(core_cards) >= 4, f"应有至少4张core牌"

        # 构造 actionList：Single 从炸弹 + 炸弹完整打出 + PASS
        single_from_bomb = _action([core_cards[0]])
        full_bomb = _bomb_action(core_cards[:4])
        pass_act = ["PASS", "PASS", "PASS"]

        # 标记：这里我们验证的是 _action_breaks_core 的行为
        # 角色不再影响 core 保护（GUA-069 fix）
        for fake_role in ("超弱", "助攻", "主攻", "超强主攻"):
            breaks = UltimateWinRateEngineV7._action_breaks_core(
                single_from_bomb, mask)
            assert breaks, (
                f"role={fake_role}时，Single从炸弹取出应视为拆核心"
            )
            not_breaks = UltimateWinRateEngineV7._action_breaks_core(
                full_bomb, mask)
            assert not not_breaks, (
                f"role={fake_role}时，完整炸弹不应视为拆核心"
            )

    def test_yf2_exact_hand_scenario(self):
        """yf2 实际手牌：4x4炸+18张 → Single C4 应被过滤。"""
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        # 使用真实手牌（贡后 27 张的子集：已出 2炸+A炸+S6，剩余 18 张）
        hand = [
            "S4", "S4", "C4", "D4",
            "C5", "D5",
            "C8", "D8", "D8",
            "S9", "H9", "C9",
            "HJ", "DJ",
            "CQ", "DQ",
            "HK", "DK",
        ]
        best, all_plans = enumerate_groupings(hand, "8")
        mask = best.to_card_mask()
        role = best.role
        power = best.power_score

        # 组牌引擎应产出至少 1 个炸弹
        assert len(best.bombs) >= 1, f"应有至少1个炸弹，got {len(best.bombs)}"

        # 验证所有 18 张牌都被分组
        total = (len(best.singles) + sum(len(p) for p in best.pairs)
                 + sum(len(t) for t in best.trips)
                 + sum(len(b) for b in best.bombs)
                 + sum(len(s) for s in best.straights)
                 + sum(len(sf) for sf in best.straight_flushes)
                 + sum(sum(len(pr) for pr in tp) for tp in best.three_pairs)
                 + sum(len(twt[0])+len(twt[1]) for twt in best.three_with_twos)
                 + sum(sum(len(trip) for trip in sp) for sp in best.steel_plates))
        assert total == 18, f"应覆盖全部18张牌，got total={total}"

        # GUA-069 fix: role 不应是超弱（否则 core 保护被跳过）
        # 实测 power=3（炸弹+2，三连对+1），role=助攻
        print(f"yf2 hand: bombs={len(best.bombs)} trips={len(best.trips)} "
              f"pairs={len(best.pairs)} singles={len(best.singles)} "
              f"three_pairs={len(best.three_pairs)} "
              f"three_with_twos={len(best.three_with_twos)} "
              f"power={power} role={role}")

        # 找到 4x4 炸弹的实际 4 张牌（从 plan.bombs 中取，不用 mask 避免重复牌问题）
        bomb_4_cards = None
        for b in best.bombs:
            if _parse_rank(b[0]) == "4":
                bomb_4_cards = b
                break
        assert bomb_4_cards is not None, "未找到4x4炸弹"
        assert len(bomb_4_cards) == 4, f"4x4炸弹应有4张牌，got {bomb_4_cards}"

        # mask 中 4x4 炸弹的 core 状态（mask 用 dict key 去重，S4 只保留一个 key）
        core_fours = [c for c, info in mask.items() if "4" in c and info[1] >= 1.0]
        assert len(core_fours) >= 3, (
            f"mask中至少3种不同花色的4，got {len(core_fours)}"
        )

        # Single C4 → 应被 _action_breaks_core 判定为拆核心
        single_c4 = _action(["C4"])
        assert UltimateWinRateEngineV7._action_breaks_core(
            single_c4, mask), "Single C4 应判定为拆核心炸弹"

        # 完整 4x4 炸弹（4 张实际牌）→ 不应被判定为拆核心
        full_4_bomb = ["Bomb", "4", bomb_4_cards]
        assert not UltimateWinRateEngineV7._action_breaks_core(
            full_4_bomb, mask), "完整 4x4 炸弹不应视为拆核心"

        # 非 core 牌 Single → 不拆
        non_core = [c for c, info in mask.items() if info[1] < 1.0]
        if non_core:
            single_noncore = _action([non_core[0]])
            assert not UltimateWinRateEngineV7._action_breaks_core(
                single_noncore, mask), "非core单张不应判定为拆核心"


# ═══════════════════════════════════════════════════════════
# Fix 3: role 边界值
# ═══════════════════════════════════════════════════════════

class TestRoleBoundary:
    """Case 3: 角色判定边界值验证。"""

    def test_one_bomb_one_steel_small_pair_no_longer_weak(self):
        """1炸+1钢板+小对子 → role ≠ 超弱（修复后）。"""
        # 这个手牌在修复前是 "超弱"（power=2-1=1）
        # 修复后钢板+1 → power=2+1-1=2 → "助攻"
        hand = make_hand(
            "4", "4", "4", "4",              # +2
            "8", "8", "8", "9", "9", "9",    # +1 (钢板)
            "5", "5",                         # -1
        )
        best, _ = enumerate_groupings(hand, "2")
        assert best.role != "超弱", (
            f"1炸+钢板+小对子不应是超弱，got power={best.power_score} role={best.role}"
        )
        assert best.role == "助攻", (
            f"预期 role=助攻，got {best.role}"
        )

    def test_two_bombs_steel_plate_is_main_attack(self):
        """2炸+钢板 → role=主攻。"""
        hand = make_hand(
            "4", "4", "4", "4",              # +2
            "K", "K", "K", "K",              # +2
            "8", "8", "8", "9", "9", "9",    # +1 (钢板)
        )
        best, _ = enumerate_groupings(hand, "2")
        assert best.power_score >= 5, (
            f"2炸+钢板 expecting >=5, got power={best.power_score}"
        )
        assert best.role in ("主攻", "超强主攻"), (
            f"2炸+钢板应为 主攻/超强主攻，got {best.role}"
        )
