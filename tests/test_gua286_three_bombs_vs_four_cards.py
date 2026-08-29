# -*- coding: utf-8 -*-
"""GUA-286：主敌剩 4 张时，变手炸弹资源 ≥3 把 → GUA-115 豁免，开最廉炸截断。

锚点：match=6a927cbd1b27100f38d87a27（logs/v8_vs_botzone_20260829_142042.log
L77-83）：下家领 TWT/A 后剩 4 张，V8 手握三把炸（Bomb/4 Bomb/5 Bomb/7）
仍被 GUA-115「火不打四」拦成 PASS。用户定音（方案 B）：变手炸弹 ≥3 时开炸。
"""

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor

BOMB_4 = ["D4", "S4", "C4", "C4"]
BOMB_5 = ["C5", "H5", "H5", "S5"]
BOMB_7 = ["H7", "C7", "S7", "D7"]
TWT_A = ["CA", "CA", "HA", "C5", "H5"]


def _enemy_four_state(*, hand_cards, action_list, numofplayers):
    return {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 1,
        "greaterAction": ["ThreeWithTwo", "A", TWT_A],
        "handCards": list(hand_cards),
        "actionList": action_list,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "numofplayers": numofplayers,
        "_role": "主攻",
    }


class TestGua286ThreeBombsVsFourCards:
    """GUA-286：主敌 rem=4 跟压 + 变手 3 把炸 → 最廉炸截断。"""

    def test_three_bombs_vs_four_cards_fire_cheapest(self):
        """变手 3 把 4 星炸（4/5/7）+ 散牌，跟压 TWT/A 敌剩 4 → 开最廉 Bomb/4。"""
        hand_cards = BOMB_4 + BOMB_5 + BOMB_7 + ["HJ", "HK"] + ["S6", "H6", "C9"]
        gs = _enemy_four_state(
            hand_cards=hand_cards,
            numofplayers=[15, 4, 10, 9],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["Bomb", "7", BOMB_7],
                ["Bomb", "5", BOMB_5],
                ["Bomb", "4", BOMB_4],
            ],
        )

        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])

        assert act[0] == "Bomb"
        assert act[1] == "4"
        assert act[2] == BOMB_4

    def test_three_bombs_excludes_blocked_baoshu_never_play(self):
        """banned 过滤（BAOSHU_RULE[4] never_play）前 GUA-286 已返回最廉炸。"""
        hand_cards = BOMB_4 + BOMB_5 + BOMB_7 + ["HJ", "HK"] + ["S6", "H6", "C9"]
        gs = _enemy_four_state(
            hand_cards=hand_cards,
            numofplayers=[15, 4, 10, 9],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["Bomb", "7", BOMB_7],
                ["Bomb", "5", BOMB_5],
                ["Bomb", "4", BOMB_4],
            ],
        )
        EndgamePreprocessor().preprocess(gs)
        enemy_ctx = gs["_endgame_context"]["enemies"].get(1) or {}
        baoshu = enemy_ctx.get("baoshu") or {}
        assert "Bomb" in baoshu.get("never_play", [])

        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert act[0] == "Bomb"
        assert act[1] == "4"

    def test_two_bombs_vs_four_cards_still_pass(self):
        """变手仅 2 把炸（<3），保留 GUA-115 火不打四 → PASS。"""
        BOMB_J = ["SJ", "HJ", "CJ", "DJ"]
        hand_cards = BOMB_4 + BOMB_5 + [BOMB_J[0], "HJ", "CJ", "DJ"] + ["S6", "C9", "HA"]
        gs = _enemy_four_state(
            hand_cards=hand_cards,
            numofplayers=[14, 4, 11, 9],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["Bomb", "4", BOMB_4],
                ["Bomb", "5", BOMB_5],
            ],
        )

        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])

        assert idx == 0
        assert act[0] == "PASS"

    def test_main_enemy_five_cards_not_in_scope(self):
        """主敌剩 5（非 4）：GUA-286 / GUA-115 均不在作用域，维持既有 Q1 行为（开炸走推荐路径）。"""
        hand_cards = BOMB_4 + BOMB_5 + BOMB_7 + ["HJ", "HK"] + ["S6", "H6", "C9"]
        gs = _enemy_four_state(
            hand_cards=hand_cards,
            numofplayers=[15, 5, 10, 8],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["Bomb", "7", BOMB_7],
                ["Bomb", "5", BOMB_5],
                ["Bomb", "4", BOMB_4],
            ],
        )
        EndgamePreprocessor().preprocess(gs)

        idx, act = EndgameDecider().decide(gs, gs["actionList"])

        assert idx == 3
        assert act[0] == "Bomb"
        assert act[1] == "4"