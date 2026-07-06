# -*- coding: utf-8 -*-
"""GUA-115：残局 Q1 敌剩 4 张时火不打四（禁 Bomb/SF 压四张敌）。"""

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import (
    BAOSHU_RULE,
    EndgamePreprocessor,
    validate_q1_rule_table_consistency,
)

BOMB_8 = ["S8", "H8", "C8", "D8"]
TWT_6 = ["S6", "S6", "D6", "C8", "C8"]


def _anchor_step51_state(*, action_list, hand_cards, numofplayers):
    return {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 3,
        "greaterAction": ["ThreeWithTwo", "6", TWT_6],
        "handCards": list(hand_cards),
        "actionList": action_list,
        "curRank": "A",
        "selfRank": "9",
        "oppoRank": "A",
        "numofplayers": numofplayers,
        "_role": "主攻",
    }


class TestGua115FireNoBombFour:
    """锚点：20260703214948445203 副 28 步 51/75。"""

    def test_q1_passes_when_enemy_four_cards_and_only_bomb_can_beat(self):
        """敌 rem=4、跟压 TWT/6、仅 Bomb 可压 → PASS。"""
        hand_cards = BOMB_8 + ["S3", "H4", "C5", "D5", "S7", "H7", "C9"]
        gs = _anchor_step51_state(
            hand_cards=hand_cards,
            numofplayers=[13, 6, 10, 4],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["Bomb", "8", BOMB_8],
            ],
        )

        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])

        assert idx == 0
        assert act[0] == "PASS"

    def test_q1_still_blocks_with_non_bomb_when_available(self):
        """有非 bomb-like 可压候选时，仍走正常 Q1（Bomb 经 BAOSHU never_play 被禁）。"""
        hand_cards = ["ST", "HT", "DT", "S3", "H3"] + BOMB_8 + ["S7", "H7", "C9"]
        twt_k = ["ST", "HT", "DT", "S3", "H3"]
        gs = _anchor_step51_state(
            hand_cards=hand_cards,
            numofplayers=[13, 6, 10, 4],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["ThreeWithTwo", "T", twt_k],
                ["Bomb", "8", BOMB_8],
            ],
        )

        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])

        assert idx == 1
        assert act[0] == "ThreeWithTwo"

    def test_baoshu_rule_four_bomb_in_never_play_not_block_with(self):
        """BAOSHU_RULE[4]：Bomb/SF 在 never_play，不在 block_with。"""
        likely, block_with, never_play = BAOSHU_RULE[4]
        assert likely == "炸弹/四张"
        assert "Bomb" not in block_with
        assert "Bomb" in never_play
        assert "StraightFlush" in never_play
        assert validate_q1_rule_table_consistency() == []

    def test_preprocess_baoshu_four_includes_bomb_never_play(self):
        """预处理：敌 rem=4 时 baoshu.never_play 含 Bomb。"""
        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 3,
            "greaterAction": ["ThreeWithTwo", "6", TWT_6],
            "handCards": BOMB_8,
            "actionList": [["PASS", "PASS", "PASS"], ["Bomb", "8", BOMB_8]],
            "curRank": "A",
            "numofplayers": [4, 8, 10, 4],
        }
        EndgamePreprocessor().preprocess(gs)
        enemy_ctx = gs["_endgame_context"]["enemies"][3]
        baoshu = enemy_ctx["baoshu"]
        assert "Bomb" in baoshu["never_play"]
        assert "StraightFlush" in baoshu["never_play"]
        assert "Bomb" not in baoshu["block_with"]
