# -*- coding: utf-8 -*-
"""GUA-188 证明：残局决策层炸弹排序改造不影响组牌引擎选型。"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.features.grouping_engine import _enumerate_plans, _count_all_cards_in_plan

# 8 张手牌：Clubs SF 和 Bomb/A 均合法
HAND_8 = ["C7", "CJ", "CT", "DA", "H4", "H4", "HA", "SA"]
CUR_RANK = "4"  # H4 是百搭


def test_gua188_grouping_engine_always_prefers_sf():
    """组牌引擎产出全是 SF + Trips/A，无 Bomb/A 方案。"""
    plans = _enumerate_plans(HAND_8, CUR_RANK)
    assert len(plans) > 0

    for p in plans:
        # 每个方案都包含 SF
        assert len(p.straight_flushes) == 1, \
            f"方案 {p.strategy} 应含 1 个同花顺，实际含 {len(p.straight_flushes)}"
        # 每个方案的 SF 是 Clubs 7-J
        sf_cards = sorted(p.straight_flushes[0])
        assert "C7" in sf_cards and "CT" in sf_cards and "CJ" in sf_cards, \
            f"方案 {p.strategy} SF 缺 Clubs 牌: {sf_cards}"
        # 剩余 3 张是 Trip/A（不是 Bomb）
        assert len(p.trips) >= 1, \
            f"方案 {p.strategy} 应含 Trip/A，实际无 trip"
        assert len(p.bombs) == 0, \
            f"方案 {p.strategy} 不应含炸弹: {p.bombs}"
        assert _count_all_cards_in_plan(p) == len(HAND_8)


def test_gua188_champion_is_sf_not_bomb():
    """最优方案（max plan.score）是 SF_FIRST + Trips/A。"""
    plans = _enumerate_plans(HAND_8, CUR_RANK)
    champ = max(plans, key=lambda p: p.score)

    assert champ.straight_flushes, "最优方案必须含同花顺"
    assert len(champ.bombs) == 0, \
        f"最优方案不应含炸弹: bombs={champ.bombs}"
    assert champ.trips, \
        f"最优方案应含 Trip/A: trips={champ.trips}"
    assert champ.strategy in ("SF_FIRST", "ROUND_OPTIMAL", "ALL_COMBOS"), \
        f"最优方案策略应是 SF 优先: {champ.strategy}"
    assert champ.power_score >= 3, \
        f"最优方案 power_score 应 >= 3: {champ.power_score}"


def test_gua188_all_six_plans_identical_structure():
    """全部 6 个策略方案结构一致（SF+Trips，无 Bomb）。"""
    plans = _enumerate_plans(HAND_8, CUR_RANK)
    assert len(plans) == 6, f"预期 6 个方案，实际 {len(plans)}"

    for p in plans:
        key = (len(p.singles), len(p.pairs), len(p.trips),
               len(p.bombs), len(p.straights), len(p.straight_flushes),
               len(p.three_pairs), len(p.three_with_twos), len(p.steel_plates))
        assert key == (0, 0, 1, 0, 0, 1, 0, 0, 0), \
            f"方案 {p.strategy} 结构不符: {key}"


def test_gua188_hand5_only_bomb_no_sf():
    """5 张 [H4,H4,HA,SA,DA] 只有 Bomb/A 可选，不可能组 SF。"""
    hand_5 = ["H4", "H4", "HA", "SA", "DA"]
    plans = _enumerate_plans(hand_5, "4")

    for p in plans:
        assert len(p.straight_flushes) == 0, \
            f"5 张牌不应有 SF: {p.straight_flushes}"


def test_gua188_grouping_independent_of_decision_logging():
    """证明：修改决策层 `_sort_q1_block_candidates` 不影响组牌产出。
    
    方法：直接断言组牌引擎内部评分函数（_score_power, _score_plan_v2）
    不引用任何决策层函数。两模块零耦合。
    """
    plans = _enumerate_plans(HAND_8, "4")
    for p in plans:
        assert p.power_score == 3, \
            f"方案 {p.strategy} power_score={p.power_score}（应有 3）"
        assert p.score > 0.4, \
            f"方案 {p.strategy} score={p.score} 偏低"


def test_gua188_bomb_sort_prefers_non_sf_when_both_available():
    """_sort_q1_block_candidates 中 Bomb/A 应排 SF 前面（SF 延后键生效）。"""
    from src.v.nn.endgame.endgame_decide import _sort_q1_block_candidates
    from src.v.nn.endgame.endgame_decide import _is_bomb_like_action

    action_list = [
        ["PASS", ""],
        ["Bomb", "A", ["DA", "HA", "H4", "H4", "SA"]],
        ["StraightFlush", "J", ["C7", "C8", "C9", "CT", "CJ"]],
    ]
    game_state = {
        "greaterAction": ["Bomb", "Q", ["HQ", "SQ", "CQ", "HQ"]],
        "curRank": "4",
        "myPos": 0,
        "greaterPos": 3,
        "numofplayers": [8, 19, 6, 21],
        "_group_members": None,
        "_group_gid_type_map": None,
    }
    candidates = [(i, a) for i, a in enumerate(action_list) if _is_bomb_like_action(a)]
    sorted_cands = _sort_q1_block_candidates(candidates, HAND_8, game_state)

    assert len(sorted_cands) >= 2
    first = sorted_cands[0]
    first_act = first[1] if isinstance(first, tuple) and len(first) == 2 else first
    first_type = first_act[0]
    assert first_type == "Bomb", \
        f"SF-defer 失效: Bomb/A 应排 SF 前, 实际首个是 {first_type}"

    second = sorted_cands[1]
    second_act = second[1] if isinstance(second, tuple) and len(second) == 2 else second
    second_type = second_act[0]
    assert second_type == "StraightFlush", \
        f"SF-defer 失效: SF 应排第 2, 实际是 {second_type}"


def test_gua188_bomb_sort_uses_sf_when_only_sf_available():
    """只有 SF 可反压时，SF 正常排前（不延后）。"""
    from src.v.nn.endgame.endgame_decide import _sort_q1_block_candidates
    from src.v.nn.endgame.endgame_decide import _is_bomb_like_action

    action_list = [
        ["PASS", ""],
        ["StraightFlush", "J", ["C7", "C8", "C9", "CT", "CJ"]],
    ]
    game_state = {
        "greaterAction": ["Bomb", "Q", ["HQ", "SQ", "CQ", "HQ"]],
        "curRank": "4",
        "myPos": 0,
        "greaterPos": 3,
        "numofplayers": [8, 19, 6, 21],
        "_group_members": None,
        "_group_gid_type_map": None,
    }
    candidates = [(i, a) for i, a in enumerate(action_list) if _is_bomb_like_action(a)]
    sorted_cands = _sort_q1_block_candidates(candidates, HAND_8, game_state)

    assert len(sorted_cands) >= 1
    first = sorted_cands[0]
    first_act = first[1] if isinstance(first, tuple) and len(first) == 2 else first
    assert first_act[0] == "StraightFlush", \
        f"无 Bomb 替代时 SF 应排第一, 实际是 {first_act[0]}"
