# -*- coding: utf-8 -*-
"""
GUA-267：火不打四的例外——自己有炸再加一手整牌时，对手剩 4 张也开炸冲刺。

锚点 match=6a8c34520fbd680d7c81dc86：手牌 QQQQ+HA 跟 Trips/9，
报四把 Bomb 禁掉后 Q1 拆 3 张 Q。用户定音：火+（单/对/顺/TWT/三张/三连对/钢板）
即使敌剩 4 也先出完整炸。
"""

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor

BOMB_Q = ["HQ", "SQ", "CQ", "SQ"]
HA = ["HA"]
TRIPS_9 = ["D9", "H9", "H9"]


def _follow_trips9_state(hand_cards, action_list, numofplayers):
    return {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Trips", "9", list(TRIPS_9)],
        "handCards": list(hand_cards),
        "actionList": action_list,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "numofplayers": list(numofplayers),
        "publicInfo": [{"rest": n} for n in numofplayers],
        "_role": "主攻",
        "_botzone_mode": True,
        "_group_members": {
            -1: [c for c in hand_cards if c not in BOMB_Q],
            0: list(BOMB_Q) if all(c in hand_cards for c in set(BOMB_Q)) else [],
        },
        "_group_gid_type_map": {-1: "scatter", 0: "Bomb"},
    }


def _qqqq_ha_actions():
    return [
        ["PASS", "PASS", "PASS"],
        ["Trips", "Q", ["HQ", "SQ", "CQ"]],
        ["Trips", "Q", ["HQ", "SQ", "SQ"]],
        ["Trips", "Q", ["CQ", "SQ", "SQ"]],
        ["Bomb", "Q", list(BOMB_Q)],
    ]


class TestGua267Detector:
    def test_bomb_plus_single(self):
        assert EndgameDecider._is_bomb_plus_one_structure_hand(BOMB_Q + HA) is True

    def test_bomb_plus_pair(self):
        assert EndgameDecider._is_bomb_plus_one_structure_hand(
            BOMB_Q + ["CA", "DA"]
        ) is True

    def test_bomb_plus_trips(self):
        assert EndgameDecider._is_bomb_plus_one_structure_hand(
            BOMB_Q + ["C7", "D7", "H7"]
        ) is True

    def test_bomb_plus_twt(self):
        assert EndgameDecider._is_bomb_plus_one_structure_hand(
            BOMB_Q + ["C5", "D5", "H5", "C8", "D8"]
        ) is True

    def test_bomb_plus_straight(self):
        assert EndgameDecider._is_bomb_plus_one_structure_hand(
            BOMB_Q + ["C3", "D4", "H5", "S6", "C7"]
        ) is True

    def test_bomb_plus_two_trips(self):
        assert EndgameDecider._is_bomb_plus_one_structure_hand(
            BOMB_Q + ["C5", "D5", "H5", "C6", "D6", "H6"]
        ) is True

    def test_scattered_not_two_hands(self):
        """炸 + 两张散单 = 三手，不是例外。"""
        assert EndgameDecider._is_bomb_plus_one_structure_hand(
            BOMB_Q + ["HA", "C3"]
        ) is False

    def test_many_cards_not_exception(self):
        assert EndgameDecider._is_bomb_plus_one_structure_hand(
            BOMB_Q + ["S3", "H4", "C5", "D5", "S7", "H7", "C9"]
        ) is False


class TestGua267CoreBreakDuplicateRank:
    def test_trips_from_four_queens_breaks_bomb(self):
        """两张 SQ 不得用 set 塌成完整炸核。"""
        gs = {
            "_group_members": {0: list(BOMB_Q)},
            "_group_gid_type_map": {0: "Bomb"},
        }
        act = ["Trips", "Q", ["HQ", "SQ", "CQ"]]
        assert EndgameDecider._action_breaks_core_structure(act, gs) is True

    def test_full_bomb_still_exempt(self):
        gs = {
            "_group_members": {0: list(BOMB_Q)},
            "_group_gid_type_map": {0: "Bomb"},
        }
        act = ["Bomb", "Q", list(BOMB_Q)]
        assert EndgameDecider._action_breaks_core_structure(act, gs) is False


class TestGua267FireVsFourSprint:
    def test_apply_banned_filter_keeps_bomb_when_bomb_plus_single(self):
        gs = _follow_trips9_state(
            BOMB_Q + HA, _qqqq_ha_actions(), [5, 4, 8, 10],
        )
        EndgamePreprocessor().preprocess(gs)
        filtered, empty = EndgameDecider().apply_banned_filter(
            list(gs["actionList"]), gs,
        )
        assert not empty
        assert any(a[0] == "Bomb" for a in filtered)

    def test_decide_plays_full_bomb_not_trips_q(self):
        """锚点：跟 Trips/9、敌剩 4、手牌 Q 炸+HA → 完整 Bomb/Q。"""
        gs = _follow_trips9_state(
            BOMB_Q + HA, _qqqq_ha_actions(), [5, 4, 8, 10],
        )
        EndgamePreprocessor().preprocess(gs)
        dec = EndgameDecider()
        filtered, _ = dec.apply_banned_filter(list(gs["actionList"]), gs)
        idx, act = dec.decide(gs, filtered)
        assert act is not None
        assert act[0] == "Bomb"
        assert act[1] == "Q"
        assert sorted(act[2]) == sorted(BOMB_Q)

    def test_gua115_still_pass_when_not_two_hands(self):
        """13 张散牌+炸、仅炸可压 → 仍火不打四 PASS。"""
        bomb = ["S8", "H8", "C8", "D8"]
        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 3,
            "greaterAction": ["ThreeWithTwo", "6", ["S6", "S6", "D6", "C5", "C5"]],
            "handCards": bomb + ["S3", "H4", "C5", "D5", "S7", "H7", "C9"],
            "actionList": [["PASS", "PASS", "PASS"], ["Bomb", "8", bomb]],
            "curRank": "A",
            "numofplayers": [13, 6, 10, 4],
            "publicInfo": [{"rest": 13}, {"rest": 6}, {"rest": 10}, {"rest": 4}],
            "_role": "主攻",
            "_botzone_mode": True,
        }
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert idx == 0
        assert act[0] == "PASS"
