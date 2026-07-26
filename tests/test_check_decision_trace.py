"""
test_check_decision_trace.py — WF-12 §0 强制检查脚本的纯函数测试

不依赖真实牌谱；对 parse_record_name / action_key / is_play_decision /
find_decision_at_step / pair_teammate_json 做单元覆盖。
"""
from __future__ import annotations

import sys
from pathlib import Path

# 把 scripts/checks/ 加入 import 路径
SCRIPTS_CHECK = Path(__file__).resolve().parent.parent / "scripts" / "checks"
sys.path.insert(0, str(SCRIPTS_CHECK))

import check_decision_trace as cdt  # noqa: E402


# ---------- parse_record_name ----------

class TestParseRecordName:
    def test_yf1_v8_standard(self):
        p = Path("game_records_v8/20260722202349717209 [yf1_v8]-[opponent_1_3]-[1]-[2].json")
        r = cdt.parse_record_name(p)
        assert r == {
            "timestamp": "20260722202349717209",
            "client": "yf1_v8",
            "opponent": "opponent_1_3",
            "round": "1",
            "suffix": "2",
        }

    def test_yf2_v7_standard(self):
        p = Path("game_records_v7/20260708230844225341 [yf2_v7]-[opponent_1_3]-[1]-[2].json")
        r = cdt.parse_record_name(p)
        assert r["client"] == "yf2_v7"
        assert r["round"] == "1"
        assert r["suffix"] == "2"

    def test_invalid_filename_returns_none(self):
        p = Path("foo/bar/random.json")
        assert cdt.parse_record_name(p) is None

    def test_missing_brackets_returns_none(self):
        p = Path("20260722 yf1_v8 - opponent_1_3 - 1 - 2.json")
        assert cdt.parse_record_name(p) is None


# ---------- action_key ----------

class TestActionKey:
    def test_pass_returns_tuple(self):
        # PASS 是合法 action，action_key 返回归一化 tuple（type="PASS", rank="", cards=()）
        # 不返回 None；None 仅在 action 非 list 或为空时返回
        k = cdt.action_key(["PASS"])
        assert k == ("PASS", "", ())

    def test_single_normalizes(self):
        # 大小写不敏感、牌内顺序忽略
        k = cdt.action_key(["Single", "7", ["DA", "D7"]])
        assert k == ("SINGLE", "7", ("D7", "DA"))

    def test_three_with_two_keeps_card_set(self):
        k = cdt.action_key(["ThreeWithTwo", "8", ["S8", "H8", "D8", "S2", "H2"]])
        assert k[0] == "THREEWITHTWO"
        assert k[1] == "8"
        assert set(k[2]) == {"S8", "H8", "D8", "S2", "H2"}

    def test_empty_list_returns_none(self):
        assert cdt.action_key([]) is None

    def test_no_rank_defaults_empty(self):
        k = cdt.action_key(["Bomb"])
        assert k == ("BOMB", "", ())


# ---------- is_play_decision ----------

class TestIsPlayDecision:
    def test_play_stage_is_play(self):
        assert cdt.is_play_decision({"context": {"stage": "play"}}) is True

    def test_tribute_excluded(self):
        assert cdt.is_play_decision({"context": {"stage": "tribute"}}) is False

    def test_back_excluded(self):
        assert cdt.is_play_decision({"context": {"stage": "back"}}) is False

    def test_no_stage_source_act_is_play(self):
        assert cdt.is_play_decision({"context": {"source": "act"}}) is True

    def test_no_stage_other_source_excluded(self):
        assert cdt.is_play_decision({"context": {"source": "other"}}) is False

    def test_missing_context_excluded(self):
        assert cdt.is_play_decision({}) is False


# ---------- find_decision_at_step ----------

def _make_game(player_id=0, actions=None, decisions=None):
    return {
        "player_id": player_id,
        "actions": actions or [],
        "my_decisions": decisions or [],
    }


def _make_play(cur_pos, cur_action):
    return {"cur_pos": cur_pos, "cur_action": cur_action}


def _make_decision(stage, action, handCards_size=10, curRank="2", layer="GUA-075推荐"):
    return {
        "context": {
            "stage": stage,
            "handCards_size": handCards_size,
            "curRank": curRank,
        },
        "action": action,
        "layer": layer,
    }


class TestFindDecisionAtStep:
    def test_simple_align(self):
        # yf1 player_id=0，前 3 步全是 player 0 出牌 → turn_idx=2
        actions = [
            _make_play(0, ["PASS"]),
            _make_play(0, ["Single", "5", ["D5"]]),
            _make_play(0, ["Pair", "7", ["D7", "C7"]]),  # 步 3
            _make_play(1, ["Single", "9", ["D9"]]),
        ]
        decisions = [
            _make_decision("play", ["PASS"], handCards_size=20),
            _make_decision("play", ["Single", "5", ["D5"]], handCards_size=18),
            _make_decision("play", ["Pair", "7", ["D7", "C7"]], handCards_size=16),
        ]
        game = _make_game(player_id=0, actions=actions, decisions=decisions)
        decision, play = cdt.find_decision_at_step(game, 3)
        assert decision["context"]["handCards_size"] == 16
        assert decision["layer"] == "GUA-075推荐"
        assert play["cur_action"][0] == "Pair"

    def test_step_not_for_player_raises(self):
        # 步 2 是 player 1 出牌，分析 player 0 → 报错
        actions = [
            _make_play(0, ["PASS"]),
            _make_play(1, ["Single", "9", ["D9"]]),
        ]
        game = _make_game(player_id=0, actions=actions, decisions=[])
        import pytest as _pytest
        with _pytest.raises(ValueError, match="cur_pos=1 != player_id=0"):
            cdt.find_decision_at_step(game, 2)

    def test_step_out_of_range_raises(self):
        game = _make_game(player_id=0, actions=[_make_play(0, ["PASS"])])
        import pytest as _pytest
        with _pytest.raises(ValueError, match="out of range"):
            cdt.find_decision_at_step(game, 999)

    def test_ordinal_action_mismatch_raises(self):
        # ordinal 对齐的 decision 但 action 不匹配 → 报错
        actions = [_make_play(0, ["Single", "5", ["D5"]])]
        decisions = [_make_decision("play", ["Single", "9", ["D9"]])]  # action 不一致
        game = _make_game(player_id=0, actions=actions, decisions=decisions)
        import pytest as _pytest
        with _pytest.raises(ValueError, match="ordinal/action mismatch"):
            cdt.find_decision_at_step(game, 1)

    def test_ordinal_mismatch_unique_fallback(self):
        # ordinal 对不上，但全表唯一匹配 → 回退
        actions = [
            _make_play(0, ["PASS"]),
            _make_play(0, ["Single", "5", ["D5"]]),
        ]
        decisions = [
            _make_decision("play", ["Single", "9", ["D9"]]),  # ordinal[0]
            _make_decision("play", ["Single", "5", ["D5"]]),  # ordinal[1]，唯一匹配
        ]
        game = _make_game(player_id=0, actions=actions, decisions=decisions)
        decision, _ = cdt.find_decision_at_step(game, 2)
        assert decision["action"][1] == "5"

    def test_tribute_excluded_from_turn_count(self):
        # tribute 决策不计入 turn_idx
        actions = [
            _make_play(0, ["PASS"]),       # turn 0（play）
            _make_play(0, ["Single", "5", ["D5"]]),  # turn 1
        ]
        decisions = [
            _make_decision("tribute", ["back"]),  # 不计入
            _make_decision("play", ["PASS"]),
            _make_decision("play", ["Single", "5", ["D5"]]),
        ]
        game = _make_game(player_id=0, actions=actions, decisions=decisions)
        decision, _ = cdt.find_decision_at_step(game, 2)
        assert decision["action"][0] == "Single"


# ---------- pair_teammate_json ----------

class TestPairTeammateJson:
    def test_pair_yf1_finds_yf2_same_round_suffix(self, tmp_path):
        yf1 = tmp_path / "20260701175356173308 [yf1_v7]-[opponent_1_3]-[36]-[2].json"
        yf2 = tmp_path / "20260701175356193021 [yf2_v7]-[opponent_1_3]-[36]-[2].json"
        yf2_other_round = tmp_path / "20260701175356194000 [yf2_v7]-[opponent_1_3]-[37]-[2].json"
        yf1.write_text("{}")
        yf2.write_text("{}")
        yf2_other_round.write_text("{}")
        result = cdt.pair_teammate_json(yf1)
        assert result == yf2

    def test_pair_returns_none_if_no_yf2(self, tmp_path):
        yf1 = tmp_path / "20260701175356173308 [yf1_v7]-[opponent_1_3]-[36]-[2].json"
        yf1.write_text("{}")
        assert cdt.pair_teammate_json(yf1) is None

    def test_pair_returns_none_for_yf2_input(self, tmp_path):
        # yf2 作为输入时不配对（pair 函数只对 yf1 工作）
        yf2 = tmp_path / "20260701175356193021 [yf2_v7]-[opponent_1_3]-[36]-[2].json"
        yf2.write_text("{}")
        assert cdt.pair_teammate_json(yf2) is None

    def test_pair_picks_closest_timestamp(self, tmp_path):
        # 两个 yf2 同 [round]-[suffix]，取最接近 yf1 timestamp 的
        yf1 = tmp_path / "20260701175356173308 [yf1_v7]-[opponent_1_3]-[36]-[2].json"
        yf2_close = tmp_path / "20260701175356193021 [yf2_v7]-[opponent_1_3]-[36]-[2].json"
        yf2_far = tmp_path / "20260701180000000000 [yf2_v7]-[opponent_1_3]-[36]-[2].json"
        yf1.write_text("{}")
        yf2_close.write_text("{}")
        yf2_far.write_text("{}")
        result = cdt.pair_teammate_json(yf1)
        assert result == yf2_close