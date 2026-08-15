# -*- coding: utf-8 -*-
"""
GUA-240: 残局自由领出 4 张 = Trips/AAA + 单 9，下家报三（剩 3 张三同张）时，
Q0 冲刺应出 Trips/AAA 冲刺（剩单 9 下次一手清），而非拆 AAA 先出 Pair/A + Single/A。

背景（2026-08-14，match=6a7f1a170fbd680d7c742f70 21:37:58，V8=player2）：
  刚 Straight 回手自由领出，手牌 4 = DA CA SA H9（组牌 G0(trips) AAA + scatter H9），
  下家 player3 剩 3 张（报三/三同张，21:38:05 日志 GUA-229 证实 next=3 remaining=1）。
  actionList {'Single':4,'Pair':3,'Trips':1}。修复前 Q0 冲刺出 Pair/A（actIndex=4）
  拆 AAA → 随后 Single/A → H9 被压到接风才出完。

根因（双因叠加）：
  ① apply_banned_filter 把 BAOSHU_RULE[3].never_play=Trips 硬删 Trips/AAA 候选
    （GUA-235 只豁免 Bomb/SF，未豁免 Trips）；
  ② 过滤后只剩 Single+Pair，_q0_self_sprint GUA-182 判定 types=={Pair,Single}
    误当「4 张两手整对」→ 对子优先拆 AAA。

修复：
  ① GUA-235 扩展：自由领出时 banned_set 一并豁免 Trips；
  ② GUA-182 精化：命中前校验手牌 rank 分布确为 2+2（两对），AAA+9 非两对不命中；
  ③ GUA-236 _select_two_turn_sprint_structure：残手为 Trips/TWT（无法压 Single
    回收）时 residue_bucket 不置 0，避免「先出散单留整牌」送单。
"""
import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider


def build_gs():
    return {
        "curRank": "2",
        "handCards": ["DA", "CA", "SA", "H9"],
        "myPos": 2,
        "curPos": 2,
        "greaterPos": 2,
        "greaterAction": ["Straight", "4", ["D4", "C5", "S6", "H7", "C8"]],
        "curAction": ["Straight", "4", ["D4", "C5", "S6", "H7", "C8"]],
        "numofplayers": [0, 9, 4, 3],
        "publicInfo": [{"rest": 0}, {"rest": 9}, {"rest": 4}, {"rest": 3}],
        "done": [],
        "stage": "play",
        "selfRank": "2",
        "oppoRank": "2",
        "_botzone_mode": True,
        "_role": "主攻",
        # 组牌结果（真实日志 L771-773：G0(trips) + scatter H9）
        "_group_members": {0: ["DA", "CA", "SA"], -1: ["H9"]},
        "_group_gid_type_map": {0: "trips"},
    }


def build_ec():
    return {
        "my_pos": 2,
        "cur_pos": 2,
        "cur_rank": "2",
        "numofplayers": [0, 9, 4, 3],
        "enemies": {
            # 下家报三（三同张）→ baoshu never_play Trips
            3: {"remaining": 3, "danger_level": "中高",
                "recommended_types": [], "banned_types": ["Trips"],
                "baoshu": {"likely_hand": "三同张", "block_with": ["Pair", "Single"],
                           "never_play": ["Trips"]}},
            1: {"remaining": 9, "danger_level": "低",
                "recommended_types": [], "banned_types": [], "baoshu": {}},
        },
        "teammate": {"remaining": 0, "is_close": False, "assist_prefer": []},
        "self": {"remaining": 4, "has_two_clean_hands": True,
                 "has_bomb": False, "should_sprint": True},
        "finished": [],
    }


def full_action_list():
    """generate_lead_actions 对 hand=['DA','CA','SA','H9'] 的真实顺序。"""
    return [
        ["Single", "A", ["DA"]],
        ["Single", "A", ["CA"]],
        ["Single", "A", ["SA"]],
        ["Single", "9", ["H9"]],
        ["Pair", "A", ["DA", "CA"]],
        ["Pair", "A", ["DA", "SA"]],
        ["Pair", "A", ["CA", "SA"]],
        ["Trips", "A", ["DA", "CA", "SA"]],
    ]


def filtered_action_list():
    """banned 过滤后（Trips 被删）只剩 Single+Pair。"""
    return [a for a in full_action_list() if a[0] != "Trips"]


def test_q0_self_sprint_picks_trips_not_single():
    """完整候选（含 Trips）：Q0 冲刺应出 Trips/AAA（先出整牌，残单 9 下次清），
    而非先出散单 Single/9（保留 AAA 无法压单 = 送单）。"""
    d = EndgameDecider()
    result = d._q0_self_sprint(build_gs(), full_action_list(), build_ec())
    assert result is not None
    idx, act = result
    assert act[0] == "Trips", f"应出 Trips/AAA 冲刺；实际 {act}"
    assert act[2] == ["DA", "CA", "SA"], f"应出 AAA；实际 {act}"


def test_q0_self_sprint_not_pair_when_baoshu_three():
    """banned 已删 Trips（只剩 Single+Pair）：AAA+9（A×3+9×1）不是两对，
    GUA-182 不应命中拆 Pair/A；应落回管线（出 Trips 由上游恢复候选，此处不得返回 Pair）。"""
    d = EndgameDecider()
    result = d._q0_self_sprint(build_gs(), filtered_action_list(), build_ec())
    assert result is None or result[1][0] != "Pair", \
        f"AAA+9 非两对，GUA-182 不应拆对；实际 {result}"


def test_apply_banned_filter_keeps_trips_on_free_lead():
    """自由领出轮：apply_banned_filter 不应删 Trips/AAA（GUA-235 豁免扩展到 Trips）。"""
    gs = build_gs()
    gs["_endgame_context"] = build_ec()
    gs["_endgame_context"]["is_active"] = True
    d = EndgameDecider()
    filtered, banned_empty = d.apply_banned_filter(full_action_list(), gs)
    assert not banned_empty
    assert any(a[0] == "Trips" for a in filtered), \
        f"自由领出应保留 Trips 候选；实际 {[a[0] for a in filtered]}"


def test_decide_integration_repro_picks_trips():
    """decide() 集成：21:37:58 复现局面 → Q0 冲刺出 Trips/AAA，非 Pair/A。"""
    gs = build_gs()
    gs["_endgame_context"] = build_ec()
    gs["_endgame_context"]["is_active"] = True
    d = EndgameDecider()
    idx, act = d.decide(gs, full_action_list())
    assert act is not None, "decide 应命中 Q0 冲刺"
    assert act[0] == "Trips", f"应出 Trips/AAA 冲刺；实际 {act}"
    assert act[2] == ["DA", "CA", "SA"], f"应出 AAA；实际 {act}"
