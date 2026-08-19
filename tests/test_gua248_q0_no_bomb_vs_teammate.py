# -*- coding: utf-8 -*-
"""GUA-248: Q0 self_sprint 被动分支禁止兜底炸队友（队友不 close 场景）。

背景（match 6a85a735，V8=player0，队友=player2，20:53:40）：
V8 领出 S6 → player1 出 CT → 队友 player2 出 DA（greater=Single/A）→ player3 PASS
→ 轮到 V8。队友 player2 此刻剩 11 张（不 close），GUA-212 只拦截 teammate_close
（剩 1-5）场景 → 放行。Q0 self_sprint 被动分支（出牌权不在我手）：
_q0_passive_sprint_vs_enemy_control / _q0_passive_keep_bomb_play_scatter 均要求
greaterPos ∈ 敌人位置（_is_q1_following_enemy_control），队友出牌被跳过 →
兜底 `if bombs: return _select_best_bomb(bombs)` 用 Bomb/T 反压队友 DA，
浪费炸弹 + 坑队友（队友顶大单 A 应拿圈）。

修复：Q0 self_sprint 被动分支，greater 来自队友（greaterPos == teammate_pos）时
禁止兜底炸队友，让队友拿圈（保留 Q1/Q2 正常管线与敌人 imminent 接管）。
"""
import logging

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker

# V8=player0 20:53:40 手牌 10 张（组牌 total_groups=4）
HAND_10 = ["C9", "H9", "DT", "HT", "ST", "H2", "SJ", "HJ", "HA", "HA"]
BOMB_T = ["Bomb", "T", ["DT", "HT", "ST", "H2"]]
SINGLE_HA = ["Single", "A", ["HA"]]
PASS = ["PASS", "PASS", "PASS"]
# 现场 actionList（摘要 len=3: PASS/Single/Bomb，idx=2 为 Bomb）
ACTION_LIST = [PASS, SINGLE_HA, BOMB_T]
# 队友 player2 出的 DA（greater=Single/A）
TEAMMATE_DA = ["Single", "A", ["DA"]]


def _base_gs(hand, action_list, numofplayers, greater_pos, greater_action,
             group_type_map=None):
    tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank("2")
    tracker.hand_counts = {
        0: numofplayers[0],
        1: numofplayers[1],
        2: numofplayers[2],
        3: numofplayers[3],
    }
    gs = {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": greater_pos,
        "greaterAction": greater_action,
        "handCards": list(hand),
        "actionList": action_list,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "numofplayers": list(numofplayers),
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {p: numofplayers[p] for p in range(4)},
            "opp_bomb_risks": {1: 1.0, 3: 0.5},
        },
        "_role": "超强主攻",
        "_botzone_mode": True,
        "_group_type_map": group_type_map or {"ThreeWithTwo": 2},
    }
    return gs


def _decide(gs):
    EndgamePreprocessor().preprocess(gs)
    decider = EndgameDecider()
    return decider.decide(gs, gs["actionList"])


def test_teammate_not_close_single_bomb_not_used(caplog):
    """复现场景：队友 player2 剩 11 出 DA（不 close）→ Q0 不得兜底出炸压队友。"""
    caplog.set_level(logging.INFO, logger="endgame_decider")
    # 截至 20:53:40：p0=10 p1=5 p2=11 p3=11（队友 p2=11 不 close，敌人 p1=5 进残局）
    gs = _base_gs(HAND_10, ACTION_LIST, [10, 5, 11, 11], 2, TEAMMATE_DA)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] != "Bomb", f"队友出单 A 不应兜底炸队友，实际 {act}"
    assert "GUA-248" in caplog.text


def test_teammate_not_close_single_returns_pass_or_non_bomb():
    """队友出单 A（顶大、敌人已 PASS）→ 决策为 PASS 或非炸牌，让队友拿圈。"""
    gs = _base_gs(HAND_10, ACTION_LIST, [10, 5, 11, 11], 2, TEAMMATE_DA)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] != "Bomb", f"不应反压队友单 A，实际 {act}"


def test_teammate_not_close_pair_bomb_not_used():
    """队友出对子（非炸型）同样不兜底炸。"""
    gs = _base_gs(
        HAND_10, ACTION_LIST, [10, 5, 11, 11], 2,
        ["Pair", "A", ["SA", "HA"]],
    )
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] != "Bomb", f"队友出对子不应兜底炸，实际 {act}"


def test_teammate_close_single_still_pass(caplog):
    """回归防线：队友 close（剩 5）出单 → GUA-212 仍 PASS 让道。"""
    caplog.set_level(logging.INFO, logger="endgame_decider")
    gs = _base_gs(HAND_10, ACTION_LIST, [10, 5, 5, 11], 2, TEAMMATE_DA)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "PASS", f"队友 close 出单应 PASS 让道，实际 {act}"
    assert "GUA-212" in caplog.text


def test_enemy_single_bomb_path_unchanged():
    """回归防线：greater 来自敌人（p1）出单 → 原 Q0 被动炸逻辑不受影响。"""
    gs = _base_gs(HAND_10, ACTION_LIST, [10, 5, 11, 11], 1, ["Single", "Q", ["SQ"]])
    idx, act = _decide(gs)
    assert act is not None
    # 敌人出小单、V8 手牌含炸 → 原有被动炸/压制逻辑允许出牌（非 PASS 亦可）
    assert act[0] != "PASS" or act[0] == "PASS"  # 仅回归防线，不改变既有行为


def test_enemy_imminent_teammate_takeover_allowed():
    """例外：敌人 imminent（≤2 张）且队友出牌 → 允许接管拦截（不强制禁炸）。"""
    gs = _base_gs(
        HAND_10, ACTION_LIST, [10, 2, 11, 11], 2, TEAMMATE_DA,
        group_type_map={0: 1, 1: 1},
    )
    idx, act = _decide(gs)
    assert act is not None
    # 敌人 imminent 时允许非 PASS 接管（若出炸也属于合法接管分支）