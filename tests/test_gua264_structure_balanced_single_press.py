# -*- coding: utf-8 -*-
"""GUA-264：跟压单时散单 vs 拆对 — 牌力差≤2 不拆；已散能压则优先用散单。

锚点 match `6a8808310fbd680d7c7da305`（logs/v8_vs_botzone_20260821_160611.log）：
  16:11:53 手 DJ+QQ+AA 压 Single/4 → 误拆 SQ（J/Q 差 1）
  16:11:56 手 DJ+CQ+AA 压 Single/9 → 误拆 DA（大单张≥K 滤掉 Q；A/Q 差 2）

用户定音：
  ① 真散单与拆对单牌力差 ≤2 → 不拆，出散单
  ② 已拆过留下的散单能压 → 优先再用，勿再拆新对
  ③ 差 >2 或无敌方报单防守需要时仍可拆
"""

from __future__ import annotations

from src.communication.botzone_adapter import ActionListGenerator
from src.v.nn import UltimateWinRateEngineV7


def _follow_state(hand, greater, numofplayers):
    gen = ActionListGenerator(cur_rank="2")
    action_list = gen.generate_follow_actions(list(hand), greater)
    return {
        "actionList": action_list,
        "handCards": list(hand),
        "myPos": 0,
        "curPos": 0,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "stage": "play",
        "greaterPos": 3,
        "greaterAction": greater,
        "curAction": greater,
        "done": [],
        "numofplayers": list(numofplayers),
        "publicInfo": [{"rest": n} for n in numofplayers],
        "_botzone_mode": True,
        "history": [],
    }


def test_gua264_prefer_scatter_j_over_split_q_when_diff_le_2():
    """下家≈6：DJ 散 + QQ → 压 Single/4 应出 J，不拆 Q（差 1）。"""
    hand = ["DJ", "SQ", "CQ", "DA", "SA"]
    greater = ["Single", "4", ["H4"]]
    # 下家 player3 剩 6（用户口径）；无报单
    gs = _follow_state(hand, greater, (5, 8, 10, 6))
    engine = UltimateWinRateEngineV7(use_grouping_engine=True)
    idx = engine.decide(gs)
    act = gs["actionList"][idx]
    assert act[0] == "Single" and act[1] == "J", act


def test_gua264_reuse_split_q_over_split_a_when_diff_le_2():
    """已拆 QQ 剩 CQ：压 Single/9 应出 CQ，不拆 AA（差 2；且躲过「大单张≥K」）。"""
    hand = ["DJ", "CQ", "DA", "SA"]
    greater = ["Single", "9", ["D9"]]
    # 下家剩 5；player1 非报单（避免 GUA-222）
    gs = _follow_state(hand, greater, (4, 6, 9, 5))
    engine = UltimateWinRateEngineV7(use_grouping_engine=True)
    idx = engine.decide(gs)
    act = gs["actionList"][idx]
    assert act[0] == "Single" and act[1] == "Q", act


def test_gua264_allow_split_when_power_gap_gt_2():
    """仅散 J + 对 A：A−J=3 >2 → 允许拆 A 压 Single/9。"""
    hand = ["DJ", "DA", "SA"]
    greater = ["Single", "9", ["D9"]]
    gs = _follow_state(hand, greater, (3, 6, 9, 5))
    engine = UltimateWinRateEngineV7(use_grouping_engine=True)
    idx = engine.decide(gs)
    act = gs["actionList"][idx]
    assert act[0] == "Single" and act[1] == "A", act


def test_gua264_enemy_one_still_allows_max_split():
    """敌方报单剩 1：防守优先，仍可出最大单（拆 A）。"""
    hand = ["DJ", "CQ", "DA", "SA"]
    greater = ["Single", "9", ["D9"]]
    gs = _follow_state(hand, greater, (4, 1, 9, 5))
    engine = UltimateWinRateEngineV7(use_grouping_engine=True)
    idx = engine.decide(gs)
    act = gs["actionList"][idx]
    assert act[0] == "Single" and act[1] == "A", act
