# -*- coding: utf-8 -*-
"""GUA-212: 残局 Q0 冲刺 / Q1 封锁不再把队友当敌方反压。

背景（对局 R16，V8=player2，队友=player0，myPos=2/teammate=0）：
残局队友已控牌（close，剩 5 张）压出 Straight/T（TJQKA 顺），V8 剩 9 张
should_sprint=True 落入 Q0 self_sprint，原逻辑直接出四头炸10 反压队友，
出完剩 C2 D3 D4 D5 S5 烂尾。根因：原「不压队友」规则只拦队友出炸型
（Bomb/StraightFlush），队友出非炸型（顺子）时放行，Q0 self_sprint
不检查 greater 是否队友。

修复：decide 入口（Q0 之前）扩展 GUA-212：greaterPos 为 teammate、
teammate close 控牌（剩 ≤5）且出任意非 PASS 牌型 → 一律 PASS 让道；
例外：有敌人 ≤2 张（imminent）时允许接管拦截。
队友剩牌多不 close 时保留 GUA-113「主攻帮挡」（敌人可能压制队友时主攻
拿回控制权）语义，不强制让道。
"""
import logging

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker

HAND_10 = ["C2", "CT", "D3", "D4", "D5", "DT", "H6", "HT", "HT", "S5"]
BOMB_T = ["Bomb", "T", ["CT", "DT", "HT", "HT"]]
PASS = ["PASS", "PASS", "PASS"]
ACTION_LIST = [BOMB_T, PASS]
# 队友 TJQKA 顺（R16 队友 player0 压出的 Straight/T）
STRAIGHT_T = ["Straight", "T", ["DT", "SJ", "DQ", "CK", "CA"]]


def _base_gs(hand, action_list, numofplayers, greater_pos, greater_action,
             group_type_map=None):
    tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank("K")
    tracker.hand_counts = {
        0: numofplayers[0],
        1: numofplayers[1],
        2: numofplayers[2],
        3: numofplayers[3],
    }
    gs = {
        "myPos": 2,
        "curPos": greater_pos,
        "greaterPos": greater_pos,
        "greaterAction": greater_action,
        "handCards": list(hand),
        "actionList": action_list,
        "curRank": "K",
        "selfRank": "K",
        "oppoRank": "K",
        "numofplayers": list(numofplayers),
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {p: numofplayers[p] for p in range(4)},
            "opp_bomb_risks": {1: 1.0, 3: 0.5},
        },
        "_role": "超强主攻",
    }
    if group_type_map is not None:
        gs["_group_type_map"] = group_type_map
    return gs


def _decide(gs):
    EndgamePreprocessor().preprocess(gs)
    decider = EndgameDecider()
    return decider.decide(gs, gs["actionList"])


def _no_imminent_enemy():
    # teammate=0 剩 5（close），敌人 p1=15 / p3=5 均 >2 → 非 imminent
    return [5, 15, 9, 5]


def test_r16_teammate_straight_returns_pass():
    """R16 复现：队友出 Straight/T，V8 手牌含炸10 → 决策 PASS 而非炸队友。"""
    gs = _base_gs(HAND_10, ACTION_LIST, _no_imminent_enemy(), 0, STRAIGHT_T)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "PASS", f"队友出顺子应 PASS 让道，实际 {act}"
    assert idx == 1


def test_teammate_pair_returns_pass():
    """队友出对子（非炸型）同样 PASS。"""
    gs = _base_gs(
        HAND_10, ACTION_LIST, _no_imminent_enemy(), 0,
        ["Pair", "A", ["SA", "HA"]],
    )
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "PASS", f"队友出对子应 PASS 让道，实际 {act}"


def test_teammate_single_returns_pass():
    """队友出单张（非炸型）同样 PASS。"""
    gs = _base_gs(
        HAND_10, ACTION_LIST, _no_imminent_enemy(), 0,
        ["Single", "A", ["SA"]],
    )
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "PASS", f"队友出单张应 PASS 让道，实际 {act}"


def test_teammate_bomb_returns_pass():
    """队友出炸型（Bomb）仍 PASS（原有行为回归）。"""
    gs = _base_gs(
        HAND_10, ACTION_LIST, _no_imminent_enemy(), 0,
        ["Bomb", "8", ["C8", "S8", "C8", "S8"]],
    )
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "PASS", f"队友出炸应 PASS 让道，实际 {act}"


def test_teammate_not_close_not_forced_pass(caplog):
    """队友不 close（剩 8）→ GUA-212 分支不触发（保留 GUA-113 帮挡/正常决策）。"""
    import logging
    caplog.set_level(logging.INFO, logger="src.v.nn.endgame.endgame_decide")
    # teammate=0 剩 8（不 close），敌人 p1=15 / p3=5 非 imminent
    gs = _base_gs(HAND_10, ACTION_LIST, [8, 15, 9, 5], 0, STRAIGHT_T)
    idx, act = _decide(gs)
    assert act is not None
    assert "GUA-212" not in caplog.text, "队友不 close 不应触发 GUA-212 让道"


def test_enemy_imminent_allows_takeover():
    """例外：有敌人 ≤2 张（imminent）→ GUA-212 不强制 PASS，Q0/Q1 可接管。"""
    # teammate=0 剩 5，敌人 p1=2 imminent；注入两手整牌（Bomb+单手）触发 Q0 sprint
    gs = _base_gs(
        ["CT", "DT", "HT", "HT", "SA", "SK", "C2", "D3", "D4"],
        ACTION_LIST, [5, 2, 9, 15], 0, STRAIGHT_T,
        group_type_map={0: 1, 1: 1},
    )
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] != "PASS", f"敌人 imminent 时应接管拦截，实际强制 PASS {act}"


def test_greater_from_enemy_not_blocked():
    """greater 来自敌人（p3）→ GUA-212 不介入，正常出牌（回归防线）。"""
    gs = _base_gs(HAND_10, ACTION_LIST, _no_imminent_enemy(), 3, STRAIGHT_T)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] != "PASS", f"敌人出顺子不应因队友规则 PASS，实际 {act}"
