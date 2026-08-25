# -*- coding: utf-8 -*-
"""GUA-279：Bomb allocation 拆另一核 SF → 禁选；R16 不豁免拆他核补星。

锚点 match=6a8d4980：G0 四星 J + G1 梅花10-A SF，五星炸抽 CJ →
GUA-154 broken=['StraightFlush']；R16 队友剩1 曾全放行导致残局仍出五星。
"""

from __future__ import annotations

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

PASS = ["PASS", "PASS", "PASS"]
BOMB_4J = ["Bomb", "J", ["SJ", "DJ", "HJ", "HJ"]]
BOMB_5J_PAD = ["Bomb", "J", ["SJ", "CJ", "DJ", "HJ", "HJ"]]  # 抽 SF 的 CJ
SF_TA = ["StraightFlush", "T", ["H2", "CT", "CJ", "CQ", "CK"]]


def _engine_match_groups():
    """复现局组牌：四星 J 炸 + 梅花 T–A（H2 配子）同花顺。"""
    eng = UltimateWinRateEngineV7(player_id=2)
    eng._current_role = "超强主攻"
    eng.group_filter_bypass_count = 0
    eng.group_filtered_count = 0
    eng._group_members = {
        0: ["SJ", "DJ", "HJ", "HJ"],
        1: ["H2", "CT", "CJ", "CQ", "CK"],
        -1: ["S8", "HT", "D3", "S4", "D5", "H6", "D7"],
    }
    eng._group_type_map = {
        0: "Bomb",
        1: "StraightFlush",
        -1: "scatter",
    }
    # card_mask: (gid, is_core, gsize) — 简化；allocation 以 group_members 为准
    eng._card_mask = {}
    for gid, cards in eng._group_members.items():
        gtype = eng._group_type_map[gid]
        is_core = 1.0 if gtype in ("Bomb", "StraightFlush") else 0.0
        for c in cards:
            eng._card_mask[c] = (gid, is_core, len(cards))
    return eng


def _gs_r16(*, teammate_rem=1, xiajia_rem=14, hand_n=16):
    """myPos=2 → 队友=0，下家=3。"""
    hand = (
        ["SJ", "DJ", "HJ", "HJ", "H2", "CT", "CJ", "CQ", "CK"]
        + ["S8", "HT", "D3", "S4", "D5", "H6", "D7"]
    )[:hand_n]
    nums = [teammate_rem, 10, hand_n, xiajia_rem]  # pos0 teammate, pos2 me, pos3 lower
    return {
        "myPos": 2,
        "curPos": 2,
        "greaterPos": 3,
        "greaterAction": ["Single", "R", ["HR"]],
        "handCards": hand,
        "curRank": "2",
        "numofplayers": nums,
        "publicInfo": [{"rest": n} for n in nums],
    }


def test_detector_five_star_pads_from_sf():
    eng = _engine_match_groups()
    assert eng._is_bomb_padding_break_other_sf(BOMB_5J_PAD) is True
    assert eng._get_broken_core_type(
        BOMB_5J_PAD, eng._card_mask, eng._group_type_map, eng._group_members,
    ) == "StraightFlush"


def test_detector_four_star_bomb_only_ok():
    eng = _engine_match_groups()
    assert eng._is_bomb_padding_break_other_sf(BOMB_4J) is False
    assert eng._get_broken_core_type(
        BOMB_4J, eng._card_mask, eng._group_type_map, eng._group_members,
    ) is None


def test_detector_full_sf_not_pad():
    eng = _engine_match_groups()
    assert eng._is_bomb_padding_break_other_sf(SF_TA) is False
    assert eng._get_broken_core_type(
        SF_TA, eng._card_mask, eng._group_type_map, eng._group_members,
    ) is None


def test_r16_still_feeds_but_blocks_pad_bomb():
    """R16 队友剩1：送单类仍放行；五星补星 Bomb 被滤；SF/四星/PASS 保留。"""
    eng = _engine_match_groups()
    gs = _gs_r16(teammate_rem=1, xiajia_rem=14)
    actions = [PASS, BOMB_5J_PAD, BOMB_4J, SF_TA, ["Single", "8", ["S8"]]]
    filtered, fmap = eng._group_consistency_filter(actions, gs)
    assert eng.group_filter_bypass_count == 1
    assert BOMB_5J_PAD not in filtered
    assert fmap[1] == -1
    assert PASS in filtered
    assert BOMB_4J in filtered
    assert SF_TA in filtered
    assert ["Single", "8", ["S8"]] in filtered


def test_main_attack_filter_blocks_pad_bomb_without_r16():
    """非 R16：主攻路径同样禁五星补星。"""
    eng = _engine_match_groups()
    gs = _gs_r16(teammate_rem=8, xiajia_rem=14)  # 非 R16
    actions = [PASS, BOMB_5J_PAD, SF_TA]
    filtered, fmap = eng._group_consistency_filter(actions, gs)
    assert BOMB_5J_PAD not in filtered
    assert fmap[1] == -1
    assert SF_TA in filtered
    assert PASS in filtered
