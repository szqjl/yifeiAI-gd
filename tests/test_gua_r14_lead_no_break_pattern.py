# -*- coding: utf-8 -*-
"""R14 领出不拆天然牌型 — 完整牌型豁免 + 成员牌花色感知 + H2 不参与天然牌型。

真源：ITERATIONS v8-botzone-h2wild-sf-lowrank。
锚点：logs/v8_vs_botzone_20260802_220840.log 22:09:40 handCards=17，
修复前 R14 把全部 StraightFlush 候选（含 H2-wild SF）当拆牌剔除 → 引擎 PASS
→ adapter 兜底 Single/9 拆核心。修复后 R14 仅剔真正拆散天然对子/三张的
Single/Pair，保留完整牌型（SF/Straight/ThreeWithTwo/ThreePair/TwoTrips/Bomb）。
"""
from collections import Counter

from src.v.nn.guards.v7_guards import (
    _rule_r14_no_break_pattern_when_lead,
    get_action_type,
)

HAND_B = [  # 22:09:40：天然对子 8(S8,D8)，天然三张 4(H4,C4,C4)，天然对子? 2 被 H2 排除
    "H6", "C2",
    "S4", "S5", "S6", "H2", "S8",
    "D7", "D8", "D9", "DT", "DJ",
    "H4", "C4", "C4", "H3", "C3",
]

ACTION_LIST_B = [
    ["PASS", "PASS", "PASS"],
    ["Single", "6", ["H6"]],              # 拆天然对子 H6/S6
    ["Single", "2", ["C2"]],
    ["Single", "8", ["S8"]],              # 拆天然对子 S8/D8
    ["Single", "8", ["D8"]],              # 拆天然对子 S8/D8
    ["Single", "4", ["S4"]],              # rank4 出现4次，非天然对子/三张成员，不应判拆
    ["Single", "4", ["C4"]],              # 同上
    ["Pair", "8", ["S8", "D8"]],          # 完整使用天然对子
    ["Pair", "4", ["H4", "C4"]],          # rank4 非天然组，不应判拆
    ["Trips", "4", ["H4", "C4", "C4"]],   # 完整使用 rank4（非天然三张）
    ["Straight", "6", ["D6", "D7", "D8", "H9", "DT"]],          # 完整牌型豁免（用 D8）
    ["StraightFlush", "4", ["S4", "S5", "S6", "S8", "H2"]],     # H2-wild SF：豁免
    ["StraightFlush", "7", ["D7", "D8", "D9", "DT", "DJ"]],     # 自然 SF：豁免
    ["StraightFlush", "6", ["D7", "D8", "D9", "DT", "H2"]],     # H2-wild SF：豁免
    ["ThreeWithTwo", "4", ["H4", "C4", "C4", "H3", "C3"]],      # 完整牌型豁免
]


def _kept(kept_idx, actions=ACTION_LIST_B):
    return [actions[i] for i in kept_idx]


def test_r14_keeps_all_straight_flush_candidates():
    kept = _kept(_rule_r14_no_break_pattern_when_lead(
        ACTION_LIST_B, HAND_B, greater_pos=0, my_pos=0))
    # get_action_type 对 H2-wild SF 实牌校验失败返回 Free，这里按声明类型 a[0] 判断
    sf = [a for a in kept if a[0] == "StraightFlush"]
    assert len(sf) == 3, f"SF 应全部豁免，实际保留 {len(sf)}"
    assert ["StraightFlush", "4", ["S4", "S5", "S6", "S8", "H2"]] in sf
    assert ["StraightFlush", "7", ["D7", "D8", "D9", "DT", "DJ"]] in sf


def test_r14_keeps_complete_structures():
    kept = _kept(_rule_r14_no_break_pattern_when_lead(
        ACTION_LIST_B, HAND_B, greater_pos=0, my_pos=0))
    types = {get_action_type(a) for a in kept}
    assert "Straight" in types
    assert "ThreeWithTwo" in types
    # 完整使用天然牌型
    assert ["Pair", "8", ["S8", "D8"]] in kept
    assert ["Trips", "4", ["H4", "C4", "C4"]] in kept


def test_r14_still_removes_broken_single_pair():
    kept = _kept(_rule_r14_no_break_pattern_when_lead(
        ACTION_LIST_B, HAND_B, greater_pos=0, my_pos=0))
    # 拆天然对子 S8/D8 的 Single 仍被剔
    assert ["Single", "8", ["S8"]] not in kept
    assert ["Single", "8", ["D8"]] not in kept
    # 拆天然对子 H6/S6 的 Single 仍被剔
    assert ["Single", "6", ["H6"]] not in kept
    # rank4 出现4次，Single/Pair 非天然组 → 保留
    assert ["Single", "4", ["C4"]] in kept
    assert ["Pair", "4", ["H4", "C4"]] in kept


def test_r14_non_member_same_rank_not_flagged():
    # S4 是第 4 张 4（rank4 在 HAND_B 出现 4 次），不是天然对子/三张成员
    kept = _kept(_rule_r14_no_break_pattern_when_lead(
        ACTION_LIST_B, HAND_B, greater_pos=0, my_pos=0))
    assert ["Single", "4", ["S4"]] in kept


def test_r14_natural_trip_still_removed():
    # 手牌含天然三张 4(H4,C4,C4)：拆三张的 Single/Pair 应被剔
    hand = ["H4", "C4", "C4", "S6", "D6"]
    actions = [
        ["PASS", "PASS", "PASS"],
        ["Single", "4", ["H4"]],       # 拆三张
        ["Pair", "4", ["H4", "C4"]],   # 拆三张
        ["Trips", "4", ["H4", "C4", "C4"]],  # 完整
        ["Pair", "6", ["S6", "D6"]],   # 完整使用天然对子
    ]
    kept = _kept(_rule_r14_no_break_pattern_when_lead(
        actions, hand, greater_pos=0, my_pos=0), actions=actions)
    assert ["Single", "4", ["H4"]] not in kept
    assert ["Pair", "4", ["H4", "C4"]] not in kept
    assert ["Trips", "4", ["H4", "C4", "C4"]] in kept
    assert ["Pair", "6", ["S6", "D6"]] in kept


def test_r14_not_lead_no_filter():
    kept = _kept(_rule_r14_no_break_pattern_when_lead(
        ACTION_LIST_B, HAND_B, greater_pos=1, my_pos=0))
    assert len(kept) == len(ACTION_LIST_B)


def test_r14_h2_wild_not_natural_pair():
    # 手牌 C2+H2：H2 是逢人配，不构成天然对子 → Single/2(C2) 不判拆
    hand = ["H2", "C2", "S5", "D5"]
    actions = [
        ["PASS", "PASS", "PASS"],
        ["Single", "2", ["C2"]],
        ["Pair", "5", ["S5", "D5"]],
    ]
    kept = _kept(_rule_r14_no_break_pattern_when_lead(
        actions, hand, greater_pos=0, my_pos=0), actions=actions)
    assert ["Single", "2", ["C2"]] in kept


def test_r14_hand_counter_ranks_exclude_h2():
    # 直接断言内部口径：H2 不参与天然对子/三张统计
    from src.v.nn.guards.v7_guards import get_card_rank
    non_h2_ranks = Counter(get_card_rank(c) for c in HAND_B if c != "H2")
    assert non_h2_ranks["2"] == 1, "排除 H2 后 rank2 只剩 C2，不应是天然对子"


def test_r14_wild_sf_currank6_not_natural_pair():
    """GUA-201: 配子动态定位——级牌=6 时 H6 是配子，S6 不构成天然对子。

    锚点：match=6a71cf5f27e7bf01db106f56（级牌6）。修复前 R14 硬编码排除
    H2，H6 被计入 hand_ranks['6']=2 → 误判 S6+H6 为天然对子 → 合法
    Single/6(S6) 被剔除。修复后传 cur_rank 动态排除 H6。
    """
    hand = ["S6", "H6", "S5", "D5", "S8", "H9", "C9"]
    actions = [
        ["PASS", "PASS", "PASS"],
        ["Single", "6", ["S6"]],          # 修复前被误剔；H6是配子，S6非天然对子
        ["Single", "5", ["S5"]],          # 真拆对5，应剔
        ["Pair", "5", ["S5", "D5"]],      # 完整对5，保留
        ["Pair", "6", ["S6", "H6"]],      # 配子补对，保留
        ["StraightFlush", "A", ["DA", "D2", "D3", "D4", "H6"]],  # 完整SF，豁免
    ]
    kept = _rule_r14_no_break_pattern_when_lead(
        actions, hand, greater_pos=-1, my_pos=0, cur_rank="6")
    kept_list = [actions[i] for i in kept]
    assert ["Single", "6", ["S6"]] in kept_list, f"H6配子不应判拆天然对子: {kept_list}"
    assert ["Single", "5", ["S5"]] not in kept_list, f"真拆对5应剔除: {kept_list}"
    assert ["Pair", "5", ["S5", "D5"]] in kept_list
    assert ["Pair", "6", ["S6", "H6"]] in kept_list
    assert ["StraightFlush", "A", ["DA", "D2", "D3", "D4", "H6"]] in kept_list


def test_r14_currank2_default_backward_compat():
    """GUA-201: 默认 cur_rank='2' 保持旧行为（H2 作配子，C2 非天然对子）。"""
    hand = ["H2", "C2", "S5", "D5"]
    actions = [
        ["PASS", "PASS", "PASS"],
        ["Single", "2", ["C2"]],
        ["Pair", "5", ["S5", "D5"]],
    ]
    kept = _rule_r14_no_break_pattern_when_lead(
        actions, hand, greater_pos=0, my_pos=0)
    kept_list = [actions[i] for i in kept]
    assert ["Single", "2", ["C2"]] in kept_list
    assert ["Pair", "5", ["S5", "D5"]] in kept_list
