# -*- coding: utf-8 -*-
"""GUA-052 108 张牌全量追踪 + 排除法推断 — 单元测试"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.v.nn.features.memory_tracker import MemoryTracker, ALL_CARD_TYPES, MEMORY_TRACKER_DIM


def test_01_init():
    mt = MemoryTracker(my_pos=0)
    assert len(ALL_CARD_TYPES) == 54
    assert mt.hand_counts[0] == 27
    assert mt.hand_counts[1] == 27


def test_02_init_from_hand():
    mt = MemoryTracker(my_pos=0)
    mt.init_from_hand(["S3", "H3", "S5", "D5", "BJ"])
    my_types = mt.get_my_hand_types()
    assert "S3" in my_types
    assert "SB" in my_types
    assert "S5" in my_types


def test_03_record_play_and_played():
    mt = MemoryTracker(my_pos=0)
    mt.init_from_hand(["S3", "H3", "S5"])
    mt.record_play(seat=0, action=["Single", "3", ["S3"]])
    played = mt.get_played_cards()
    assert "S3" in played
    assert played["S3"] >= 1


def test_04_hand_count_update():
    mt = MemoryTracker(my_pos=0)
    mt.init_from_hand(["S3"])
    mt.record_play(seat=0, action=["Single", "3", ["S3"]])
    assert mt.get_hand_count(0) <= 26  # hand_count after play


def test_05_bomb_tracking():
    mt = MemoryTracker(my_pos=0)
    mt.record_bomb(seat=1)
    mt.record_bomb(seat=1)
    assert mt.bombs_played[1] == 2


def test_06_opponent_bomb_risk():
    mt = MemoryTracker(my_pos=0)
    mt.hand_counts[1] = 8
    mt.record_bomb(seat=1)
    risk = mt.get_opponent_bomb_risk(1)
    assert risk > 0.0


def test_07_level_card_tracking():
    mt = MemoryTracker(my_pos=0)
    mt.set_level_rank("2")
    assert len(mt.level_cards_remaining) == 4


def test_08_state_vector_dim():
    mt = MemoryTracker(my_pos=0)
    mt.init_from_hand(["S3", "H3"])
    mt.record_play(seat=1, action=["Single", "5", ["S5"]])
    vec = mt.get_state_vector()
    assert len(vec) == MEMORY_TRACKER_DIM, f"got {len(vec)}"


def test_09_reset():
    mt = MemoryTracker(my_pos=0)
    mt.init_from_hand(["S3"])
    mt.record_play(seat=1, action=["Single", "5", ["S5"]])
    mt.record_bomb(seat=2)
    mt.reset()
    assert mt.get_hand_count(0) == 27
    assert mt.get_hand_count(1) == 27
    assert len(mt.play_history) == 0
    assert mt.inference_time_ms == 0.0


def test_10_inference_simple():
    mt = MemoryTracker(my_pos=0, enable_inference=True, max_infer_depth=1)
    mt.init_from_hand(["S3", "H3", "D3", "C3"])
    mt.record_play(seat=1, action=["Single", "3", ["S3"]])
    owners = mt.get_card_owners("S3")
    assert 4 in owners or 1 in owners  # either played(4) or seat 1 has it
