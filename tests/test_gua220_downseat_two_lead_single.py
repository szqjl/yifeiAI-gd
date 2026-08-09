# -*- coding: utf-8 -*-
"""GUA-220 下家剩 2 张时的残局领出策略（单先于对 / 送队友 TWT）。

场景（用户原始牌型）：1 号手牌 KKK,JJ,AA,2,H2,6（curRank=2，H2 配子），
KKK+H2 成隐式配子炸 Bomb/K。下家剩 2 张时，GUA-219 修复后 `_q1_enemy_critical_lead_special`
safe_structured 会领出 Pair/J——若下家是 Q 对子，可直接压 J 对子头游。

GUA-220 两级决策：
  Tier 1：下家剩 2 张 + 队友剩 5 张且前序打过 TWT → 优先不组炸弹送队友 TWT
          （豁免 _is_bomb_destroying_action，允许拆隐式配子炸）
  Tier 2：否则（无法判定队友 5 张为 TWT）→ 单先于对，领出能逼下家拆对的最小单张，
          且出后我方仍持有更大的非炸单张可回收（保证继续领出）。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import EndgameDecider


# 复现局手牌：K 炸族 {CK,DK,SK,H2} + 对J + 对A + 散牌（S2、S6）
HAND_REPRO = [
    "CK", "DK", "SK", "H2",
    "HJ", "DJ",
    "SA", "DA",
    "S2", "S6",
]

GROUP_MEMBERS = {
    0: ["CK", "DK", "SK", "H2"],   # G0(Bomb): 隐式配子炸（3K+H2）
    1: ["HJ", "DJ"],               # G1(pair)
    2: ["SA", "DA"],               # G2(pair)
    -1: ["S2", "S6"],              # 散牌
}

GROUP_GID_TYPE = {
    0: "Bomb",
    1: "pair",
    2: "pair",
    -1: "scatter",
}


class _FakeTracker:
    def __init__(self, play_history):
        self.play_history = play_history


def build_action_list():
    """复现局 actionList：单张 + 整牌 + 拆炸候选 + 完整 Bomb/K。"""
    return [
        ["PASS", "PASS", "PASS"],                       # 0
        ["Single", "6", ["S6"]],                        # 1: 最小安全单（不拆炸，可回收）
        ["Single", "2", ["S2"]],                        # 2: 级牌单
        ["Single", "J", ["HJ"]],                        # 3: 单 J（不拆炸）
        ["Single", "A", ["SA"]],                        # 4: 单 A（不拆炸）
        ["Single", "K", ["CK"]],                        # 5: 单 K → 拆隐式配子炸 K
        ["Pair", "J", ["HJ", "DJ"]],                    # 6: 对 J（不拆 K 炸）→ 修复前 GUA-219 会选它
        ["Pair", "A", ["SA", "DA"]],                    # 7: 对 A（不拆 K 炸）
        ["Pair", "K", ["CK", "DK"]],                    # 8: 拆 K 炸
        ["ThreeWithTwo", "K", ["CK", "DK", "SK", "S2", "S6"]],  # 9: TWT/K 拆 K 炸（送队友用）
        ["Trips", "K", ["CK", "DK", "SK"]],             # 10: 拆 K 炸
        ["Bomb", "K", ["CK", "DK", "SK", "H2"]],        # 11: 完整 Bomb/K
    ]


def build_state(teammate_remaining=9, teammate_close=False, tracker=None,
                down_remaining=2, cur_pos=0):
    """构造复现局：我方 0 自由领出，下家(1)剩 down_remaining 张，上家(3)剩 9 张。"""
    game_state = {
        "myPos": 0,
        "curPos": cur_pos,
        "greaterPos": -1,
        "greaterAction": [],
        "curRank": "2",
        "handCards": list(HAND_REPRO),
        "numofplayers": [len(HAND_REPRO), down_remaining, 5, 9],
        "_botzone_mode": True,
        "_group_members": dict(GROUP_MEMBERS),
        "_group_gid_type_map": dict(GROUP_GID_TYPE),
    }
    if tracker is not None:
        game_state["_memory_tracker"] = tracker
    ec = {
        "my_pos": 0,
        "cur_pos": cur_pos,
        "cur_rank": "2",
        "numofplayers": [len(HAND_REPRO), down_remaining, 5, 9],
        "enemies": {
            1: {
                "remaining": down_remaining,
                "danger_level": "极高",
                "recommended_types": ["最大单张"],
                "banned_types": [],
                "baoshu": {
                    "likely_hand": "单张(听牌)",
                    "block_with": ["ThreeWithTwo", "TwoTrips", "ThreePair", "Straight", "Bomb"],
                    "never_play": [],
                },
            },
            3: {"remaining": 9, "danger_level": "低", "recommended_types": [], "banned_types": [], "baoshu": {}},
        },
        "teammate": {
            "remaining": teammate_remaining,
            "is_close": teammate_close,
            "assist_prefer": [],
        },
        "self": {
            "remaining": len(HAND_REPRO),
            "has_two_clean_hands": False,
            "has_bomb": True,
            "should_sprint": False,
        },
        "finished": [],
    }
    return game_state, ec


def singles_of(actions):
    return [(i, a) for i, a in enumerate(actions) if a[0] == "Single"]


class TestGua220DownseatTwoSingleFirst:
    def test_single_first_picks_smallest_safe_6(self):
        """下家剩 2 张 → 单先于对，选最小不拆炸且可回收的单张 Single/6"""
        gs, ec = build_state(down_remaining=2)
        d = EndgameDecider()
        result = d._q1_downseat_two_single_first(singles_of(build_action_list()), gs, ec)
        assert result is not None
        idx, act = result
        assert act[0] == "Single", f"应出单张；实际出 {act}"
        assert act[1] == "6", f"应选最小安全单 Single/6；实际出 {act}"
        assert idx == 1

    def test_single_k_destroying_wild_bomb_excluded(self):
        """Single/K 用 K 族牌 → 拆隐式配子炸 → 被排除（不会选到）"""
        gs, ec = build_state(down_remaining=2)
        d = EndgameDecider()
        single_k = ["Single", "K", ["CK"]]
        assert d._is_bomb_destroying_action(single_k, HAND_REPRO, gs) is True
        result = d._q1_downseat_two_single_first(singles_of(build_action_list()), gs, ec)
        idx, act = result
        assert act[1] != "K", f"不应出拆炸单 K；实际出 {act}"

    def test_not_lead_turn_returns_none(self):
        """非我方领出轮 → 不触发"""
        gs, ec = build_state(down_remaining=2, cur_pos=1)
        d = EndgameDecider()
        assert d._q1_downseat_two_single_first(singles_of(build_action_list()), gs, ec) is None

    def test_downseat_not_two_returns_none(self):
        """下家非剩 2 张 → 不触发（剩 1 张报单走原整牌逻辑）"""
        gs, ec = build_state(down_remaining=1)
        d = EndgameDecider()
        assert d._q1_downseat_two_single_first(singles_of(build_action_list()), gs, ec) is None

    def test_no_recapture_returns_none(self):
        """出最小单后无更大非炸单张可回收 → 回退（避免把牌权白送）"""
        hand = ["S6", "CK", "DK", "SK", "H2"]  # 只有 6 + 配子炸 K 族
        gs = {
            "myPos": 0, "curPos": 0, "greaterPos": -1, "greaterAction": [],
            "curRank": "2", "handCards": list(hand),
            "numofplayers": [5, 2, 5, 9], "_botzone_mode": True,
            "_group_members": {0: ["CK", "DK", "SK", "H2"], -1: ["S6"]},
            "_group_gid_type_map": {0: "Bomb", -1: "scatter"},
        }
        ec = {
            "my_pos": 0, "cur_pos": 0, "cur_rank": "2",
            "enemies": {1: {"remaining": 2}, 3: {"remaining": 9}},
            "teammate": {"remaining": 5, "is_close": True, "assist_prefer": []},
        }
        d = EndgameDecider()
        act_list = [["Single", "6", ["S6"]], ["Single", "K", ["CK"]], ["Bomb", "K", hand]]
        result = d._q1_downseat_two_single_first(singles_of(act_list), gs, ec)
        assert result is None, f"无回收单应回退；实际返回 {result}"


class TestGua220FeedTeammateTWT:
    def _state(self, tracker):
        return build_state(
            teammate_remaining=5, teammate_close=True, tracker=tracker, down_remaining=2,
        )

    def test_feed_twt_when_teammate_five_and_played_twt(self):
        """队友剩 5 + 前序打过 TWT + 下家剩 2 → 送 TWT/K（豁免拆炸过滤）"""
        tracker = _FakeTracker([
            {"seat": 2, "action_type": "ThreeWithTwo", "cards": ["C8", "H8", "D8", "S9", "D9"]},
        ])
        gs, ec = self._state(tracker)
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(build_action_list())]
        result = d._q1_feed_teammate_twt_when_downseat_two(gs, candidates, ec)
        assert result is not None
        idx, act = result
        assert act[0] == "ThreeWithTwo", f"应送 TWT；实际出 {act}"
        # TWT/K 用 K 族牌拆 Bomb/K，但本特判豁免（「不组炸弹送队友」之意）
        assert d._is_bomb_destroying_action(act, HAND_REPRO, gs) is True, "TWT/K 应拆 K 炸但被豁免送牌"

    def test_no_twt_history_returns_none(self):
        """队友无前序 TWT 记忆 → 无法判定 5 张为 TWT → 回退（交给 Tier 2 单先于对）"""
        tracker = _FakeTracker([
            {"seat": 2, "action_type": "Pair", "cards": ["C8", "H8"]},
        ])
        gs, ec = self._state(tracker)
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(build_action_list())]
        assert d._q1_feed_teammate_twt_when_downseat_two(gs, candidates, ec) is None

    def test_teammate_not_close_returns_none(self):
        """队友非 close（非 5 张）→ 不触发"""
        gs, ec = build_state(
            teammate_remaining=9, teammate_close=False, down_remaining=2,
            tracker=_FakeTracker([{"seat": 2, "action_type": "ThreeWithTwo", "cards": []}]),
        )
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(build_action_list())]
        assert d._q1_feed_teammate_twt_when_downseat_two(gs, candidates, ec) is None

    def test_downseat_not_two_returns_none(self):
        """下家非剩 2 张 → 不触发"""
        tracker = _FakeTracker([
            {"seat": 2, "action_type": "ThreeWithTwo", "cards": ["C8", "H8", "D8", "S9", "D9"]},
        ])
        gs, ec = build_state(
            teammate_remaining=5, teammate_close=True, tracker=tracker, down_remaining=3,
        )
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(build_action_list())]
        assert d._q1_feed_teammate_twt_when_downseat_two(gs, candidates, ec) is None


class TestGua220EndToEnd:
    def test_q1_block_enemy_downseat_two_leads_single(self):
        """端到端 `_q1_block_enemy`：下家剩 2 张领出 → 出单（非 Pair/J）"""
        gs, ec = build_state(down_remaining=2)
        d = EndgameDecider()
        action_list = build_action_list()
        result = d._q1_block_enemy(gs, action_list, ec)
        assert result is not None, "下家剩 2 张领出应有候选"
        idx, act = result
        assert act[0] == "Single", f"下家剩 2 张应单先于对；实际出 {act}"

    def test_straight_keeps_lock_when_downseat_two(self):
        """下家剩 2 但锁敌首选是顺子（3+ 张）→ 仍锁死顺子，不单先于对（GUA-078 语义）。

        顺子 5 张下家 2 张压不了，是安全锁；「单先于对」只针对对子（2 张可被下家压）。
        """
        hand = ["S4", "HR", "S3", "S3", "C3", "H7", "H7", "C5", "C6", "S7"]
        action_list = [
            ["Single", "4", ["S4"]],
            ["Single", "R", ["HR"]],
            ["Trips", "3", ["S3", "S3", "C3"]],
            ["Pair", "7", ["H7", "H7"]],
            ["Straight", "3", ["S3", "S4", "C5", "C6", "S7"]],
        ]
        gs = {
            "myPos": 0, "curPos": 0, "greaterPos": -1, "greaterAction": [],
            "handCards": list(hand), "curRank": "3",
            "numofplayers": [10, 2, 12, 9], "_botzone_mode": True,
        }
        ec = {
            "my_pos": 0, "cur_pos": 0, "cur_rank": "3",
            "enemies": {
                1: {"remaining": 2, "danger_level": "极高",
                    "recommended_types": ["最大单张"], "banned_types": [],
                    "baoshu": {"likely_hand": "单张(听牌)", "block_with": [],
                               "never_play": []}},
                3: {"remaining": 9, "danger_level": "低", "recommended_types": [],
                    "banned_types": [], "baoshu": {}},
            },
            "teammate": {"remaining": 12, "is_close": False, "assist_prefer": []},
        }
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(action_list)]
        result = d._q1_enemy_critical_lead_special(
            gs, candidates, ec, main_pos=1, main_enemy=ec["enemies"][1],
        )
        assert result is not None
        idx, act = result
        assert act[0] == "Straight", f"有顺子应锁死顺子；实际出 {act}"
        assert act[2] == ["S3", "S4", "C5", "C6", "S7"]
