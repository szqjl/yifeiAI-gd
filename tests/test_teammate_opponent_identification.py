# -*- coding: utf-8 -*-
"""
队友与对方识别测试
掼蛋规则：0与2一队，1与3一队；teammate_pos = (my_pos + 2) % 4
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from communication.game_recorder import (
    get_teammate_pos,
    get_opponent_positions,
    is_teammate,
    ensure_my_pos_int,
)


def test_teammate_pos():
    """0-2 一队，1-3 一队"""
    assert get_teammate_pos(0) == 2
    assert get_teammate_pos(2) == 0
    assert get_teammate_pos(1) == 3
    assert get_teammate_pos(3) == 1
    print("  [OK] get_teammate_pos(0..3)")


def test_opponent_positions():
    """对手为 (my_pos+1)%4 与 (my_pos+3)%4"""
    assert get_opponent_positions(0) == (1, 3)
    assert get_opponent_positions(1) == (2, 0)
    assert get_opponent_positions(2) == (3, 1)
    assert get_opponent_positions(3) == (0, 2)
    print("  [OK] get_opponent_positions(0..3)")


def test_is_teammate():
    assert is_teammate(0, 2) is True
    assert is_teammate(0, 1) is False
    assert is_teammate(1, 3) is True
    assert is_teammate(2, 0) is True
    assert is_teammate(0, -1) is False
    assert is_teammate(0, 0) is False
    print("  [OK] is_teammate(my_pos, other_pos)")


def test_ensure_my_pos_int():
    assert ensure_my_pos_int({"myPos": 1}, 0) == 1
    assert ensure_my_pos_int({"myPos": "2"}, 0) == 2
    assert ensure_my_pos_int({"playerPosition": 3}, 0) == 3
    assert ensure_my_pos_int({}, 2) == 2
    assert ensure_my_pos_int({"myPos": None}, 1) == 1
    print("  [OK] ensure_my_pos_int(data, fallback)")


if __name__ == "__main__":
    print("队友与对方识别验证")
    print("-" * 50)
    test_teammate_pos()
    test_opponent_positions()
    test_is_teammate()
    test_ensure_my_pos_int()
    print("-" * 50)
    print("全部通过：M/V 系列可依 my_pos 正确识别队友与对方。")
