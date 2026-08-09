# -*- coding: utf-8 -*-
"""GUA-219 残局敌方报单领出 `_is_bomb_destroying_action` 不识别隐式配子炸。

场景（打桩验证 57 回合）：配子炸 K 族 = {CK,DK,H2}（组牌引擎 G0(Bomb):['CK','DK','DK','H2']，
3K+H2 成 Bomb/K，K 天然仅 3 张）。候选 TWT/K、Trips/K、Pair/K、Pair/2(S2,H2) 均拆 K 炸；
Pair/J(HJ DJ)、Pair/A(SA DA) 不拆。

修复前 `_is_bomb_destroying_action`（endgame_decide.py:2828-2833）只认「手牌某 rank ≥4 张」的
显式炸：K 天然仅 CK,DK,DK 3 张（H2 归 rank 2 组）→ 对 K 不触发 in_hand>=4 → 所有用 K 的候选判
False（不拆炸）→ safe_structured 含 TWT/K（`_q1_structure_priority` ThreeWithTwo=1 最高）→
`_select_enemy_one_locking_structure` 选 TWT/K 拆掉 Bomb/K。

修复后回溯组牌引擎 `_group_members`（识别隐式配子炸成员牌）→ TWT/K/Trips/K/Pair/K/Pair/2 判拆炸
被滤 → safe_structured 只剩 Pair/J + Pair/A → 按 `_q1_structure_priority`（同 Pair=5）+
`_max_card_value`（J<A）→ Pair/J（保留 Bomb/K 兜底）。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import EndgameDecider


# 复现局手牌：K 炸族 {CK,DK,DK,H2} + 对J + 对A + 散牌（S2 与 H2 可组 Pair/2）
HAND_REPRO = [
    "CK", "DK", "DK", "H2",
    "HJ", "DJ",
    "SA", "DA",
    "S2", "S3", "C4", "S4",
]

GROUP_MEMBERS = {
    0: ["CK", "DK", "DK", "H2"],   # G0(Bomb): 隐式配子炸（3K+H2）
    1: ["HJ", "DJ"],               # G1(pair)
    2: ["SA", "DA"],               # G2(pair)
    -1: ["S2", "S3", "C4", "S4"],  # 散牌
}

GROUP_GID_TYPE = {
    0: "Bomb",
    1: "pair",
    2: "pair",
    -1: "scatter",
}


def build_action_list():
    """复现局 actionList。候选含拆炸整牌（TWT/K、Trips/K、Pair/K、Pair/2）与安全对子。"""
    return [
        ["PASS", "PASS", "PASS"],                       # 0
        ["Pair", "J", ["HJ", "DJ"]],                    # 1: 不拆 K 炸 → 安全
        ["Pair", "A", ["SA", "DA"]],                    # 2: 不拆 K 炸 → 安全
        ["Pair", "K", ["CK", "DK"]],                    # 3: 拆 K 炸
        ["Pair", "K", ["DK", "DK"]],                    # 4: 拆 K 炸
        ["Pair", "2", ["S2", "H2"]],                    # 5: 用 H2 → 拆 K 炸
        ["Trips", "K", ["CK", "DK", "DK"]],             # 6: 拆 K 炸
        ["ThreeWithTwo", "K", ["CK", "DK", "DK", "S3", "C4"]],  # 7: 拆 K 炸
        ["ThreeWithTwo", "K", ["CK", "DK", "DK", "S3", "S4"]],  # 8: 拆 K 炸
        ["ThreeWithTwo", "K", ["CK", "DK", "DK", "C4", "S4"]],  # 9: 拆 K 炸
    ]


def build_state(greater_action="LEAD", enemy_remaining=1):
    """构造复现局。greater_action="LEAD" 表示自由领出（敌方报单领出轮）。"""
    if greater_action == "LEAD":
        g_action = []
        g_pos = -1
        cur_pos = 0
    else:
        g_action = greater_action
        g_pos = 3
        cur_pos = 0
    game_state = {
        "myPos": 0,
        "curPos": cur_pos,
        "greaterPos": g_pos,
        "greaterAction": g_action,
        "curRank": "2",
        "handCards": list(HAND_REPRO),
        "numofplayers": [len(HAND_REPRO), enemy_remaining, 9, 9],
        "_botzone_mode": True,
        "_group_members": dict(GROUP_MEMBERS),
        "_group_gid_type_map": dict(GROUP_GID_TYPE),
    }
    ec = {
        "my_pos": 0,
        "cur_pos": cur_pos,
        "cur_rank": "2",
        "numofplayers": [len(HAND_REPRO), enemy_remaining, 9, 9],
        "enemies": {
            1: {
                "remaining": enemy_remaining,
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
        "teammate": {"remaining": 9, "is_close": False, "assist_prefer": []},
        "self": {
            "remaining": len(HAND_REPRO),
            "has_two_clean_hands": False,
            "has_bomb": True,
            "should_sprint": False,
        },
        "finished": [],
    }
    return game_state, ec


class TestGua219ImplicitWildBomb:
    def test_twt_k_destroys_wild_bomb(self):
        """TWT/K（用 CK,DK,DK）→ 拆隐式配子炸 K → True"""
        gs, _ = build_state()
        d = EndgameDecider()
        for idx in (7, 8, 9):
            assert d._is_bomb_destroying_action(build_action_list()[idx], HAND_REPRO, gs) is True, \
                f"idx {idx} TWT/K 应判拆 K 炸"

    def test_trips_pair_k_destroy_wild_bomb(self):
        """Trips/K、Pair/K、Pair/2(S2,H2) → 拆隐式配子炸 K → True"""
        gs, _ = build_state()
        d = EndgameDecider()
        for idx in (3, 4, 5, 6):
            assert d._is_bomb_destroying_action(build_action_list()[idx], HAND_REPRO, gs) is True, \
                f"idx {idx} 应判拆 K 炸"

    def test_pair_j_a_keep_wild_bomb(self):
        """Pair/J、Pair/A（不用 K 族牌）→ 不拆 K 炸 → False"""
        gs, _ = build_state()
        d = EndgameDecider()
        for idx in (1, 2):
            assert d._is_bomb_destroying_action(build_action_list()[idx], HAND_REPRO, gs) is False, \
                f"idx {idx} 不应判拆 K 炸"

    def test_complete_bomb_action_not_destroying(self):
        """完整 Bomb/K 动作本身 → False（不拆炸，GUA-206 语义）"""
        gs, _ = build_state()
        d = EndgameDecider()
        bomb_act = ["Bomb", "K", ["CK", "DK", "DK", "H2"]]
        assert d._is_bomb_destroying_action(bomb_act, HAND_REPRO, gs) is False

    def test_select_locking_structure_picks_pair_j(self):
        """safe_structured 只剩 Pair/J + Pair/A → 按 priority(5) + max_card_value(J<A) 选 Pair/J"""
        gs, _ = build_state()
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(build_action_list())]
        structured = [(i, a) for i, a in candidates
                      if a[0] not in ("PASS", "Single")
                      and a[0] not in ("Bomb", "StraightFlush", "JokerBomb")]
        safe_structured = [
            (i, a) for i, a in structured
            if not d._is_bomb_destroying_action(a, HAND_REPRO, gs)
        ]
        assert safe_structured, "应有安全整牌候选"
        picked = d._select_enemy_one_locking_structure(safe_structured, gs)
        assert picked is not None
        idx, act = picked
        assert act[0] == "Pair", f"应选 Pair 保留 K 炸；实际出 {act}"
        assert act[1] == "J", f"J<A 应选 Pair/J；实际出 {act}"


class TestGua219EndToEnd:
    def test_q1_enemy_critical_lead_picks_pair_j(self):
        """端到端 `_q1_enemy_critical_lead_special`：敌方报单领出轮 → 出 Pair/J（非 TWT/K）"""
        gs, ec = build_state(enemy_remaining=1)
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(build_action_list())]
        result = d._q1_enemy_critical_lead_special(
            gs, candidates, ec, main_pos=1,
            main_enemy=ec["enemies"][1],
        )
        assert result is not None, "敌方报单领出轮应有整牌锁敌候选"
        idx, act = result
        assert act[0] == "Pair", f"应保留 K 炸出 Pair；实际出 {act}"
        assert act[1] == "J", f"应出 Pair/J；实际出 {act}"
        assert act[2] == ["HJ", "DJ"], f"Pair/J 应为 HJ DJ；实际 {act}"


class TestGua219Fallback:
    def test_no_group_members_falls_back_rank_count(self):
        """`_group_members` 缺失 → 回退手牌 rank≥4 显式炸计数（旧行为保持）"""
        hand = ["S8", "H8", "C8", "D8", "D9", "H9", "S3"]  # 4×8 = 显式炸 core
        act = ["Pair", "8", ["S8", "H8"]]
        d = EndgameDecider()
        # 无 _group_members → 旧 rank 计数仍判拆炸
        assert d._is_bomb_destroying_action(act, hand) is True
        # 显式 4×8 在 _group_members 中以 Bomb 组提供 → 新逻辑同样判拆炸
        gs = {
            "_group_members": {0: ["S8", "H8", "C8", "D8"], 1: ["D9", "H9"], -1: ["S3"]},
            "_group_gid_type_map": {0: "Bomb", 1: "pair", -1: "scatter"},
        }
        assert d._is_bomb_destroying_action(act, hand, gs) is True
        # 非拆核对子 → False
        act9 = ["Pair", "9", ["D9", "H9"]]
        assert d._is_bomb_destroying_action(act9, hand, gs) is False
