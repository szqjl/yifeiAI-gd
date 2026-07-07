# -*- coding: utf-8 -*-
"""GUA-134 单元 + 集成测试：C3 / C5 / C6 yf2 自闭合决策（高闭合率三手清空）

C3：@1 finish = 顺子（杂牌通道不能跨型压 TWT §4.4）→ yf2 必跟 TWT 夺权
C5：@1 finish = 更小 TWT（同型互压 finish < yf2 TWT）→ yf2 必跟 TWT 夺权
C6：@1 finish = 5 张散（非整牌型）→ yf2 必跟 TWT 夺权

共同路径：圈 1 yf2 跟 min TWT → @1 必 PASS → yf2 圈 2 领出 6J → 三手清空头游。
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor


# ── 测试数据 ──

ANCHOR_HAND = [
    "SJ", "SJ", "HJ", "HJ", "DJ", "DJ",  # JJJJJJ
    "S7", "S7", "C7",  # 777
    "D8", "D8", "C8",  # 888
    "S2", "D2",  # 22
]
BOMB_6J = ["SJ", "SJ", "HJ", "HJ", "DJ", "DJ"]
TWT_333_22 = ["ThreeWithTwo", "3", ["S3", "H3", "D3", "S2", "D2"]]


def _build_action_list(twt_options=None, six_j=True, include_pass=True):
    acts = []
    if include_pass:
        acts.append(["PASS", "PASS", "PASS"])
    if six_j:
        acts.append(["Bomb", "J", BOMB_6J])
    if twt_options:
        acts.extend(twt_options)
    return acts


def _build_c3_state(hand_cards=None, action_list=None, *, enemy_remaining=5,
                     teammate_remaining=10, my_pos=0,
                     greater_pos=1, greater_action=None,
                     cur_rank="2", enemy_ctx_finish=None):
    """C3: @1 finish = 5 张顺子。remaining = 10 表示 @1 报 5 + finish 5。"""
    if greater_action is None:
        greater_action = TWT_333_22
    numofplayers = [
        len(hand_cards or ANCHOR_HAND),
        enemy_remaining,
        teammate_remaining,
        8,
    ]
    gs = {
        "myPos": my_pos,
        "curPos": greater_pos,
        "greaterPos": greater_pos,
        "greaterAction": greater_action,
        "handCards": list(hand_cards or ANCHOR_HAND),
        "actionList": list(action_list or _build_action_list(
            twt_options=[
                ["ThreeWithTwo", "7", ["S7", "S7", "C7", "S2", "H2"]],
                ["ThreeWithTwo", "8", ["S8", "S8", "C8", "S2", "H2"]],
            ],
            six_j=True,
            include_pass=True,
        )),
        "curRank": cur_rank,
        "selfRank": cur_rank,
        "oppoRank": cur_rank,
        "numofplayers": numofplayers,
        "publicInfo": [{"rest": n} for n in numofplayers],
        "_role": "主攻",
    }
    return gs


def _preprocess(gs):
    EndgamePreprocessor().preprocess(gs)
    ec = gs["_endgame_context"]
    # Inject finish_type into enemy_ctx to simulate C3/C5/C6 detection
    enemy = ec.get("enemies", {}).get(gs["greaterPos"], {})
    if enemy:
        if "finish_type" not in enemy:
            enemy["finish_type"] = gs.get("_finish_type_override", None)
        if "finish_rank_value" not in enemy:
            enemy["finish_rank_value"] = gs.get("_finish_rank_value", 0)
    return gs


# ════════════════════════════════════════════
#  _classify_c356_kind
# ════════════════════════════════════════════

class TestClassifyC356Kind:
    def test_straight_finish_is_c3(self):
        enemy_ctx = {"remaining": 10, "finish_type": "Straight"}
        gs = {}
        d = EndgameDecider()
        kind = d._classify_c356_kind(enemy_ctx, gs, TWT_333_22)
        assert kind == "straight"

    def test_smaller_twt_finish_is_c5(self):
        enemy_ctx = {"remaining": 10, "finish_type": "ThreeWithTwo",
                     "finish_rank_value": 5}
        gs = {}
        d = EndgameDecider()
        kind = d._classify_c356_kind(enemy_ctx, gs, TWT_333_22)
        assert kind == "smaller_twt"

    def test_scatter_finish_is_c6(self):
        enemy_ctx = {"remaining": 10, "finish_type": "Scatter"}
        gs = {}
        d = EndgameDecider()
        kind = d._classify_c356_kind(enemy_ctx, gs, TWT_333_22)
        assert kind == "scatter"

    def test_no_finish_type_returns_unknown(self):
        enemy_ctx = {"remaining": 5}
        gs = {}
        d = EndgameDecider()
        kind = d._classify_c356_kind(enemy_ctx, gs, TWT_333_22)
        assert kind == "unknown"

    def test_infer_straight_from_remaining_5(self):
        """remaining - 5 == 5 → Straight"""
        enemy_ctx = {"remaining": 10}
        gs = {}
        d = EndgameDecider()
        kind = d._classify_c356_kind(enemy_ctx, gs, TWT_333_22)
        assert kind == "straight"

    def test_infer_scatter_from_remaining_2(self):
        """remaining - 5 == 2 → Scatter"""
        enemy_ctx = {"remaining": 7}
        gs = {}
        d = EndgameDecider()
        kind = d._classify_c356_kind(enemy_ctx, gs, TWT_333_22)
        assert kind == "scatter"


# ════════════════════════════════════════════
#  _is_c3_c5_c6_scenario
# ════════════════════════════════════════════

class TestIsC3C5C6Scenario:
    def test_c3_straight_finish_matches(self):
        gs = _build_c3_state()
        gs["_finish_type_override"] = "Straight"
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_c3_c5_c6_scenario(gs, ec)
        assert ctx is not None
        assert ctx["c356_kind"] == "straight"

    def test_c5_smaller_twt_matches(self):
        gs = _build_c3_state()
        gs["_finish_type_override"] = "ThreeWithTwo"
        gs["_finish_rank_value"] = 5
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_c3_c5_c6_scenario(gs, ec)
        assert ctx is not None
        assert ctx["c356_kind"] == "smaller_twt"

    def test_c6_scatter_matches(self):
        gs = _build_c3_state()
        gs["_finish_type_override"] = "Scatter"
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_c3_c5_c6_scenario(gs, ec)
        assert ctx is not None
        assert ctx["c356_kind"] == "scatter"

    def test_no_finish_returns_none(self):
        gs = _build_c3_state()
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        # No finish_type override → unknown
        ctx = d._is_c3_c5_c6_scenario(gs, ec)
        assert ctx is None


# ════════════════════════════════════════════
#  _c3_c5_c6_decision
# ════════════════════════════════════════════

class TestC3C5C6Decision:
    def test_c3_follows_min_twt(self):
        gs = _build_c3_state()
        gs["_finish_type_override"] = "Straight"
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_c3_c5_c6_scenario(gs, ec)
        assert ctx is not None
        result = d._c3_c5_c6_decision(gs, gs["actionList"], ec, ctx)
        assert result is not None
        idx, act = result
        assert act[0] == "ThreeWithTwo"
        assert act[1] in ("7", "8")  # min TWT

    def test_c5_follows_min_twt(self):
        gs = _build_c3_state()
        gs["_finish_type_override"] = "ThreeWithTwo"
        gs["_finish_rank_value"] = 4
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_c3_c5_c6_scenario(gs, ec)
        assert ctx is not None
        result = d._c3_c5_c6_decision(gs, gs["actionList"], ec, ctx)
        assert result is not None
        idx, act = result
        assert act[0] == "ThreeWithTwo"
        assert act[1] in ("7", "8")

    def test_no_twt_falls_back_to_pass(self):
        """无 TWT 可跟 → 兜底 PASS（@1 必头游）"""
        gs = _build_c3_state(action_list=_build_action_list(
            twt_options=None, six_j=True, include_pass=True,
        ))
        gs["_finish_type_override"] = "Straight"
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_c3_c5_c6_scenario(gs, ec)
        assert ctx is not None
        result = d._c3_c5_c6_decision(gs, gs["actionList"], ec, ctx)
        assert result is not None
        idx, act = result
        # 兜底 PASS
        assert act[0] == "PASS"


# ════════════════════════════════════════════
#  集成：EndgameDecider.decide() C3/C5/C6 场景
# ════════════════════════════════════════════

class TestIntegrationC356:
    def test_c3_integration_selects_twt(self):
        """C3 集成：yf2 应跟 min TWT（不出 6J）"""
        gs = _build_c3_state()
        gs["_finish_type_override"] = "Straight"
        gs = _preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert idx is not None and act is not None
        # 不出 6J（高闭合率，6J 是兜底）
        assert act[0] != "Bomb", f"C3 不应出 6J；实际出 {act}"
        # 应出 TWT
        assert act[0] == "ThreeWithTwo"

    def test_c5_integration_selects_twt(self):
        gs = _build_c3_state()
        gs["_finish_type_override"] = "ThreeWithTwo"
        gs["_finish_rank_value"] = 4
        gs = _preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert idx is not None and act is not None
        assert act[0] != "Bomb", f"C5 不应出 6J；实际出 {act}"
        assert act[0] == "ThreeWithTwo"

    def test_c6_integration_selects_twt(self):
        gs = _build_c3_state()
        gs["_finish_type_override"] = "Scatter"
        gs = _preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert idx is not None and act is not None
        assert act[0] != "Bomb", f"C6 不应出 6J；实际出 {act}"
        assert act[0] == "ThreeWithTwo"
