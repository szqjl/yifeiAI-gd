# -*- coding: utf-8 -*-
"""GUA-260：锁敌整牌按残手质量选，禁止拆 trips 拼 TWT。

锚点 match `6a87e5a30fbd680d7c7d8acf`（logs/v8_vs_botzone_20260821_133714.log
13:44:38）：手牌 555+777+H3，下家剩 2，组牌为 2×trips+scatter；Q1 锁敌却因
structure_priority(TWT≻Trips) 打出 ThreeWithTwo/5，残手两张散单。
应先 Trips/5，留下 Trips/7+单争二游。
"""

from __future__ import annotations

from src.communication.botzone_adapter import ActionListGenerator
from src.v.nn import UltimateWinRateEngineV7
from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.guards.v7_guards import get_action_type


HAND = ["C5", "H5", "S5", "D7", "H7", "S7", "H3"]


def _lead_state(numofplayers=(7, 2, 8, 0)):
    gen = ActionListGenerator(cur_rank="2")
    action_list = gen.generate_lead_actions(list(HAND))
    return {
        "actionList": action_list,
        "handCards": list(HAND),
        "myPos": 0,
        "curPos": 0,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "stage": "play",
        "greaterPos": -1,
        "greaterAction": ["PASS", "PASS", "PASS"],
        "curAction": ["PASS", "PASS", "PASS"],
        "done": [3],
        "numofplayers": list(numofplayers),
        "publicInfo": [{"rest": n} for n in numofplayers],
        "_botzone_mode": True,
        "history": [],
        # 与实测组牌一致：两 trips + 散单（无 TWT 组）
        "_group_members": {
            0: ["C5", "H5", "S5"],
            1: ["D7", "H7", "S7"],
            -1: ["H3"],
        },
        "_group_gid_type_map": {0: "trips", 1: "trips", -1: "scatter"},
    }


def test_gua260_locking_prefers_trips_over_twt_breaking_trips():
    """锁敌候选含 Trips/5 与 TWT/55577 → 选完整 Trips，不拆 777。"""
    gs = _lead_state()
    d = EndgameDecider()
    cands = [
        (i, a)
        for i, a in enumerate(gs["actionList"])
        if get_action_type(a) in ("Trips", "ThreeWithTwo", "Pair")
    ]
    picked = d._select_enemy_one_locking_structure(cands, gs)
    assert picked is not None
    _, act = picked
    assert get_action_type(act) == "Trips", f"应选 Trips 非 TWT，实际 {act}"
    assert act[1] == "5", f"应先出较小 Trips/5，实际 {act}"


def test_gua260_twt_breaks_core_trips():
    """55577 消耗 trips/7 的两张 → 判拆核心。"""
    gs = _lead_state()
    twt = ["ThreeWithTwo", "5", ["C5", "H5", "S5", "D7", "H7"]]
    trips = ["Trips", "5", ["C5", "H5", "S5"]]
    d = EndgameDecider()
    assert d._action_breaks_core_structure(twt, gs) is True
    assert d._action_breaks_core_structure(trips, gs) is False


def test_gua260_residue_metrics_twt_all_scatter():
    """TWT 后残手两散单；Trips 后残手仍有 trips。"""
    hands_t, scatter_t = EndgameDecider._locking_residue_metrics(
        ["ThreeWithTwo", "5", ["C5", "H5", "S5", "D7", "H7"]], HAND,
    )
    hands_r, scatter_r = EndgameDecider._locking_residue_metrics(
        ["Trips", "5", ["C5", "H5", "S5"]], HAND,
    )
    assert hands_t == 2 and scatter_t == 1
    assert hands_r == 2 and scatter_r == 0


def test_gua260_decide_enemy_two_lead_trips_not_twt():
    """端到端：下家 rest=2 领出 → Trips/5，非 ThreeWithTwo。"""
    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
    gs = _lead_state((7, 2, 8, 0))
    # 去掉预注入组牌，让引擎自己组（应仍为 2×trips）
    gs.pop("_group_members", None)
    gs.pop("_group_gid_type_map", None)
    idx = engine.decide(gs)
    chosen = gs["actionList"][idx]
    assert get_action_type(chosen) == "Trips", f"应出 Trips，实际 {chosen}"
    assert chosen[1] == "5"
