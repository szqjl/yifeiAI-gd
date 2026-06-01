# -*- coding: utf-8 -*-
"""yf_replay：加载时按 my_decisions 调整贡前 initial_hand。"""

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tools"))

from yf_replay import apply_tribute_back_to_hand  # noqa: E402


def _simulate_my_hand_at_step(initial, my_decisions, player_id, actions, step):
    hand = apply_tribute_back_to_hand(initial, my_decisions, player_id)
    bag = Counter(hand)
    pid = int(player_id)
    for action in actions[:step]:
        if action.get("cur_pos") != pid:
            continue
        cur = action.get("cur_action") or []
        if not cur or str(cur[0]).upper() == "PASS":
            continue
        if len(cur) < 3 or not isinstance(cur[2], list):
            continue
        for card in cur[2]:
            if isinstance(card, str) and len(card) >= 2:
                key = card[0].upper() + card[1:].upper()
            else:
                continue
            bag[key] -= 1
            if bag[key] <= 0:
                del bag[key]
    return sorted(bag.elements())


@pytest.fixture
def tribute_only_hand():
    """27 张含 S2，进贡 act 出 S2 → 有效起手 26 张。"""
    hand = [f"H{i}" for i in range(2, 10)] + ["HA", "HK", "HQ"]
    hand += [f"S{i}" for i in range(2, 10)] + ["SA", "SK"]
    hand += [f"C{i}" for i in range(2, 7)] + ["CA"]
    assert len(hand) == 27
    assert hand.count("S2") == 1
    my_decisions = [
        {
            "action": ["tribute", "tribute", ["S2"]],
            "context": {"source": "act", "stage": "tribute"},
        }
    ]
    return hand, my_decisions


@pytest.mark.unit
def test_apply_tribute_act_removes_outgoing(tribute_only_hand):
    hand, my_decisions = tribute_only_hand
    adjusted = apply_tribute_back_to_hand(hand, my_decisions, 0)
    assert "S2" not in adjusted
    assert len(adjusted) == 26


@pytest.mark.unit
def test_apply_notify_tribute_adds_received():
    hand = ["C9", "DA"]
    my_decisions = [
        {
            "action": ["tribute", "tribute", ["S2"]],
            "context": {
                "source": "notify",
                "tribute_pos": 3,
                "receive_tribute_pos": 0,
                "stage": "tribute",
            },
        }
    ]
    adjusted = apply_tribute_back_to_hand(hand, my_decisions, 0)
    assert "S2" in adjusted
    assert len(adjusted) == 3


@pytest.mark.unit
def test_apply_notify_back_adds_received():
    hand = ["C9", "S2"]
    my_decisions = [
        {
            "action": ["tribute", "tribute", ["S2"]],
            "context": {"source": "act", "stage": "tribute"},
        },
        {
            "action": ["back", "back", ["H4"]],
            "context": {
                "source": "notify",
                "back_pos": 3,
                "receive_back_pos": 0,
                "stage": "back",
            },
        },
    ]
    adjusted = apply_tribute_back_to_hand(hand, my_decisions, 0)
    assert "S2" not in adjusted
    assert "H4" in adjusted
    assert adjusted == ["C9", "H4"]


@pytest.mark.unit
def test_legacy_tribute_without_source_treated_as_outgoing():
    hand = ["S2", "C9"]
    my_decisions = [{"action": ["tribute", "tribute", ["S2"]], "context": {}}]
    adjusted = apply_tribute_back_to_hand(hand, my_decisions, 0)
    assert adjusted == ["C9"]


@pytest.mark.unit
def test_full_sequence_tribute_out_back_in():
    """进贡出 S2、收还贡 H4：牌数恢复 27，组成正确。"""
    hand = ["S2"] + [f"C{i}" for i in range(2, 10)] + ["CA", "CK", "CQ", "CJ", "CT"]
    hand += [f"D{i}" for i in range(2, 10)] + ["DA", "DK", "DQ", "DJ", "DT"]
    assert len(hand) == 27
    my_decisions = [
        {
            "action": ["tribute", "tribute", ["S2"]],
            "context": {"source": "act", "stage": "tribute"},
        },
        {
            "action": ["back", "back", ["H4"]],
            "context": {
                "source": "notify",
                "back_pos": 2,
                "receive_back_pos": 0,
                "stage": "back",
            },
        },
    ]
    adjusted = apply_tribute_back_to_hand(hand, my_decisions, 0)
    assert "S2" not in adjusted
    assert "H4" in adjusted
    assert len(adjusted) == 27


@pytest.mark.unit
def test_sample_game_20260601_yf1_tribute_sb_back_s3():
    """round 56 样例局：进贡 SB、收还贡 S3。"""
    fname = "20260601104553134255 [yf1_m3]-[opponent_1_3]-[56]-[9].json"
    p = Path(__file__).resolve().parents[1] / "game_records" / fname
    if not p.exists():
        pytest.skip("sample game not in game_records")
    data = json.loads(p.read_text(encoding="utf-8"))
    raw = data["initial_hand"]
    assert "SB" in raw and "S3" not in raw
    adj = apply_tribute_back_to_hand(raw, data["my_decisions"], 0)
    assert "SB" not in adj and "S3" in adj
    assert len(adj) == 27


@pytest.mark.unit
def test_simulate_hand_before_pass_only_c9():
    """贡后只剩 C9，模拟到只剩过牌前手牌为 [C9]。"""
    initial = ["C9"]
    initial += [f"H{i}" for i in range(2, 10)] + ["HA", "HK", "HQ", "HJ", "HT"]
    initial += [f"S{i}" for i in range(2, 10)] + ["SA", "SK", "SQ", "SJ", "ST"]
    assert len(initial) == 27
    my_decisions = [
        {
            "action": ["tribute", "tribute", ["S2"]],
            "context": {"source": "act", "stage": "tribute"},
        }
    ]
    # 仅保留 C9 的出牌序列（其余 25 张按单张出）
    actions = []
    played = [c for c in apply_tribute_back_to_hand(initial, my_decisions, 0) if c != "C9"]
    for card in played:
        actions.append({"cur_pos": 0, "cur_action": ["Single", "Single", [card]]})
    actions.append({"cur_pos": 0, "cur_action": ["PASS", "PASS", []]})
    hand = _simulate_my_hand_at_step(initial, my_decisions, 0, actions, len(actions))
    assert hand == ["C9"]
