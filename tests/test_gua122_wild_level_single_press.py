# -*- coding: utf-8 -*-
"""GUA-122：残局 Q1 压级牌单张时，有非逢人配同级牌则不得裸出 H{curRank}。"""

import pytest

from src.v.nn.endgame.endgame_decide import (
    EndgameDecider,
    _sort_q1_block_candidates,
    _sort_q1_prefer_non_wild_level_singles,
)
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker


def _wild(cur_rank: str) -> str:
    return f"H{cur_rank}"


def _level_card(suit: str, cur_rank: str) -> str:
    return f"{suit}{cur_rank}"


class TestGua122WildLevelSingleSort:
    @pytest.mark.parametrize("cur_rank", ["5", "8", "Q", "K"])
    def test_prefers_non_wild_level_single_over_wild(self, cur_rank: str):
        wild = _wild(cur_rank)
        plain = _level_card("C", cur_rank)
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Single", cur_rank, [wild]],
            ["Single", cur_rank, [plain]],
        ]
        cands = [(i, a) for i, a in enumerate(action_list) if a[0] != "PASS"]
        hand = [wild, plain, "S3", "H4"]
        gs = {"curRank": cur_rank, "greaterAction": ["Single", "J", ["HJ"]]}
        ordered = _sort_q1_block_candidates(cands, hand, gs)
        assert ordered[0][1][2] == [plain]

    def test_only_wild_level_single_still_usable(self):
        cur_rank = "7"
        wild = _wild(cur_rank)
        cands = [(1, ["Single", cur_rank, [wild]])]
        ordered = _sort_q1_prefer_non_wild_level_singles(cands, cur_rank)
        assert ordered[0][1][2] == [wild]

    def test_non_level_rank_singles_unaffected(self):
        cur_rank = "8"
        cands = [
            (1, ["Single", "9", ["S9"]]),
            (2, ["Single", "T", ["ST"]]),
        ]
        ordered = _sort_q1_prefer_non_wild_level_singles(cands, cur_rank)
        assert [i for i, _ in ordered] == [1, 2]


class TestGua122EndgameDecideIntegration:
    def _run_q1_single_press(
        self,
        *,
        cur_rank: str,
        hand_cards,
        action_list,
        greater_action,
        enemy_rem: int,
    ):
        tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand(hand_cards)
        tracker.set_level_rank(cur_rank)
        tracker.hand_counts = {0: 14, 1: enemy_rem, 2: len(hand_cards), 3: 20}

        gs = {
            "myPos": 2,
            "curPos": 1,
            "greaterPos": 1,
            "greaterAction": greater_action,
            "handCards": list(hand_cards),
            "actionList": action_list,
            "curRank": cur_rank,
            "selfRank": cur_rank,
            "oppoRank": "K",
            "numofplayers": [14, enemy_rem, len(hand_cards), 20],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 14, 1: enemy_rem, 2: len(hand_cards), 3: 20},
                "opp_bomb_risks": {1: 1.0, 3: 0.0},
            },
            "_role": "主攻",
        }
        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        return decider.decide(gs, gs["actionList"] if banned_empty else filtered)

    def test_wf12_anchor_84441454613_step39(self):
        """WF-12 84441445615 副38 步39：curRank=Q 压 K 应出 CQ 非 HQ。"""
        cur_rank = "Q"
        hand_cards = [
            "H4", "S5", "S5", "S6", "H6", "S7", "D7", "D7",
            "S9", "ST", "SJ", "HA", "DA", "HQ", "CQ",
        ]
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Single", "A", ["HA"]],
            ["Single", "A", ["DA"]],
            ["Single", cur_rank, ["HQ"]],
            ["Single", cur_rank, ["CQ"]],
            ["Bomb", "7", ["S7", "D7", "D7", "HQ"]],
        ]
        idx, act = self._run_q1_single_press(
            cur_rank=cur_rank,
            hand_cards=hand_cards,
            action_list=action_list,
            greater_action=["Single", "K", ["CK"]],
            enemy_rem=2,
        )
        assert idx == 4
        assert act == ["Single", cur_rank, ["CQ"]]

    def test_cur_rank_k_press_single_q(self):
        cur_rank = "K"
        hand_cards = ["HK", "SK", "S4", "H5"]
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Single", cur_rank, ["HK"]],
            ["Single", cur_rank, ["SK"]],
        ]
        idx, act = self._run_q1_single_press(
            cur_rank=cur_rank,
            hand_cards=hand_cards,
            action_list=action_list,
            greater_action=["Single", "Q", ["CQ"]],
            enemy_rem=3,
        )
        assert idx == 2
        assert act == ["Single", cur_rank, ["SK"]]
