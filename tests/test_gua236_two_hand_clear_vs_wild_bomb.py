# -*- coding: utf-8 -*-
"""GUA-236：两手清（5-9 顺 + 配子 TWT）不得被「逢人配升炸」拆成单炸+散单。

锚点 hand（match=6a7c8a1a，curRank=2）:
  H5,C6,H8,C9,S7,H7,D7,H2,DT,ST
应组：Straight(5-9 含一枚 7) + ThreeWithTwo(两枚 7 + H2 + TT)
不应组：Bomb(777+H2) + scatter(H5,C6,H8,C9) + pair(TT)
"""

from src.communication.botzone_adapter import ActionListGenerator
from src.v.nn.features.grouping_engine import (
    GroupingPlan,
    _score_power,
    _score_plan_v2,
    enumerate_groupings,
)

HAND = ["H5", "C6", "H8", "C9", "S7", "H7", "D7", "H2", "DT", "ST"]
CUR = "2"
SEVENS = {"S7", "H7", "D7"}
STRAIGHT_CORE = {"H5", "C6", "H8", "C9"}


def _is_two_hand_clear(plan: GroupingPlan) -> bool:
    """Straight(5-9 含一枚 7) + TWT(两枚 7 + H2 + TT)，无炸弹无散单。"""
    if plan.bombs or plan.singles:
        return False
    if len(plan.straights) != 1 or len(plan.three_with_twos) != 1:
        return False
    st = set(plan.straights[0])
    if not STRAIGHT_CORE.issubset(st):
        return False
    if len(st & SEVENS) != 1:
        return False
    trip, pair = plan.three_with_twos[0]
    twt = set(trip) | set(pair)
    if "H2" not in twt:
        return False
    if twt & {"DT", "ST"} != {"DT", "ST"}:
        return False
    if len(twt & SEVENS) != 2:
        return False
    return True


def _bomb_scatter_plan() -> GroupingPlan:
    p = GroupingPlan(cur_rank=CUR, strategy="manual_bomb_scatter")
    p.bombs = [["S7", "H7", "D7", "H2"]]
    p.singles = ["H5", "C6", "H8", "C9"]
    p.pairs = [["DT", "ST"]]
    return p


def _two_clear_plan() -> GroupingPlan:
    p = GroupingPlan(cur_rank=CUR, strategy="manual_two_clear")
    p.straights = [["H5", "C6", "S7", "H8", "C9"]]
    p.three_with_twos = [(["H7", "D7", "H2"], ["DT", "ST"])]
    return p


class TestGua236ActionListWildTwt:
    def test_lead_actionlist_has_wild_twt_77h2_tt(self):
        """配子 TWT：两枚 7 + H2 + TT 必须进 actionList（GUA-195 只补了 Trips）。"""
        acts = ActionListGenerator(cur_rank=CUR).generate_lead_actions(HAND)
        twts = [a for a in acts if a[0] == "ThreeWithTwo"]
        assert any(
            "H2" in a[2]
            and set(a[2]) & {"DT", "ST"} == {"DT", "ST"}
            and len(set(a[2]) & SEVENS) == 2
            for a in twts
        ), f"缺配子 TWT，现有={twts}"


class TestGua236GroupingPreferTwoHandClear:
    def test_enumerate_prefers_straight_plus_wild_twt(self):
        """组牌最优方案应为两手清，而非 Bomb(777+H2)+4 散单+TT。"""
        best, plans = enumerate_groupings(HAND, CUR)
        assert _is_two_hand_clear(best), (
            f"best strategy={best.strategy} bombs={best.bombs} "
            f"straights={best.straights} twt={best.three_with_twos} "
            f"singles={best.singles} power={best.power_score}"
        )
        assert any(_is_two_hand_clear(p) for p in plans)

    def test_two_hand_clear_score_beats_bomb_scatter(self):
        """两手清方案分必须压过「单炸 + 一堆散单」。"""
        two = _two_clear_plan()
        bomb = _bomb_scatter_plan()
        _score_plan_v2(two, [two, bomb])
        _score_plan_v2(bomb, [two, bomb])
        assert two.power_score > bomb.power_score
        assert two.num_rounds() < bomb.num_rounds()
        assert two.score > bomb.score


class TestGua236PowerSelectRepro:
    """方案 B 对照：若候选含两手清，纯牌力也会选它（复现用，非修目标）。"""

    def test_pure_power_picks_two_clear_when_present(self):
        two = _two_clear_plan()
        bomb = _bomb_scatter_plan()
        assert _score_power(two, CUR) > _score_power(bomb, CUR)
        assert _score_power(two, CUR) == 0.4
        assert _score_power(bomb, CUR) == -2.0


class TestGua236LeadStraightBeforeTwt:
    """剩顺+TWT 两手清：领出优先 Straight，再打 TWT。"""

    def test_q0_lead_straight_before_wild_twt(self):
        from src.v.nn.endgame.endgame_decide import EndgameDecider
        from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor

        acts = ActionListGenerator(cur_rank=CUR).generate_lead_actions(HAND)
        best, _ = enumerate_groupings(HAND, CUR)
        assert _is_two_hand_clear(best)
        st_cards = list(best.straights[0])
        trip, pair = best.three_with_twos[0]
        twt_cards = list(trip) + list(pair)
        gs = {
            "handCards": list(HAND),
            "curRank": CUR,
            "myPos": 0,
            "curPos": 0,
            "greaterPos": -1,
            "greaterAction": [],
            "numofplayers": [10, 8, 10, 6],
            "publicInfo": [{"rest": r} for r in [10, 8, 10, 6]],
            "_botzone_mode": True,
            "_role": "助攻",
            # 与引擎注入一致：子结构计数 → 语义 2 手 → should_sprint
            "_group_type_map": {
                "straight": 1,
                "trip_in_three_with_two": 1,
                "pair_in_three_with_two": 1,
            },
            "_group_members": {0: st_cards, 1: list(trip), 2: list(pair)},
            "_group_gid_type_map": {
                0: "straight",
                1: "trip_in_three_with_two",
                2: "pair_in_three_with_two",
            },
        }
        EndgamePreprocessor().preprocess(gs)
        assert gs["_endgame_context"]["self"]["should_sprint"] is True
        filtered, _ = EndgameDecider().apply_banned_filter(list(acts), gs)
        idx, act = EndgameDecider().decide(gs, filtered)
        assert act is not None
        assert act[0] == "Straight", f"应先出顺，实际 {act[0]}/{act[1]}"
        assert set(act[2]) == set(st_cards), f"应出组牌顺 {st_cards}，实际 {act[2]}"
        # 残余一手须为配子 TWT（可在 actionList 命中）
        residue = set(HAND) - set(act[2])
        assert residue == set(twt_cards)
