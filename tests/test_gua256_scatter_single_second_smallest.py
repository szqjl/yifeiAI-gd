# -*- coding: utf-8 -*-
"""GUA-256：Q1 压单时，手牌有 ≥2 个可压普通散单（非级牌）且无炸弹 →
出「倒数第二小」的散单，不用级牌大单拦。

match 6a869e90（logs/v8_vs_botzone_20260820_142630.log L108-115，第46回合）：
V8=player0 手牌 6 = 散单 D8/CJ/DQ/C2 + 对子 SA/HA，greater=Single/7，无炸弹。
修复前 Q1 出 `Single/C2`（级牌），用户判定应出倒数第二小的散单 CJ。
"""

import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker


def _build_gs(hand_cards, cur_rank, greater, group_members, group_type_map, enemies):
    my_pos = 0
    tracker = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand_cards)
    tracker.set_level_rank(cur_rank)
    counts = {0: len(hand_cards)}
    for pos, rem in enemies.items():
        counts[pos] = rem
    counts.setdefault(2, 8)  # 队友手牌计数
    tracker.hand_counts = counts

    gs = {
        "myPos": my_pos,
        "curPos": 3,
        "greaterPos": 3,
        "greaterAction": greater,
        "handCards": list(hand_cards),
        "curRank": cur_rank,
        "selfRank": cur_rank,
        "oppoRank": "K",
        "numofplayers": [counts.get(p, 20) for p in range(4)],
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": counts,
            "opp_bomb_risks": {p: 1.0 for p in enemies},
        },
        "_role": "主攻",
    }
    EndgamePreprocessor().preprocess(gs)
    gs["_group_members"] = group_members
    gs["_group_gid_type_map"] = group_type_map
    return gs


class TestGua256ScatterSingleSecondSmallestUnit:
    def test_picks_second_smallest_scatter_single(self):
        """手牌 D8/CJ/DQ/C2 散单 + SA/HA 对子，压 Single/7 → 选 CJ（倒数第二小）。"""
        hand = ["D8", "CJ", "DQ", "C2", "SA", "HA"]
        gs = _build_gs(
            hand, "2",
            ["Single", "7", ["S7"]],
            {-1: ["D8", "CJ", "DQ", "C2"], 0: ["SA", "HA"]},
            {-1: "scatter", 0: "pair"},
            {1: 5, 3: 9},
        )
        candidates = [
            (0, ["PASS", "PASS", "PASS"]),
            (1, ["Single", "8", ["D8"]]),
            (2, ["Single", "J", ["CJ"]]),
            (3, ["Single", "Q", ["DQ"]]),
            (4, ["Single", "2", ["C2"]]),
            (5, ["Single", "A", ["SA"]]),
            (6, ["Single", "A", ["HA"]]),
        ]
        ec = {"enemies": {1: {"remaining": 5}, 3: {"remaining": 9}}, "my_pos": 0}
        res = EndgameDecider()._q1_scatter_single_second_smallest_press(
            gs, candidates, ec, 1, {"remaining": 5, "recommended_types": ["Single"]},
        )
        assert res is not None
        assert res[1] == ["Single", "J", ["CJ"]]

    def test_none_when_no_bomb_but_single_scatter_can_press(self):
        """可压散单只有 1 张时（D8），不触发（需 ≥2 个）。"""
        hand = ["D8", "C2", "SA", "HA"]
        gs = _build_gs(
            hand, "2",
            ["Single", "7", ["S7"]],
            {-1: ["D8", "C2"], 0: ["SA", "HA"]},
            {-1: "scatter", 0: "pair"},
            {1: 5, 3: 9},
        )
        candidates = [
            (0, ["PASS", "PASS", "PASS"]),
            (1, ["Single", "8", ["D8"]]),
            (2, ["Single", "2", ["C2"]]),
            (3, ["Single", "A", ["SA"]]),
            (4, ["Single", "A", ["HA"]]),
        ]
        ec = {"enemies": {1: {"remaining": 5}, 3: {"remaining": 9}}, "my_pos": 0}
        res = EndgameDecider()._q1_scatter_single_second_smallest_press(
            gs, candidates, ec, 1, {"remaining": 5, "recommended_types": ["Single"]},
        )
        assert res is None

    def test_none_when_greater_not_single(self):
        """greater 不是 Single 不触发。"""
        hand = ["D8", "CJ", "DQ", "C2", "SA", "HA"]
        gs = _build_gs(
            hand, "2",
            ["Pair", "7", ["S7", "H7"]],
            {-1: ["D8", "CJ", "DQ", "C2"], 0: ["SA", "HA"]},
            {-1: "scatter", 0: "pair"},
            {1: 5, 3: 9},
        )
        candidates = [
            (0, ["PASS", "PASS", "PASS"]),
            (1, ["Single", "8", ["D8"]]),
            (2, ["Single", "J", ["CJ"]]),
            (3, ["Single", "Q", ["DQ"]]),
            (4, ["Single", "2", ["C2"]]),
        ]
        ec = {"enemies": {1: {"remaining": 5}, 3: {"remaining": 9}}, "my_pos": 0}
        res = EndgameDecider()._q1_scatter_single_second_smallest_press(
            gs, candidates, ec, 1, {"remaining": 5, "recommended_types": ["Single"]},
        )
        assert res is None


class TestGua256EndgameDecideIntegration:
    def test_round46_match_6a869e90_press_single7_plays_cj(self):
        """复现 match 6a869e90 第46回合：压 Single/7 应出 CJ 而非 C2。"""
        hand = ["D8", "CJ", "DQ", "C2", "SA", "HA"]
        gs = _build_gs(
            hand, "2",
            ["Single", "7", ["S7"]],
            {-1: ["D8", "CJ", "DQ", "C2"], 0: ["SA", "HA"]},
            {-1: "scatter", 0: "pair"},
            {1: 5, 3: 9},
        )
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Single", "8", ["D8"]],
            ["Single", "J", ["CJ"]],
            ["Single", "Q", ["DQ"]],
            ["Single", "2", ["C2"]],
            ["Single", "A", ["SA"]],
            ["Single", "A", ["HA"]],
        ]
        gs["actionList"] = action_list
        decider = EndgameDecider()
        filtered, banned_empty = decider.apply_banned_filter(action_list, gs)
        idx, act = decider.decide(gs, action_list if banned_empty else filtered)
        assert act == ["Single", "J", ["CJ"]]