# -*- coding: utf-8 -*-
"""GUA-211: 炸弹/同花顺推荐被组牌保护拦截后，回退找不拆核心的同类 Bomb/SF。

背景（match 6a7476fe 19:59:05，V8=player0 超强主攻手牌 20 = Bomb8888 + SF S3-S7 + 散牌，
greater=ThreeWithTwo/K）：GUA-205 主动开炸意图触发，_recommend_bomb_from_mask 按
「SF 优先 → 牌点大优先」选中 SF/8 ['S4','S5','S6','S7','S8']（拆 Bomb 组 S8），
GUA-075 组牌保护判 broken=StraightFlush 拦截后原直接回退 PASS——而 actionList 里
完整核心 SF/7 ['S3','S4','S5','S6','S7'] 与 Bomb 8888 都在，却不被尝试。

修复：GUA-075 炸弹拦截分支调用 _find_alternative_core_intact_bomb 回退到
不拆核心的同类 Bomb/SF（follow 模式还须能压过 greater）。
"""
import logging

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_engine():
    eng = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    eng.logger = logging.getLogger("test_gua211")
    eng.player_id = 0
    eng._current_role = "超强主攻"
    eng._group_members = {
        -1: ["SQ", "DA"],
        0: ["C8", "S8", "C8", "S8"],          # Bomb 8888
        1: ["S3", "S4", "S5", "S6", "S7"],    # SF S3-S7（完整核心）
        2: ["SJ", "HJ"],
        3: ["C2", "S2"],
        4: ["CK", "DK", "SK"],
        5: ["H9", "C9"],
    }
    eng._group_type_map = {
        0: "Bomb", 1: "StraightFlush", 2: "pair", 3: "pair",
        4: "trip_in_three_with_two", 5: "pair_in_three_with_two",
    }
    eng._card_mask = {  # 退化兜底
        "C8": (0,), "S8": (0,), "S3": (1,), "S4": (1,), "S5": (1,),
        "S6": (1,), "S7": (1,),
    }
    eng.RANK_ORDER = dict(UltimateWinRateEngineV7.RANK_ORDER)
    return eng


BOMB_8888 = ["Bomb", "8", ["C8", "S8", "C8", "S8"]]
SF_6 = ["StraightFlush", "6", ["S2", "S3", "S4", "S5", "S6"]]
SF_7 = ["StraightFlush", "7", ["S3", "S4", "S5", "S6", "S7"]]
SF_8 = ["StraightFlush", "8", ["S4", "S5", "S6", "S7", "S8"]]
PASS = ["PASS", "PASS", "PASS"]

ACTION_LIST = [BOMB_8888, SF_6, SF_7, SF_8, PASS]


def test_repro_picks_sf7_over_bomb_and_sf8():
    """复现局：greater=ThreeWithTwo/K，排除被拦的 SF/8 → 回退选完整核心 SF/7。"""
    eng = _make_engine()
    greater = ["ThreeWithTwo", "K", ["DK", "HK", "SK", "H3", "H3"]]
    alt = eng._find_alternative_core_intact_bomb(
        ACTION_LIST, 3, eng._card_mask, eng._group_type_map,
        eng._group_members, greater, "2",
    )
    assert alt == 2, f"应回退到 SF/7 (idx=2)，实际 {alt}"
    assert ACTION_LIST[alt] == SF_7


def test_prefers_core_intact_sf_over_core_intact_bomb():
    """不拆核心候选中 SF(9) 优先于普通 Bomb(4)：exclude SF/8 → SF/7 而非 8888。"""
    eng = _make_engine()
    alt = eng._find_alternative_core_intact_bomb(
        ACTION_LIST, 3, eng._card_mask, eng._group_type_map,
        eng._group_members, None, "2",
    )
    assert alt == 2
    assert ACTION_LIST[alt] == SF_7


def test_follow_requires_beats_greater():
    """follow 模式：候选压不过 greater（敌方 SF/8）→ 无替代返回 -1。"""
    eng = _make_engine()
    greater = SF_8  # 完整核心 SF/7 与 Bomb 8888 均压不过 SF/8
    alt = eng._find_alternative_core_intact_bomb(
        ACTION_LIST, 3, eng._card_mask, eng._group_type_map,
        eng._group_members, greater, "2",
    )
    assert alt == -1, f"SF/7 压不过 SF/8，应 -1；实际 {alt}"


def test_all_candidates_break_core_returns_minus1():
    """全部候选都拆核心（仅 SF/6 与 SF/8，均 broken）→ -1（维持回退 PASS）。"""
    eng = _make_engine()
    action_list = [SF_6, SF_8, PASS]
    alt = eng._find_alternative_core_intact_bomb(
        action_list, 1, eng._card_mask, eng._group_type_map,
        eng._group_members, ["Pair", "9", ["H9", "C9"]], "2",
    )
    assert alt == -1


def test_exclude_idx_skipped():
    """exclude_idx 自身被跳过：唯一不拆核心候选即 exclude_idx → 无替代 -1。"""
    eng = _make_engine()
    action_list = [PASS, SF_7, PASS]
    alt = eng._find_alternative_core_intact_bomb(
        action_list, 1, eng._card_mask, eng._group_type_map,
        eng._group_members, ["Pair", "9", ["H9", "C9"]], "2",
    )
    assert alt == -1


def test_exclude_bomb_still_falls_back_to_sf():
    """exclude 完整核心 SF/7 → 剩余不拆核心 Bomb 8888 仍可作替代。"""
    eng = _make_engine()
    alt = eng._find_alternative_core_intact_bomb(
        ACTION_LIST, 2, eng._card_mask, eng._group_type_map,
        eng._group_members, ["Pair", "9", ["H9", "C9"]], "2",
    )
    assert alt == 0
    assert ACTION_LIST[alt] == BOMB_8888
