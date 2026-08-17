# -*- coding: utf-8 -*-
"""
GUA-244: 剩余池（remainingPool）推理 → 残局「对子先于单/整牌」决策。

A/B 段（adapter 注入 + 引擎校验注入 `_remaining_pool_cards`）已由
tests/test_botzone_adapter.py / GUA-243 等回归覆盖；本文件聚焦 C 段决策层：

  ① `_pool_single_beat_risk`：P(主敌剩余牌含能压低单的张，含级牌)
  ② `_pool_pair_beat_risk`：P(主敌剩余牌含 >pair_rank 对子)
  ③ `_gua244_pair_lead_safe`：自由领出 + 主敌剩 ≤3 + 池风险「单 ≥0.7 且对 <0.3」
     → 豁免报双/报三的 Pair 禁封
  ④ `_q1_pool_pair_first_special`：满足条件时先出最高「不拆整牌核心」对子
  ⑤ `_seat_may_hold_single_above` 池优先路径（确定性残牌全集）
  ⑥ 集成：#17 出 Pair/7（原 Single/C6）；无池回退原链

背景（2026-08-15，match=6a8003e60fbd680d7c754f20，V8=player2，
logs/v8_vs_botzone_20260815_141037.log）：
  #17 自由领出，V8 手 C6 D5 66 77（5 张），队友 p0 剩 7，主敌 p1 剩 2（报双，
  BAOSHU_RULE[2].never_play=['Pair']），真实剩余池 15 张含级牌 D2。
  修复前：Pair 被 banned 硬删 → 决策链兜底出 Single/C6（L201-203），被级牌
  D2 接走 → p1 S8 走完头游，V8 末游。池推理：单被接 104/105=0.99、
  对子被接 6/105=0.057 → 应出 Pair/7（77）。
  #16 起手 10 张（TWT AAA+JJ + 66 + 77 + D5 + C6），主敌 p1 剩 2：应优先
  出最高「不拆整牌核心」对子（Pair/J，AAA+66 仍可重组 TWT），而非拆 AAA 出
  Pair/A、也不是直接 TWT 锁。
"""
import pytest

from src.communication.botzone_adapter import ActionListGenerator
from src.v.nn.endgame.endgame_decide import EndgameDecider

# 真实剩余池（干净解析器核实，15 张，含级牌 D2；rank 8×3 Q×2 K×2 A×2 均 >7）
POOL17 = [
    "C8", "CA", "CA", "CK", "CT", "D2", "D5", "D7", "DK", "DQ",
    "H8", "HJ", "S5", "S8", "SQ",
]

# 报双规则（BAOSHU_RULE[2]）：never_play=['Pair']
BAOSHU_DOUBLE = {
    "likely_hand": "对子",
    "block_with": ["ThreeWithTwo", "TwoTrips", "ThreePair", "Straight", "Bomb", "Trips"],
    "never_play": ["Pair"],
}

HAND_Q17 = ["C6", "H6", "H7", "S7", "D5"]          # #17：66 77 + 低单 5/6
HAND_Q16 = ["C6", "D5", "DA", "H6", "H7", "HA", "S7", "SA", "SJ", "SJ"]  # #16 起手


def q17_ec(main_rem=2):
    """#17 残局上下文：p1 剩 main_rem（报双），p3 剩 6，队友 p0 剩 7。"""
    enemies = {
        1: {"remaining": main_rem, "danger_level": "中高",
            "recommended_types": [], "banned_types": [],
            "baoshu": BAOSHU_DOUBLE if main_rem == 2 else {}},
        3: {"remaining": 6, "danger_level": "中",
            "recommended_types": [], "banned_types": [], "baoshu": {}},
    }
    return {
        "my_pos": 2,
        "cur_pos": 2,
        "cur_rank": "2",
        "numofplayers": [7, main_rem, 5, 6],
        "is_active": True,
        "enemies": enemies,
        "teammate": {"remaining": 7, "is_close": False, "assist_prefer": []},
        "self": {"remaining": 5, "has_two_clean_hands": False,
                 "has_bomb": False, "should_sprint": False},
        "finished": [],
    }


def build_gs(hand, numofplayers, pool=None, ec=None):
    """自由领出轮（greaterPos==myPos==2）的基础 game_state。"""
    gs = {
        "curRank": "2",
        "handCards": list(hand),
        "myPos": 2,
        "curPos": 2,
        "greaterPos": 2,
        "greaterAction": ["Bomb", "Q", ["DQ", "CQ", "CQ", "SQ"]],
        "curAction": ["Bomb", "Q", ["DQ", "CQ", "CQ", "SQ"]],
        "numofplayers": list(numofplayers),
        "publicInfo": [{"rest": n} for n in numofplayers],
        "done": [],
        "stage": "play",
        "selfRank": "2",
        "oppoRank": "2",
        "_botzone_mode": True,
    }
    if ec is not None:
        gs["_endgame_context"] = ec
    if pool is not None:
        gs["_remaining_pool_cards"] = list(pool)
    return gs


def q17_action_list():
    """#17 手牌 5 张的自由领出动作（Single×5 + Pair×2）。"""
    return [
        ["Single", "5", ["D5"]],
        ["Single", "6", ["C6"]],
        ["Single", "6", ["H6"]],
        ["Single", "7", ["H7"]],
        ["Single", "7", ["S7"]],
        ["Pair", "6", ["C6", "H6"]],
        ["Pair", "7", ["H7", "S7"]],
    ]


# ── ① 单被接概率（含级牌）──

def test_pool_single_beat_risk_precise_q17():
    """主敌剩 2、池 15 张、低单 5（级牌 2 能压）→ 被接 = 1 - C(2,2)/C(15,2) = 104/105。"""
    gs = build_gs(HAND_Q17, [7, 2, 5, 6], pool=POOL17)
    d = EndgameDecider()
    assert d._pool_single_beat_risk(gs, 1, "5") == pytest.approx(104 / 105)
    assert d._pool_single_beat_risk(gs, 1, "6") == pytest.approx(104 / 105)


def test_pool_single_beat_risk_negative():
    """无池 → None；该席剩 0 → 0.0；低单 K（>K 仅 A×2+D2）→ 39/105 < 0.7。"""
    d = EndgameDecider()
    gs = build_gs(HAND_Q17, [7, 2, 5, 6], pool=None)
    assert d._pool_single_beat_risk(gs, 1, "5") is None
    gs = build_gs(HAND_Q17, [7, 2, 5, 6], pool=POOL17)
    assert d._pool_single_beat_risk(gs, 1, "K") == pytest.approx(39 / 105)
    gs0 = build_gs(HAND_Q17, [7, 0, 5, 6], pool=POOL17)  # seat1 剩 0
    assert d._pool_single_beat_risk(gs0, 1, "5") == pytest.approx(0.0)


# ── ② 对子被接概率 ──

def test_pool_pair_beat_risk_precise_q17():
    """对 7 被接 = 池中 >7 对子（8×3/Q×2/K×2/A×2）6/105；对 A 无可压 → 0。"""
    gs = build_gs(HAND_Q17, [7, 2, 5, 6], pool=POOL17)
    d = EndgameDecider()
    assert d._pool_pair_beat_risk(gs, 1, "7") == pytest.approx(6 / 105)
    assert d._pool_pair_beat_risk(gs, 1, "6") == pytest.approx(6 / 105)
    assert d._pool_pair_beat_risk(gs, 1, "J") == pytest.approx(3 / 105)
    assert d._pool_pair_beat_risk(gs, 1, "A") == pytest.approx(0.0)
    gs0 = build_gs(HAND_Q17, [7, 0, 5, 6], pool=POOL17)  # seat1 剩 0
    assert d._pool_pair_beat_risk(gs0, 1, "7") == pytest.approx(0.0)


# ── ③ _gua244_pair_lead_safe ──

def test_gua244_pair_lead_safe_true_q17():
    """#17：自由领出 + 主敌剩 2 + 池存在 + ≥2 对 + 低单 → True（豁免 Pair）。"""
    gs = build_gs(HAND_Q17, [7, 2, 5, 6], pool=POOL17, ec=q17_ec())
    d = EndgameDecider()
    assert d._gua244_pair_lead_safe(gs, gs["_endgame_context"])


def test_gua244_pair_lead_safe_false_negative():
    """无池 / 主敌剩 4 / 低单大（K 风险低）→ 均 False。"""
    d = EndgameDecider()
    gs_nopool = build_gs(HAND_Q17, [7, 2, 5, 6], pool=None, ec=q17_ec())
    assert not d._gua244_pair_lead_safe(gs_nopool, gs_nopool["_endgame_context"])

    gs_rem4 = build_gs(HAND_Q17, [7, 4, 5, 6], pool=POOL17, ec=q17_ec(main_rem=4))
    assert not d._gua244_pair_lead_safe(gs_rem4, gs_rem4["_endgame_context"])

    # 低单 K：单被接 0.371 < 0.7 → 不豁免
    hand_big = ["H6", "S6", "H7", "S7", "DK"]
    gs_big = build_gs(hand_big, [7, 2, 5, 6], pool=POOL17, ec=q17_ec())
    assert not d._gua244_pair_lead_safe(gs_big, gs_big["_endgame_context"])


# ── ④ _q1_pool_pair_first_special ──

def test_q1_pool_pair_first_special_q17():
    """#17 有池：候选含 Pair/66、Pair/77 → 返回最高不拆核心对子 Pair/7。"""
    d = EndgameDecider()
    gs = build_gs(HAND_Q17, [7, 2, 5, 6], pool=POOL17, ec=q17_ec())
    cands = list(enumerate(q17_action_list()))
    main_enemy = gs["_endgame_context"]["enemies"][1]
    result = d._q1_pool_pair_first_special(gs, cands, gs["_endgame_context"], 1, main_enemy)
    assert result is not None
    assert result[1][0] == "Pair" and result[1][1] == "7", f"应出 77；实际 {result}"


def test_q1_pool_pair_first_special_no_pool():
    """无池 → None（不触发）。"""
    d = EndgameDecider()
    gs = build_gs(HAND_Q17, [7, 2, 5, 6], pool=None, ec=q17_ec())
    cands = list(enumerate(q17_action_list()))
    main_enemy = gs["_endgame_context"]["enemies"][1]
    assert d._q1_pool_pair_first_special(gs, cands, gs["_endgame_context"], 1, main_enemy) is None


# ── ⑤ _seat_may_hold_single_above 池路径 ──

def test_seat_may_hold_single_above_pool_path():
    """有池：池含能压单 → True（确定性残牌全集）；该席剩 0 → False。"""
    d = EndgameDecider()
    gs = build_gs(HAND_Q17, [7, 2, 5, 6], pool=POOL17)
    assert d._seat_may_hold_single_above(gs, 1, "5", "2") is True
    assert d._seat_may_hold_single_above(gs, 3, "5", "2") is True
    gs["numofplayers"] = [7, 0, 5, 6]
    assert d._seat_may_hold_single_above(gs, 1, "5", "2") is False


# ── ⑥ 集成 ──

def test_decide_q17_pool_picks_pair_7():
    """decide 集成：#17 有池 → banned 豁免 Pair → 出 Pair/7（原 Single/C6）。"""
    d = EndgameDecider()
    gs = build_gs(HAND_Q17, [7, 2, 5, 6], pool=POOL17, ec=q17_ec())
    filtered, empty = d.apply_banned_filter(q17_action_list(), gs)
    assert not empty
    assert any(a[0] == "Pair" for a in filtered), f"有池应豁免 Pair；实际 {[a[0] for a in filtered]}"
    idx, act = d.decide(gs, filtered)
    assert act is not None and act[0] == "Pair", f"应出对子；实际 {act}"
    assert act[2] == ["H7", "S7"], f"应出 77；实际 {act}"


def test_decide_q17_no_pool_fallback_single():
    """decide 集成对照：#17 无池 → Pair 仍被 banned → 兜底出最小单（原链）。"""
    d = EndgameDecider()
    gs = build_gs(HAND_Q17, [7, 2, 5, 6], pool=None, ec=q17_ec())
    filtered, empty = d.apply_banned_filter(q17_action_list(), gs)
    assert not empty
    assert not any(a[0] == "Pair" for a in filtered), f"无池应删 Pair；实际 {[a[0] for a in filtered]}"
    idx, act = d.decide(gs, filtered)
    assert act is not None and act[0] == "Single", f"应兜底出单；实际 {act}"
    assert act[2] == ["C6"], f"应出 Single/C6；实际 {act}"


def test_decide_q16_pool_preserves_twt_core_picks_pair_j():
    """#16 起手 10 张有池：出最高「不拆整牌核心」对子 Pair/J，非拆 AAA 的 Pair/A。
    组牌把 TWT(AAA+JJ) 拆成 trip(AAA)+pair(JJ)，GUA-219 只查 Bomb/SF 组；
    GUA-244 用 rank 计数==3 拦截 Pair/A，保住 TWT 核心。"""
    alg = ActionListGenerator()
    alg.cur_rank = "2"
    action_list = alg.generate_lead_actions(HAND_Q16)
    d = EndgameDecider()
    gs = build_gs(HAND_Q16, [7, 2, 10, 6], pool=POOL17, ec=q17_ec())
    filtered, empty = d.apply_banned_filter(action_list, gs)
    assert not empty
    idx, act = d.decide(gs, filtered)
    assert act is not None and act[0] == "Pair", f"应优先出对子；实际 {act}"
    assert act[1] == "J", f"应出 Pair/J（不拆 AAA）；实际 {act}"
    assert act[2] == ["SJ", "SJ"], f"应出 JJ；实际 {act}"
