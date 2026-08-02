# -*- coding: utf-8 -*-
"""
BotzoneAdapter 单元测试 — 牌编码双射 + ActionList 生成。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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


def test_has_pass():
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H5"]
    actions = gen.generate_lead_actions(hand)
    pass_actions = [a for a in actions if a[0] == "PASS"]
    assert len(pass_actions) == 1


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


# ── 9. 全组合与官方牌型对齐 ─────────────────────

def _collect(al, t):
    return [a for a in al if a[0] == t]


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
             if s[1] == "5" and sorted(_card_rank(c) for c in s[2]) == ["2", "3", "4", "5", "A"]]
    assert a2345, f"应能生成 A2345 顺子"

    # TJQKA
    hand_tjqka = ["ST", "HJ", "DQ", "CK", "SA", "S3", "D7"]
    tjqka = [s for s in _collect(gen.generate_lead_actions(hand_tjqka), "Straight")
             if s[1] == "A" and sorted(_card_rank(c) for c in s[2]) == ["A", "J", "K", "Q", "T"]]
    assert tjqka, f"应能生成 TJQKA 顺子"


def test_straight_full_combos_multi_suit():
    """顺子全组合：同一 5 连窗口覆盖不同花色组合（不只有单组合）。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "H4", "D4", "D5", "C5", "C6", "S6", "S7", "H7"]
    straights = _collect(gen.generate_lead_actions(hand), "Straight")
    by_high = {}
    for s in straights:
        by_high.setdefault(s[1], []).append(tuple(sorted(s[2])))
    # 3-4-5-6-7 窗口应有多个花色组合
    assert len(by_high.get("7", [])) >= 2, f"应生成多花色顺子组合: {by_high}"


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
    """同花顺：只能 5 张且同花色。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "S4", "S5", "S6", "S7", "S8", "S9", "H2"]
    sf = _collect(gen.generate_lead_actions(hand), "StraightFlush")
    assert len(sf) >= 1
    for s in sf:
        assert len(s[2]) == 5, f"同花顺必须 5 张: {s[2]}"
        assert len(set(c[0] for c in s[2])) == 1, f"同花顺需同花色: {s[2]}"


def test_bomb_full_and_four():
    """炸弹：覆盖全量（>=4）+ 4 张小炸。"""
    gen = ActionListGenerator(cur_rank="2")
    hand = ["S3", "H3", "D3", "C3", "S3", "H2"]  # 5 张 3 + H2
    bombs = _collect(gen.generate_lead_actions(hand), "Bomb")
    sizes = sorted(len(b[2]) for b in bombs)
    assert 4 in sizes and 5 in sizes, f"炸弹应含 4 张和全量 5 张: {sizes}"
