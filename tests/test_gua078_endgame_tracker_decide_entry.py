# -*- coding: utf-8 -*-
"""GUA-078：MemoryTracker 在 decide() 入口就绪，残局 Q1 可封锁报单炸。

设计真源：``docs/knowledge/skills/07_opening/end position.md`` §二 / §3.3 / §1.20
回放：``20260621204653147750`` 步62 yf1@0 有 K 炸 + @1 rest=1 → Q1 Bomb K。
"""
import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor, endgame_rule
from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

# 回放 20260621204653147750 步62：yf1@0 反推手牌（restCards + 步67/70 出牌）
YF1_HAND_STEP62 = [
    "C3", "C5", "CK", "CK", "D6", "H4", "HK", "S5", "S6", "S6", "S7", "S7", "S8", "SK",
]

BOMB_10 = ["ST", "CT", "DT", "DT"]
BOMB_K = ["SK", "HK", "CK", "CK"]
BOMB_4 = ["S4", "S4", "H4", "C4"]
BOMB_6 = ["S6", "H6", "C6", "D6"]

YF1_HAND_ENEMY5 = [
    "S3", "C3", "S4", "S4", "H4", "C4", "H7", "C7",
    "S8", "H8", "HT", "CT", "HQ", "HQ", "CQ", "SK", "H2",
]

YF1_HAND_TEAMMATE_CONTROL = [
    "S5", "H5", "C5", "D5", "S7", "H7", "C9", "D9",
    "SJ", "HJ", "CQ", "DQ", "SK", "DK", "SA", "CA",
]

Q1_RULE_HAND = ["S4", "H4", "S8", "H8", "SK", "H2", "C3", "D5"]
YF1_HAND_ENEMY2_LEAD = ["S4", "C5", "C6", "S7", "H7", "H7", "S3", "S3", "C3", "HR"]


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

    def test_upper_enemy_remaining_5_prefers_single_cover_when_teammate_not_strong(self):
        """上家剩 5 张出单时，若队友牌力不强，Q1 应保留单压而非直接炸。"""
        tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand(YF1_HAND_ENEMY5)
        tracker.set_level_rank("2")
        tracker.hand_counts = {0: 17, 1: 9, 2: 22, 3: 5}

        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 3,  # 上家
            "greaterAction": ["Single", "8", ["C8"]],
            "handCards": list(YF1_HAND_ENEMY5),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Single", "K", ["SK"]],
                ["Bomb", "4", list(BOMB_4)],
            ],
            "curRank": "2",
            "selfRank": "2",
            "oppoRank": "2",
            "numofplayers": [17, 9, 22, 5],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 17, 1: 9, 2: 22, 3: 5},
                "opp_bomb_risks": {1: 1.0, 3: 1.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx is not None
        assert act[0] == "Single"
        assert act[1] == "K"
        assert act[2] == ["SK"]

    def test_lower_enemy_remaining_5_keeps_bomb_when_teammate_strong_and_shape_unknown(self):
        """下家剩 5 张时，若无法明确推断且队友牌力偏强，可保留炸弹。"""
        tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand(YF1_HAND_ENEMY5)
        tracker.set_level_rank("2")
        tracker.hand_counts = {0: 17, 1: 5, 2: 6, 3: 22}

        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 1,  # 下家
            "greaterAction": ["Single", "8", ["C8"]],
            "handCards": list(YF1_HAND_ENEMY5),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Single", "K", ["SK"]],
                ["Bomb", "4", list(BOMB_4)],
            ],
            "curRank": "2",
            "selfRank": "2",
            "oppoRank": "2",
            "numofplayers": [17, 5, 6, 22],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 17, 1: 5, 2: 6, 3: 22},
                "opp_bomb_risks": {1: 1.0, 3: 1.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx is not None
        assert act[0] == "Bomb"
        assert act[1] == "4"
        assert sorted(act[2]) == sorted(BOMB_4)

    @pytest.mark.parametrize(
        ("greater_action", "cur_rank", "prepare_tracker"),
        [
            (
                ["Bomb", "4", list(BOMB_4)],
                "2",
                lambda tracker: None,
            ),
            (
                ["Single", "5", ["H5"]],
                "5",
                lambda tracker: (
                    tracker.card_state.__setitem__("HR", [tracker.PLAYED, tracker.PLAYED]),
                    tracker.card_state.__setitem__("SB", [tracker.PLAYED, tracker.PLAYED]),
                ),
            ),
        ],
    )
    def test_q1_passes_when_teammate_control_is_already_max(
        self, greater_action, cur_rank, prepare_tracker,
    ):
        """队友已用炸弹或记忆可证实的最大同型控牌时，Q1 不应再兜底反压队友。"""
        tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand(YF1_HAND_TEAMMATE_CONTROL)
        tracker.set_level_rank(cur_rank)
        tracker.hand_counts = {0: 16, 1: 9, 2: 13, 3: 5}
        prepare_tracker(tracker)

        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 2,  # 队友控牌
            "greaterAction": greater_action,
            "handCards": list(YF1_HAND_TEAMMATE_CONTROL),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Bomb", "5", ["S5", "H5", "C5", "D5"]],
            ],
            "curRank": cur_rank,
            "selfRank": cur_rank,
            "oppoRank": cur_rank,
            "numofplayers": [16, 9, 13, 5],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 16, 1: 9, 2: 13, 3: 5},
                "opp_bomb_risks": {1: 1.0, 3: 1.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx is not None
        assert act[0] == "PASS"

    @pytest.mark.parametrize(
        ("greater_action", "cur_rank", "action_list"),
        [
            (
                ["Bomb", "4", list(BOMB_4)],
                "2",
                [
                    ["PASS", "PASS", "PASS"],
                    ["StraightFlush", "3", ["D3", "D4", "D5", "D6", "D7"]],
                    ["Bomb", "5", ["S5", "H5", "C5", "D5"]],
                ],
            ),
            (
                ["Bomb", "6", list(BOMB_6) + ["H3"]],
                "3",
                [
                    ["PASS", "PASS", "PASS"],
                    ["StraightFlush", "3", ["D3", "D4", "D5", "D6", "D7"]],
                    ["Bomb", "8", ["S8", "H8", "C8", "D8"]],
                ],
            ),
        ],
    )
    def test_q1_does_not_bomb_overcall_when_teammate_already_controls(
        self, greater_action, cur_rank, action_list,
    ):
        """队友已控牌时，Q1 不得再用同花顺/更大炸反压队友。"""
        tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
        hand_cards = [
            "D3", "D4", "D5", "D6", "D7",
            "S5", "H5", "C5", "D5",
            "S8", "H8", "C8", "D8",
            "SK", "SA", "CA", "H3",
        ]
        tracker.init_from_hand(hand_cards)
        tracker.set_level_rank(cur_rank)
        tracker.hand_counts = {0: 17, 1: 1, 2: 13, 3: 6}

        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 2,
            "greaterAction": greater_action,
            "handCards": list(hand_cards),
            "actionList": action_list,
            "curRank": cur_rank,
            "selfRank": cur_rank,
            "oppoRank": cur_rank,
            "numofplayers": [17, 1, 13, 6],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 17, 1: 1, 2: 13, 3: 6},
                "opp_bomb_risks": {1: 1.0, 3: 1.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx is not None
        assert act[0] == "PASS"

    def test_q1_enemy_remaining_2_lead_prefers_locking_structure_over_single(self):
        """敌方剩 2 张且我方领牌时，有顺子可直接锁死跟牌窗口，不应先领单。"""
        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": list(YF1_HAND_ENEMY2_LEAD),
            "actionList": [
                ["Single", "4", ["S4"]],
                ["Single", "R", ["HR"]],
                ["Trips", "3", ["S3", "S3", "C3"]],
                ["Pair", "7", ["H7", "H7"]],
                ["Straight", "3", ["S3", "S4", "C5", "C6", "S7"]],
            ],
            "curRank": "3",
            "selfRank": "2",
            "oppoRank": "3",
            "numofplayers": [10, 2, 12, 9],
            "_belief": {
                "hand_counts": {0: 10, 1: 2, 2: 12, 3: 9},
                "opp_bomb_risks": {1: 0.0, 3: 0.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx is not None
        assert act[0] == "Straight"
        assert act[2] == ["S3", "S4", "C5", "C6", "S7"]

    def test_q1_teammate_single_control_without_safe_overcall_passes_instead_of_breaking_pair(self):
        """队友领单、关键敌方后手剩 2 张时，若我方无安全单，不应拆对反超队友。"""
        gs = {
            "myPos": 2,
            "curPos": 0,
            "greaterPos": 0,
            "greaterAction": ["Single", "4", ["S4"]],
            "handCards": ["S7", "D7", "C8", "CQ"],
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Single", "7", ["S7"]],
                ["Single", "8", ["C8"]],
                ["Single", "Q", ["CQ"]],
            ],
            "curRank": "3",
            "selfRank": "2",
            "oppoRank": "3",
            "numofplayers": [12, 0, 4, 2],
            "_belief": {
                "hand_counts": {0: 12, 1: 0, 2: 4, 3: 2},
                "opp_bomb_risks": {1: 0.0, 3: 0.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx is not None
        assert act[0] == "PASS"

    def test_q1_teammate_single_control_uses_only_safe_single_overcall_when_enemy_rest_1(self):
        """关键敌方只剩 1 张时，若必须反超队友，只能出当前外部无压制的安全单。"""
        tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand(["D7", "C8", "CQ"])
        tracker.set_level_rank("3")
        tracker.hand_counts = {0: 1, 1: 0, 2: 3, 3: 1}

        for rank in ("3", "K", "A"):
            for suit in ("S", "H", "D", "C"):
                tracker.card_state[f"{suit}{rank}"] = [tracker.PLAYED, tracker.PLAYED]
        tracker.card_state["SB"] = [tracker.PLAYED, tracker.PLAYED]
        tracker.card_state["HR"] = [tracker.PLAYED, tracker.PLAYED]

        gs = {
            "myPos": 2,
            "curPos": 0,
            "greaterPos": 0,
            "greaterAction": ["Single", "5", ["C5"]],
            "handCards": ["D7", "C8", "CQ"],
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Single", "7", ["D7"]],
                ["Single", "8", ["C8"]],
                ["Single", "Q", ["CQ"]],
            ],
            "curRank": "3",
            "selfRank": "2",
            "oppoRank": "3",
            "numofplayers": [1, 0, 3, 1],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 1, 1: 0, 2: 3, 3: 1},
                "opp_bomb_risks": {1: 0.0, 3: 0.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx is not None
        assert act[0] == "Single"
        assert act[1] == "Q"
        assert act[2] == ["CQ"]

    def test_q1_does_not_pass_when_enemy_is_one_card_from_going_out_and_pair_can_cover(self):
        """回放锚点：对手剩 1 张且我有可压对子时，残局 Q1 不应把 PASS 排到前面。"""
        tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
        hand_cards = ["C6", "D6", "S7", "H7", "S8", "S9", "CT", "CJ", "SQ", "SK", "S2", "H2"]
        tracker.init_from_hand(hand_cards)
        tracker.set_level_rank("2")
        tracker.hand_counts = {0: 11, 1: 7, 2: 12, 3: 1}

        gs = {
            "myPos": 2,
            "curPos": 1,
            "greaterPos": 3,
            "greaterAction": ["Pair", "T", ["DT", "DT"]],
            "handCards": list(hand_cards),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Pair", "J", ["CJ", "H2"]],
                ["Pair", "Q", ["SQ", "H2"]],
                ["Pair", "K", ["SK", "H2"]],
                ["Pair", "2", ["S2", "H2"]],
            ],
            "curRank": "2",
            "selfRank": "2",
            "oppoRank": "2",
            "numofplayers": [11, 7, 12, 1],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 11, 1: 7, 2: 12, 3: 1},
                "opp_bomb_risks": {1: 1.0, 3: 1.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx is not None
        assert act[0] == "Pair"
        assert act != ["PASS", "PASS", "PASS"]

    def test_q1_prefers_min_sufficient_bomb_over_upgrading_four_bomb_to_five_bomb(self):
        """对方非炸牌型且任意炸可压时，Q1 应优先最小足够炸，禁止无收益 4 炸升 5 炸。"""
        tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
        hand_cards = list(BOMB_6) + ["H3", "S8", "H8", "CQ", "DK", "SA"]
        tracker.init_from_hand(hand_cards)
        tracker.set_level_rank("3")
        tracker.hand_counts = {0: 7, 1: 1, 2: 10, 3: 8}

        gs = {
            "myPos": 2,
            "curPos": 1,
            "greaterPos": 1,
            # 用 Pair 控牌测 GUA-103 最小足够炸；ThreeWithTwo 会先被 GUA-135 截走
            "greaterAction": ["Pair", "K", ["SK", "HK"]],
            "handCards": list(hand_cards),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Bomb", "6", list(BOMB_6)],
                ["Bomb", "6", list(BOMB_6) + ["H3"]],
            ],
            "curRank": "3",
            "selfRank": "3",
            "oppoRank": "3",
            "numofplayers": [7, 1, 10, 8],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 7, 1: 1, 2: 10, 3: 8},
                "opp_bomb_risks": {1: 1.0, 3: 1.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx is not None
        assert act[0] == "Bomb"
        assert sorted(act[2]) == sorted(BOMB_6)

    def test_q1_prefers_full_five_bomb_over_four_bomb_leaving_orphan_when_beating_pair(
        self,
    ):
        """WF-12 48445203 步58：压 Pair/9 时不得拆五星炸留单 5。"""
        from src.v.nn.endgame.endgame_decide import _sort_q1_block_candidates

        hand_cards = [
            "H2", "D2", "C4", "C4", "S5", "H5", "H5", "C5", "D5",
            "S7", "C7", "D7", "S9", "H9", "C9", "ST", "CJ", "DQ", "SK", "DA",
        ]
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Bomb", "5", ["S5", "H5", "H5", "D5"]],
            ["Bomb", "5", ["S5", "H5", "H5", "C5"]],
            ["Bomb", "5", ["S5", "H5", "C5", "D5"]],
            ["Bomb", "5", ["H5", "H5", "C5", "D5"]],
            ["Bomb", "5", ["S5", "H5", "H5", "C5", "D5"]],
        ]
        cands = [(i, a) for i, a in enumerate(action_list) if a[0] != "PASS"]
        gs = {
            "curRank": "A",
            "greaterAction": ["Pair", "9", ["C9", "D9"]],
        }
        ordered = _sort_q1_block_candidates(cands, hand_cards, gs)
        assert ordered[0][0] == 5
        assert len(ordered[0][1][2]) == 5

        tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand(hand_cards)
        tracker.set_level_rank("A")
        tracker.hand_counts = {0: 10, 1: 11, 2: 20, 3: 8}

        gs_full = {
            "myPos": 2,
            "curPos": 2,
            "greaterPos": 1,
            "greaterAction": ["Pair", "9", ["C9", "D9"]],
            "handCards": list(hand_cards),
            "actionList": action_list,
            "curRank": "A",
            "selfRank": "A",
            "oppoRank": "A",
            "numofplayers": [10, 11, 20, 8],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 10, 1: 11, 2: 20, 3: 8},
                "opp_bomb_risks": {1: 0.3, 3: 0.2},
            },
        }
        EndgamePreprocessor().preprocess(gs_full)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs_full["actionList"], gs_full)
        idx, act = decider.decide(
            gs_full, gs_full["actionList"] if banned_empty else filtered
        )
        assert idx == 5
        assert act[0] == "Bomb"
        assert sorted(act[2]) == sorted(["S5", "H5", "H5", "C5", "D5"])

    def test_q1_prefers_pure_five_bomb_over_six_bomb_with_wild_when_beating_four_bomb(self):
        """对方也是炸弹时，Q1 仍应最小足够炸，禁止把纯 5 星炸无收益升成 6 星炸。"""
        tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
        hand_cards = [
            "D2", "S5", "H5", "H5", "C5", "C5", "S7", "C7", "D7", "D7",
            "D8", "C9", "D9", "D9", "HT", "DJ", "SQ", "DQ", "DA", "HK",
        ]
        tracker.init_from_hand(hand_cards)
        tracker.set_level_rank("K")
        tracker.hand_counts = {0: 20, 1: 3, 2: 13, 3: 2}

        pure_five_bomb = ["S5", "H5", "H5", "C5", "C5"]
        six_bomb_with_wild = ["S5", "H5", "H5", "C5", "C5", "HK"]
        gs = {
            "myPos": 0,
            "curPos": 3,
            "greaterPos": 3,
            "greaterAction": ["Bomb", "Q", ["HQ", "HQ", "CQ", "DQ"]],
            "handCards": list(hand_cards),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Bomb", "5", ["S5", "H5", "H5", "C5", "HK"]],
                ["Bomb", "5", pure_five_bomb],
                ["Bomb", "5", ["S5", "H5", "C5", "C5", "HK"]],
                ["Bomb", "5", ["H5", "H5", "C5", "C5", "HK"]],
                ["Bomb", "7", ["S7", "C7", "D7", "D7", "HK"]],
                ["Bomb", "5", six_bomb_with_wild],
            ],
            "curRank": "K",
            "selfRank": "K",
            "oppoRank": "K",
            "numofplayers": [20, 3, 13, 2],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 20, 1: 3, 2: 13, 3: 2},
                "opp_bomb_risks": {1: 1.0, 3: 1.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx == 2
        assert act[0] == "Bomb"
        assert sorted(act[2]) == sorted(pure_five_bomb)
        assert "HK" not in act[2]

    @pytest.mark.parametrize(
        ("hand_cards", "action_list", "cur_rank", "prepare_tracker", "expected_type", "expected_rank"),
        [
            (
                ["SK", "SA", "SB", "H3", "C3", "D4", "C5", "C6", "S7"],
                [
                    ["Single", "K", ["SK"]],
                    ["Single", "A", ["SA"]],
                    ["Single", "B", ["SB"]],
                    ["Single", "3", ["H3"]],
                    ["Straight", "7", ["C3", "D4", "C5", "C6", "S7"]],
                ],
                "3",
                lambda tracker: tracker.card_state.__setitem__("HR", [tracker.PLAYED, tracker.PLAYED]),
                "Straight",
                "7",
            ),
            (
                ["SK", "SA", "SB", "H3"],
                [
                    ["Single", "K", ["SK"]],
                    ["Single", "A", ["SA"]],
                    ["Single", "B", ["SB"]],
                    ["Single", "3", ["H3"]],
                ],
                "3",
                lambda tracker: None,
                "Single",
                "B",
            ),
        ],
    )
    def test_q1_enemy_rest_one_lead_prefers_locking_structure_then_safe_or_strongest_single(
        self, hand_cards, action_list, cur_rank, prepare_tracker, expected_type, expected_rank,
    ):
        """敌方剩 1 张且我方领牌：先整牌锁敌；无整牌时再看安全单，仍无则不得退回去领 K。"""
        tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand(hand_cards)
        tracker.set_level_rank(cur_rank)
        tracker.hand_counts = {0: len(hand_cards), 1: 1, 2: 8, 3: 7}
        prepare_tracker(tracker)

        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 0,
            "greaterAction": ["StraightFlush", "3", ["D3", "D4", "D5", "D6", "D7"]],
            "handCards": list(hand_cards),
            "actionList": action_list,
            "curRank": cur_rank,
            "selfRank": cur_rank,
            "oppoRank": cur_rank,
            "numofplayers": [len(hand_cards), 1, 8, 7],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: len(hand_cards), 1: 1, 2: 8, 3: 7},
                "opp_bomb_risks": {1: 1.0, 3: 1.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx is not None
        assert act[0] == expected_type
        assert act[1] == expected_rank
        assert act != ["Single", "K", ["SK"]]

    @pytest.mark.parametrize("cur_pos", [0, -1])
    def test_q1_two_turn_sprint_lead_prefers_structured_finish_over_single_lead(self, cur_pos):
        """GUA-110：仅剩两手冲刺时，自由领出必须先出整牌，不得退回最大单张。"""
        hand_cards = ["S7", "C7", "HQ", "SK", "SK", "CK"]
        tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand(hand_cards)
        tracker.set_level_rank("A")
        tracker.hand_counts = {0: 6, 1: 1, 2: 2, 3: 7}

        gs = {
            "myPos": 0,
            "curPos": cur_pos,
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": list(hand_cards),
            "actionList": [
                ["Single", "Q", ["HQ"]],
                ["Pair", "7", ["S7", "C7"]],
                ["Trips", "K", ["SK", "SK", "CK"]],
                ["Single", "K", ["SK"]],
                ["ThreeWithTwo", "K", ["SK", "SK", "CK", "S7", "C7"]],
            ],
            "curRank": "A",
            "selfRank": "9",
            "oppoRank": "A",
            "numofplayers": [6, 1, 2, 7],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 6, 1: 1, 2: 2, 3: 7},
                "opp_bomb_risks": {1: 1.0, 3: 1.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx is not None
        assert act[0] == "ThreeWithTwo"
        assert act[1] == "K"
        assert act[2] == ["SK", "SK", "CK", "S7", "C7"]

    def test_q1_free_lead_prunes_risky_pair_lane_when_enemy_can_still_own_channel(self):
        """GUA-111：若队友无对子接力、敌方外部仍可能有更大对子，则 Q1 不得机械续出次级对子。"""
        hand_cards = ["S7", "C7", "HQ"]
        tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand(hand_cards)
        tracker.set_level_rank("A")
        tracker.hand_counts = {0: 3, 1: 0, 2: 2, 3: 5}

        high_ranks = {"8", "9", "T", "J", "Q", "K", "A"}
        for ct, copies in list(tracker.card_state.items()):
            rank = ct if ct in ("SB", "HR") else (ct[1:] if len(ct) >= 2 else ct)
            if rank not in high_ranks and ct not in ("SB", "HR"):
                continue
            if ct == "HQ":
                tracker.card_state[ct] = [tracker.MY_HAND, tracker.PLAYED]
                continue
            if ct == "S8":
                tracker.card_state[ct] = [3, 3]
                continue
            tracker.card_state[ct] = [tracker.PLAYED, tracker.PLAYED]

        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": list(hand_cards),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Single", "Q", ["HQ"]],
                ["Pair", "7", ["S7", "C7"]],
            ],
            "curRank": "A",
            "selfRank": "9",
            "oppoRank": "A",
            "numofplayers": [3, 0, 2, 5],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 3, 1: 0, 2: 2, 3: 5},
                "opp_bomb_risks": {1: 0.0, 3: 0.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert idx is not None
        assert act[0] == "Single"
        assert act[1] == "Q"
        assert ["Pair", "7", ["S7", "C7"]] in gs["actionList"]

    def test_q1_finish_now_prefers_trips_over_breaking_complete_hand(self):
        """GUA-112：手牌可被一个 Trips 候选完整覆盖时，不得先拆成单张。"""
        hand_cards = ["HJ", "DJ", "HA"]
        gs = {
            "myPos": 0,
            "curPos": -1,
            "greaterPos": -1,
            "greaterAction": ["PASS", "PASS", "PASS"],
            "handCards": list(hand_cards),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Single", "A", ["HA"]],
                ["Pair", "J", ["HJ", "DJ"]],
                ["Trips", "J", ["HJ", "DJ", "HA"]],
            ],
            "curRank": "A",
            "selfRank": "A",
            "oppoRank": "A",
            "numofplayers": [3, 1, 9, 8],
        }

        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])

        assert idx == 3
        assert act[0] == "Trips"
        assert sorted(act[2]) == sorted(hand_cards)

    def test_q1_finish_now_prefers_trips_over_pair_plus_single_split(self):
        """GUA-112：三张同点牌可一手清牌时，不得拆成 Pair + Single。"""
        hand_cards = ["S6", "C6", "D6"]
        gs = {
            "myPos": 0,
            "curPos": -1,
            "greaterPos": -1,
            "greaterAction": ["PASS", "PASS", "PASS"],
            "handCards": list(hand_cards),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Single", "6", ["S6"]],
                ["Pair", "6", ["S6", "C6"]],
                ["Trips", "6", ["S6", "C6", "D6"]],
            ],
            "curRank": "K",
            "selfRank": "K",
            "oppoRank": "K",
            "numofplayers": [3, 1, 9, 8],
        }

        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])

        assert idx == 3
        assert act[0] == "Trips"
        assert sorted(act[2]) == sorted(hand_cards)

    @pytest.mark.parametrize("remaining", [1, 2, 3, 4, 5, 6])
    def test_q1_endgame_rule_recommended_types_do_not_conflict_with_banned_types(self, remaining):
        """Q1 规则表自洽：recommended_types 映射出的动作类型不得再被同条 banned_types 禁掉。"""
        pre = EndgamePreprocessor()
        _, recommended_names, banned_types = endgame_rule[remaining]
        recommended_types = set(pre._map_types(recommended_names))

        assert recommended_types.isdisjoint(set(banned_types))

    @pytest.mark.parametrize("remaining", [1, 3, 5])
    def test_q1_banned_filter_keeps_single_candidates_when_rule_recommends_single(self, remaining):
        """remaining=1/3/5 时，若规则推荐单张，banned_filter 不得把合法 Single 全删掉。"""
        tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand(Q1_RULE_HAND)
        tracker.set_level_rank("2")
        tracker.hand_counts = {0: 8, 1: remaining, 2: 11, 3: 12}

        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 3,
            "greaterAction": ["Single", "7", ["C7"]],
            "handCards": list(Q1_RULE_HAND),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Single", "K", ["SK"]],
                ["Single", "2", ["H2"]],
                ["Pair", "4", ["S4", "H4"]],
            ],
            "curRank": "2",
            "selfRank": "2",
            "oppoRank": "2",
            "numofplayers": [8, remaining, 11, 12],
            "_memory_tracker": tracker,
            "_belief": {
                "hand_counts": {0: 8, 1: remaining, 2: 11, 3: 12},
                "opp_bomb_risks": {1: 1.0, 3: 1.0},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        filtered, banned_empty = EndgameDecider().apply_banned_filter(gs["actionList"], gs)

        single_types = [act for act in filtered if act[0] == "Single"]
        assert banned_empty is False
        assert single_types

    @pytest.mark.parametrize(
        ("numofplayers", "my_pos", "greater_pos", "greater_action", "action_list", "expected_type"),
        [
            (
                [6, 1, 1, 2],
                0,
                3,
                ["Pair", "Q", ["CQ", "DQ"]],
                [
                    ["PASS", "PASS", "PASS"],
                    ["Pair", "K", ["SK", "DK"]],
                ],
                "Pair",
            ),
            (
                [10, 3, 16, 0],
                0,
                1,
                ["Trips", "4", ["C4", "C4", "D4"]],
                [
                    ["PASS", "PASS", "PASS"],
                    ["Trips", "J", ["SJ", "CJ", "CJ"]],
                    ["Trips", "K", ["SK", "HK", "DK"]],
                ],
                "Trips",
            ),
            (
                [4, 3, 3, 2],
                0,
                3,
                ["Pair", "K", ["HK", "HK"]],
                [
                    ["PASS", "PASS", "PASS"],
                    ["Pair", "A", ["SA", "CA"]],
                ],
                "Pair",
            ),
            (
                [6, 1, 1, 6],
                2,
                3,
                ["Single", "2", ["D2"]],
                [
                    ["PASS", "PASS", "PASS"],
                    ["Single", "B", ["SB"]],
                ],
                "Single",
            ),
        ],
    )
    def test_q1_banned_filter_protects_main_target_recommended_and_current_greater_type(
        self, numofplayers, my_pos, greater_pos, greater_action, action_list, expected_type,
    ):
        """Q1 不应让 secondary enemy 的 banned 或当前残局表把主目标推荐型 / 当前同型控牌删到只剩 PASS。"""
        gs = {
            "myPos": my_pos,
            "curPos": greater_pos,
            "greaterPos": greater_pos,
            "greaterAction": greater_action,
            "handCards": ["SK", "DK", "SJ", "CJ", "CJ", "HK", "DK", "SB", "SA", "CA"],
            "actionList": action_list,
            "curRank": "2",
            "selfRank": "2",
            "oppoRank": "2",
            "numofplayers": numofplayers,
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
        idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

        assert banned_empty is False
        assert any(candidate[0] == expected_type for candidate in filtered)
        assert idx is not None
        assert act[0] == expected_type


class TestGua113AssistYieldToTeammateControl:
    """GUA-113：超弱/助攻在队友控牌时 Q1 必须 PASS，不得用结构牌反压队友。"""

    def test_q1_assist_role_passes_when_teammate_controls_three_with_two(self):
        """锚点：20260702195833037993 66/84 — 超弱不得用 KKK+66 压队友 T 三带二。"""
        hand_cards = ["C6", "D6", "H8", "D9", "ST", "DQ", "CK", "DK", "DK"]
        tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand(hand_cards)
        tracker.set_level_rank("3")
        tracker.hand_counts = {0: 9, 1: 12, 2: 8, 3: 10}

        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 2,
            "greaterAction": ["ThreeWithTwo", "T", ["HT", "HT", "DT", "HJ", "HJ"]],
            "handCards": list(hand_cards),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["ThreeWithTwo", "K", ["CK", "DK", "DK", "C6", "D6"]],
            ],
            "curRank": "3",
            "selfRank": "2",
            "oppoRank": "3",
            "numofplayers": [9, 12, 8, 10],
            "_memory_tracker": tracker,
            "_role": "超弱",
            "_belief": {
                "hand_counts": {0: 9, 1: 12, 2: 8, 3: 10},
                "opp_bomb_risks": {1: 0.5, 3: 0.5},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        idx, act = decider.decide(gs, gs["actionList"])

        assert idx == 0
        assert act[0] == "PASS"

    def test_q1_main_attack_may_still_press_when_enemy_can_suppress_teammate(self):
        """主攻在同圈况下仍可帮挡（记牌推断敌或可压队友 T 三带二）。"""
        hand_cards = ["C6", "D6", "H8", "D9", "ST", "DQ", "CK", "DK", "DK"]
        tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
        tracker.init_from_hand(hand_cards)
        tracker.set_level_rank("3")
        tracker.hand_counts = {0: 9, 1: 12, 2: 8, 3: 10}

        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 2,
            "greaterAction": ["ThreeWithTwo", "T", ["HT", "HT", "DT", "HJ", "HJ"]],
            "handCards": list(hand_cards),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["ThreeWithTwo", "K", ["CK", "DK", "DK", "C6", "D6"]],
            ],
            "curRank": "3",
            "selfRank": "2",
            "oppoRank": "3",
            "numofplayers": [9, 12, 8, 10],
            "_memory_tracker": tracker,
            "_role": "主攻",
            "_belief": {
                "hand_counts": {0: 9, 1: 12, 2: 8, 3: 10},
                "opp_bomb_risks": {1: 0.5, 3: 0.5},
            },
        }

        EndgamePreprocessor().preprocess(gs)
        decider = EndgameDecider()
        idx, act = decider.decide(gs, gs["actionList"])

        assert idx == 1
        assert act[0] == "ThreeWithTwo"
        assert act[1] == "K"


class TestQ0StraightFlushSprint:
    """Q0：StraightFlush 计入 bomb-like 资源 + 被动压炸两手冲刺。"""

    def test_has_bomb_recognizes_grouping_straight_flush_key(self):
        """组牌引擎 StraightFlush 计数应触发 should_sprint。"""
        gs = {
            "handCards": ["D9", "DJ", "CQ", "DQ", "DQ", "DK", "HA"],
            "curRank": "A",
            "myPos": 2,
            "numofplayers": [12, 1, 7, 12],
            "_group_type_map": {"StraightFlush": 1, "pair": 1},
        }
        EndgamePreprocessor().preprocess(gs)
        self_ctx = gs["_endgame_context"]["self"]
        assert self_ctx["has_two_clean_hands"] is True
        assert self_ctx["has_bomb"] is True
        assert self_ctx["should_sprint"] is True

    def test_q0_passive_sprint_prefers_straight_flush_over_star_bomb(self):
        """WF-12 84441894503 步45：SF+对子压敌8炸，应出 StraightFlush 而非 Q 星炸。"""
        hand = ["D9", "DJ", "CQ", "DQ", "DQ", "DK", "HA"]
        sf = ["StraightFlush", "9", ["D9", "DJ", "DQ", "DK", "HA"]]
        gs = {
            "myPos": 2,
            "curPos": 1,
            "greaterPos": 1,
            "greaterAction": ["Bomb", "8", ["S8", "H8", "C8", "D8"]],
            "handCards": list(hand),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                sf,
                ["Bomb", "Q", ["CQ", "DQ", "DQ", "HA"]],
            ],
            "curRank": "A",
            "selfRank": "A",
            "oppoRank": "A",
            "numofplayers": [12, 1, 7, 12],
            "_group_type_map": {"StraightFlush": 1, "pair": 1},
        }

        EndgamePreprocessor().preprocess(gs)
        assert gs["_endgame_context"]["self"]["should_sprint"] is True

        idx, act = EndgameDecider().decide(gs, gs["actionList"])

        assert idx == 1
        assert act[0] == "StraightFlush"
        assert sorted(act[2]) == sorted(sf[2])

    def test_action_beats_greater_straight_flush_beats_four_bomb(self):
        from src.v.nn.endgame.endgame_decide import _action_beats_greater

        sf = ["StraightFlush", "9", ["D9", "DJ", "DQ", "DK", "HA"]]
        bomb8 = ["Bomb", "8", ["S8", "H8", "C8", "D8"]]
        assert _action_beats_greater(sf, bomb8, "A") is True
        assert _action_beats_greater(bomb8, sf, "A") is False

    def test_semantic_hands_coalesce_steel_plate(self):
        """Bomb + 2×trip_in_steel_plate 语义手数=2，应触发 should_sprint。"""
        from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor

        gs = {
            "handCards": ["C4", "D4", "H4", "S4", "H7", "C7", "S7", "S8", "H8", "C8"],
            "curRank": "A",
            "myPos": 2,
            "numofplayers": [12, 9, 10, 12],
            "_group_type_map": {
                "Bomb": 1,
                "trip_in_steel_plate": 2,
            },
        }
        EndgamePreprocessor().preprocess(gs)
        self_ctx = gs["_endgame_context"]["self"]
        assert self_ctx["has_two_clean_hands"] is True
        assert self_ctx["has_bomb"] is True
        assert self_ctx["should_sprint"] is True

    def test_q0_lead_bomb_plus_steel_prefers_two_trips(self):
        """GUA-110/Q0：炸+钢板自由领出须整组 TwoTrips，不得 Trips/7。"""
        bomb = ["C4", "D4", "H4", "S4"]
        t7 = ["H7", "C7", "S7"]
        t8 = ["S8", "H8", "C8"]
        hand = bomb + t7 + t8
        gs = {
            "myPos": 2,
            "curPos": -1,
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": list(hand),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Trips", "7", t7],
                ["Trips", "8", t8],
                ["TwoTrips", "7", t7 + t8],
                ["Bomb", "4", bomb],
            ],
            "curRank": "A",
            "selfRank": "A",
            "oppoRank": "A",
            "numofplayers": [12, 9, 10, 12],
            "_group_type_map": {"Bomb": 1, "trip_in_steel_plate": 2},
        }
        EndgamePreprocessor().preprocess(gs)
        assert gs["_endgame_context"]["self"]["should_sprint"] is True

        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert idx is not None
        assert act[0] == "TwoTrips"
        assert set(act[2]) == set(t7 + t8)
