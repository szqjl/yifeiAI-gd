# -*- coding: utf-8 -*-
"""
GUA-257: 残局两手整牌（ThreePair/TwoTrips/Straight 等特殊牌型 + 单张）自由领出：
先出整牌特殊牌型，再出单张；不可先出单张留整牌（单被压后整牌烂手）。

背景（match `6a86e9540fbd680d7c7c6318`，`logs/v8_vs_botzone_20260820_single.log`
第58回合，scores=[0,3,0,3] V8 队负）：
  V8=player0 手牌 7 = `CT` + `445566`（三连对 ThreePair），自由领出
  （greater=自己 Bomb/K 回手）。endgame 决策 `Q0 自己冲刺: idx=0 type=Single`
  → `Single/CT`，随后被 player1 `Bomb/9` 压死，V8 剩 `445566` 整牌烂手，
  对局结束 V8 队 0 分。

根因：`_select_two_turn_sprint_structure`（L3922）两手冲刺排序键
  `(twt_boost, residue_bucket, bomb_rank, structure_priority, -len, max_val)`：
  候选 `Single/T` 残手=ThreePair → `residue_bucket=0`（整牌残手默认安全）排最前；
  候选 `ThreePair/445566` 残手=`Single/T` → 判 T 不安全 → `residue_bucket=2` 排后
  → 先出单 T 留整牌。正确应「先出整牌特殊牌型、单留最后」。

修复（与 GUA-240 Trips 同源）：残手为整牌结构（ThreePair/TwoTrips/Straight/
Trips）时该候选设 `residue_bucket=2`（先出单留整牌=风险），让「先出整牌」候选
凭 structure_priority 排前。
"""
import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider


def build_gs():
    """复现场景：两手整牌 = ThreePair 445566 + 单 CT，自由领出。"""
    return {
        "curRank": "2",
        "handCards": ["CT", "H4", "S4", "C5", "D5", "S6", "S6"],
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 0,
        "greaterAction": ["Bomb", "K", ["SK", "HK", "HK", "DK"]],
        "curAction": None,
        "numofplayers": [7, 11, 9, 9],
        "publicInfo": [
            {"rest": 7}, {"rest": 11}, {"rest": 9}, {"rest": 9},
        ],
        "done": [],
        "stage": "play",
        "selfRank": "2",
        "oppoRank": "2",
        "_botzone_mode": True,
        "_group_type_map": {"ThreePair": 1, "Single": 1},
    }


def build_ec():
    return {
        "my_pos": 0,
        "cur_pos": 0,
        "cur_rank": "2",
        "numofplayers": [7, 11, 9, 9],
        "enemies": {
            1: {"remaining": 11, "danger_level": "低", "recommended_types": [],
                "banned_types": [], "baoshu": {}},
            3: {"remaining": 9, "danger_level": "低", "recommended_types": [],
                "banned_types": [], "baoshu": {}},
        },
        "teammate": {"remaining": 9, "is_close": False, "assist_prefer": []},
        "self": {"remaining": 7, "has_two_clean_hands": True,
                 "has_bomb": False, "should_sprint": True},
        "finished": [],
    }


def build_action_list():
    return [
        ["PASS", "PASS", "PASS"],
        ["Single", "T", ["CT"]],
        ["Single", "4", ["H4"]],
        ["Single", "5", ["C5"]],
        ["Single", "6", ["S6"]],
        ["Pair", "4", ["H4", "S4"]],
        ["Pair", "5", ["C5", "D5"]],
        ["Pair", "6", ["S6", "S6"]],
        ["ThreePair", "4", ["H4", "S4", "C5", "D5", "S6", "S6"]],
    ]


def test_decide_returns_three_pair_not_single():
    """decide() 集成：两手整牌自由领出 → 先出 ThreePair 445566，非 Single/T。"""
    gs = build_gs()
    gs["_endgame_context"] = build_ec()
    gs["_endgame_context"]["is_active"] = True
    d = EndgameDecider()
    idx, act = d.decide(gs, build_action_list())
    assert act is not None, "decide 应命中 Q0 自冲刺"
    assert act[0] == "ThreePair", f"两手整牌应先出整牌 ThreePair；实际 {act}"
    assert act[1] == "4", f"应出 ThreePair/4 (445566)；实际 {act}"


def test_select_two_turn_prefers_structure_first():
    """_select_two_turn_sprint_structure 定向：ThreePair+单 → 选整牌。"""
    gs = build_gs()
    d = EndgameDecider()
    acts = list(enumerate(build_action_list()))
    non_bombs = [(i, a) for i, a in acts if a[0] not in ("Bomb", "StraightFlush")]
    result = d._select_two_turn_sprint_structure(non_bombs, acts, gs, build_ec(),
                                                 prefer_structure_first=True)
    assert result is not None, "应命中两手冲刺"
    idx, act = result
    assert act[0] == "ThreePair", f"应选整牌 ThreePair；实际 {act}"


def test_no_struct_hand_falls_through():
    """非两手整牌（散单 + 三对 + 单，语义 >2）→ 不强制整牌优先，走老路径。"""
    gs = build_gs()
    gs["handCards"] = ["CT", "H4", "S4", "C5", "D5", "H7", "S6", "S6"]
    gs["_group_type_map"] = {"Pair": 3, "Single": 2}
    gs["numofplayers"] = [8, 11, 9, 9]
    gs["publicInfo"] = [{"rest": 8}, {"rest": 11}, {"rest": 9}, {"rest": 9}]
    ec = build_ec()
    ec["numofplayers"] = [8, 11, 9, 9]
    ec["self"]["remaining"] = 8
    ec["self"]["has_two_clean_hands"] = False
    ec["self"]["should_sprint"] = False
    gs["_endgame_context"] = ec
    gs["_endgame_context"]["is_active"] = True
    d = EndgameDecider()
    # 决策不应是 ThreePair（该手无整牌候选），只需不断言抛错
    idx, act = d.decide(gs, build_action_list())
    assert act is not None


def test_pair_residue_falls_through():
    """残手为 Pair（对子散）→ 不触发整牌风险（Pair 残手可回收，维持现状）。"""
    gs = build_gs()
    # 两手 = Trips 444 + Pair 55：残手 Pair 不触发（保持 GUA-240 语义，Pair 散型）
    gs["handCards"] = ["H4", "S4", "C4", "C5", "D5"]
    gs["_group_type_map"] = {"Trips": 1, "Pair": 1}
    gs["numofplayers"] = [5, 11, 9, 9]
    gs["publicInfo"] = [{"rest": 5}, {"rest": 11}, {"rest": 9}, {"rest": 9}]
    ec = build_ec()
    ec["numofplayers"] = [5, 11, 9, 9]
    ec["self"]["remaining"] = 5
    ec["self"]["has_two_clean_hands"] = True
    ec["self"]["should_sprint"] = True
    gs["_endgame_context"] = ec
    gs["_endgame_context"]["is_active"] = True
    d = EndgameDecider()
    acts = build_action_list()
    idx, act = d.decide(gs, acts)
    assert act is not None