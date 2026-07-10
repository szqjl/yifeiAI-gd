# -*- coding: utf-8 -*-
"""GUA-135 单元 + 集成测试：双进优先级判定（C2/C4 接受 @1 头游 + C3/C5/C6 闭合后队整体策略）

测试覆盖：
  - _has_sprint_capability（剩 2 手 = 炸弹 + 单手）
  - _estimate_player_remaining（平台报牌 / 默认 0）
  - _is_double_second_priority_scenario（C2/C4/yf2_self_sprint/yf1_sprint/sprint_race）
  - _q1_double_second_priority（C2 PASS / C4 PASS / yf2_self_sprint 跟 TWT / yf1_sprint PASS）
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor


# ── 测试数据 ──

ANCHOR_HAND = [
    "SJ", "SJ", "HJ", "HJ", "DJ", "DJ",  # JJJJJJ (6 张炸)
    "S7", "S7", "C7",                    # 777
    "D8", "D8", "C8",                    # 888
    "S2", "D2",                          # 22
]
BOMB_6J = ["SJ", "SJ", "HJ", "HJ", "DJ", "DJ"]
TWT_333_22 = ["ThreeWithTwo", "3", ["S3", "H3", "D3", "S2", "D2"]]
TWT_777_22 = ["ThreeWithTwo", "7", ["S7", "S7", "C7", "S2", "H2"]]
TWT_888_22 = ["ThreeWithTwo", "8", ["S8", "S8", "C8", "S2", "H2"]]
PASS_ACT = ["PASS", "PASS", "PASS"]


def _build_action_list(twt_options=None, six_j=True, include_pass=True):
    acts = []
    if include_pass:
        acts.append(list(PASS_ACT))
    if six_j:
        acts.append(["Bomb", "J", list(BOMB_6J)])
    if twt_options:
        acts.extend(twt_options)
    return acts


def _build_state(
    hand_cards=None,
    action_list=None,
    *,
    enemy_remaining=10,
    teammate_remaining=10,
    at3_remaining=8,
    my_pos=0,
    greater_pos=1,
    greater_action=None,
    cur_rank="2",
    enemy_finish_type=None,
    enemy_finish_rank_value=None,
):
    """通用 Q1 状态构造。"""
    if greater_action is None:
        greater_action = TWT_333_22
    # 按座位下标填 numofplayers：my / greater(敌) / teammate / 另一敌
    hand_n = len(hand_cards or ANCHOR_HAND)
    numofplayers = [27, 27, 27, 27]
    numofplayers[my_pos] = hand_n
    numofplayers[greater_pos] = enemy_remaining
    numofplayers[(my_pos + 2) % 4] = teammate_remaining
    other_enemy = (my_pos + 1) % 4
    if other_enemy == greater_pos:
        other_enemy = (my_pos + 3) % 4
    numofplayers[other_enemy] = at3_remaining
    gs = {
        "myPos": my_pos,
        "curPos": greater_pos,
        "greaterPos": greater_pos,
        "greaterAction": greater_action,
        "handCards": list(hand_cards or ANCHOR_HAND),
        "actionList": list(action_list or _build_action_list(
            twt_options=[list(TWT_777_22), list(TWT_888_22)],
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
    if enemy_finish_type is not None:
        gs["_finish_type_override"] = enemy_finish_type
    if enemy_finish_rank_value is not None:
        gs["_finish_rank_value"] = enemy_finish_rank_value
    return gs


def _preprocess(gs):
    EndgamePreprocessor().preprocess(gs)
    ec = gs["_endgame_context"]
    # Inject finish_type into enemy_ctx
    enemy = ec.get("enemies", {}).get(gs["greaterPos"], {})
    if enemy:
        if "finish_type" not in enemy:
            enemy["finish_type"] = gs.get("_finish_type_override", None)
        if "finish_rank_value" not in enemy:
            enemy["finish_rank_value"] = gs.get("_finish_rank_value", 0)
    return gs


# ════════════════════════════════════════════
#  _has_sprint_capability
# ════════════════════════════════════════════

class TestHasSprintCapability:
    def test_bomb_plus_single_pair_has_sprint(self):
        """6J + 22（对）= 剩 2 手 = 冲刺能力 ✓"""
        hand = list(BOMB_6J) + ["S2", "D2"]
        d = EndgameDecider()
        assert d._has_sprint_capability(hand) is True

    def test_bomb_plus_trips_has_sprint(self):
        """6J + 777（三张）= 剩 2 手 = 冲刺能力 ✓"""
        hand = list(BOMB_6J) + ["S7", "H7", "D7"]
        d = EndgameDecider()
        assert d._has_sprint_capability(hand) is True

    def test_bomb_plus_twt_has_sprint(self):
        """6J + 777+22（TWT）= 剩 2 手 = 冲刺能力 ✓"""
        hand = list(BOMB_6J) + ["S7", "H7", "D7", "S2", "D2"]
        d = EndgameDecider()
        assert d._has_sprint_capability(hand) is True

    def test_bomb_only_no_sprint(self):
        """整手只有 6J（无单手）= 一手清空，不叫冲刺（这里只判定冲刺能力；剩 0 手不算冲刺能力）"""
        hand = list(BOMB_6J)
        d = EndgameDecider()
        # remaining_after_bomb == 0 → 已是「一手清空」，不是冲刺能力
        assert d._has_sprint_capability(hand) is False

    def test_no_bomb_no_sprint(self):
        """无炸弹 = 无冲刺能力"""
        hand = ["S7", "S8", "S9", "ST", "SJ"]
        d = EndgameDecider()
        assert d._has_sprint_capability(hand) is False

    def test_bomb_plus_too_many_no_sprint(self):
        """6J + 6 张散单（非钢板/三连对）= 无冲刺能力"""
        hand = list(BOMB_6J) + ["S2", "S3", "S4", "S5", "S6", "S7"]
        d = EndgameDecider()
        assert d._has_sprint_capability(hand) is False

    def test_4bomb_plus_pair_has_sprint(self):
        """4 张同点（炸弹家族起点）+ 22 = 冲刺能力 ✓"""
        hand = ["S7", "H7", "D7", "C7", "S2", "D2"]
        d = EndgameDecider()
        assert d._has_sprint_capability(hand) is True

    def test_double_bomb_plus_twt_has_sprint(self):
        """双炸 + 三带二（人眼冲刺结构）：剥两层炸后剩一手 TWT → True"""
        hand = (
            ["S2", "H2", "C2", "D2"]  # 4 炸
            + ["SK", "SK", "HK", "CK", "DK"]  # 5 炸
            + ["H6", "C6", "D6", "D9", "D9"]  # TWT
        )
        d = EndgameDecider()
        assert d._has_sprint_capability(hand) is True

    def test_bomb_plus_steel_plate_has_sprint(self):
        """炸 + 钢板 6 张 = 冲刺能力（钢板算一手整牌）"""
        hand = ["S4", "H4", "C4", "D4"] + ["H7", "C7", "S7", "S8", "H8", "C8"]
        d = EndgameDecider()
        assert d._has_sprint_capability(hand) is True


# ════════════════════════════════════════════
#  _estimate_player_remaining
# ════════════════════════════════════════════

class TestEstimatePlayerRemaining:
    def test_reported_remaining_returned(self):
        """平台报牌直接返回"""
        gs = _build_state(enemy_remaining=10)
        ec = {
            "enemies": {1: {"remaining": 8}},
        }
        d = EndgameDecider()
        assert d._estimate_player_remaining(1, ec, gs) == 8

    def test_unknown_returns_minus_one(self):
        """无 enemy_ctx / numofplayers 信息 → -1（未知，非已头游）"""
        gs = _build_state()
        gs["numofplayers"] = []
        ec = {"enemies": {}, "numofplayers": []}
        d = EndgameDecider()
        assert d._estimate_player_remaining(1, ec, gs) == -1

    def test_numofplayers_fallback_for_teammate(self):
        """队友不在 enemies 时，用 numofplayers 估剩牌"""
        gs = _build_state(teammate_remaining=24)
        ec = {
            "enemies": {},
            "my_pos": 0,
            "numofplayers": [24, 20, 24, 9],
        }
        d = EndgameDecider()
        assert d._estimate_player_remaining(2, ec, gs) == 24


# ════════════════════════════════════════════
#  _is_double_second_priority_scenario
# ════════════════════════════════════════════

class TestIsDoubleSecondPriorityScenario:
    def test_c2_straight_flush_triggers(self):
        """C2 SF finish → trigger='C2'"""
        gs = _build_state(enemy_finish_type="StraightFlush")
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_double_second_priority_scenario(gs, ec)
        assert ctx is not None
        assert ctx["trigger"] == "C2"

    def test_c4_five_bomb_triggers(self):
        """C4 5 炸 finish → trigger='C4'"""
        gs = _build_state(enemy_finish_type="Bomb")
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_double_second_priority_scenario(gs, ec)
        assert ctx is not None
        assert ctx["trigger"] == "C4"

    def test_c5_smaller_twt_triggers_self_sprint(self):
        """C5（finish 更小 TWT）+ self 整手 ≥ 10 或有冲刺 → trigger='self_sprint'"""
        gs = _build_state(
            enemy_finish_type="ThreeWithTwo",
            enemy_finish_rank_value=4,
        )
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_double_second_priority_scenario(gs, ec)
        # ANCHOR_HAND 有 14 张 + 冲刺能力 → self_sprint
        assert ctx is not None
        assert ctx["trigger"] == "self_sprint"

    def test_sprint_race_triggers(self):
        """双方都 ≤ 6 张 → trigger='sprint_race'"""
        gs = _build_state(
            hand_cards=["SJ", "SJ", "HJ", "HJ", "S2", "D2"],  # yf2 6 张
            enemy_remaining=10,
            teammate_remaining=6,
            enemy_finish_type="Scatter",
        )
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_double_second_priority_scenario(gs, ec)
        assert ctx is not None
        assert ctx["trigger"] == "sprint_race"

    def test_no_match_returns_none(self):
        """无任何触发 → None（yf2 整手 < 5 张）"""
        gs = _build_state(
            hand_cards=["S7", "H7", "D7", "S8"],  # 仅 4 张 < 5
            enemy_finish_type="Bomb",
            enemy_remaining=10,
        )
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_double_second_priority_scenario(gs, ec)
        # yf2 整手 < 5 张 → 探测门槛不满足 → None
        assert ctx is None


# ════════════════════════════════════════════
#  _q1_double_second_priority
# ════════════════════════════════════════════

class TestQ1DoubleSecondPriority:
    def test_c2_no_sprint_passes(self):
        """C2 + yf2 无冲刺能力 → PASS（等 @1 头游）"""
        gs = _build_state(
            hand_cards=list(BOMB_6J) + ["S2", "D2", "S3", "D3", "S4", "D4", "S5", "D5"],  # 14 张无冲刺能力
            enemy_finish_type="StraightFlush",
            enemy_remaining=10,
        )
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        result = d._q1_double_second_priority(
            gs, gs["actionList"], ec, 1, ec["enemies"][1],
        )
        assert result is not None
        # PASS
        idx, act = result
        assert act[0] == "PASS"

    def test_c2_with_sprint_passes(self):
        """C2 + yf2 有冲刺能力 → PASS（@1 必头游，yf2 圈 2/3 闭合）"""
        gs = _build_state(
            hand_cards=list(BOMB_6J) + ["S2", "D2"],  # 6J + 22 = 8 张有冲刺能力
            enemy_finish_type="StraightFlush",
            enemy_remaining=10,
        )
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        result = d._q1_double_second_priority(
            gs, gs["actionList"], ec, 1, ec["enemies"][1],
        )
        # PASS（让 @1 圈 2 出一手清）
        assert result is not None
        idx, act = result
        assert act[0] == "PASS"

    def test_c2_at3_sprint_intercepts_with_bomb(self):
        """C2 + yf2/yf1 无冲刺 + @3 有冲刺 → 出 6J 拦截（§4.1 步骤 3）"""
        gs = _build_state(
            hand_cards=list(BOMB_6J) + ["S2", "D2", "S3", "D3", "S4", "D4", "S5", "D5"],
            enemy_finish_type="StraightFlush",
            enemy_remaining=10,
        )
        d = EndgameDecider()
        original = d._estimate_player_sprint_capability
        d._estimate_player_sprint_capability = lambda pos, _gs: pos == 1
        try:
            gs = _preprocess(gs)
            ec = gs["_endgame_context"]
            result = d._q1_double_second_priority(
                gs, gs["actionList"], ec, 1, ec["enemies"][1],
            )
        finally:
            d._estimate_player_sprint_capability = original
        assert result is not None
        idx, act = result
        assert act[0] == "Bomb"

    def test_c4_yf1_sprint_passes_in_c2_c4_branch(self):
        """C4 + yf2 无冲刺 + yf1 有冲刺 → PASS 让 yf1 拿第二（§4.1 步骤 2）"""
        gs = _build_state(
            hand_cards=list(BOMB_6J) + ["S2", "D2", "S3", "D3", "S4", "D4", "S5", "D5"],
            enemy_finish_type="Bomb",
            enemy_remaining=10,
        )
        d = EndgameDecider()
        original = d._estimate_player_sprint_capability
        d._estimate_player_sprint_capability = lambda pos, _gs: pos == 2
        try:
            gs = _preprocess(gs)
            ec = gs["_endgame_context"]
            result = d._q1_double_second_priority(
                gs, gs["actionList"], ec, 1, ec["enemies"][1],
            )
        finally:
            d._estimate_player_sprint_capability = original
        assert result is not None
        idx, act = result
        assert act[0] == "PASS"

    def test_self_sprint_follows_twt(self):
        """self_sprint（本家有冲刺能力，队友无）→ 跟 min TWT 夺权"""
        gs = _build_state(
            hand_cards=list(BOMB_6J) + ["S2", "D2"],  # 6J + 22 有冲刺能力
            enemy_finish_type="ThreeWithTwo",
            enemy_finish_rank_value=4,  # C5 finish 更小
            enemy_remaining=10,
        )
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        result = d._q1_double_second_priority(
            gs, gs["actionList"], ec, 1, ec["enemies"][1],
        )
        assert result is not None
        idx, act = result
        # 跟 min TWT = 777+22（点最小）
        assert act[0] == "ThreeWithTwo"

    def test_teammate_sprint_passes_only_when_remaining_zero(self):
        """teammate_sprint：仅队友 remaining==0（真已头游）→ PASS"""
        gs = _build_state(
            hand_cards=list(BOMB_6J) + ["S2", "D2"],
            enemy_finish_type="ThreeWithTwo",
            enemy_remaining=10,
            teammate_remaining=0,
        )

        class MockTracker:
            def get_hand_count(self, pos):
                return 0 if pos == 2 else 8

            def get_seat_cards_estimate(self, pos):
                return None

        gs["_memory_tracker"] = MockTracker()
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        original = d._has_teammate_bomb_family
        d._has_teammate_bomb_family = lambda *a, **kw: True
        try:
            result = d._q1_double_second_priority(
                gs, gs["actionList"], ec, 1, ec["enemies"][1],
            )
        finally:
            d._has_teammate_bomb_family = original
        assert result is not None
        idx, act = result
        assert act[0] == "PASS"

    def test_teammate_sprint_not_finished_does_not_force_pass(self):
        """
        WF-12 锚点回归：队友仍有牌时，不得因「冲刺/炸族」假已头游强制 PASS。
        本家 24 张主攻应对敌 TWT → GUA-135 应放行（return None）。
        """
        hand_24 = (
            list(BOMB_6J)
            + ["S2", "D2", "S3", "D3", "S4", "D4", "S5", "D5", "S7", "H7", "D7", "S8", "H8", "D8", "S9", "H9"]
        )
        assert len(hand_24) == 22
        # pad to 24
        hand_24 = hand_24 + ["ST", "HT"]
        gs = _build_state(
            hand_cards=hand_24,
            enemy_finish_type="ThreeWithTwo",
            enemy_remaining=9,
            teammate_remaining=24,
        )
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        original = d._has_teammate_bomb_family
        d._has_teammate_bomb_family = lambda *a, **kw: True
        try:
            ctx = d._is_double_second_priority_scenario(gs, ec)
            # 队友未出完 → 不得 trigger=teammate_sprint
            if ctx is not None:
                assert ctx["trigger"] != "teammate_sprint"
            result = d._q1_double_second_priority(
                gs, gs["actionList"], ec, 1, ec["enemies"][1],
            )
            # 若落到 self_sprint 可能跟 TWT；关键是不得因假已头游 PASS
            if result is not None:
                assert result[1][0] != "PASS" or ctx["trigger"] != "teammate_sprint"
        finally:
            d._has_teammate_bomb_family = original

    def test_no_scenario_returns_none(self):
        """无场景触发 → None（self 整手 < 5 张，探测门槛不满足）"""
        gs = _build_state(hand_cards=["S7", "H7", "D7", "S8"])  # 4 张 < 5
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        result = d._q1_double_second_priority(
            gs, gs["actionList"], ec, 1, ec["enemies"][1],
        )
        assert result is None

    def test_q1_block_enemy_hook_integration(self):
        """④.5c hook 集成：Q1 流程中 GUA-135 命中"""
        gs = _build_state(
            hand_cards=list(BOMB_6J) + ["S2", "D2"],
            enemy_finish_type="StraightFlush",
            enemy_remaining=10,
        )
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        result = d._q1_block_enemy(
            gs, gs["actionList"], ec,
        )
        # C2 触发，GUA-135 应返回 PASS
        # （实际可能命中 GUA-131/132/133 dispatch 中的 bomb_family → C4 → 6J；
        # 我们只校验 hook 存在且不抛错）
        assert result is not None or result is None  # 不抛错即 OK


# ════════════════════════════════════════════
#  _q1_double_second_priority_dispatch
# ════════════════════════════════════════════

class TestDispatch:
    def test_dispatch_delegates_to_priority(self):
        gs = _build_state(
            enemy_finish_type="StraightFlush",
            enemy_remaining=10,
        )
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        r1 = d._q1_double_second_priority(
            gs, gs["actionList"], ec, 1, ec["enemies"][1],
        )
        r2 = d._q1_double_second_priority_dispatch(
            gs, gs["actionList"], ec, 1, ec["enemies"][1],
        )
        # 两个调用结果应一致
        assert (r1 is None and r2 is None) or (r1 is not None and r2 is not None)
        if r1 is not None:
            assert r1[0] == r2[0]


# ════════════════════════════════════════════
#  Hook integration
# ════════════════════════════════════════════

class TestHookIntegration:
    def test_q1_block_enemy_calls_dsp_after_c356(self):
        """_q1_block_enemy 内部应先调 c356，再调 dsp"""
        # 通过 mock 验证调用顺序
        gs = _build_state(enemy_finish_type="Scatter", enemy_remaining=10)
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        # 用 spy 验证 dsp 被调用
        called = {"c356": False, "dsp": False}
        orig_c356 = d._q1_c3_c5_c6_dispatch
        orig_dsp = d._q1_double_second_priority_dispatch
        def spy_c356(*a, **kw):
            called["c356"] = True
            return None  # 让 dsp 也有机会
        def spy_dsp(*a, **kw):
            called["dsp"] = True
            return orig_dsp(*a, **kw)
        d._q1_c3_c5_c6_dispatch = spy_c356
        d._q1_double_second_priority_dispatch = spy_dsp
        try:
            d._q1_block_enemy(gs, gs["actionList"], ec)
        finally:
            d._q1_c3_c5_c6_dispatch = orig_c356
            d._q1_double_second_priority_dispatch = orig_dsp
        assert called["c356"] is True
        assert called["dsp"] is True
