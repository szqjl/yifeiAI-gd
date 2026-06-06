# -*- coding: utf-8 -*-
"""yf_replay：本副等级解析须优先 act·play，勿被贡还/beginning 快照覆盖。"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tools"))

from yf_replay import resolve_episode_levels  # noqa: E402


def _sample_with_tribute_then_play(play_cur="9", play_self="8", play_oppo="9"):
    """贡还 notify 带 beginning 级 4，play act 带还贡后真值。"""
    return {
        "game_info": {"selfRank": "8", "oppoRank": "6", "curRank": "4"},
        "my_decisions": [
            {
                "action": ["tribute", "tribute", ["HR"]],
                "context": {
                    "source": "notify",
                    "stage": "tribute",
                    "selfRank": "8",
                    "oppoRank": "6",
                    "curRank": "4",
                },
            },
            {
                "action": ["back", "back", ["C6"]],
                "context": {
                    "source": "notify",
                    "stage": "back",
                    "selfRank": "8",
                    "oppoRank": "6",
                    "curRank": "4",
                },
            },
            {
                "action": ["Single", "5", ["S5"]],
                "context": {
                    "source": "act",
                    "stage": "play",
                    "selfRank": play_self,
                    "oppoRank": play_oppo,
                    "curRank": play_cur,
                },
            },
        ],
    }


@pytest.mark.unit
def test_resolve_levels_prefers_play_over_tribute_notify():
    levels = resolve_episode_levels(
        _sample_with_tribute_then_play(),
        "20260601112040960695 [yf1_m3]-[opponent_1_3]-[38]-[4].json",
    )
    assert levels["curRank"] == "9"
    assert levels["selfRank"] == "8"
    assert levels["oppoRank"] == "9"


@pytest.mark.unit
def test_resolve_levels_play_k_after_tribute_nine():
    """对齐 mdc round 40：贡还 curRank=9，play 起 curRank=K。"""
    data = _sample_with_tribute_then_play(play_cur="K", play_self="J", play_oppo="9")
    levels = resolve_episode_levels(
        data,
        "20260601112041622568 [yf2_m3]-[40]-[9].json",
    )
    assert levels["curRank"] == "K"
    assert levels["selfRank"] == "J"
    assert levels["oppoRank"] == "9"


@pytest.mark.unit
def test_resolve_levels_tribute_fallback_when_no_play():
    data = {
        "game_info": {"curRank": "4"},
        "my_decisions": [
            {
                "action": ["tribute", "tribute", ["HR"]],
                "context": {
                    "source": "act",
                    "stage": "tribute",
                    "selfRank": "8",
                    "oppoRank": "6",
                    "curRank": "6",
                },
            },
        ],
    }
    levels = resolve_episode_levels(data, "sample [yf1_m3]-[x]-[1]-[4].json")
    assert levels["curRank"] == "6"


@pytest.mark.unit
def test_resolve_levels_filename_fallback_only_without_context():
    data = {"game_info": {"curRank": "4"}}
    levels = resolve_episode_levels(
        data,
        "20260601112040960695 [yf1_m3]-[opponent_1_3]-[38]-[4].json",
    )
    assert levels["curRank"] == "4"
