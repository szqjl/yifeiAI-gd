# -*- coding: utf-8 -*-
"""
GUA-224 残局「三张+三张+对子」应打钢板 TwoTrips 而非三带二

match 6a78308c（logs/v8_vs_botzone_20260809_152013.log 15:49:28）：
V8 残局手牌含 888/999 钢板候选，endgame_decide 推荐 TwoTrips(888999)，
但被 _is_partial_composite_lead 误判「半组」拦截 → 回退 GUA-075 打低牌力
ThreeWithTwo，被更大牌型（StraightFlush/KKK 等）压制失去上游。

根因：组牌引擎把钢板子组归入 trip_in_three_with_two（如 777+888+55 中 777
被组进 TWT 子组），完整 TwoTrips(777888) 触及该子组 → _is_partial_composite_lead
按「声明非 ThreeWithTwo 却触及 TWT 子组」判半组 → 拦。

用户场景：最后剩 777+888+55，V8 打 TWT(777+55) 被 KKK 压制失去上游，
应打钢板 TwoTrips(777888)——特殊牌型被压概率极小。

修复：_is_partial_composite_lead 对完整复合动作（TwoTrips/ThreePair/ThreeWithTwo）
且 allocation 用满所有触及复合子组（无部分使用）时放行（非半组）。
"""
import pytest

from src.v.nn.features.grouping_engine import enumerate_groupings
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
from src.v.nn.endgame.endgame_decide import EndgameDecider


def make_hand(*ranks: str) -> list:
    """从 rank 列表构造手牌（自动分配花色）。"""
    cards = []
    suit_cycle = ["S", "H", "C", "D"]
    for i, r in enumerate(ranks):
        cards.append(f"{suit_cycle[i % 4]}{r}")
    return cards


class _FakeLogger:
    def debug(self, msg, *args, **kwargs): pass
    def info(self, msg, *args, **kwargs): pass
    def warning(self, msg, *args, **kwargs): pass
    def error(self, msg, *args, **kwargs): pass


def _make_engine(hand, cur_rank="2"):
    """用真实组牌引擎产出 mask/group，构造 engine（GUA-224 场景）。"""
    best, _ = enumerate_groupings(hand, cur_rank)
    mask, gmap, members = best.to_card_mask()
    engine = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    engine.logger = _FakeLogger()
    engine._card_mask = mask
    engine._group_type_map = gmap
    engine._group_members = members
    engine._current_role = "主攻"
    engine._anchor_role = None
    engine._best_plan = best
    engine._grouping_features = None
    engine.player_id = 0
    engine._tracker = None
    engine.group_filter_bypass_count = 0
    engine.group_filtered_count = 0
    return engine


# ═══════════════════════════════════════════════════════════
# _is_partial_composite_lead 单元断言
# ═══════════════════════════════════════════════════════════

class TestPartialCompositeLead:
    """Case 1: 完整复合动作不应被误判为半组。"""

    @pytest.fixture
    def hand(self):
        # 777 + 888 + 55 = 8 张残局
        return make_hand("7", "7", "7", "8", "8", "8", "5", "5")

    @pytest.fixture
    def engine(self, hand):
        return _make_engine(hand)

    def test_complete_twotrips_not_partial(self, engine):
        """完整钢板 TwoTrips(777888) → 非半组，放行。"""
        two_trips = ["TwoTrips", "7", ["S7", "H7", "C7", "S8", "H8", "D8"]]
        assert engine._is_partial_composite_lead(two_trips) is False

    def test_complete_three_with_two_not_partial(self, engine):
        """完整三带二 TWT(777+55) → 非半组，放行。"""
        twt = ["ThreeWithTwo", "7", ["S7", "H7", "C7", "C5", "D5"]]
        assert engine._is_partial_composite_lead(twt) is False

    def test_half_steel_plate_trips_still_blocked(self, engine):
        """半组钢板 Trips(777 只出三张) → 仍判半组，拦截。"""
        trips = ["Trips", "7", ["S7", "H7", "C7"]]
        assert engine._is_partial_composite_lead(trips) is True

    def test_half_three_with_two_pair_still_blocked(self, engine):
        """半组三带二 Pair(55 只出对子) → 仍判半组，拦截。"""
        pair = ["Pair", "5", ["C5", "D5"]]
        assert engine._is_partial_composite_lead(pair) is True


# ═══════════════════════════════════════════════════════════
# _group_consistency_filter 端到端
# ═══════════════════════════════════════════════════════════

class TestGroupConsistencyFilterKeepsTwotrips:
    """Case 2: filter 不再拦截完整钢板，TwoTrips 保留。"""

    @pytest.fixture
    def hand(self):
        return make_hand("7", "7", "7", "8", "8", "8", "5", "5")

    @pytest.fixture
    def engine(self, hand):
        return _make_engine(hand)

    def test_filter_keeps_twotrips(self, engine, hand):
        gs = {
            "myPos": 0,
            "curRank": "2",
            "handCards": hand,
            "publicInfo": [{"rest": 8}, {"rest": 6}, {"rest": 6}, {"rest": 7}],
            "numofplayers": [8, 6, 6, 7],
            "greaterPos": -1,
            "greaterAction": [],
            "history": [],
            "recentPlays": [],
        }
        two_trips = ["TwoTrips", "7", ["S7", "H7", "C7", "S8", "H8", "D8"]]
        twt7 = ["ThreeWithTwo", "7", ["S7", "H7", "C7", "C5", "D5"]]
        actions = [
            ["PASS", "PASS", "PASS"],
            two_trips,
            twt7,
            ["Pair", "5", ["C5", "D5"]],
        ]
        filtered, fmap = engine._group_consistency_filter(actions, gs)
        assert two_trips in filtered, "完整钢板 TwoTrips 不应被 filter 拦截"


# ═══════════════════════════════════════════════════════════
# EndgameDecider 端到端
# ═══════════════════════════════════════════════════════════

class TestEndgameDecidePrefersTwotrips:
    """Case 3: 8 张残局领出，endgame_decide 推荐钢板 TwoTrips 而非 TWT。"""

    def test_decide_recommends_twotrips(self):
        hand = make_hand("7", "7", "7", "8", "8", "8", "5", "5")
        actions = [
            ["PASS", "PASS", "PASS"],
            ["TwoTrips", "7", ["S7", "H7", "C7", "S8", "H8", "D8"]],
            ["ThreeWithTwo", "7", ["S7", "H7", "C7", "C5", "D5"]],
            ["ThreeWithTwo", "8", ["S8", "H8", "D8", "C5", "D5"]],
            ["Pair", "5", ["C5", "D5"]],
        ]
        gs = {
            "myPos": 0,
            "curRank": "2",
            "handCards": hand,
            "publicInfo": [{"rest": 8}, {"rest": 5}, {"rest": 9}, {"rest": 6}],
            "numofplayers": [8, 5, 9, 6],
            "greaterPos": -1,
            "greaterAction": [],
            "history": [],
            "recentPlays": [],
            "actionList": actions,
            "_endgame_context": {
                "is_active": True,
                "numofplayers": [8, 5, 9, 6],
                "my_pos": 0,
                "enemies": {
                    1: {"remaining": 5, "danger_level": "低", "recommended_types": [], "banned_types": []},
                    3: {"remaining": 6, "danger_level": "低", "recommended_types": [], "banned_types": []},
                },
                "teammate": {"remaining": 9, "is_close": False, "assist_prefer": []},
                "self": {"remaining": 8, "has_two_clean_hands": True, "has_bomb": False, "should_sprint": True},
            },
        }
        decider = EndgameDecider()
        idx, act = decider.decide(gs, actions)
        assert act is not None, "残局应命中端局决策"
        assert act[0] == "TwoTrips", f"应推荐钢板 TwoTrips，got {act[:2]}"
        assert act[1] == "7", f"应推荐 TwoTrips/7，got {act[:2]}"
