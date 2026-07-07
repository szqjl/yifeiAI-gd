# -*- coding: utf-8 -*-
"""GUA-131 / GUA-132 / GUA-133 单元 + 集成测试。

C1 队友协作冲刺（@1 出 5 张 TWT + finish 是更大 TWT）
C2 同花顺 SF finish（@1 一手清必头游，yf 队闭合 @3）
C4 5 星炸 finish（@1 一手清必头游，yf2 6J 自闭合）

测试覆盖：
  - _is_bomb_family 单元（bomb + SF + 王炸 + PASS + bomb_like via declaration）
  - _is_joker_bomb 单元
  - _detect_c1_c2_c4_context（命中 + 不命中）
  - _classify_finish_type
  - _c1_decision：跟 min TWT 形成冲刺能力
  - _c2_decision：跟 min TWT 形成冲刺能力
  - _c4_decision：必出 6J
  - 集成：EndgameDecider.decide() 在 C1 锚点牌谱步 51/89 走 777+22 / 888+22（不出 6J）
"""

import pytest
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import (
    EndgameDecider,
    _is_bomb_family,
    _is_joker_bomb,
    _is_bomb_like_action,
)
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor


# ── 测试数据 ──

# 锚点牌谱 yf2 整手 14 张：JJJJJJ + 777 + 888 + 22
ANCHOR_HAND = [
    "SJ", "SJ", "HJ", "HJ", "DJ", "DJ",  # JJJJJJ
    "S7", "S7", "C7",  # 777
    "D8", "D8", "C8",  # 888
    "S2", "D2",  # 22
]

# 6J bomb
BOMB_6J = ["SJ", "SJ", "HJ", "HJ", "DJ", "DJ"]

# 333+22 @1 当前出牌（5 张 TWT）
TWT_333_22 = ["ThreeWithTwo", "3", ["S3", "H3", "D3", "S2", "D2"]]

# 777+22 / 888+22（yf2 候选）
TWT_777_22 = ["ThreeWithTwo", "7", ["S7", "H7", "C7", "S2", "H2"]]
TWT_888_22 = ["ThreeWithTwo", "8", ["S8", "H8", "C8", "S2", "H2"]]
# 上面 cards 用了 hand 里没有的 S8/H8/H2 — 测试用 hand 补上这些牌以便真实可出


def _build_action_list(twt_options=None, six_j=True, include_pass=True):
    """构建测试用 actionList。"""
    acts = []
    if include_pass:
        acts.append(["PASS", "PASS", "PASS"])
    if six_j:
        acts.append(["Bomb", "J", BOMB_6J])
    if twt_options:
        acts.extend(twt_options)
    return acts


def _build_anchor_state(hand_cards=None, action_list=None, *, enemy_remaining=5,
                        teammate_remaining=10, my_pos=0,
                        greater_pos=None, greater_action=None,
                        cur_rank="2", teammate_hand=None):
    """
    构造 C1 锚点牌谱步 51/89 game_state 模拟。
    阵营：@1 (pos=1) + @3 (pos=2) vs yf1 (pos=0..3) + yf2 (pos=0)
    默认 yf2=my_pos=0，队友 yf1=pos=2。
    """
    if greater_pos is None:
        greater_pos = 1  # @1 上家
    if greater_action is None:
        greater_action = TWT_333_22
    numofplayers = [
        len(hand_cards or ANCHOR_HAND),  # yf2 (my_pos=0)
        enemy_remaining,                  # @1 上家
        teammate_remaining,                # yf1 队友
        8,                                 # @3 下家（兜底）
    ]
    return {
        "myPos": my_pos,
        "curPos": greater_pos,
        "greaterPos": greater_pos,
        "greaterAction": greater_action,
        "handCards": list(hand_cards or ANCHOR_HAND),
        "actionList": list(action_list or _build_action_list(
            twt_options=[TWT_777_22, TWT_888_22], six_j=True, include_pass=True,
        )),
        "curRank": cur_rank,
        "selfRank": cur_rank,
        "oppoRank": cur_rank,
        "numofplayers": numofplayers,
        "publicInfo": [{"rest": n} for n in numofplayers],
        "_role": "主攻",
    }


def _preprocess(gs):
    EndgamePreprocessor().preprocess(gs)
    return gs


# ════════════════════════════════════════════
#  _is_bomb_family 单元
# ════════════════════════════════════════════

class TestIsBombFamily:
    def test_bomb_4_declared(self):
        """4 张同点炸 → bomb family"""
        act = ["Bomb", "6", ["S6", "H6", "D6", "C6"]]
        assert _is_bomb_family(act) is True

    def test_bomb_5_declared(self):
        """5 张同点炸 → bomb family"""
        act = ["Bomb", "J", ["SJ", "HJ", "DJ", "CJ", "H9"]]
        assert _is_bomb_family(act) is True

    def test_bomb_6_declared(self):
        """6 张同点炸（JJJJJJ）→ bomb family"""
        act = ["Bomb", "J", BOMB_6J]
        assert _is_bomb_family(act) is True

    def test_straight_flush_declared(self):
        """同花顺 SF → bomb family（§4.1）"""
        sf = ["StraightFlush", "5", ["S5", "S6", "S7", "S8", "S9"]]
        assert _is_bomb_family(sf) is True

    def test_joker_bomb(self):
        """王炸（SJ+BJ）→ bomb family"""
        jb = ["BJ", "SJ"]
        assert _is_bomb_family(jb) is True

    def test_three_with_two_not_bomb_family(self):
        """三带二 → NOT bomb family（杂牌通道）"""
        twt = ["ThreeWithTwo", "3", ["S3", "H3", "D3", "S2", "D2"]]
        assert _is_bomb_family(twt) is False

    def test_pass_not_bomb_family(self):
        assert _is_bomb_family(["PASS", "PASS", "PASS"]) is False

    def test_empty_not_bomb_family(self):
        assert _is_bomb_family([]) is False
        assert _is_bomb_family(None) is False


class TestIsJokerBomb:
    def test_sj_bj(self):
        assert _is_joker_bomb(["SJ", "BJ"]) is True
    def test_bj_sj(self):
        assert _is_joker_bomb(["BJ", "SJ"]) is True
    def test_joker_with_other(self):
        """王 + 普通牌 → 不是王炸"""
        assert _is_joker_bomb(["SJ", "S2"]) is False
    def test_empty(self):
        assert _is_joker_bomb([]) is False


# ════════════════════════════════════════════
#  _detect_c1_c2_c4_context
# ════════════════════════════════════════════

class TestDetectC1C2C4Context:
    def test_anchor_step_51_89_matches(self):
        """C1 锚点牌谱步 51/89 上下文命中"""
        gs = _preprocess(_build_anchor_state())
        ec = gs["_endgame_context"]
        decider = EndgameDecider()
        ctx = decider._detect_c1_c2_c4_context(gs, ec)
        assert ctx is not None
        assert ctx["enemy_pos"] == 1
        assert ctx["teammate_pos"] == 2
        assert ctx["remaining_after_press"] == 0  # 5-5=0
        assert ctx["hand_cards"] is not None

    def test_not_enemy_control_returns_none(self):
        """非敌方控牌（队友控牌）→ 不触发"""
        gs = _preprocess(_build_anchor_state(greater_pos=2))
        ec = gs["_endgame_context"]
        decider = EndgameDecider()
        ctx = decider._detect_c1_c2_c4_context(gs, ec)
        assert ctx is None

    def test_hand_too_small_returns_none(self):
        """yf2 整手 <10 → 不触发"""
        gs = _preprocess(_build_anchor_state(hand_cards=ANCHOR_HAND[:6]))
        ec = gs["_endgame_context"]
        decider = EndgameDecider()
        ctx = decider._detect_c1_c2_c4_context(gs, ec)
        assert ctx is None

    def test_enemy_remaining_out_of_range_returns_none(self):
        """@1 余张不在 [5, 6] → 不触发"""
        gs = _preprocess(_build_anchor_state(enemy_remaining=10))
        ec = gs["_endgame_context"]
        decider = EndgameDecider()
        ctx = decider._detect_c1_c2_c4_context(gs, ec)
        assert ctx is None


# ════════════════════════════════════════════
#  _classify_finish_type
# ════════════════════════════════════════════

class TestClassifyFinishType:
    def test_bomb_family_when_remaining_5_with_high_bomb_risk(self):
        """remaining == 5 + bomb_risk ≥ 0.5 → bomb_family"""
        from src.v.nn.endgame.endgame_decide import _classify_finish_type
        enemy_ctx = {"pos": 1, "remaining": 5}
        gs = {"_belief": {"opp_bomb_risks": {1: 0.7}}}
        decider = EndgameDecider()
        kind = decider._classify_finish_type(enemy_ctx, gs)
        assert kind == "bomb_family"

    def test_twt_when_low_bomb_risk(self):
        enemy_ctx = {"pos": 1, "remaining": 5}
        gs = {"_belief": {"opp_bomb_risks": {1: 0.1}}}
        decider = EndgameDecider()
        kind = decider._classify_finish_type(enemy_ctx, gs)
        assert kind == "twt"


# ════════════════════════════════════════════
#  _c1_decision
# ════════════════════════════════════════════

class TestC1Decision:
    def test_follows_min_twt_when_yf1_has_intercept(self):
        """C1：yf1 有拦截能力 → 跟 min TWT 形成冲刺能力"""
        gs = _preprocess(_build_anchor_state(teammate_remaining=12))
        ec = gs["_endgame_context"]
        action_list = gs["actionList"]
        decider = EndgameDecider()
        ctx = decider._detect_c1_c2_c4_context(gs, ec)
        assert ctx is not None
        result = decider._c1_decision(gs, action_list, ec, ctx)
        assert result is not None
        idx, act = result
        # 应该是 777+22 或 888+22（min TWT）
        assert act[0] == "ThreeWithTwo"
        assert act[1] in ("7", "8")

    def test_plays_6j_when_yf1_cannot_intercept(self):
        """C1：yf1 拦截能力弱 + yf2 有 6J → 出 6J 自闭合"""
        gs = _preprocess(_build_anchor_state(teammate_remaining=3))
        ec = gs["_endgame_context"]
        action_list = gs["actionList"]
        decider = EndgameDecider()
        ctx = decider._detect_c1_c2_c4_context(gs, ec)
        assert ctx is not None
        result = decider._c1_decision(gs, action_list, ec, ctx)
        assert result is not None
        idx, act = result
        # 兜底：出 6J
        assert act[0] == "Bomb"
        assert act[1] == "J"


# ════════════════════════════════════════════
#  _c2_decision
# ════════════════════════════════════════════

class TestC2Decision:
    def test_follows_min_twt_for_sprint_capability(self):
        """C2：@1 finish=SF 必头游 → 跟 min TWT 形成冲刺能力"""
        gs = _preprocess(_build_anchor_state())
        ec = gs["_endgame_context"]
        # 强制 finish_kind = bomb_family 走 C4（实际 C2 走 C4 兜底）
        action_list = gs["actionList"]
        decider = EndgameDecider()
        ctx = decider._detect_c1_c2_c4_context(gs, ec)
        ctx["finish_kind"] = "bomb_family"
        result = decider._c2_decision(gs, action_list, ec, ctx)
        assert result is not None
        idx, act = result
        assert act[0] == "ThreeWithTwo"
        assert act[1] in ("7", "8")


# ════════════════════════════════════════════
#  _c4_decision
# ════════════════════════════════════════════

class TestC4Decision:
    def test_must_play_6j_over_5_enemy_bomb(self):
        """C4：@1 finish=5 星炸 → yf2 必出 6J 反抢"""
        gs = _preprocess(_build_anchor_state())
        ec = gs["_endgame_context"]
        action_list = gs["actionList"]
        decider = EndgameDecider()
        ctx = decider._detect_c1_c2_c4_context(gs, ec)
        result = decider._c4_decision(gs, action_list, ec, ctx)
        assert result is not None
        idx, act = result
        # 必出 6J
        assert act[0] == "Bomb"
        assert act[1] == "J"
        assert len(act[2]) == 6


# ════════════════════════════════════════════
#  集成：EndgameDecider.decide() 在 C1 锚点牌谱步 51/89
# ════════════════════════════════════════════

class TestIntegrationAnchorStep51:
    """
    WF-12 锚点牌谱：game_records_v7/20260706222548831117 [yf1_v7]-[opponent_1_3]-[10]-[2].json
    步 51/89：@1 333+22 (5 张 TWT) → yf2 必出 777+22 或 888+22，**不出 6J**。
    """
    def test_anchor_step_51_selects_twt_not_6j(self):
        gs = _preprocess(_build_anchor_state())
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert idx is not None and act is not None
        # 关键：不能出 6J
        assert act[0] != "Bomb", f"步 51 不应出 6J；实际出 {act}"
        # 应出 777+22 或 888+22
        assert act[0] == "ThreeWithTwo"
        assert act[1] in ("7", "8")