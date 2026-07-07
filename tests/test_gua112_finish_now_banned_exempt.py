# -*- coding: utf-8 -*-
"""GUA-112：一手清候选不受 Q1 banned_filter 删除；任意牌型均可 finish-now。"""

import pytest

from src.v.nn.endgame.endgame_decide import (
    EndgameDecider,
    find_finish_now_candidate,
    finish_now_protected_action_types,
)
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker


def _base_gs(hand_cards, action_list, *, numofplayers, cur_rank="K"):
    tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand_cards)
    tracker.set_level_rank(cur_rank)
    tracker.hand_counts = {
        0: len(hand_cards),
        1: numofplayers[1],
        2: numofplayers[2],
        3: numofplayers[3],
    }
    return {
        "myPos": 0,
        "curPos": -1,
        "greaterPos": -1,
        "greaterAction": None,
        "handCards": list(hand_cards),
        "actionList": action_list,
        "curRank": cur_rank,
        "selfRank": cur_rank,
        "oppoRank": cur_rank,
        "numofplayers": list(numofplayers),
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {
                0: len(hand_cards),
                1: numofplayers[1],
                2: numofplayers[2],
                3: numofplayers[3],
            },
            "opp_bomb_risks": {1: 1.0, 3: 0.5},
        },
        "_role": "超弱",
    }


def _decide_after_preprocess(gs):
    EndgamePreprocessor().preprocess(gs)
    decider = EndgameDecider()
    filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
    al = gs["actionList"] if banned_empty else filtered
    return decider.decide(gs, al), filtered


class TestGua112FinishNowBannedExempt:
    def test_wf12_anchor_trips_when_enemy_rem3_bans_trips(self):
        """84440863663 步106：@1 rem=3 禁 Trips，仍应一手 Trips/A 清牌。"""
        hand = ["SA", "HA", "DA"]
        al = [
            ["Single", "A", ["SA"]],
            ["Single", "A", ["HA"]],
            ["Single", "A", ["DA"]],
            ["Pair", "A", ["SA", "DA"]],
            ["Pair", "A", ["SA", "HA"]],
            ["Pair", "A", ["HA", "DA"]],
            ["Trips", "A", hand],
        ]
        gs = _base_gs(hand, al, numofplayers=[3, 3, 5, 7])
        (idx, act), filtered = _decide_after_preprocess(gs)
        assert any(a[0] == "Trips" for a in filtered)
        assert idx == filtered.index(["Trips", "A", hand])
        assert act[0] == "Trips"
        assert sorted(act[2]) == sorted(hand)

    def test_pair_finish_now_when_enemy_rem2_bans_pair(self):
        hand = ["S7", "C7"]
        finish = ["Pair", "7", hand]
        al = [
            ["Single", "7", ["S7"]],
            ["Single", "7", ["C7"]],
            finish,
        ]
        gs = _base_gs(hand, al, numofplayers=[2, 2, 8, 9])
        (idx, act), filtered = _decide_after_preprocess(gs)
        assert finish in filtered
        assert act == finish

    def test_bomb_finish_now_when_baoshu_never_play_bomb(self):
        hand = ["S5", "H5", "C5", "D5"]
        finish = ["Bomb", "5", hand]
        al = [
            ["Single", "5", ["S5"]],
            finish,
        ]
        gs = _base_gs(hand, al, numofplayers=[4, 4, 6, 8])
        (idx, act), filtered = _decide_after_preprocess(gs)
        assert finish in filtered
        assert act == finish

    def test_straight_finish_now_survives_pair_ban_at_rem4(self):
        hand = ["S3", "S4", "S5", "S6", "S7"]
        finish = ["Straight", "7", hand]
        al = [
            ["Single", "3", ["S3"]],
            ["Pair", "3", ["S3", "S4"]],
            finish,
        ]
        gs = _base_gs(hand, al, numofplayers=[5, 4, 7, 8])
        (idx, act), filtered = _decide_after_preprocess(gs)
        assert finish in filtered
        assert act == finish

    def test_three_with_two_finish_now(self):
        hand = ["S8", "H8", "D8", "S3", "H3"]
        finish = ["ThreeWithTwo", "8", hand]
        al = [
            ["Trips", "8", ["S8", "H8", "D8"]],
            finish,
        ]
        gs = _base_gs(hand, al, numofplayers=[5, 3, 6, 9])
        (idx, act), _ = _decide_after_preprocess(gs)
        assert act == finish

    def test_two_trips_finish_now(self):
        hand = ["S4", "H4", "C4", "S5", "H5", "C5"]
        finish = ["TwoTrips", "5", hand]
        al = [["Trips", "4", ["S4", "H4", "C4"]], finish]
        gs = _base_gs(hand, al, numofplayers=[6, 5, 7, 8])
        (idx, act), _ = _decide_after_preprocess(gs)
        assert act == finish

    def test_three_pair_finish_now(self):
        hand = ["S3", "H3", "S4", "H4", "S5", "H5"]
        finish = ["ThreePair", "5", hand]
        al = [finish]
        gs = _base_gs(hand, al, numofplayers=[6, 6, 8, 9])
        (idx, act), _ = _decide_after_preprocess(gs)
        assert act == finish

    def test_protected_types_include_finish_now_type(self):
        hand = ["SA", "HA", "DA"]
        al = [
            ["Pair", "A", ["SA", "DA"]],
            ["Trips", "A", hand],
        ]
        gs = _base_gs(hand, al, numofplayers=[3, 3, 5, 7])
        EndgamePreprocessor().preprocess(gs)
        protected = finish_now_protected_action_types(gs, al)
        assert "Trips" in protected

    def test_find_finish_now_module_helper(self):
        hand = ["HJ", "DJ", "HA"]
        al = [["Trips", "J", hand]]
        gs = {"handCards": hand}
        found = find_finish_now_candidate(gs, al)
        assert found == (0, al[0])
