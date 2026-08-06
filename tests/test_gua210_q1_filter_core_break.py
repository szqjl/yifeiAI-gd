# -*- coding: utf-8 -*-
"""
GUA-210: Q1 封锁候选过滤「拆核心」动作 单元测试

背景（2026-08-06，match=6a7476fe27e7bf01db13279e req15）：
  残局 V8 手牌 7 = DA, SQ + 同花顺 S2-S6，4 号（player3）出 Single/K (HK)。
  出 DA 压 K 后剩 SF + 单 Q 两手冲刺。修复前 Q1 通用路径 `_sort_q1_block_candidates`
  + `_select_best_index` 优先选级牌 S2 压牌，但 S2 是 StraightFlush 核心组
  [S2..S6] 的成员 → decide 层 `_action_breaks_core_structure` 拦截 → 直接 PASS，
  从不回退到不拆核心的 scatter 候选 DA，浪费头游机会。

修复：`_q1_block_enemy` 通用路径前对 non_banned_candidates 过滤拆核心动作
  （`_filter_q1_core_break_candidates`），仅在仍有非 PASS 候选时生效；
  全部拆核心时维持原列表，交由 GUA-199 拦截层裁决 PASS。
"""
import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider


def build_gs():
    return {
        "curRank": "2",
        "handCards": ["DA", "SQ", "S2", "S3", "S4", "S5", "S6"],
        "myPos": 0,
        "_group_members": {
            -1: ["SQ", "DA"],
            0: ["S2", "S3", "S4", "S5", "S6"],
        },
        "_group_gid_type_map": {0: "StraightFlush"},
    }


CANDIDATES = [
    (0, ["PASS", "PASS", "PASS"]),
    (1, ["Single", "A", ["DA"]]),
    (2, ["Single", "2", ["S2"]]),
    (3, ["StraightFlush", "2", ["S2", "S3", "S4", "S5", "S6"]]),
]


def test_filter_keeps_non_core_break_candidates():
    """级牌 S2 拆 SF 核心被滤除，DA（scatter 不拆核心）与 PASS/完整 SF 保留。"""
    d = EndgameDecider()
    kept = d._filter_q1_core_break_candidates(list(CANDIDATES), build_gs())
    kept_acts = [act[:3] for _i, act in kept]
    assert ["Single", "A", ["DA"]] in kept_acts, kept_acts
    assert ["Single", "2", ["S2"]] not in kept_acts, kept_acts
    assert ["PASS", "PASS", "PASS"] in kept_acts, kept_acts
    # 完整 SF 是核心整牌本身（GUA-206 豁免），保留
    assert ["StraightFlush", "2", ["S2", "S3", "S4", "S5", "S6"]] in kept_acts, kept_acts


def test_filter_all_core_break_returns_original():
    """全部候选都拆核心（仅 PASS + 拆核心单张）→ 返回原列表（GUA-199 拦截兜底）。"""
    d = EndgameDecider()
    candidates = [
        (0, ["PASS", "PASS", "PASS"]),
        (1, ["Single", "2", ["S2"]]),
    ]
    kept = d._filter_q1_core_break_candidates(candidates, build_gs())
    assert kept == candidates, kept


def test_filter_none_break_keeps_all():
    """无拆核心候选 → 原样返回。"""
    d = EndgameDecider()
    candidates = [
        (0, ["PASS", "PASS", "PASS"]),
        (1, ["Single", "A", ["DA"]]),
    ]
    kept = d._filter_q1_core_break_candidates(candidates, build_gs())
    assert kept == candidates, kept


def test_q1_block_enemy_repro_picks_da():
    """复现局集成：Q1 封锁 enemy 压 Single/K → 出 DA（不拆核心），非 S2、非 PASS。"""
    gs = build_gs()
    gs.update({
        "curPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "K", ["HK"]],
        "curAction": ["Single", "K", ["HK"]],
        "numofplayers": [7, 2, 5, 3],
        "publicInfo": [{"rest": 7}, {"rest": 2}, {"rest": 5}, {"rest": 3}],
        "done": [],
        "stage": "play",
        "selfRank": "2",
        "oppoRank": "2",
        "history": [
            {"pos": 0, "action": ["Single", "7", ["S7"]]},
            {"pos": 1, "action": ["Single", "K", ["SK"]]},
            {"pos": 2, "action": ["PASS", "PASS", "PASS"]},
            {"pos": 3, "action": ["Single", "K", ["HK"]]},
        ],
    })
    ec = {
        "my_pos": 0,
        "cur_pos": 0,
        "cur_rank": "2",
        "numofplayers": [7, 2, 5, 3],
        "enemies": {
            1: {"remaining": 2, "danger_level": "高",
                "recommended_types": [], "banned_types": [], "baoshu": {}},
            3: {"remaining": 3, "danger_level": "中",
                "recommended_types": [], "banned_types": [], "baoshu": {}},
        },
        "teammate": {"remaining": 5, "is_close": False,
                     "assist_prefer": []},
        "self": {"remaining": 7, "has_two_clean_hands": False,
                 "has_bomb": False, "should_sprint": False},
        "finished": [],
    }
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "A", ["DA"]],
        ["Single", "2", ["S2"]],
        ["StraightFlush", "2", ["S2", "S3", "S4", "S5", "S6"]],
    ]
    d = EndgameDecider()
    result = d._q1_block_enemy(gs, action_list, ec)
    assert result is not None, "Q1 应命中封锁（返回 None 表示未命中）"
    idx, act = result
    assert act[0] == "Single", f"应出 Single 压 K；实际 {act}"
    assert act[2] == ["DA"], f"应出 DA（不拆 SF 核心）；实际 {act}"
