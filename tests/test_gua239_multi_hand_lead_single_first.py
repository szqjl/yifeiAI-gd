# -*- coding: utf-8 -*-
"""
GUA-239: 自由领出多手先单试探（最小天然单）单元测试

背景（2026-08-13，match=6a7dd97c0fbd680d7c72d3cd 22:49:44，V8=player2）：
  残局 V8 刚 Bomb/A 回手**自由领出**，手牌 14 = SF(H7,H2,H2,HT,HJ) + HR
  + 4 对子（S5D5 / DJCJ / HQCQ / D2S2），**下家 P3 剩 6 张**。
  修复前 Q1 封锁按 endgame_rule[6]（recommended=`[ThreePair,TwoTrips,Straight,Trips]`）
  匹配唯一命中 `Straight/7`（H7,H2,H2,HT,HJ，GUA-232 自由领出禁升级强制保持 Straight）
  → 被 P1 `Straight/8` 压死失权，此后只能拆对子单走、`S5,D5` 对子烂手。

修复：`_q1_block_enemy` 在「自由领出 + 本方多手（≥4 手且含对子 ≥2）+ 下家剩 6 张
  + 有天然单可拆」时，优先出最小天然单（Single/7 H7）试探（保留大王 HR / 对子作回手），
  而非匹配 recommended 甩整牌 SF/Straight。出 H7 有意拆 SF 核心组 → 设
  `_gua239_single_probe` 标记，decide 层 `_action_breaks_core_structure` 与引擎
  `_group_consistency_filter` 据此豁免（否则被转 PASS / 回退 GUA-075，修复失效）。
"""
import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider


def build_gs():
    return {
        "curRank": "2",
        "handCards": [
            "H7", "H2", "H2", "HT", "HJ", "HR",
            "S5", "D5", "DJ", "CJ", "HQ", "CQ", "D2", "S2",
        ],
        "myPos": 2,
        "curPos": 2,
        "greaterPos": 2,
        "greaterAction": ["Bomb", "A", ["HA", "SA", "DA", "SA"]],
        "curAction": ["Bomb", "A", ["HA", "SA", "DA", "SA"]],
        "numofplayers": [0, 5, 14, 6],
        "publicInfo": [
            {"rest": 0}, {"rest": 5}, {"rest": 14}, {"rest": 6},
        ],
        "done": [],
        "stage": "play",
        "selfRank": "2",
        "oppoRank": "2",
        "_botzone_mode": True,
        "_group_members": {
            -1: ["HR"],
            0: ["H7", "H2", "H2", "HT", "HJ"],
            1: ["S5", "D5"],
            2: ["DJ", "CJ"],
            3: ["HQ", "CQ"],
            4: ["D2", "S2"],
        },
        "_group_gid_type_map": {
            0: "StraightFlush",
            1: "pair", 2: "pair", 3: "pair", 4: "pair",
        },
    }


def build_ec():
    return {
        "my_pos": 2,
        "cur_pos": 2,
        "cur_rank": "2",
        "numofplayers": [0, 5, 14, 6],
        "enemies": {
            1: {"remaining": 5, "danger_level": "低",
                "recommended_types": ["Straight", "TwoTrips", "ThreePair"],
                "banned_types": [], "baoshu": {}},
            3: {"remaining": 6, "danger_level": "中",
                "recommended_types": ["ThreePair", "TwoTrips", "Straight", "Trips"],
                "banned_types": [], "baoshu": {}},
        },
        "teammate": {"remaining": 0, "is_close": False, "assist_prefer": []},
        "self": {"remaining": 14, "has_two_clean_hands": False,
                 "has_bomb": False, "should_sprint": False},
        "finished": [],
    }


def build_action_list():
    return [
        ["PASS", "PASS", "PASS"],
        ["Single", "7", ["H7"]],
        ["Single", "T", ["HT"]],
        ["Single", "R", ["HR"]],
        ["Pair", "5", ["S5", "D5"]],
        ["Pair", "J", ["DJ", "CJ"]],
        ["Pair", "Q", ["HQ", "CQ"]],
        ["Pair", "2", ["D2", "S2"]],
        ["Straight", "7", ["H7", "HT", "HJ", "H2", "H2"]],
        ["StraightFlush", "7", ["H7", "H2", "H2", "HT", "HJ"]],
        ["Bomb", "A", ["HA", "SA", "DA", "SA"]],
    ]


def test_q1_block_enemy_repro_picks_smallest_natural_single():
    """复现局集成：Q1 自由领出多手 → 出最小天然单 Single/7（H7），非 Straight 甩整牌。"""
    gs = build_gs()
    d = EndgameDecider()
    result = d._q1_block_enemy(gs, build_action_list(), build_ec())
    assert result is not None, "GUA-239 应命中（返回 None 表示未命中）"
    idx, act = result
    assert act[0] == "Single", f"应出 Single 试探；实际 {act}"
    assert act[2] == ["H7"], f"应出最小天然单 H7；实际 {act}"
    # 有意拆 SF 核心 → 标记须已设置（决定层/引擎据此豁免拆核心拦截）
    assert gs.get("_gua239_single_probe") is True, "应设 _gua239_single_probe 标记"


def test_picks_smallest_natural_single_among_many():
    """多张天然单时选最小（9 散单存在仍选 7）。"""
    gs = build_gs()
    gs["handCards"] = ["H7", "H9", "H2", "H2", "HT", "HJ", "HR",
                       "S5", "D5", "DJ", "CJ", "HQ", "CQ", "D2", "S2"]
    gs["_group_members"] = {
        -1: ["HR"],
        0: ["H7", "H2", "H2", "HT", "HJ"],
        1: ["S5", "D5"], 2: ["DJ", "CJ"], 3: ["HQ", "CQ"], 4: ["D2", "S2"],
    }
    action_list = list(enumerate(build_action_list() + [["Single", "9", ["H9"]]]))
    d = EndgameDecider()
    result = d._q1_multi_hand_lead_single_first(gs, action_list, build_ec())
    assert result is not None
    idx, act = result
    assert act[2] == ["H7"], f"应选最小天然单 H7；实际 {act}"


def test_downseat_not_six_no_trigger():
    """下家非 6 张 → 不触发。"""
    gs = build_gs()
    ec = build_ec()
    gs["numofplayers"] = [0, 5, 14, 5]
    gs["publicInfo"] = [{"rest": 0}, {"rest": 5}, {"rest": 14}, {"rest": 5}]
    ec["numofplayers"] = [0, 5, 14, 5]
    ec["enemies"][3]["remaining"] = 5
    d = EndgameDecider()
    assert d._q1_multi_hand_lead_single_first(gs, build_action_list(), ec) is None


def test_not_multi_hand_no_trigger():
    """本方少手（<4 手或无对子 ≥2）→ 不触发。"""
    gs = build_gs()
    # 手 5 = 拆掉对子，只剩 SF + 单 R + 单 7 一手散 = 3 手、0 对
    gs["handCards"] = ["H7", "H2", "H2", "HT", "HJ", "HR", "S5"]
    gs["_group_members"] = {-1: ["HR", "S5"], 0: ["H7", "H2", "H2", "HT", "HJ"]}
    gs["_group_gid_type_map"] = {0: "StraightFlush"}
    d = EndgameDecider()
    assert d._q1_multi_hand_lead_single_first(gs, build_action_list(), build_ec()) is None


def test_no_natural_single_no_trigger():
    """无天然单（每 rank 至少成对/成组）→ 不触发。"""
    gs = build_gs()
    # 手 6 = 3 对（rank 全出现 2 次）→ 无天然单
    gs["handCards"] = ["S5", "D5", "S9", "D9", "HK", "CK"]
    gs["_group_members"] = {
        1: ["S5", "D5"], 2: ["S9", "D9"], 3: ["HK", "CK"],
    }
    gs["_group_gid_type_map"] = {1: "pair", 2: "pair", 3: "pair"}
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Pair", "5", ["S5", "D5"]],
        ["Pair", "9", ["S9", "D9"]],
        ["Pair", "K", ["HK", "CK"]],
    ]
    d = EndgameDecider()
    assert d._q1_multi_hand_lead_single_first(gs, action_list, build_ec()) is None


def test_not_free_lead_no_trigger():
    """非自由领出（跟牌轮）→ 不触发。"""
    gs = build_gs()
    ec = build_ec()
    # 跟牌轮：greaterPos 为下家 P3 出的 Single
    gs["curPos"] = 2
    gs["greaterPos"] = 3
    gs["greaterAction"] = ["Single", "Q", ["CQ"]]
    gs["curAction"] = ["Single", "Q", ["CQ"]]
    ec["cur_pos"] = 3
    d = EndgameDecider()
    assert d._q1_multi_hand_lead_single_first(gs, build_action_list(), ec) is None


def test_decide_returns_single_not_pass():
    """decide() 集成：Q1 命中 GUA-239 出 Single/7（拆 SF 核心）→ 不被转 PASS。"""
    gs = build_gs()
    gs["_endgame_context"] = build_ec()
    gs["_endgame_context"]["is_active"] = True
    d = EndgameDecider()
    idx, act = d.decide(gs, build_action_list())
    assert act is not None, "decide 应命中 Q1 GUA-239"
    assert act[0] == "Single", f"应出 Single；实际 {act}"
    assert act[2] == ["H7"], f"应出最小天然单 H7；实际 {act}"


class _FakeLogger:
    def info(self, *a, **k):
        pass

    def debug(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass


def _make_engine(gs):
    """按 test_gua069 模式构造 engine 并跑组牌引擎（补 _anchor_role 走完整路径）。"""
    from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
    engine = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    engine.logger = _FakeLogger()
    engine._card_mask = None
    engine._current_role = "主攻"
    engine._last_hand_hash = None
    engine._anchor_role = "主攻"
    engine.group_filter_bypass_count = 0
    engine.group_filtered_count = 0
    engine._tracker = None
    engine.player_id = 2
    engine._group_type_map = {}
    engine._run_grouping_engine(gs)
    return engine


def test_engine_filter_exempts_gua239_single_probe():
    """引擎 _group_consistency_filter：标记置位 → 拆 SF 的 Single/7 放行；
    无标记 → 正常拦截（回退 GUA-075 会破坏修复）。"""
    gs = build_gs()
    engine = _make_engine(gs)
    # 确认组牌引擎产出 SF 核心组（与真实日志 bombs=0 / group0=SF 一致）
    assert engine._group_type_map.get(0) == "StraightFlush", engine._group_type_map
    actions = [
        ["Single", "7", ["H7"]],
        ["StraightFlush", "7", ["H7", "H2", "H2", "HT", "HJ"]],
        ["PASS", "PASS", "PASS"],
    ]
    gs["_gua239_single_probe"] = True
    filtered, fmap = engine._group_consistency_filter(actions, gs)
    assert fmap[0] != -1, f"有标记应放行拆 SF 的 Single/7；fmap={fmap}"

    gs_no_marker = dict(gs)
    gs_no_marker.pop("_gua239_single_probe", None)
    filtered2, fmap2 = engine._group_consistency_filter(actions, gs_no_marker)
    assert fmap2[0] == -1, f"无标记应拦截拆 SF 的 Single/7；fmap={fmap2}"


# ---- GUA-253：GUA-239 天然单过滤排除逢人配 H{curRank}（match 6a86823d） ----

def build_gs_bomb_wild():
    """match 6a86823d 12:27:58 领出轮：手 666777JJKK+H2，
    组牌 H2 配成 G0(Bomb)=6666，下家剩 6 张。修复前 H2 被当天然单单出。"""
    return {
        "curRank": "2",
        "handCards": [
            "C6", "S6", "C6", "H2", "CK", "DK", "D7", "H7", "S7", "CJ", "HJ",
        ],
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 0,
        "greaterAction": ["Pair", "A", ["HA", "DA"]],
        "curAction": ["Pair", "A", ["HA", "DA"]],
        "numofplayers": [11, 6, 8, 5],
        "publicInfo": [
            {"rest": 11}, {"rest": 6}, {"rest": 8}, {"rest": 5},
        ],
        "done": [],
        "stage": "play",
        "selfRank": "2",
        "oppoRank": "2",
        "_botzone_mode": True,
        "_group_members": {
            0: ["C6", "S6", "C6", "H2"],
            1: ["CK", "DK"],
            2: ["D7", "H7", "S7"],
            3: ["CJ", "HJ"],
        },
        "_group_gid_type_map": {
            0: "Bomb",
            1: "pair",
            2: "trip_in_three_with_two",
            3: "pair_in_three_with_two",
        },
    }


def build_ec_bomb_wild():
    return {
        "my_pos": 0,
        "cur_pos": 0,
        "cur_rank": "2",
        "numofplayers": [11, 6, 8, 5],
        "enemies": {
            1: {"remaining": 6, "danger_level": "中",
                "recommended_types": ["ThreePair", "TwoTrips", "Straight", "Trips"],
                "banned_types": [], "baoshu": {}},
            3: {"remaining": 5, "danger_level": "低",
                "recommended_types": ["Straight", "TwoTrips", "ThreePair"],
                "banned_types": [], "baoshu": {}},
        },
        "teammate": {"remaining": 8, "is_close": False, "assist_prefer": []},
        "self": {"remaining": 11, "has_two_clean_hands": False,
                 "has_bomb": True, "should_sprint": False},
        "finished": [],
    }


def build_action_list_bomb_wild():
    return [
        ["PASS", "PASS", "PASS"],
        ["Single", "2", ["H2"]],
        ["Single", "7", ["D7"]],
        ["Pair", "J", ["CJ", "HJ"]],
        ["Pair", "K", ["CK", "DK"]],
        ["Trips", "7", ["D7", "H7", "S7"]],
        ["Bomb", "6", ["C6", "S6", "C6", "H2"]],
        ["ThreeWithTwo", "7", ["D7", "H7", "S7", "CK", "DK"]],
    ]


def test_gua253_wild_level_card_excluded_from_natural_single():
    """逢人配 H2（组进炸弹配子）不得当天然单试探——单出即拆炸弹，浪费万能牌。"""
    gs = build_gs_bomb_wild()
    d = EndgameDecider()
    result = d._q1_multi_hand_lead_single_first(
        gs, list(enumerate(build_action_list_bomb_wild())), build_ec_bomb_wild())
    # 修复前：唯一天然单候选 = H2 → 返回 Single/H2（bug）
    # 修复后：H2 排除 → 无天然单 → 返回 None，落 Q1 正常路径（组炸/整牌）
    assert result is None, f"H2 应被排除，GUA-239 不触发（无天然单）；实际 {result}"


def test_gua253_decide_not_single_h2():
    """decide() 集成：手 666777JJKK+H2 领出，不得单出 H2 拆炸弹核心。"""
    gs = build_gs_bomb_wild()
    gs["_endgame_context"] = build_ec_bomb_wild()
    gs["_endgame_context"]["is_active"] = True
    d = EndgameDecider()
    idx, act = d.decide(gs, build_action_list_bomb_wild())
    assert act is not None, "decide 应命中"
    assert act[0] != "Single" or act[2] != ["H2"], \
        f"不得单出逢人配 H2（拆炸弹 6666）；实际 {act}"
    assert act[0] in ("Bomb", "ThreeWithTwo", "Pair", "Trips"), \
        f"应组炸/整牌/对子，而非单出 H2；实际 {act}"
