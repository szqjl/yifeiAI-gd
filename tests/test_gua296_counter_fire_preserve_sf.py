# -*- coding: utf-8 -*-
"""GUA-296：counter 开炸「炸够用就好、不拆原组牌 StraightFlush 凑 5 星炸」。

锚点：match=6a95841d1b27100f38db7794 第12回合（logs/fetch_match_6a95841d...log）。
  上家 player3 出 4 头炸 `Bomb/QQQQ`，V8 手 25 张结构：
    G0 3炸: D3,H3,D3,C3（4张）
    G1 4炸: H4,C4,H4,D4（4张）
    G2 同花顺: S3,S4,S5,S6,S7（黑桃 3-7）
    G3 straight: H9,CT,SJ,CQ,HK ；G4 pair: H7,S7 ；G-1 scatter: DT,HJ,DK,DA,D2
  actionList 4 项：PASS / Bomb×2（33333 5星、44444 5星）/ StraightFlush(3-7)。
  4 头炸 3、4 均压不过 4 头炸 QQQQ（同 4 星比点 3、4 < Q）→ 按用户规则
  「4 星不够压对手炸时用同花顺」→ 应出 `StraightFlush/3`，保留 3炸+4炸。
  实际却拆同花顺（GUA-154 self 记 broken=['StraightFlush']）用 `Bomb/33333`
  5 星炸，失去同花顺+3炸+4炸 结构，且多出 S5、S6 两散单（V8 队负）。

用户定音（2026-08-31）：设本副有 5个3、5个4（皆含黑桃3/4）+ 黑桃5/6/7，
  对手 4个Q。4星 3、4 均无法压过 4个Q → 应用 3-7 同花顺压，不用 5个3。
  不要拆原组牌引擎已组成的 StraightFlush 去凑 5 星炸。
"""
from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor

SF_37 = ["S3", "S4", "S5", "S6", "S7"]
BOMB_3 = ["D3", "H3", "D3", "C3"]
BOMB_4 = ["H4", "C4", "H4", "D4"]
BOMB_5STAR_3 = ["D3", "S3", "H3", "D3", "C3"]
BOMB_5STAR_4 = ["H4", "S4", "H4", "C4", "D4"]
G3_STRAIGHT = ["H9", "CT", "SJ", "CQ", "HK"]
G4_PAIR = ["H7", "S7"]
GSCATTER = ["DT", "HJ", "DK", "DA", "D2"]
BOMB_QQQQ = ["HQ", "HQ", "CQ", "DQ"]


_GROUP_MEMBERS = {
    "g0": list(BOMB_3),
    "g1": list(BOMB_4),
    "g2": list(SF_37),
    "g3": list(G3_STRAIGHT),
    "g4": list(G4_PAIR),
    "g_scatter": list(GSCATTER),
}
_GROUP_TYPE_MAP = {
    "g0": "Bomb",
    "g1": "Bomb",
    "g2": "StraightFlush",
    "g3": "straight",
    "g4": "pair",
    "g_scatter": "scatter",
}


def _counter_sf_state(*, hand_cards, action_list, numofplayers):
    return {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Bomb", "Q", BOMB_QQQQ],
        "handCards": list(hand_cards),
        "actionList": action_list,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "numofplayers": numofplayers,
        "_role": "主攻",
        "_group_members": dict(_GROUP_MEMBERS),
        "_group_gid_type_map": dict(_GROUP_TYPE_MAP),
    }


def _full_hand():
    return (BOMB_3 + BOMB_4 + SF_37 + G3_STRAIGHT + G4_PAIR + GSCATTER)


class TestGua296CounterFirePreserveSf:
    """GUA-296：counter 对手炸时不拆原组牌同花顺凑 5 星炸。"""

    def test_5star_vs_qqqq_prefers_sf_not_breaking_sf(self):
        """5个3(含S3)、5个4(含S4)+黑桃5/6/7，对手 4个Q → 出 StraightFlush(3-7)，不拆 SF。"""
        hand_cards = _full_hand()
        gs = _counter_sf_state(
            hand_cards=hand_cards,
            numofplayers=[25, 1, 1, 1],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["Bomb", "3", BOMB_5STAR_3],
                ["Bomb", "4", BOMB_5STAR_4],
                ["StraightFlush", "3", SF_37],
            ],
        )
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])

        assert act[0] == "StraightFlush", f"4星压不过 QQQQ，应用同花顺，实际 {act[0]}"
        assert act[1] == "3"
        assert act[2] == SF_37

    def test_sf_beats_greater_when_plus_ones_cannot(self):
        """同花顺允许压大于的 4 头炸（greaterPos=3 上家非队友）。"""
        hand_cards = _full_hand()
        gs = _counter_sf_state(
            hand_cards=hand_cards,
            numofplayers=[25, 1, 1, 1],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["StraightFlush", "3", SF_37],
                ["Bomb", "3", BOMB_5STAR_3],
                ["Bomb", "4", BOMB_5STAR_4],
            ],
        )
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert act[0] == "StraightFlush", f"应选 StraightFlush，实际 {act[0]}"


    def test_four_star_bomb_beats_greater_keeps_bomb(self):
        """若 4 星炸本身能压过对手炸（如对手 3 星/单，或自家 4 星点更大）→ 不必用 SF，炸够用就好。"""
        hand_cards = _full_hand()
        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 3,
            "greaterAction": ["Bomb", "3", ["D3", "H3", "C3", "S3"]],
            "handCards": list(hand_cards),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Bomb", "4", BOMB_4],
                ["StraightFlush", "3", SF_37],
            ],
            "curRank": "2",
            "selfRank": "2",
            "oppoRank": "2",
            "numofplayers": [25, 1, 1, 1],
            "_role": "主攻",
            "_group_members": dict(_GROUP_MEMBERS),
            "_group_gid_type_map": dict(_GROUP_TYPE_MAP),
        }
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        # 4 星 4炸 能压过 4 星 3炸（4>3），够用即可，不必动同花顺
        assert act[0] == "Bomb" and act[1] == "4", f"应选 Bomb/4 足够压，实际 {act}"

    def test_gua286_path_preserves_sf_vs_qqqq(self):
        """GUA-286 主敌剩4 跟压 QQQQ（hand 含 3炸+4炸+SF33-7）→ 用 SF 压，不拆 SF。"""
        hand_cards = _full_hand()
        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 1,
            "greaterAction": ["Bomb", "Q", BOMB_QQQQ],
            "handCards": list(hand_cards),
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["StraightFlush", "3", SF_37],
                ["Bomb", "4", BOMB_5STAR_4],
                ["Bomb", "3", BOMB_5STAR_3],
            ],
            "curRank": "2",
            "selfRank": "2",
            "oppoRank": "2",
            "numofplayers": [25, 4, 1, 20],
            "_role": "主攻",
            "_group_members": dict(_GROUP_MEMBERS),
            "_group_gid_type_map": dict(_GROUP_TYPE_MAP),
        }
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert act[0] == "StraightFlush", f"GUA-286 应选 SF 压 QQQQ 而非拆 SF，实际 {act[0]}"

    def test_power_order_helper_sf_gt_five_gt_four(self):
        """牌力序对齐：`_bomb_weakest_first_key` 弱→强 4星(40)<5星(50)<同花顺(55)，够用就好。"""
        from src.v.nn.endgame.endgame_decide import _bomb_weakest_first_key
        assert _bomb_weakest_first_key(["Bomb", "3", BOMB_3]) == 40
        assert _bomb_weakest_first_key(["Bomb", "3", BOMB_5STAR_3]) == 50
        assert _bomb_weakest_first_key(["StraightFlush", "3", SF_37]) == 55
        # 含配子（H2 级牌）的 5 星炸也能稳定判 5 星，不因 get_action_type 重导而失效
        wild_5star = ["Bomb", "3", ["C3", "D3", "H3", "S3", "H2"]]
        assert _bomb_weakest_first_key(wild_5star) == 50

    def test_cheapest_bomb_or_sf_weakest_sufficient(self):
        """`_select_cheapest_bomb_or_sf` 选最弱够用档：4星炸 ≻ 5星炸 ≻ 同花顺（牌力序一致、不浪费更强火力）。"""
        al = [
            ["PASS", "PASS", "PASS"],
            ["Bomb", "4", BOMB_5STAR_4],
            ["Bomb", "3", BOMB_5STAR_3],
            ["StraightFlush", "3", SF_37],
        ]
        picked = EndgameDecider()._select_cheapest_bomb_or_sf(al, "2")
        assert picked is not None
        assert picked[1][0] == "Bomb" and picked[1][1] == "3", f"应选最弱 5星 Bomb/3（4星不在候选），实际 {picked}"
        # 仅含 4星炸 + 同花顺时，4星够用就选 4星不动同花顺
        al2 = [
            ["PASS", "PASS", "PASS"],
            ["Bomb", "3", BOMB_3],
            ["StraightFlush", "3", SF_37],
        ]
        picked2 = EndgameDecider()._select_cheapest_bomb_or_sf(al2, "2")
        assert picked2 is not None
        assert picked2[1][0] == "Bomb" and picked2[1][1] == "3", f"4星够压应选 Bomb/3 不动同花顺，实际 {picked2}"
