# -*- coding: utf-8 -*-
"""GUA-078：MemoryTracker 在 decide() 入口就绪，残局 Q1 可封锁报单炸。

设计真源：``docs/knowledge/skills/07_opening/end position.md`` §二 / §3.3 / §1.20
回放：``20260621204653147750`` 步62 yf1@0 有 K 炸 + @1 rest=1 → Q1 Bomb K。
"""
import pytest

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

# 回放 20260621204653147750 步62：yf1@0 反推手牌（restCards + 步67/70 出牌）
YF1_HAND_STEP62 = [
    "C3", "C5", "CK", "CK", "D6", "H4", "HK", "S5", "S6", "S6", "S7", "S7", "S8", "SK",
]

BOMB_10 = ["ST", "CT", "DT", "DT"]
BOMB_K = ["SK", "HK", "CK", "CK"]


def _step62_game_state(*, public_info):
    return {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Bomb", "T", BOMB_10],
        "handCards": list(YF1_HAND_STEP62),
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Bomb", "K", BOMB_K],
        ],
        "curRank": "4",
        "selfRank": "4",
        "oppoRank": "7",
        "publicInfo": public_info,
    }


@pytest.fixture(autouse=True)
def _fresh_engine():
    yield


class TestGua078TrackerAtDecideEntry:
    """wiki endgame-preprocessor-overview 张力4：记忆管线先于残局 numofplayers。"""

    def test_step62_endgame_bomb_when_public_info_rest(self):
        """@1 报单 1 张 + publicInfo.rest → 残局 Q1 出 K 炸，非 PASS。"""
        gs = _step62_game_state(
            public_info=[
                {"rest": 14},
                {"rest": 1},
                {"rest": 10},
                {"rest": 11},
            ],
        )
        engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
        engine.on_game_start(0)

        idx = engine.decide(gs)
        chosen = gs["actionList"][idx]

        assert chosen[0] == "Bomb"
        assert chosen[1] == "K"
        assert sorted(chosen[2]) == sorted(BOMB_K)
        assert engine._endgame_activated_count >= 1
        assert engine._endgame_hit_count >= 1
        assert gs.get("numofplayers", [None] * 4)[1] == 1

    def test_step62_pass_without_rest_blind_numofplayers(self):
        """无 publicInfo / Tracker 盲猜 → is_active 假、残局不炸（回归根因）。"""
        gs = _step62_game_state(public_info=[])
        engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
        engine.on_game_start(0)

        idx = engine.decide(gs)
        assert gs["actionList"][idx][0] == "PASS"
        assert engine._endgame_hit_count == 0
