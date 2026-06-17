# -*- coding: utf-8 -*-
"""Regression tests for GameRecorder same-round hand merge (GUA-025)."""

import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from communication.game_recorder import GameRecorder  # noqa: E402

ROUND19_YF2 = REPO / "game_records/20260529223719968305 [yf2_m3]-[opponent_1_3]-[19]-[K].json"
ROUND19_YF1 = REPO / "game_records/20260529223719987048 [yf1_m3]-[opponent_1_3]-[19]-[K].json"
ROUND12_YF1 = REPO / "game_records/20260529223715483407 [yf1_m3]-[opponent_1_3]-[12]-[Q].json"


def _rank_counts(cards):
    return Counter(c[1:] for c in cards if isinstance(c, str) and len(c) >= 2)


@pytest.mark.skipif(not ROUND19_YF2.exists(), reason="round 19 sample record missing")
def test_merge_round19_uses_teammate_hand_not_other_round():
    data = GameRecorder.load_game(ROUND19_YF2)
    hands = data.get("all_players_hands", {})
    pos0 = hands.get("0") or hands.get(0)
    assert pos0, "pos 0 hand should be merged from yf1 round 19"

    rc = _rank_counts(pos0)
    # round 19 yf1 has 3 aces including SA; round 12 wrongly merged had 0 aces, 4 threes
    assert rc.get("A", 0) == 3
    assert rc.get("3", 0) == 2
    assert "SA" in pos0

    round12 = GameRecorder.load_game(ROUND12_YF1)
    round12_hand = round12.get("initial_hand", [])
    assert _rank_counts(pos0) != _rank_counts(round12_hand)


@pytest.mark.skipif(not ROUND19_YF2.exists(), reason="round 19 sample record missing")
def test_merge_normalizes_string_keys_only():
    data = GameRecorder.load_game(ROUND19_YF2)
    hands = data.get("all_players_hands", {})
    assert all(isinstance(k, str) for k in hands.keys())
    assert "0" in hands
    assert "2" in hands
    assert 0 not in hands and 2 not in hands


def test_parse_record_filename():
    parsed = GameRecorder.parse_record_filename(
        "20260529223719968305 [yf2_m3]-[opponent_1_3]-[19]-[K].json"
    )
    assert parsed is not None
    assert parsed["round"] == "19"
    assert parsed["level"] == "K"
    assert parsed["opponent"] == "opponent_1_3"
    assert parsed["player_name"] == "yf2_m3"


@pytest.mark.skipif(not (ROUND19_YF2.exists() and ROUND19_YF1.exists()), reason="round 19 samples missing")
def test_replay_hand_deduction_after_step20():
    """Simulate replay card removal with corrected merge — no orphan 5/2 after ThreeWithTwo."""
    import json

    data = GameRecorder.load_game(ROUND19_YF2)
    yf1_raw = json.loads(ROUND19_YF1.read_text(encoding="utf-8"))
    hands = {"0": list(data["all_players_hands"]["0"])}

    def played_cards(cur_action):
        if not cur_action or cur_action[0] == "PASS":
            return []
        if len(cur_action) >= 3:
            return list(cur_action[2])
        return []

    for action in data["actions"][:20]:
        if action.get("cur_pos") != 0:
            continue
        for card in played_cards(action.get("cur_action")):
            assert card in hands["0"], f"missing {card} at step play {action.get('cur_action')}"
            hands["0"].remove(card)

    rc = _rank_counts(hands["0"])
    assert rc.get("5", 0) == 0
    assert rc.get("2", 0) == 0
    assert rc.get("3", 0) == 0
