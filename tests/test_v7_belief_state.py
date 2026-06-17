"""Tests for V7 situation classifier (套路一 prototype)."""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.v.nn.features.belief_state import (
    extract_situation_vector,
    SITUATION_DIM,
    SITUATION_AGGRESSIVE,
    SITUATION_DEFENSIVE,
    SITUATION_WAITING,
    SITUATION_PROTECT,
    SITUATION_NAMES,
)


def _make_game_state(**overrides) -> dict:
    """Build minimal game_state dict for testing."""
    return {
        "handCards": [],
        "myPos": 0,
        "curPos": 0,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "curBombNum": 0,
        "actionList": [["PASS"]],
        "history": [],
        **overrides,
    }


def test_output_shape():
    """Should return shape (4,) float32."""
    gs = _make_game_state()
    result = extract_situation_vector(gs)
    assert isinstance(result, np.ndarray), f"expected ndarray, got {type(result)}"
    assert result.shape == (SITUATION_DIM,), f"shape={result.shape}"
    assert result.dtype == np.float32, f"dtype={result.dtype}"


def test_output_softmax():
    """Situation vector should sum to ~1.0."""
    gs = _make_game_state()
    result = extract_situation_vector(gs)
    assert abs(result.sum() - 1.0) < 1e-5, f"sum={result.sum()}"


def test_aggressive_strong_hand():
    """Strong hand with bombs → aggressive should be argmax."""
    gs = _make_game_state(
        handCards=["S2", "H2", "D2", "C2", "SA", "HA", "DA", "CA", "BJ", "RJ"],
        curRank="2",
        history=[],
    )
    result = extract_situation_vector(gs)
    argmax = int(np.argmax(result))
    assert argmax == SITUATION_AGGRESSIVE, (
        f"expected aggressive argmax, got {SITUATION_NAMES[argmax]}: "
        f"{dict(zip(SITUATION_NAMES, result.tolist()))}"
    )


def test_defensive_weak_hand():
    """Weak hand → defensive or waiting should dominate (not aggressive)."""
    gs = _make_game_state(
        handCards=["S3", "H4", "D5", "C6", "S7", "H8"],
        curRank="2",
        selfRank="2",
        oppoRank="A",
        history=[],
    )
    result = extract_situation_vector(gs)
    argmax = int(np.argmax(result))
    assert argmax != SITUATION_AGGRESSIVE, (
        f"aggressive should not be argmax for weak hand, got: "
        f"{dict(zip(SITUATION_NAMES, result.tolist()))}"
    )


def test_protect_partner_few_cards():
    """Partner has few cards → protect should be argmax."""
    gs = _make_game_state(
        handCards=["S2", "H3", "D4", "C5", "S6", "H7", "D8", "C9", "ST", "HT"],
        myPos=0,
        curRank="2",
        history=[
            {
                "curAction": ["Single", "A"],
                "curPos": 0,
                "numofplayers": [10, 15, 5, 20],
            }
        ],
    )
    result = extract_situation_vector(gs)
    argmax = int(np.argmax(result))
    assert argmax == SITUATION_PROTECT, (
        f"expected protect argmax, got {SITUATION_NAMES[argmax]}: "
        f"{dict(zip(SITUATION_NAMES, result.tolist()))}"
    )


def test_waiting_neutral():
    """Neutral game state → waiting should be argmax."""
    gs = _make_game_state(
        handCards=["S3", "H4", "D5", "C6", "S7", "H8", "D9", "CT", "SJ", "HQ"],
        curRank="5",
        selfRank="5",
        oppoRank="5",
        history=[
            {
                "curAction": ["Single", "7"],
                "curPos": 1,
                "numofplayers": [15, 14, 16, 13],
            }
        ],
    )
    result = extract_situation_vector(gs)
    argmax = int(np.argmax(result))
    assert argmax == SITUATION_WAITING, (
        f"expected waiting argmax, got {SITUATION_NAMES[argmax]}: "
        f"{dict(zip(SITUATION_NAMES, result.tolist()))}"
    )


def test_aggressive_plus_bombs():
    """2+ bombs → aggressive should be argmax."""
    gs = _make_game_state(
        handCards=["S2", "H2", "D2", "C2", "SA", "HA", "DA", "CA", "S4", "H4", "D4", "C4", "S5", "H5"],
        curRank="2",
        history=[],
    )
    result = extract_situation_vector(gs)
    argmax = int(np.argmax(result))
    assert argmax == SITUATION_AGGRESSIVE, (
        f"expected aggressive argmax, got {SITUATION_NAMES[argmax]}: "
        f"{dict(zip(SITUATION_NAMES, result.tolist()))}"
    )


def test_partner_overrides_aggressive():
    """Partner almost done → protect should be argmax even if I'm strong."""
    gs = _make_game_state(
        handCards=["S2", "H2", "D2", "C2", "SA", "HA", "DA", "CA", "BJ", "RJ"],
        myPos=0,
        curRank="2",
        history=[
            {
                "curAction": ["Single", "A"],
                "curPos": 1,
                "numofplayers": [10, 15, 3, 20],
            }
        ],
    )
    result = extract_situation_vector(gs)
    argmax = int(np.argmax(result))
    assert argmax == SITUATION_PROTECT, (
        f"expected protect argmax even with strong hand, got {SITUATION_NAMES[argmax]}: "
        f"{dict(zip(SITUATION_NAMES, result.tolist()))}"
    )


def test_empty_hand():
    """Empty hand → should not crash."""
    gs = _make_game_state(handCards=[])
    result = extract_situation_vector(gs)
    assert abs(result.sum() - 1.0) < 1e-5


def test_missing_history():
    """No history → should still produce valid output."""
    gs = _make_game_state(
        handCards=["S2", "H3", "D4", "C5"],
        myPos=0,
        curRank="2",
    )
    # Remove history entirely
    gs.pop("history", None)
    result = extract_situation_vector(gs)
    assert abs(result.sum() - 1.0) < 1e-5


if __name__ == "__main__":
    test_output_shape()
    test_output_softmax()
    test_aggressive_strong_hand()
    test_defensive_weak_hand()
    test_protect_partner_few_cards()
    test_waiting_neutral()
    test_aggressive_plus_bombs()
    test_partner_overrides_aggressive()
    test_empty_hand()
    test_missing_history()
    print("All belief_state tests passed")
