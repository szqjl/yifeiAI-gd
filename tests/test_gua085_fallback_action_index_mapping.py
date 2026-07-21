# -*- coding: utf-8 -*-
"""GUA-085：回退 NN 路径 group_actions → actionList 内容回查（修复 flt_map 错位）。"""

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

TARGET = ["ThreeWithTwo", "K", ["HK", "DK", "H8", "CT", "CT"]]
HAND = [
    "S2", "H2", "C3", "C3", "C4", "C5", "C6", "S7", "H7", "D7",
    "S9", "H9", "D9", "ST", "HT", "CT", "CT", "DT", "SQ", "HQ",
    "DQ", "SK", "SK", "HK", "DK", "HA", "H8",
]


def _generated_card_mask():
    source = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
    source._run_grouping_engine(
        {
            "myPos": 0,
            "handCards": HAND,
            "curRank": "8",
            "publicInfo": [{}, {}, {}, {}],
        }
    )
    return source._card_mask, source._group_type_map, source._group_members


def _build_action_list(target_idx: int = 973):
    al = [["PASS", "PASS", "PASS"]]
    al.append(["Single", "T", ["DT"]])
    al.append(["Single", "A", ["HA"]])
    while len(al) < target_idx:
        al.append(["Single", "3", ["C3"]])
    al.append(TARGET)
    while len(al) < 1234:
        al.append(["Pair", "2", ["S2", "H2"]])
    return al


def _engine_with_record_mask():
    card_mask, gtm, gm = _generated_card_mask()
    eng = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=False)
    eng._card_mask = card_mask
    eng._group_type_map = gtm
    eng._group_members = gm
    eng._current_role = "主攻"
    return eng


class TestGua085ContentMapping:
    def test_match_chosen_finds_first_identical_action(self):
        al = _build_action_list(973)
        chosen = ["Pair", "2", ["S2", "H2"]]
        idx = UltimateWinRateEngineV7._match_chosen_to_original_action_list(chosen, al)
        assert al[idx] == chosen
        assert idx == 974

    def test_model_path_does_not_map_to_three_with_two_slot(self, monkeypatch):
        """主路径失败后 model 选 group_actions[4]=Pair/2，不得 return 973(TWT/K)。"""
        monkeypatch.setattr(
            UltimateWinRateEngineV7,
            "_run_grouping_engine",
            lambda self, gs: None,
        )
        eng = _engine_with_record_mask()
        al = _build_action_list(973)
        al_no_dt = [a for a in al if not (a[0] == "Single" and a[2] == ["DT"])]
        gs = {
            "myPos": 0,
            "curPos": -1,
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": HAND,
            "actionList": al_no_dt,
            "curRank": "8",
            "publicInfo": [{}, {}, {}, {}],
            "numofplayers": [27, 27, 27, 27],
        }
        eng._model_decision = lambda gs, gal: 4

        idx = eng.decide(gs)
        assert al_no_dt[idx][0] != "ThreeWithTwo"
        assert al_no_dt[idx] == ["Pair", "2", ["S2", "H2"]]

    def test_fallback_content_mapping_overrides_stale_filter_index(self):
        """回归：旧 flt_map 可指向不同内容，最终必须按动作内容回查。"""
        from src.v.nn.guards.v7_guards import filter_action_list

        eng = _engine_with_record_mask()
        al = _build_action_list(973)
        gs = {
            "myPos": 0,
            "curPos": -1,
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": HAND,
            "actionList": al,
            "curRank": "8",
            "publicInfo": [{}, {}, {}, {}],
            "numofplayers": [27, 27, 27, 27],
        }
        filtered, action_map = filter_action_list(gs)
        ga, flt_map = eng._group_consistency_filter(filtered, gs)
        chosen = ga[1]
        wrong_orig = action_map[flt_map[1]]
        assert chosen == ["Single", "A", ["HA"]]
        assert al[wrong_orig] == ["Pair", "2", ["S2", "H2"]]
        matched = eng._match_chosen_to_original_action_list(chosen, al)
        assert matched != wrong_orig
        assert al[matched] == chosen


class TestGua085LeadRecommendSkipsSfCore:
    def test_lead_can_use_duplicate_scatter_without_breaking_sf_core(self):
        """GUA-154：两个 C3 分属散张/SF 时，可领散张 C3 且不拆 SF。"""
        eng = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
        gs = {
            "myPos": 0,
            "curPos": -1,
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": HAND,
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Single", "T", ["DT"]],
                ["Single", "A", ["HA"]],
            ],
            "curRank": "8",
            "publicInfo": [{}, {}, {}, {}],
            "numofplayers": [27, 27, 27, 27],
        }
        eng._run_grouping_engine(gs)
        rec = eng._recommend_lead_impl(
            gs, eng._card_mask, HAND, "8")
        assert rec is not None
        assert rec["type"] == "Single"
        assert rec["cards"] == ["C3"]
        broken = UltimateWinRateEngineV7._get_broken_core_type(
            ["Single", rec["rank"], rec["cards"]],
            eng._card_mask,
            eng._group_type_map,
            eng._group_members,
        )
        assert broken is None
