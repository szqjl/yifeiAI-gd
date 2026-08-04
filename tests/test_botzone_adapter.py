# -*- coding: utf-8 -*-
"""
BotzoneAdapter 单元测试 — 牌编码双射 + ActionList 生成。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from src.communication.botzone_adapter import (
    bz_to_v8_card,
    v8_to_bz_int,
    bz_to_v8_cards,
    v8_to_bz_cards,
    CardTracker,
    ActionListGenerator,
    _card_rank,
    _rank_to_order,
)


# ── 1. 牌编码双射 ─────────────────────────────

def test_bz_card_a():
    """Botzone 0-3 对应 A (4 种花色)."""
    assert bz_to_v8_card(0) == "HA"  # 0 = heart A
    assert bz_to_v8_card(1) == "DA"  # 1 = diamond A
    assert bz_to_v8_card(2) == "SA"  # 2 = spade A
    assert bz_to_v8_card(3) == "CA"  # 3 = club A


def test_bz_card_2():
    """Botzone 4-7 对应 2."""
    assert bz_to_v8_card(4) == "H2"
    assert bz_to_v8_card(5) == "D2"
    assert bz_to_v8_card(7) == "C2"


def test_bz_card_t():
    """Botzone 36-39 对应 T (10)."""
    assert bz_to_v8_card(36) == "HT"
    assert bz_to_v8_card(39) == "CT"


def test_bz_card_k():
    """Botzone 48-51 对应 K."""
    assert bz_to_v8_card(48) == "HK"
    assert bz_to_v8_card(51) == "CK"


def test_bz_card_jokers():
    """Botzone 52/106 小王, 53/107 大王."""
    assert bz_to_v8_card(52) == "SB"
    assert bz_to_v8_card(53) == "HR"
    assert bz_to_v8_card(106) == "SB"
    assert bz_to_v8_card(107) == "HR"


def test_v8_to_bz_roundtrip():
    """Roundtrip: V8 -> Botzone -> V8."""
    v8_cards = ["S2", "HA", "DT", "CQ", "SB", "HR", "H7"]
    for v8 in v8_cards:
        bz = v8_to_bz_int(v8)
        v8_back = bz_to_v8_card(bz)
        assert v8 == v8_back, f"Roundtrip fail: {v8} -> {bz} -> {v8_back}"


def test_bz_to_v8_roundtrip():
    """Roundtrip: Botzone -> V8 -> Botzone (first deck)."""
    for i in range(54):
        v8 = bz_to_v8_card(i)
        bz = v8_to_bz_int(v8, deck_offset=0)
        assert i == bz, f"Roundtrip fail: {i} -> {v8} -> {bz}"


def test_bz_second_deck():
    """Second deck (54-107) maps to same V8 strings as first deck."""
    for i in range(54, 108):
        v8 = bz_to_v8_card(i)
        v8_first = bz_to_v8_card(i - 54)
        assert v8 == v8_first, f"{i}: {v8} != {v8_first}"


def test_v8_to_bz_second_deck():
    """v8_to_bz_int with deck_offset=1 produces 54-107."""
    assert v8_to_bz_int("S2", deck_offset=1) == 54 + 4 + 2  # 54 + 4*1 + 2
    assert v8_to_bz_int("HA", deck_offset=1) == 54 + 0  # 54 + 4*0 + 0


def test_bulk_conversion():
    """Batch conversion."""
    bz_hand = [0, 1, 2, 3, 52, 53, 36, 37, 38, 39]
    v8 = bz_to_v8_cards(bz_hand)
    assert v8 == ["HA", "DA", "SA", "CA", "SB", "HR", "HT", "DT", "ST", "CT"]
    bz_back = v8_to_bz_cards(v8)
    assert bz_back == bz_hand


# ── 2. CardTracker ─────────────────────────────

def test_card_tracker_basic():
    ct = CardTracker.from_bz_hand([0, 1, 54, 55])  # HA x2
    assert len(ct.remaining["HA"]) == 2
    first = ct.remove("HA")
    assert first in (0, 54)
    second = ct.remove("HA")
    assert second in (0, 54)
    assert first != second
    assert ct.remove("HA") is None  # exhausted


def test_card_tracker_remove_multi():
    ct = CardTracker.from_bz_hand([0, 1, 2, 3, 52, 53])
    result = ct.remove_multi(["HA", "DA", "SB"])
    assert len(result) == 3
    assert 0 in result  # HA
    assert 1 in result  # DA
    assert 52 in result  # SB


def test_card_tracker_deck_aware():
    """Tracker correctly handles two-deck mapping."""
    bz_hand = [0, 54]  # Two heart Aces
    ct = CardTracker.from_bz_hand(bz_hand)
    assert len(ct.remaining["HA"]) == 2
    r1 = ct.remove("HA")
    r2 = ct.remove("HA")
    assert {r1, r2} == {0, 54}


# ── 3. ActionListGenerator ─────────────────────

def _check_action(action, expected_type):
    assert isinstance(action, list) and len(action) >= 3
    assert action[0] == expected_type, f"Expected {expected_type}, got {action[0]}"
    assert isinstance(action[2], list)


def test_lead_singles():
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H5", "DK", "C2"]
    actions = gen.generate_lead_actions(hand)
    singles = [a for a in actions if a[0] == "Single"]
    assert len(singles) == 4
    for s in singles:
        assert len(s[2]) == 1


def test_lead_pairs():
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "D5", "C5", "S5"]
    actions = gen.generate_lead_actions(hand)
    pairs = [a for a in actions if a[0] == "Pair"]
    assert len(pairs) >= 1
    for p in pairs:
        assert len(p[2]) == 2


def test_lead_trips():
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "D3", "C5", "S5"]
    actions = gen.generate_lead_actions(hand)
    trips = [a for a in actions if a[0] == "Trips"]
    assert len(trips) >= 1
    for t in trips:
        assert len(t[2]) == 3


def test_lead_trips_with_wild_pairs_pair_into_trips():
    """GUA-195：H2 配子补对成三张。

    H2+ST+HT 领出应生成 Trips/10（一手清）候选，而非只有 Single×3+Pair×1，
    否则残局先出单 H2 再出对 10 分两次打（实测 match 6a717aab27e7bf01db10369f
    13:38:30）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["H2", "ST", "HT"]
    actions = gen.generate_lead_actions(hand)
    trips = [a for a in actions if a[0] == "Trips"]
    assert any(sorted(t[2]) == sorted(["H2", "ST", "HT"]) for t in trips), trips
    for t in trips:
        assert len(t[2]) == 3
    # 一手清检测应命中 Trips/10
    from src.v.nn.endgame.endgame_decide import find_finish_now_candidate
    hit = find_finish_now_candidate(
        {"handCards": hand, "curRank": "2"}, actions,
    )
    assert hit is not None
    assert hit[1][0] == "Trips"
    assert sorted(hit[1][2]) == sorted(hand)


def test_lead_bomb():
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "D3", "C3", "S5"]
    actions = gen.generate_lead_actions(hand)
    bombs = [a for a in actions if a[0] == "Bomb"]
    assert len(bombs) >= 1
    for b in bombs:
        assert len(b[2]) >= 4


def test_lead_three_with_two():
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "D3", "C5", "S5"]
    actions = gen.generate_lead_actions(hand)
    twt = [a for a in actions if a[0] == "ThreeWithTwo"]
    assert len(twt) >= 1
    for t in twt:
        assert len(t[2]) == 5


def test_lead_straight():
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H4", "D5", "C6", "S7"]  # 3-4-5-6-7 straight
    actions = gen.generate_lead_actions(hand)
    straights = [a for a in actions if a[0] == "Straight"]
    assert len(straights) >= 1
    for s in straights:
        assert len(s[2]) >= 5


def test_lead_has_no_pass():
    """领出轮 actionList 应不含 PASS（对齐 OpenGuanDan 服务器领出轮实测无 PASS）。

    修复前 lead 首项恒为 ["PASS","PASS","PASS"]，领出/接风轮引擎选 PASS 被
    兜底成弱单张（logs/v8_vs_botzone_20260802_220840.log 22:09:03 → Single/J）。
    """
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H5"]
    actions = gen.generate_lead_actions(hand)
    pass_actions = [a for a in actions if a[0] == "PASS"]
    assert len(pass_actions) == 0, f"领出轮不应含 PASS: {actions}"
    assert len(actions) >= 2, f"应含可出候选: {actions}"


def test_follow_beats_greater():
    """Following actions should beat greater action."""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "D3", "S5", "H5", "D5", "S7", "H7", "D7"]
    greater = ["Pair", "5", ["S5", "H5"]]
    actions = gen.generate_follow_actions(hand, greater)
    for a in actions:
        if a[0] == "PASS":
            continue
        if a[0] == "Bomb":
            continue  # bombs always beat
        assert a[0] == "Pair", f"Expected Pair, got {a[0]}"
        assert _rank_to_order(a[1], "2") > _rank_to_order("5", "2"), \
            f"Rank {a[1]} not > 5"


def test_bomb_in_follow():
    """Bombs should always appear in follow actions."""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "D3", "C3", "S5"]  # has a bomb
    greater = ["Single", "K", ["SK"]]
    actions = gen.generate_follow_actions(hand, greater)
    bombs = [a for a in actions if a[0] == "Bomb"]
    assert len(bombs) >= 1


def test_straight_flush_bomb_in_follow():
    """同花顺是炸弹：跟牌轮对手出 Single/Pair/Trips 等非炸牌型时，
    actionList 必须含同花顺整手候选，否则手牌仅剩 SF 时该压不压 PASS。
    锚点：match=6a714a8027e7bf01db1017a3 —— C5-C9 SF 对 Single/7、Pair/8
    全程 PASS（修复前生成器只补同 rank≥4 四头炸，漏同花顺炸）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["C5", "C6", "C7", "C8", "C9"]  # 一手同花顺炸弹

    for greater in (
        ["Single", "7", ["S7"]],
        ["Pair", "8", ["S8", "H8"]],
        ["Trips", "5", ["S5", "H5", "D5"]],
        ["Straight", "3", ["S3", "H4", "D5", "C6", "S7"]],
        ["ThreeWithTwo", "K", ["SK", "HK", "DK", "S4", "H4"]],
    ):
        actions = gen.generate_follow_actions(hand, greater)
        sfs = [a for a in actions if a[0] == "StraightFlush"]
        assert sfs, f"greater={greater} 应含同花顺候选: {actions}"
        assert ["StraightFlush", "5",
                ["C5", "C6", "C7", "C8", "C9"]] in sfs, sfs


def test_straight_flush_bomb_follow_pairs_and_trips():
    """同花顺炸候选与拆牌单张共存：对 Single/7 既有拆 C8/C9 单张，
    也有 SF 整手（引擎据此可走 Q0.5 一手清，而非 PASS）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["C5", "C6", "C7", "C8", "C9"]
    greater = ["Single", "7", ["S7"]]
    actions = gen.generate_follow_actions(hand, greater)
    types = {a[0] for a in actions}
    assert "StraightFlush" in types, actions
    assert "Single" in types, actions
    assert all(a[0] != "Bomb" for a in actions), (
        "手牌无 4 张同 rank，不应出现四头炸: "
        f"{[a for a in actions if a[0] == 'Bomb']}")


def test_straight_flush_bomb_follow_respects_bomb_count():
    """同花顺压 4/5 张炸，6+ 炸压同花顺（裁判 G1）：
    对 6 张炸 greater 不补 SF（SF 压不过 6+ 炸）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["C5", "C6", "C7", "C8", "C9"]
    # 6 张炸
    greater_big = ["Bomb", "A",
                   ["SA", "SA", "DA", "DA", "HA", "HA"]]
    actions = gen.generate_follow_actions(hand, greater_big)
    sfs = [a for a in actions if a[0] == "StraightFlush"]
    assert not sfs, f"6+ 炸压同花顺，不应补 SF: {actions}"
    # 4 张炸 → 同花顺可压
    greater_small = ["Bomb", "A", ["SA", "SA", "DA", "DA"]]
    actions2 = gen.generate_follow_actions(hand, greater_small)
    sfs2 = [a for a in actions2 if a[0] == "StraightFlush"]
    assert sfs2, f"4 张炸应可被同花顺压: {actions2}"


def test_follow_single_pair_generates_all_combos():
    """follow 的 Single/Pair/Trips 应生成该 rank 全部 n 组合，
    让引擎可挑不拆核心组的组合（避免该压不压 PASS）。
    锚点：match=6a6ecd15 play 全程 PASS——HQ 在 SF core，
    旧逻辑只生成 cards[:n] 恒为 HQ，GUA-176 无替代。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["HQ", "DQ", "SQ", "S3"]
    greater = ["Single", "5", ["S5"]]
    singles = [a for a in gen.generate_follow_actions(hand, greater)
               if a[0] == "Single"]
    q_singles = sorted(a[2][0] for a in singles if a[1] == "Q")
    assert q_singles == ["DQ", "HQ", "SQ"], f"应有全部 Q 单张: {q_singles}"

    greater_pair = ["Pair", "8", ["S8", "H8"]]
    pairs = [a for a in gen.generate_follow_actions(hand, greater_pair)
             if a[0] == "Pair"]
    q_pairs = sorted(tuple(sorted(a[2])) for a in pairs if a[1] == "Q")
    assert ("DQ", "SQ") in q_pairs, f"应包含不拆核的 DQ+SQ: {q_pairs}"


def test_follow_gua176_prefers_non_core_combos():
    """GUA-176 替代搜索应跳过拆核组合、选非核组合（DQ/SQ）。"""
    from src.communication.botzone_adapter import ActionListGenerator
    from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
    from src.v.nn.features.grouping_engine import enumerate_groupings

    hand = ["SA", "CA", "SA", "H2", "H8", "H9", "HT", "HJ", "HQ",
            "D3", "H4", "D5", "C6", "C7", "D7", "D8", "H9", "CT", "CJ",
            "C2", "S3", "S4", "H5", "H6", "DQ", "SQ"]
    plan, _ = enumerate_groupings(hand, "2")
    mask, type_map, members = plan.to_card_mask()
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = mask
    engine._group_type_map = type_map
    engine._group_members = members
    gen = ActionListGenerator(cur_rank="2")

    ga = ["Pair", "8", ["S8", "H8"]]
    al = gen.generate_follow_actions(hand, ga)
    idx = engine._find_alternative_non_core_breaking_action(
        al, -1, mask, type_map, members, greater_action=ga)
    assert idx >= 0
    assert al[idx][0] == "Pair" and sorted(al[idx][2]) == ["DQ", "SQ"], al[idx]

    ga2 = ["Single", "5", ["S5"]]
    al2 = gen.generate_follow_actions(hand, ga2)
    idx2 = engine._find_alternative_non_core_breaking_action(
        al2, -1, mask, type_map, members, greater_action=ga2)
    assert idx2 >= 0
    assert al2[idx2][0] == "Single" and al2[idx2][2] == ["DQ"], al2[idx2]


# ── 4. _classify_action (via BotzoneAdapter) ──

def test_classify_single():
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    result = adapter._classify_action(["S3"])
    assert result == ["Single", "3", ["S3"]]


def test_classify_pair():
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    result = adapter._classify_action(["S5", "H5"])
    assert result[0] == "Pair"
    assert result[1] == "5"


def test_classify_bomb():
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    result = adapter._classify_action(["S5", "H5", "D5", "C5"])
    assert result[0] == "Bomb"
    assert result[1] == "5"


def test_classify_pass():
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    result = adapter._classify_action([])
    assert result == ["PASS", "PASS", "PASS"]


# ── 8. Botzone play history 双格式解析 ─────────
def test_parse_play_history_array_format():
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    history = [[[26], [26]], [], [], [[69], [69]]]
    parsed = adapter._parse_bz_play_history(history)
    assert parsed == [
        (0, [26], [26]),
        (1, [], []),
        (2, [], []),
        (3, [69], [69]),
    ]


def test_parse_play_history_dict_format():
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    history = [
        {"player": 2, "response": [[11, 8], [11, 8]]},
        {"player": 3, "response": []},
    ]
    parsed = adapter._parse_bz_play_history(history)
    assert parsed == [
        (2, [11, 8], [11, 8]),
        (3, [], []),
    ]


def test_parse_play_history_empty():
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    assert adapter._parse_bz_play_history([]) == []
    assert adapter._parse_bz_play_history(None) == []


def test_classify_three_with_two():
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    result = adapter._classify_action(["S5", "H5", "D5", "S3", "H3"])
    assert result[0] == "ThreeWithTwo"
    assert result[1] == "5"


def test_classify_straight():
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    result = adapter._classify_action(["S3", "H4", "D5", "C6", "S7"])
    assert result[0] == "Straight"


def test_classify_straight_flush():
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    result = adapter._classify_action(["S3", "S4", "S5", "S6", "S7"])
    assert result[0] == "StraightFlush"


def test_classify_straight_with_level_card_low():
    """级牌不提升：level=2 时 2-3-4-5-6 仍是合法顺子（裁判 cardscale 语义）。

    锚点：match=6a71ace3 对手打 2-6 顺子被误判 'Free' → 跟牌轮无 Straight
    候选 → 手有 5-9 顺子却 PASS。修复前 _is_consecutive 用 _rank_to_order
    （级牌 2 提升为 15）→ 2-6 不连续 → 'Free'。
    """
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    result = adapter._classify_action(["D2", "C3", "C4", "D5", "D6"])
    assert result == ["Straight", "2", ["D2", "C3", "C4", "D5", "D6"]], result
    # A2345 / TJQKA 窗口低牌与裁判 points 一致
    assert adapter._classify_action(["SA", "S2", "H3", "D4", "C5"]) == \
        ["Straight", "A", ["SA", "S2", "H3", "D4", "C5"]]
    assert adapter._classify_action(["ST", "HJ", "DQ", "CK", "SA"]) == \
        ["Straight", "T", ["ST", "HJ", "DQ", "CK", "SA"]]


def test_follow_straight_beats_level_low_straight():
    """跟牌轮 greater=2-6 顺子时，手牌 5-9 顺子必须进入候选（该压不压回归）。

    锚点：match=6a71ace3 第 24 回合——V8 手有 S5-S9，2 号对手打 2-6 顺子，
    队友/对手均过，V8 因 greater 被误判 'Free' 导致 actionList 只有 PASS+SF
    → 全程 PASS。修复后必须含 Straight/5。
    """
    from src.communication.botzone_adapter import ActionListGenerator
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S5", "S6", "C7", "C8", "S9"]
    greater = ["Straight", "2", ["D2", "C3", "C4", "D5", "D6"]]
    actions = gen.generate_follow_actions(hand, greater)
    straights = [a for a in actions if a[0] == "Straight"]
    assert ["Straight", "5", ["S5", "S6", "C7", "C8", "S9"]] in straights, actions


# ── 9. 全组合与官方牌型对齐 ─────────────────────

def _collect(al, t):
    return [a for a in al if a[0] == t]


def _make_adapter():
    from src.communication.botzone_adapter import BotzoneAdapter
    return BotzoneAdapter("test", "test_key")


def test_straight_only_five_cards():
    """官方：顺子只能五张。不能生成长顺（6+）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H4", "D5", "C6", "S7", "H8", "C9"]  # 3-4-5-6-7-8-9
    straights = _collect(gen.generate_lead_actions(hand), "Straight")
    assert len(straights) >= 1
    for s in straights:
        assert len(s[2]) == 5, f"顺子必须 5 张: {s[2]}"


def test_straight_a2345_and_tjqka():
    """官方：A 可作 1（A2345）或 14（TJQKA）；JQKA2 非法。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["SA", "S2", "H3", "D4", "C5",  # A2345
            "ST", "HJ", "DQ", "CK", "SA2",  # 注意 SA2 非法牌
            "S2"]
    # 分开验证：A2345
    hand_a2345 = ["SA", "S2", "H3", "D4", "C5", "H7", "D9"]
    a2345 = [s for s in _collect(gen.generate_lead_actions(hand_a2345), "Straight")
             if s[1] == "A" and sorted(_card_rank(c) for c in s[2]) == ["2", "3", "4", "5", "A"]]
    assert a2345, f"应能生成 A2345 顺子"

    # TJQKA
    hand_tjqka = ["ST", "HJ", "DQ", "CK", "SA", "S3", "D7"]
    tjqka = [s for s in _collect(gen.generate_lead_actions(hand_tjqka), "Straight")
             if s[1] == "T" and sorted(_card_rank(c) for c in s[2]) == ["A", "J", "K", "Q", "T"]]
    assert tjqka, f"应能生成 TJQKA 顺子"


def test_straight_full_combos_multi_suit():
    """顺子全组合：同一 5 连窗口覆盖不同花色组合（不只有单组合）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "H4", "D4", "D5", "C5", "C6", "S6", "S7", "H7"]
    straights = _collect(gen.generate_lead_actions(hand), "Straight")
    by_low = {}
    for s in straights:
        by_low.setdefault(s[1], []).append(tuple(sorted(s[2])))
    # 3-4-5-6-7 窗口应有多个花色组合（rank=窗口低牌 '3'）
    assert len(by_low.get("3", [])) >= 2, f"应生成多花色顺子组合: {by_low}"


def test_threepair_full_combos():
    """三连对：每 rank 的 pair 全组合。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "D3", "S4", "H4", "D4", "S5", "H5", "D5", "H2"]
    tp = _collect(gen.generate_lead_actions(hand), "ThreePair")
    assert len(tp) >= 1
    for t in tp:
        assert len(t[2]) == 6
        ranks = sorted(_card_rank(c) for c in t[2])
        assert ranks == ["3", "3", "4", "4", "5", "5"], t[2]


def test_twotrips_full_combos():
    """钢板：每 rank 的 trip 全组合。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "D3", "C3", "S4", "H4", "D4", "S5"]
    tt = _collect(gen.generate_lead_actions(hand), "TwoTrips")
    assert len(tt) >= 1
    for t in tt:
        assert len(t[2]) == 6
        ranks = sorted(_card_rank(c) for c in t[2])
        assert ranks == ["3", "3", "3", "4", "4", "4"], t[2]


def test_twt_full_combos_pair_choices():
    """三带二：trip 固定时 pair 应有多个候选组合。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "D3", "S5", "H5", "D5", "C5", "H2"]
    twt = _collect(gen.generate_lead_actions(hand), "ThreeWithTwo")
    # trip=3 配 5 的对子：S5H5/S5D5/S5C5/H5D5/H5C5/D5C5
    trip3_pairs = {tuple(sorted(t[2][3:])) for t in twt
                   if sorted(_card_rank(c) for c in t[2][:3]) == ["3", "3", "3"]}
    assert len(trip3_pairs) >= 4, f"三带二应提供多个 pair 组合: {len(trip3_pairs)}"


def test_sf_only_five_and_same_suit():
    """同花顺：只能 5 张；非万能牌必须同花色（H2 逢人配可跨花色补位）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "S4", "S5", "S6", "S7", "S8", "S9", "H2"]
    sf = _collect(gen.generate_lead_actions(hand), "StraightFlush")
    assert len(sf) >= 1
    for s in sf:
        assert len(s[2]) == 5, f"同花顺必须 5 张: {s[2]}"
        non_wild = [c for c in s[2] if c != "H2"]
        assert len(non_wild) >= 3, f"同花顺至少 3 张自然牌: {s[2]}"
        assert len(set(c[0] for c in non_wild)) == 1, f"非万能牌需同花色: {s[2]}"


def test_h2_wild_sf_generated_low_rank():
    """H2 逢人配同花顺：H2 补窗口缺位，rank 取窗口低牌。

    锚点：logs/v8_vs_botzone_20260802_220840.log G0 手牌 ['S4','S5','S6','H2','S8']
    服务器 RAW ['StraightFlush','4',['H2','H2','D6','D7','D8']] → rank='4'。
    """
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S4", "S5", "S6", "H2", "S8"]
    sf = _collect(gen.generate_lead_actions(hand), "StraightFlush")
    assert len(sf) == 1, f"仅 4-8 一窗口可补位，不应多生成: {sf}"
    s = sf[0]
    assert s[0] == "StraightFlush" and s[1] == "4", s
    assert sorted(s[2]) == sorted(["S4", "S5", "S6", "S8", "H2"]), s
    assert len(s[2]) == 5, s


def test_h2_wild_sf_two_h2_up_to_2_gaps():
    """两副牌上限：同一 SF 至多 2 张 H2（服务器 size=2209 实证）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["D6", "D7", "D8", "H2", "H2"]
    sf = _collect(gen.generate_lead_actions(hand), "StraightFlush")
    keys = {(s[1], tuple(sorted(s[2]))) for s in sf}
    # 3 张 D6-D8 + 2 H2：窗口 4-8 缺 4,5 → rank '4'（服务器同款）
    assert ("4", ("D6", "D7", "D8", "H2", "H2")) in keys, sf
    # 窗口 5-9 缺 5,9 → rank '5'（服务器同样出现过）
    assert ("5", ("D6", "D7", "D8", "H2", "H2")) in keys, sf


def test_sf_natural_low_rank():
    """自然同花顺 rank 取窗口低牌（服务器：9-K → '9'）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["H9", "HT", "HJ", "HQ", "HK", "H8", "S3"]
    sf = _collect(gen.generate_lead_actions(hand), "StraightFlush")
    target = ["StraightFlush", "9", ["H9", "HT", "HJ", "HQ", "HK"]]
    assert target in sf, f"自然同花顺 rank 应为低牌 '9': {sf}"


def test_straight_low_rank():
    """顺子 rank 取窗口低牌（服务器：D6-DT → '6'）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["D6", "D7", "D8", "H9", "DT", "S2"]
    st = _collect(gen.generate_lead_actions(hand), "Straight")
    target = ["Straight", "6", ["D6", "D7", "D8", "H9", "DT"]]
    assert target in st, f"顺子 rank 应为低牌 '6': {st}"


def test_classify_sf_low_rank():
    """_classify_action 同花顺/顺子 rank 解析为窗口低牌（与服务器 greater_action 一致）。"""
    adapter = _make_adapter()
    sf = adapter._classify_action(["H9", "HT", "HJ", "HQ", "HK"])
    assert sf[0] == "StraightFlush" and sf[1] == "9", sf
    st = adapter._classify_action(["D6", "D7", "D8", "H9", "DT"])
    assert st[0] == "Straight" and st[1] == "6", st


def test_follow_sf_h2_wild_and_natural():
    """跟牌：H2-wild 与自然同花顺仅保留能压过 greater 者（比窗口最高牌）。"""
    gen = ActionListGenerator(cur_rank="2")
    # greater 2-6（rank 低牌 '2'，窗口最高 '6'）
    greater = ["StraightFlush", "2", ["S2", "S3", "S4", "S5", "S6"]]
    hand = ["S3", "S4", "S5", "S6", "S7", "H2", "D9", "C9"]
    follow = gen.generate_follow_actions(hand, greater)
    sfs = [a for a in follow if a[0] == "StraightFlush"]
    keys = {(s[1], tuple(sorted(s[2]))) for s in sfs}
    # 自然 3-7（rank 低牌 '3'，窗口最高 7）压过 2-6
    assert ("3", ("S3", "S4", "S5", "S6", "S7")) in keys, sfs
    # H2 补 8 的 4-8（rank '4'，窗口最高 8）压过 2-6
    assert ("4", ("H2", "S4", "S5", "S6", "S7")) in keys, sfs
    # 2-6 的 H2 补位（窗口最高 '6' = greater，不能压过）应排除
    assert ("2", ("H2", "S3", "S4", "S5", "S6")) not in keys, sfs


def test_follow_straight_by_window_top():
    """跟牌顺子：按窗口最高牌压过 greater（rank 字段是低牌）。"""
    gen = ActionListGenerator(cur_rank="2")
    greater = ["Straight", "3", ["S3", "H4", "D5", "C6", "S7"]]  # 3-7，最高 7
    hand = ["S4", "H5", "D6", "C7", "S8", "S3", "D9", "H9"]
    follow = gen.generate_follow_actions(hand, greater)
    strs = [a for a in follow if a[0] == "Straight"]
    low_ranks = {s[1] for s in strs}
    # 4-8（rank '4'）与 5-9（rank '5'）最高牌 8/9 > 7 → 保留
    assert "4" in low_ranks, f"应保留 4-8: {strs}"
    assert "5" in low_ranks, f"应保留 5-9: {strs}"
    # 3-7（最高 7 = greater，不能压过）应排除
    assert "3" not in low_ranks, f"不应保留 3-7: {strs}"


def test_beats_sf_by_window_top():
    """_beats 对同花顺按窗口最高牌比较（rank 字段已是低牌）。"""
    adapter = _make_adapter()
    a = ["StraightFlush", "9", ["H9", "HT", "HJ", "HQ", "HK"]]  # 9-K
    b = ["StraightFlush", "2", ["S2", "S3", "S4", "S5", "S6"]]  # 2-6
    assert adapter._beats(a, b, "2") is True, "9-K 应压过 2-6"
    assert adapter._beats(b, a, "2") is False, "2-6 不应压过 9-K"


def test_h2_wild_sf_no_h2():
    """无 H2 时不生成逢人配同花顺（自然同花顺不受影响）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S4", "S5", "S6", "S8", "D2"]  # 无 H2，4-8 缺 7 无牌可补
    sf = _collect(gen.generate_lead_actions(hand), "StraightFlush")
    assert sf == [], f"无 H2 不应生成补位同花顺: {sf}"
    hand2 = ["S4", "S5", "S6", "S7", "S8", "D2"]  # 有自然 4-8
    sf2 = _collect(gen.generate_lead_actions(hand2), "StraightFlush")
    assert ["StraightFlush", "4", ["S4", "S5", "S6", "S7", "S8"]] in sf2, sf2


def test_h6_wild_sf_generated_follow():
    """GUA-200: 配子不限于 H2，cur_rank=6 时 H6 补位同花顺必须生成。

    锚点：match=6a71cf5f27e7bf01db106f56 回合19（19:39:47）手牌
    DA,D2,D3,D4,H6 + 对3/对7/对10，greater Single/HR。修复前 actionList
    只有 PASS+Bomb/3（H6 拆 SF core 被 _group_consistency_filter 拦截），
    该用完整 SF A2345 炸却没炸 → 对手双上。修复后必须含
    ['StraightFlush','A',['DA','D2','D3','D4','H6']]（完整 core 组，不拆）。
    """
    gen = ActionListGenerator(cur_rank="6")
    hand = ["DA", "D2", "D3", "D4", "H6", "H3", "S3", "H7", "C7", "CT", "ST"]
    follow = gen.generate_follow_actions(hand, ["Single", "R", ["HR"]])
    target = ["StraightFlush", "A", ["DA", "D2", "D3", "D4", "H6"]]
    assert target in follow, f"H6 配子应生成 A2345 同花顺: {follow}"


def test_h6_wild_sf_lead():
    """GUA-200: cur_rank=6 领出也生成 H6 配子同花顺。"""
    gen = ActionListGenerator(cur_rank="6")
    hand = ["DA", "D2", "D3", "D4", "H6", "S3"]
    sf = _collect(gen.generate_lead_actions(hand), "StraightFlush")
    assert ["StraightFlush", "A", ["DA", "D2", "D3", "D4", "H6"]] in sf, sf


def test_h3_wild_sf_generated():
    """GUA-200: cur_rank=3 时 H3 作配子补位（非 H2 硬编码）。"""
    gen = ActionListGenerator(cur_rank="3")
    hand = ["DA", "D2", "D4", "D5", "H3", "S3", "C3"]
    follow = gen.generate_follow_actions(hand, ["Single", "R", ["HR"]])
    target = ["StraightFlush", "A", ["DA", "D2", "D4", "D5", "H3"]]
    assert target in follow, f"H3 配子应生成 A2345 同花顺: {follow}"


def test_wild_sf_beats_single_joker():
    """GUA-200: 配子 SF（完整 core）能压 Single/大王，且不视为拆 core。"""
    adapter = _make_adapter()
    sf = ["StraightFlush", "A", ["DA", "D2", "D3", "D4", "H6"]]
    greater = ["Single", "R", ["HR"]]
    assert adapter._beats(sf, greater, "6") is True, "A2345 SF 应压过大王"


def test_bomb_full_and_four():
    """炸弹：覆盖全量（>=4）+ 4 张小炸。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "D3", "C3", "S3", "H2"]  # 5 张 3 + H2
    bombs = _collect(gen.generate_lead_actions(hand), "Bomb")
    sizes = sorted(len(b[2]) for b in bombs)
    assert 4 in sizes and 5 in sizes, f"炸弹应含 4 张和全量 5 张: {sizes}"


# ── 10. 两副牌重复牌（Botzone）回归 ─────────────

def test_twt_with_duplicate_suit_cards():
    """两副牌下同 rank 同花色重复（如 CJ/HJ/HJ）必须能组 ThreeWithTwo。

    锚点：match=6a6f3a80 两处 GUA-075 推荐 ThreeWithTwo/J
    [C7,CJ,D7,HJ,HJ] 无法匹配 actionList → PASS。
    旧 _combos 用 _uniq_cards（dict.fromkeys）去重吞掉重复 HJ →
    trip 组合为空 → TWT 缺失。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["C7", "D7", "CJ", "HJ", "HJ", "S5", "H5"]
    twt = _collect(gen.generate_lead_actions(hand), "ThreeWithTwo")
    j_twts = [a for a in twt if a[1] == "J"]
    assert j_twts, f"应有 J 的三带二（含两张 HJ）: {twt}"
    for t in j_twts:
        assert len(t[2]) == 5
        assert sorted(_card_rank(c) for c in t[2][:3]) == ["J", "J", "J"], t[2]


def test_follow_twt_with_duplicate_suit_cards():
    """跟牌轮 TWT 对重复花色牌同样成立（原 20:39:43/20:39:51 PASS 场景）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["C7", "CJ", "D7", "HJ", "HJ", "S5", "H5"]
    greater = ["ThreeWithTwo", "5", ["C5", "D5", "S5", "C6", "D6"]]
    actions = gen.generate_follow_actions(hand, greater)
    j_twts = [a for a in actions if a[0] == "ThreeWithTwo" and a[1] == "J"]
    assert j_twts, f"跟牌轮应有 J 三带二: {actions}"


def test_combos_keeps_duplicates():
    """_combos 保留两副牌重复牌：['CJ','HJ','HJ'] 取 3 应得 1 组。"""
    from src.communication.botzone_adapter import ActionListGenerator
    combos = ActionListGenerator._combos(["CJ", "HJ", "HJ"], 3)
    assert len(combos) == 1
    assert sorted(combos[0]) == ["CJ", "HJ", "HJ"], combos


def test_combos_dedup_by_sorted_key():
    """_combos 对同牌面不同顺序去重：CJ/HJ/HJ 任意排列只产一组。"""
    from src.communication.botzone_adapter import ActionListGenerator
    combos = ActionListGenerator._combos(["HJ", "CJ", "HJ"], 3)
    assert len(combos) == 1
    assert sorted(combos[0]) == ["CJ", "HJ", "HJ"], combos


# ── 11. numofplayers / publicInfo（残局激活）──────

def test_accumulate_played_cards_dedup_overlap():
    """跨 request history 重叠时 played_cards 用 set 去重，不重复计数。"""
    from src.communication.botzone_adapter import (
        BotzoneAdapter, BotzoneGameState,
    )
    adapter = BotzoneAdapter("test", "test_key")
    game = BotzoneGameState(match_id="m1")
    # request 1: player0 出 2 张, player1 出 1 张
    adapter._accumulate_played_cards(game, [
        {"player": 0, "response": [[10, 64], [10, 64]]},
        {"player": 1, "response": [[66], [66]]},
    ])
    # request 2: 同一手牌再次出现在近四手 history 中（重叠）
    adapter._accumulate_played_cards(game, [
        {"player": 0, "response": [[10, 64], [10, 64]]},
        {"player": 2, "response": [[69], [69]]},
    ])
    assert game.played_cards[0] == {10, 64}, game.played_cards
    assert game.played_cards[1] == {66}, game.played_cards
    assert game.played_cards[2] == {69}, game.played_cards


def test_extract_global_new_top_level_format():
    """新格式：字段平铺在 request 顶层（含 seed/level 数组），无 global 包裹。"""
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    req = {
        "seed": "1110065070",
        "level": ["2", "2"],
        "tribute": 0,
        "first": None,
        "last": None,
    }
    g = adapter._extract_global(req)
    assert g.get("level") == ["2", "2"], g
    assert g.get("tribute") == 0, g


def test_extract_global_old_wrapped_format():
    """旧格式：global 包裹，level 为字符串。"""
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    req = {"global": {"level": "2", "tribute": 1}, "history": []}
    g = adapter._extract_global(req)
    assert g == {"level": "2", "tribute": 1}, g


def test_resolve_level_string_and_array():
    """_resolve_level：字符串与数组（每阵营等级）都解析为 V8 所在阵营等级。"""
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    assert adapter._resolve_level("2", 0) == "2"
    assert adapter._resolve_level(["2", "2"], 0) == "2"
    assert adapter._resolve_level(["2", "3"], 0) == "2"  # V8=teamA
    assert adapter._resolve_level(["2", "3"], 2) == "2"  # 队友=teamA
    assert adapter._resolve_level(["2", "3"], 1) == "3"  # 对手=teamB
    assert adapter._resolve_level(["2", "3"], 3) == "3"  # 对手=teamB
    assert adapter._resolve_level([], 0) == "2"          # 空数组兜底
    assert adapter._resolve_level(None, 0) == "2"        # 缺省兜底


def test_handle_deal_new_top_level_format():
    """新格式发牌：顶层 level 数组解析为 V8 阵营等级。"""
    from src.communication.botzone_adapter import (
        BotzoneAdapter, BotzoneGameState,
    )
    adapter = BotzoneAdapter("test", "test_key")
    game = BotzoneGameState(match_id="m1", player_id=0)
    game.played_cards = {0: {10}}
    adapter._handle_deal(game, {
        "deliver": [0, 1, 2],
        "your_id": 0,
        "seed": "1110065070",
        "level": ["2", "2"],
        "tribute": 0,
        "first": None,
        "last": None,
    })
    assert game.cur_rank == "2", game.cur_rank
    assert game.played_cards == {}


def test_handle_play_request_new_top_level_format():
    """新格式 play 请求：顶层 level 数组同样更新 cur_rank。"""
    from src.communication.botzone_adapter import (
        BotzoneAdapter, BotzoneGameState,
    )
    adapter = BotzoneAdapter("test", "test_key")
    game = BotzoneGameState(match_id="m1", player_id=0)
    game.cur_rank = "2"
    adapter._handle_play_request(game, {
        "stage": "play",
        "history": [],
        "done": [],
        "pass_on": -1,
        "seed": "1110065070",
        "level": ["2", "2"],
        "tribute": 0,
        "first": None,
        "last": None,
    })
    assert game.cur_rank == "2", game.cur_rank


def test_handle_play_request_updates_played_cards():
    """_handle_play_request 应累计各席已出牌（含 PASS 跳过）。"""
    from src.communication.botzone_adapter import (
        BotzoneAdapter, BotzoneGameState,
    )
    adapter = BotzoneAdapter("test", "test_key")
    game = BotzoneGameState(match_id="m1")
    req = {
        "stage": "play",
        "history": [
            {"player": 1, "response": [[36, 92], [36, 92]]},
            {"player": 2, "response": [[], []]},
        ],
        "done": [],
        "pass_on": -1,
        "global": {"level": "2"},
    }
    adapter._handle_play_request(game, req)
    assert game.played_cards[1] == {36, 92}, game.played_cards
    assert 2 not in game.played_cards or game.played_cards[2] == set()


def test_deal_resets_played_cards():
    """新副发牌应清空 played_cards（跨副不串）。"""
    from src.communication.botzone_adapter import (
        BotzoneAdapter, BotzoneGameState,
    )
    adapter = BotzoneAdapter("test", "test_key")
    game = BotzoneGameState(match_id="m1")
    game.played_cards = {0: {10}, 1: {66}}
    adapter._handle_deal(game, {"deliver": [0, 1, 2], "your_id": 0,
                                "global": {"level": "2"}})
    assert game.played_cards == {}


class _StubEngine:
    """最小 decision_engine 桩：decide 恒返回 0。"""

    def decide(self, game_state) -> int:
        return 0


def _make_adapter_with_engine():
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    adapter.set_decision_engine(_StubEngine())
    return adapter


def _run_play_decision(adapter, game, req):
    import asyncio
    return asyncio.run(adapter._handle_play_decision("m1", game, req))


def test_jiefeng_lead_must_play():
    """接风领出轮（request B：QQQ44 之后已有 PASS）必须出牌，禁止 PASS。

    复现 match=6a6ffd1327e7bf01db0ebeb8 request 22：
    done=[3,2]，player2 末手 QQQ44，其后 P0/P1 均已 PASS → V8 是下一个未出完者，
    必须领出；返回非法 PASS 会被平台判「1号玩家决策错误」中止。
    """
    from src.communication.botzone_adapter import BotzoneGameState
    adapter = _make_adapter_with_engine()
    game = BotzoneGameState(match_id="m1", player_id=0)
    # V8 残局 7 张：S7, DJ, HJ, S4, C4, H4, H5
    game.hand_cards = ["S7", "DJ", "HJ", "S4", "C4", "H4", "H5"]
    game.cur_rank = "2"
    req = {
        "stage": "play",
        "history": [
            {"player": 1, "response": [[], []]},
            {"player": 2, "response": [[45, 98, 46, 67, 66], [45, 98, 46, 67, 66]]},
            {"player": 0, "response": [[], []]},
            {"player": 1, "response": [[], []]},
        ],
        "done": [3, 2],
        "pass_on": -1,
        "global": {"level": "2"},
    }
    resp = _run_play_decision(adapter, game, req)
    import json as _json
    parsed = _json.loads(resp)
    assert parsed != [[], []], f"接风领出轮返回 PASS: {resp}"


def test_follow_turn_may_pass():
    """跟牌轮（request A：QQQ44 为 history 末条，无人对之 PASS）可 PASS。

    复现 match=6a6ffd1327e7bf01db0ebeb8 request 21：
    done=[3,2]，player2 刚出 QQQ44 是末条，V8 是首个响应者，跟牌轮可 PASS。
    """
    from src.communication.botzone_adapter import BotzoneGameState
    adapter = _make_adapter_with_engine()
    game = BotzoneGameState(match_id="m1", player_id=0)
    game.hand_cards = ["S7", "DJ", "HJ", "S4", "C4", "H4", "H5"]
    game.cur_rank = "2"
    req = {
        "stage": "play",
        "history": [
            {"player": 2, "response": [[45, 98, 46, 67, 66], [45, 98, 46, 67, 66]]},
        ],
        "done": [3, 2],
        "pass_on": 2,
        "global": {"level": "2"},
    }
    resp = _run_play_decision(adapter, game, req)
    import json as _json
    parsed = _json.loads(resp)
    assert parsed == [[], []], f"跟牌轮应可 PASS: {resp}"


def test_greater_done_but_v8_unresponded_is_follow_turn():
    """request C：greater 已 done 但 V8 尚未对该手表态 → 仍是跟牌轮，可 PASS。

    复现 match=6a70986927e7bf01db0f2585 21:33:03（S69）：
    history=[P0:[], P1:[59,6]=对2, P2:[], P3:[]]，done=[1]，pass_on=1。
    P1 已出完、P2/P3 均 PASS，但 trailing 不含 V8(P0) 自己的 PASS 表态，
    V8 是最后一个未表态者——平台视角仍须跟牌（同型/炸/PASS），
    不能自由领出。旧判定误判为「接风领出 → must_play=True」，
    领出 Straight 被平台判「牌型与上家不一致」中止（实测对局）。
    """
    from src.communication.botzone_adapter import BotzoneGameState
    adapter = _make_adapter_with_engine()
    game = BotzoneGameState(match_id="m1", player_id=0)
    game.hand_cards = ["C3", "D4", "H5", "S6", "C7", "D8", "H9", "S10", "CJ", "DQ", "HK"]
    game.cur_rank = "2"
    req = {
        "stage": "play",
        "history": [
            {"player": 0, "response": [[], []]},
            {"player": 1, "response": [[59, 6], [59, 6]]},
            {"player": 2, "response": [[], []]},
            {"player": 3, "response": [[], []]},
        ],
        "done": [1],
        "pass_on": 1,
        "global": {"level": "2"},
    }
    resp = _run_play_decision(adapter, game, req)
    import json as _json
    parsed = _json.loads(resp)
    assert parsed == [[], []], (
        f"V8 未表态应为跟牌轮可 PASS（实测会跟对2失败而 PASS）: {resp}"
    )


def test_numofplayers_and_public_info():
    """numofplayers（对手剩张 = 27 - 已出，done 玩家 0）+ publicInfo[].rest。"""
    from src.communication.botzone_adapter import (
        BotzoneAdapter, BotzoneGameState,
    )
    adapter = BotzoneAdapter("test", "test_key")
    game = BotzoneGameState(match_id="m1", player_id=0)
    game.hand_cards = ["S3", "H5", "D7", "C9", "HJ"]  # 5 张
    game.played_cards = {1: {10, 64, 66}, 2: {69}, 3: {1, 2, 3, 4, 5, 6}}
    known_done = [3]
    numofplayers = adapter._compute_numofplayers(game, game.hand_cards, known_done)
    assert numofplayers == [5, 24, 26, 0], numofplayers
    public_info = [{"rest": n} for n in numofplayers]
    assert public_info == [
        {"rest": 5}, {"rest": 24}, {"rest": 26}, {"rest": 0},
    ], public_info


# ── 12. GUA-19x 回归：领出无 PASS + history 键对齐 ────

class _RecordingEngine:
    """记录最后一次传给 decide 的 game_state。"""

    def __init__(self):
        self.last_game_state = None

    def decide(self, game_state) -> int:
        self.last_game_state = dict(game_state)
        return 0


def _make_recording_adapter():
    from src.communication.botzone_adapter import BotzoneAdapter
    engine = _RecordingEngine()
    adapter = BotzoneAdapter("test", "test_key")
    adapter.set_decision_engine(engine)
    return adapter, engine


def test_history_keys_aligned_with_engine():
    """history 条目键对齐引擎：pos/action + PASS 条目的 context.greaterAction。

    修复前 adapter 传 "_history" 键 + "player" 键，引擎只读 g["history"] +
    pos/seat → MemoryTracker 回放静默失效；现必须用 pos + history。
    """
    from src.communication.botzone_adapter import BotzoneGameState
    adapter, engine = _make_recording_adapter()
    game = BotzoneGameState(match_id="m1", player_id=0)
    game.hand_cards = ["S3", "H5", "D7", "C9", "SJ", "HJ", "D2", "C2", "S2"]  # 9 张
    game.cur_rank = "2"
    # player1 出对 3，player2 PASS，轮到 V8(0) 跟牌
    pair_bz = v8_to_bz_cards(["S3", "H3"])
    req = {
        "stage": "play",
        "history": [
            {"player": 1, "response": [pair_bz, pair_bz]},
            {"player": 2, "response": [[], []]},
        ],
        "done": [],
        "pass_on": -1,
        "global": {"level": "2"},
    }
    _run_play_decision(adapter, game, req)
    gs = engine.last_game_state
    assert gs is not None
    assert "history" in gs, f"game_state 应含 history 键: {list(gs.keys())}"
    history = gs["history"]
    assert len(history) == 2, history
    # 条目 1：player1 出 Pair
    e0 = history[0]
    assert e0.get("pos") == 1, e0
    assert e0["action"][0] == "Pair", e0
    # 条目 2：player2 PASS，context.greaterAction 指向当时面对的最大动作（Pair）
    e1 = history[1]
    assert e1.get("pos") == 2, e1
    assert e1["action"][0] == "PASS", e1
    assert e1.get("context", {}).get("greaterAction", [])[0] == "Pair", e1


def test_history_passes_running_greater_not_final():
    """PASS 条目的 context.greaterAction 用当时的 running greater。

    同一 request 内后续还有更大动作时，先前 PASS 条目不得引用最终更大动作。
    """
    from src.communication.botzone_adapter import BotzoneGameState
    adapter, engine = _make_recording_adapter()
    game = BotzoneGameState(match_id="m1", player_id=0)
    game.hand_cards = ["S3", "H5", "D7", "C9", "SJ", "HJ", "D2", "C2", "S2"]
    game.cur_rank = "2"
    # player1 出单 5，player2 PASS（面对 单5），player3 出单 7（新的更大）
    single5 = v8_to_bz_cards(["H5"])
    single7 = v8_to_bz_cards(["D7"])
    req = {
        "stage": "play",
        "history": [
            {"player": 1, "response": [single5, single5]},
            {"player": 2, "response": [[], []]},
            {"player": 3, "response": [single7, single7]},
        ],
        "done": [],
        "pass_on": -1,
        "global": {"level": "2"},
    }
    _run_play_decision(adapter, game, req)
    gs = engine.last_game_state
    history = gs["history"]
    assert len(history) == 3, history
    # player2 的 PASS 面对的是当时的 greater（单5），不是最后的单7
    pass_entry = history[1]
    ga = pass_entry["context"]["greaterAction"]
    assert ga[0] == "Single" and ga[1] == "5", ga
    assert history[2]["action"][0] == "Single" and history[2]["action"][1] == "7"


def test_deal_calls_on_game_start():
    """每副发牌应调用引擎 on_game_start（重置 tracker / 增量回放游标）。

    缺失会跨副串位：_tracker_history_replayed 从上一副末值继续，新副首 request
    的 history 从头开始 → 增量回放 `history[start:]` 全空，MemoryTracker 失忆。
    """
    from src.communication.botzone_adapter import BotzoneGameState
    calls = {"n": 0}

    class _OnStartEngine:
        def on_game_start(self, my_pos=None, game_id=None):
            calls["n"] += 1
            calls["my_pos"] = my_pos

        def decide(self, game_state) -> int:
            return 0

    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter("test", "test_key")
    adapter.set_decision_engine(_OnStartEngine())
    game = BotzoneGameState(match_id="m1", player_id=0)
    adapter._handle_deal(game, {"deliver": [0, 1, 2], "your_id": 0,
                                "global": {"level": "2"}})
    assert calls["n"] == 1, calls
    assert calls.get("my_pos") == 0, calls


def test_memory_tracker_replays_new_history_format():
    """引擎 decide 可正确消费 adapter 新 history 格式（pos + action + greaterAction）。

    修复前 adapter 用 "_history"+"player" 键，引擎只读 g["history"]+pos/seat →
    MemoryTracker 回放静默失效（对手牌张数推算失真）。本测试验证：
      ① 非 PASS 条目被 record_play（tracker 记录该牌已出）；
      ② PASS 条目 + context.greaterAction 触发 record_pass（记该 PASS 面对的牌型）。
    """
    import importlib
    try:
        ultimate = importlib.import_module(
            "src.v.nn.ultimate_win_rate_engine_v7")
        UltimateWinRateEngineV7 = ultimate.UltimateWinRateEngineV7
        FEATURE_IMPORT_OK = ultimate.FEATURE_IMPORT_OK
    except Exception:
        pytest_skip = True
    else:
        pytest_skip = not FEATURE_IMPORT_OK
    if pytest_skip:
        pytest.skip("V8 特征/引擎不可用，跳过集成测试")

    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
    engine.on_game_start(0)
    # player1 出对 3，player2 出对 5（压 3），player3 PASS（面对 对5）
    history = [
        {"pos": 1, "action": ["Pair", "3", ["S3", "H3"]]},
        {"pos": 2, "action": ["Pair", "5", ["S5", "H5"]]},
        {"pos": 3, "action": ["PASS", "PASS", "PASS"],
         "context": {"greaterAction": ["Pair", "5", ["S5", "H5"]]}},
    ]
    gs = {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 2,
        "greaterAction": ["Pair", "5", ["S5", "H5"]],
        "handCards": ["C3", "D3", "S6", "H6", "D6", "C7", "S8", "H9", "D9",
                      "ST", "CT", "SJ", "DJ", "SK", "DK"],
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Pair", "6", ["S6", "H6"]],
            ["Pair", "9", ["H9", "D9"]],
        ],
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "publicInfo": [{"rest": 15}, {"rest": 24}, {"rest": 24}, {"rest": 26}],
        "history": history,
    }
    idx = engine.decide(gs)
    assert isinstance(idx, int) and idx >= 0, idx
    # tracker 已回放 3 条
    assert engine._tracker is not None
    assert engine._tracker_history_replayed == 3, engine._tracker_history_replayed
    # 对手 2 已出对 5（两张 5），剩张应从 27 扣到 24（publicInfo 亦为 24）
    hand_counts = engine._tracker.hand_counts
    assert hand_counts.get(2) == 24, hand_counts


# ── 11. 裁判语义回归（G1/G4/G5/G2）────────────

def test_beats_bomb_sf_mutual_exclusion_by_count():
    """G1：同花顺只压 4/5 张炸，6+ 炸压同花顺（裁判 checkBigger 先比张数）。"""
    adapter = _make_adapter()
    sf = ["StraightFlush", "9", ["H9", "HT", "HJ", "HQ", "HK"]]  # 9-K
    bomb4 = ["Bomb", "A", ["HA", "DA", "SA", "CA"]]
    bomb5 = ["Bomb", "K", ["HK", "DK", "SK", "CK", "HK"]]
    bomb6 = ["Bomb", "Q", ["HQ", "DQ", "SQ", "CQ", "HQ", "DQ"]]
    # 同花顺 vs 炸弹
    assert adapter._beats(sf, bomb4, "2") is True, "SF 应压 4 张炸"
    assert adapter._beats(sf, bomb5, "2") is True, "SF 应压 5 张炸"
    assert adapter._beats(sf, bomb6, "2") is False, "6+ 炸 > 同花顺"
    # 炸弹 vs 同花顺
    assert adapter._beats(bomb4, sf, "2") is False, "4 张炸不压同花顺"
    assert adapter._beats(bomb5, sf, "2") is False, "5 张炸不压同花顺"
    assert adapter._beats(bomb6, sf, "2") is True, "6+ 炸压同花顺"


def test_beats_bomb_vs_bomb_count_then_rank():
    """G5：炸弹对炸弹先比张数，同张数再比牌值（裁判 points[0]/points[1]）。"""
    adapter = _make_adapter()
    bomb4a = ["Bomb", "A", ["HA", "DA", "SA", "CA"]]
    bomb5k = ["Bomb", "K", ["HK", "DK", "SK", "CK", "HK"]]
    bomb4k = ["Bomb", "K", ["HK", "DK", "SK", "CK"]]
    bomb4j = ["Bomb", "J", ["HJ", "DJ", "SJ", "CJ"]]
    assert adapter._beats(bomb4a, bomb5k, "2") is False, "4 张 A 炸不能压 5 张 K 炸"
    assert adapter._beats(bomb5k, bomb4a, "2") is True, "5 张 K 炸压 4 张 A 炸"
    assert adapter._beats(bomb4k, bomb4j, "2") is True, "同张数比牌值"
    assert adapter._beats(bomb4j, bomb4k, "2") is False, "同张数牌值小者不压"


def test_follow_bomb_filters_by_count():
    """G5：跟牌炸弹按张数过滤——4 张高值炸不能跟进 5/6 张炸，5 张炸可压 4 张炸。"""
    gen = ActionListGenerator(cur_rank="2")
    # greater = 5 张 K 炸；手牌仅 4 张 A 炸 → 不应出现在跟牌候选
    greater5k = ["Bomb", "K", ["HK", "DK", "SK", "CK", "HK"]]
    hand4a = ["HA", "DA", "SA", "CA", "S3", "H3", "D3"]
    bombs = _collect(gen.generate_follow_actions(hand4a, greater5k), "Bomb")
    assert bombs == [], f"4 张 A 炸不能压 5 张 K 炸: {bombs}"
    # greater = 4 张 A 炸；手牌 5 张 K 炸 → 应出现在跟牌候选
    greater4a = ["Bomb", "A", ["HA", "DA", "SA", "CA"]]
    hand5k = ["HK", "DK", "SK", "CK", "HK", "H3", "D3"]
    bombs = _collect(gen.generate_follow_actions(hand5k, greater4a), "Bomb")
    sizes = [len(b[2]) for b in bombs]
    assert 5 in sizes, f"5 张 K 炸应能压 4 张 A 炸: {bombs}"


def test_follow_straight_flush_only_six_plus_bombs():
    """G1：跟牌同花顺时，4/5 张炸不进入候选，6+ 炸保留。"""
    gen = ActionListGenerator(cur_rank="2")
    greater_sf = ["StraightFlush", "4", ["C4", "C5", "C6", "C7", "C8"]]  # 4-8
    hand = ["H5", "D5", "S5", "C5",                  # 4 张 5 炸
            "H6", "D6", "S6", "C6", "H6", "D6"]      # 6 张 6 炸
    bombs = _collect(gen.generate_follow_actions(hand, greater_sf), "Bomb")
    sizes = sorted(len(b[2]) for b in bombs)
    assert sizes == [6], f"仅 6+ 炸可压同花顺: {bombs}"


def test_return_tribute_threshold():
    """G4：还贡 ≤9（level='9' 时 ≤8），级牌/10 均不可还。"""
    from src.communication.botzone_adapter import BotzoneGameState
    adapter = _make_adapter()
    game = BotzoneGameState(match_id="m1", player_id=0)
    game.cur_rank = "2"
    game.hand_cards = ["ST", "H9", "H8", "H3"]  # T 不可还，应还最小合法 3
    resp = adapter._handle_return_request("m1", game, {"global": {"level": "2"}})
    assert bz_to_v8_card(int(resp[1:-1])) == "H3", resp
    # level='9'：只能还 ≤8（级牌 9 与 10 均不可还）
    game2 = BotzoneGameState(match_id="m1", player_id=0)
    game2.cur_rank = "9"
    game2.hand_cards = ["S9", "S8", "S7"]
    resp2 = adapter._handle_return_request("m1", game2, {"global": {"level": "9"}})
    assert bz_to_v8_card(int(resp2[1:-1])) == "S7", resp2


def test_h2_wild_sf_claim_replaced():
    """G2：H2 逢人配同花顺的 claim 把配子替换为所代表 rank 的同花牌。"""
    adapter = _make_adapter()
    # [S4,S5,S6,H2,S8] rank='4' → 窗口 4-8，缺 7 → H2 替换为 S7
    chosen = ["StraightFlush", "4", ["S4", "S5", "S6", "H2", "S8"]]
    claim = adapter._build_bz_claim(chosen, "2", v8_to_bz_cards(chosen[2]))
    assert claim == v8_to_bz_cards(["S4", "S5", "S6", "S7", "S8"]), claim
    # 同一副牌按窗口低牌消歧：rank='3' → 窗口 3-7，缺 3 → H2 替换为 S3
    chosen2 = ["StraightFlush", "3", ["H2", "S4", "S5", "S6", "S7"]]
    claim2 = adapter._build_bz_claim(chosen2, "2", v8_to_bz_cards(chosen2[2]))
    assert claim2 == v8_to_bz_cards(["S3", "S4", "S5", "S6", "S7"]), claim2
    # A2345 窗口：H2 是自然级牌，无需替换（claim==action）
    chosen3 = ["StraightFlush", "A", ["HA", "H2", "H3", "H4", "H5"]]
    bz3 = v8_to_bz_cards(chosen3[2])
    assert adapter._build_bz_claim(chosen3, "2", bz3) == bz3, "A2345 的 H2 为自然级牌"
    # 非同花顺含 H2（Single/Pair）→ claim==action
    chosen4 = ["Single", "2", ["H2"]]
    assert adapter._build_bz_claim(chosen4, "2", [4]) == [4], "非配子场景 claim==action"


def test_play_decision_h2_wild_sf_claim_in_response():
    """G2 集成：出牌响应 [action, claim] 中 H2-wild 同花顺的 claim 替换配子。"""
    from src.communication.botzone_adapter import BotzoneGameState

    class _FixedGen:
        cur_rank = "2"

        def generate_lead_actions(self, hand_cards):
            return [["StraightFlush", "4", ["S4", "S5", "S6", "H2", "S8"]]]

        def generate_follow_actions(self, hand_cards, greater):
            return [["PASS", "PASS", "PASS"]]

    adapter = _make_adapter_with_engine()
    adapter.action_generator = _FixedGen()
    game = BotzoneGameState(match_id="m1", player_id=0)
    game.cur_rank = "2"
    game.hand_cards = ["S4", "S5", "S6", "H2", "S8"]
    req = {"stage": "play", "history": [], "global": {"level": "2"}}
    resp = _run_play_decision(adapter, game, req)
    import json as _json
    action, claim = _json.loads(resp)
    assert action == v8_to_bz_cards(["S4", "S5", "S6", "H2", "S8"]), action
    assert claim == v8_to_bz_cards(["S4", "S5", "S6", "S7", "S8"]), claim


def test_follow_wild_bomb_candidate():
    """GUA-199：跟牌侧逢人配补炸——自然 3 张 + H2 → 4 张 Bomb 候选。

    修复前炸弹兜底只认自然 4+ 同 rank，手牌 444+H2 时候选仅 PASS+Pair，
    引擎拆炸弹 core 打弱牌（match=6a71ace3 回合11：H4,H4,D4,H2,C2 对
    Pair/8 只出 22 对子）。
    """
    gen = ActionListGenerator(cur_rank="2")
    hand = ["H4", "H4", "D4", "H2", "C2"]
    greater = ["Pair", "8", ["D8", "S8"]]
    actions = gen.generate_follow_actions(hand, greater)
    bombs = [a for a in actions if a[0] == "Bomb"]
    assert ["Bomb", "4", ["H4", "H4", "D4", "H2"]] in bombs, actions


def test_lead_wild_bomb_candidate():
    """GUA-199：领出侧逢人配补炸——自然 3 张 + H2 → 4 张 Bomb 候选。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["H4", "H4", "D4", "H2"]
    actions = gen.generate_lead_actions(hand)
    bombs = [a for a in actions if a[0] == "Bomb"]
    assert ["Bomb", "4", ["H4", "H4", "D4", "H2"]] in bombs, actions


def test_wild_bomb_claim_replaced():
    """GUA-199：逢人配补炸的 claim 把配子替换为所代表 rank（G2 同规则）。"""
    adapter = _make_adapter()
    chosen = ["Bomb", "4", ["H4", "H4", "D4", "H2"]]
    claim = adapter._build_bz_claim(chosen, "2", v8_to_bz_cards(chosen[2]))
    assert claim == v8_to_bz_cards(["H4", "H4", "D4", "S4"]), claim
    # 配子作自然级牌（Bomb/2 含 H2）→ claim==action
    chosen2 = ["Bomb", "2", ["S2", "H2", "D2", "C2"]]
    bz2 = v8_to_bz_cards(chosen2[2])
    assert adapter._build_bz_claim(chosen2, "2", bz2) == bz2, "Bomb/2 的 H2 为自然级牌"
    # 无配子炸弹 → claim==action
    chosen3 = ["Bomb", "K", ["HK", "DK", "SK", "CK"]]
    bz3 = v8_to_bz_cards(chosen3[2])
    assert adapter._build_bz_claim(chosen3, "2", bz3) == bz3, "无配子 claim==action"


def test_follow_wild_bomb_beats_bomb_by_count_and_rank():
    """GUA-199：配子补炸参与比炸——4 张炸同张数比牌值，5+ 张炸不可压。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["H4", "H4", "D4", "H2", "C2"]
    # greater 4 张炸（rank 3）→ 配子 4 张炸（rank 4）可压
    greater_bomb = ["Bomb", "3", ["S3", "H3", "D3", "C3"]]
    acts = gen.generate_follow_actions(hand, greater_bomb)
    bombs = [a for a in acts if a[0] == "Bomb"]
    assert ["Bomb", "4", ["H4", "H4", "D4", "H2"]] in bombs, acts
    # greater 5 张炸 → 配子 4 张炸不可压（裁判先比张数 G5）
    greater_5 = ["Bomb", "3", ["S3", "H3", "D3", "C3", "S3"]]
    acts5 = gen.generate_follow_actions(hand, greater_5)
    assert all(a[0] == "PASS" or len(a[2]) >= 5 for a in acts5), acts5

