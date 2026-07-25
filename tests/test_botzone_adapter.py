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
