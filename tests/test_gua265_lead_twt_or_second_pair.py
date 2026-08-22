# -*- coding: utf-8 -*-
"""
GUA-265: 无炸领出、手牌 = TWT/三张 + 多对、下家剩 6/7
  不得机械打最大单（拆级牌对）。

锚点 match=6a884eac（logs/v8_vs_botzone_20260821_210704.log 21:12:33）：
  手牌 88+TT+KKK+22，bombs=0，下家剩 7，Q1 兜底出 Single/C2（级牌最大单）。
  用户定音：
    ① 记牌能判断 KKK/TWT 最大 → 先出 TWT，剩 4 张像炸；
    ② 不确定是否最大 → 打第二小对子，级牌对回收；
    ③ 打最大单仅当自己还有炸弹。
"""
from src.communication.botzone_adapter import ActionListGenerator
from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker

HAND = ["D8", "H8", "DT", "ST", "SK", "CK", "DK", "C2", "D2"]
CUR = "2"
TWT_K = ["SK", "CK", "DK", "D8", "H8"]


def _mark_outside_played(t: MemoryTracker, rank: str):
    for suit in ("S", "H", "D", "C"):
        copies = t.card_state[f"{suit}{rank}"]
        for i in range(2):
            if copies[i] != t.MY_HAND:
                copies[i] = t.PLAYED


def _tracker(hand, *, twt_is_max=False):
    t = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
    t.init_from_hand(hand)
    t.set_level_rank(CUR)
    t.sync_my_jokers(hand)
    t.hand_counts = {0: len(hand), 1: 7, 2: 12, 3: 10}
    if twt_is_max:
        # 外面 A / 级牌 2 都凑不出三张 → KKK/TWT 可视为最大
        _mark_outside_played(t, "A")
        _mark_outside_played(t, "2")
    return t


def _gs(tracker):
    hand = list(HAND)
    acts = ActionListGenerator(cur_rank=CUR).generate_lead_actions(hand)
    return {
        "handCards": hand,
        "curRank": CUR,
        "myPos": 0,
        "curPos": 0,
        "greaterPos": -1,
        "greaterAction": [],
        "numofplayers": [9, 7, 12, 10],
        "publicInfo": [{"rest": r} for r in [9, 7, 12, 10]],
        "_botzone_mode": True,
        "_role": "超强主攻",
        "_memory_tracker": tracker,
        "actionList": acts,
        "_group_members": {
            0: ["DT", "ST"],
            1: ["C2", "D2"],
            2: ["SK", "CK", "DK"],
            3: ["D8", "H8"],
        },
        "_group_gid_type_map": {
            0: "pair",
            1: "pair",
            2: "trip_in_three_with_two",
            3: "pair_in_three_with_two",
        },
    }, acts


def _decide(tracker):
    gs, acts = _gs(tracker)
    EndgamePreprocessor().preprocess(gs)
    # 对齐锚点：三手结构不冲刺，走 Q1
    self_ctx = gs.setdefault("_endgame_context", {}).setdefault("self", {})
    self_ctx["should_sprint"] = False
    self_ctx["has_two_clean_hands"] = False
    self_ctx["has_bomb"] = False
    filtered, _ = EndgameDecider().apply_banned_filter(list(acts), gs)
    idx, act = EndgameDecider().decide(gs, filtered)
    return act


class TestGua265NoBombLeadNotMaxSingle:
    def test_uncertain_leads_second_smallest_pair_keeps_level(self):
        """外面 A 未打光 → TWT 未必最大 → 出对 T，保留级牌对 2。"""
        act = _decide(_tracker(HAND, twt_is_max=False))
        assert act is not None
        assert act[0] != "Single", f"无炸不应打最大单，实际 {act}"
        assert act[0] == "Pair" and act[1] == "T", f"应出第二小对 T，实际 {act}"
        assert set(act[2]) == {"DT", "ST"}

    def test_memory_twt_max_leads_twt_leave_four(self):
        """记牌：外面 A 与级牌 2 都凑不出三张 → TWT/K 最大，先出 TWT。"""
        act = _decide(_tracker(HAND, twt_is_max=True))
        assert act is not None
        assert act[0] == "ThreeWithTwo", f"TWT 最大应先出 TWT，实际 {act}"
        assert act[1] == "K"
        assert set(act[2]) == set(TWT_K)

    def test_self_has_bomb_does_not_force_twt_or_pair(self):
        """自己还有炸 → 本特判不接管（最大单路径仍可走）。"""
        hand = HAND + ["S9", "H9", "C9", "D9"]
        t = _tracker(hand)
        gs, acts = _gs(t)
        gs["handCards"] = hand
        gs["numofplayers"] = [13, 7, 12, 10]
        gs["_group_members"][4] = ["S9", "H9", "C9", "D9"]
        gs["_group_gid_type_map"][4] = "Bomb"
        EndgamePreprocessor().preprocess(gs)
        cands = list(enumerate(ActionListGenerator(cur_rank=CUR).generate_lead_actions(hand)))
        ec = gs["_endgame_context"]
        hit = EndgameDecider()._q1_no_bomb_twt_pairs_lead(gs, cands, ec)
        assert hit is None
