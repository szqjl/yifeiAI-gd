# -*- coding: utf-8 -*-
"""GUA-235：领出冲刺不受 baoshu 硬删 Bomb；C356 无 TWT 有炸时回退 Q1。"""

from src.communication.botzone_adapter import ActionListGenerator
from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor


def _lead_a5_five_bomb_state(numofplayers):
    """SF 后手牌：A-5 顺 + 五星 6 炸（match=6a7c7876 形态）。"""
    hand = ["HA", "C2", "S3", "D4", "D5", "S6", "C6", "C6", "D6", "H6"]
    acts = ActionListGenerator(cur_rank="2").generate_lead_actions(hand)
    gs = {
        "handCards": hand,
        "curRank": "2",
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 0,
        "greaterAction": ["StraightFlush", "8", ["H8", "H9", "HT", "HJ", "HQ"]],
        "numofplayers": list(numofplayers),
        "publicInfo": [{"rest": r} for r in numofplayers],
        "_botzone_mode": True,
        "_role": "超强主攻",
    }
    return gs, acts


class TestGua235BaoshuLeadKeepsBomb:
    def test_apply_banned_filter_lead_keeps_bomb_when_enemy_four(self):
        """敌剩 4：领出轮 baoshu never_play 不得硬删 Bomb。"""
        gs, acts = _lead_a5_five_bomb_state([10, 6, 10, 4])
        EndgamePreprocessor().preprocess(gs)
        filtered, empty = EndgameDecider().apply_banned_filter(list(acts), gs)
        assert not empty
        assert any(a[0] == "Bomb" for a in filtered)
        assert any(a[0] == "Straight" and a[1] == "A" for a in filtered)

    def test_q0_lead_picks_straight_a_not_single_a_when_enemy_four(self):
        """敌剩 4：领出两手冲刺应 Straight/A，而非 Single/A。"""
        gs, acts = _lead_a5_five_bomb_state([10, 6, 10, 4])
        EndgamePreprocessor().preprocess(gs)
        dec = EndgameDecider()
        filtered, _ = dec.apply_banned_filter(list(acts), gs)
        idx, act = dec.decide(gs, filtered)
        assert act is not None
        assert act[0] == "Straight"
        assert act[1] == "A"
        assert set(act[2]) == {"HA", "C2", "S3", "D4", "D5"}

    def test_follow_enemy_four_still_bans_bomb_via_gua115(self):
        """跟压报四：火不打四仍成立（仅 Bomb 可压 → PASS）。"""
        bomb = ["S8", "H8", "C8", "D8"]
        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 3,
            "greaterAction": ["ThreeWithTwo", "6", ["S6", "S6", "D6", "C8", "C8"]],
            "handCards": bomb + ["S3", "H4", "C5", "D5", "S7", "H7", "C9"],
            "curRank": "A",
            "numofplayers": [13, 6, 10, 4],
            "publicInfo": [{"rest": 13}, {"rest": 6}, {"rest": 10}, {"rest": 4}],
            "_role": "主攻",
            "_botzone_mode": True,
        }
        acts = [["PASS", "PASS", "PASS"], ["Bomb", "8", bomb]]
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, acts)
        assert idx == 0
        assert act[0] == "PASS"


class TestGua235C356FallbackWhenBombAvailable:
    def test_twt_enemy_six_with_bomb_sf_not_pass(self):
        """敌剩 6 出 TWT、无更大 TWT 可跟、有 Bomb/SF → 不得 C356 直接 PASS。"""
        hand = [
            "HA", "C2", "S3", "D4", "D5", "S6",
            "C6", "C6", "D6", "H6",
            "H9", "HT", "HJ", "HQ", "H2",
        ]
        greater = ["ThreeWithTwo", "Q", ["SQ", "DQ", "CQ", "H7", "D7"]]
        acts = ActionListGenerator(cur_rank="2").generate_follow_actions(hand, greater)
        assert any(a[0] == "Bomb" for a in acts)
        assert any(a[0] == "StraightFlush" for a in acts)
        assert not any(a[0] == "ThreeWithTwo" for a in acts)

        gs = {
            "handCards": hand,
            "curRank": "2",
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 3,
            "greaterAction": greater,
            "numofplayers": [15, 8, 12, 6],
            "publicInfo": [{"rest": 15}, {"rest": 8}, {"rest": 12}, {"rest": 6}],
            "_botzone_mode": True,
            "_role": "超强主攻",
        }
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, acts)
        assert act is not None
        assert act[0] != "PASS"
        assert act[0] in ("Bomb", "StraightFlush")
