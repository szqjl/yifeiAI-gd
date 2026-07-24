# -*- coding: utf-8 -*-
"""GUA-150 单元测试：self_sprint 让道误判修复（比较 self/teammate 冲刺路径长度）

测试覆盖（基于 WF-12 锚点 20260716222448436062 步 35/79）：
  - self_sprint + teammate_sprint + self_hands ≤ teammate_hands → 选 min 非炸非 PASS 动作夺权（不 PASS）
  - self_sprint + teammate_sprint + self_hands > teammate_hands → PASS 让道
  - self_sprint + teammate_sprint + teammate_hands 未知 → 保守 PASS（保持原行为）
  - self_sprint + teammate_sprint + 无非炸候选 → PASS 保留炸弹
  - self_hands == teammate_hands → 选 lead（≤ 包含等于）

锚点：
  - self hand=7 [H8,S8,D8,H8,D8,CT,SB]（5 星 8 炸+CT+SB）
  - 平台 actionList = [PASS, Single/B[SB], Bomb/8×4 variants]
  - 期望：选 Single/B（idx=1），不选 PASS
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor


# ── 测试数据（用户牌谱步 35 场景）──

HAND_5STAR_8 = ["H8", "S8", "D8", "H8", "D8", "CT", "SB"]  # 5 星 8 炸 + CT + SB
TWT_GREATER = ["ThreeWithTwo", "5", ["S5", "H5", "D5", "S2", "D2"]]  # client4 级牌 5 TWT
PASS_ACT = ["PASS", "PASS", "PASS"]
SINGLE_B_SB = ["Single", "B", ["SB"]]
BOMB_8_4STAR_A = ["Bomb", "8", ["H8", "D8", "H8", "D8"]]
BOMB_8_4STAR_B = ["Bomb", "8", ["H8", "S8", "D8", "D8"]]
BOMB_8_4STAR_C = ["Bomb", "8", ["H8", "S8", "D8", "H8"]]
BOMB_8_5STAR = ["Bomb", "8", ["H8", "S8", "D8", "H8", "D8"]]


def _build_action_list():
    """模拟平台给出的 6 项候选（与用户牌谱 actionList_sample 一致）。"""
    return [
        list(PASS_ACT),
        list(SINGLE_B_SB),
        list(BOMB_8_4STAR_A),
        list(BOMB_8_4STAR_B),
        list(BOMB_8_4STAR_C),
        list(BOMB_8_5STAR),
    ]


def _build_state(
    hand_cards=None,
    action_list=None,
    *,
    my_pos=0,
    greater_pos=1,
    enemy_remaining=10,
    teammate_remaining=7,
    at3_remaining=8,
    cur_rank="5",
):
    """构造 GUA-135 self_sprint 触发场景的 game_state。"""
    hand_n = len(hand_cards or HAND_5STAR_8)
    numofplayers = [27, 27, 27, 27]
    numofplayers[my_pos] = hand_n
    numofplayers[greater_pos] = enemy_remaining
    numofplayers[(my_pos + 2) % 4] = teammate_remaining
    other_enemy = (my_pos + 1) % 4
    if other_enemy == greater_pos:
        other_enemy = (my_pos + 3) % 4
    numofplayers[other_enemy] = at3_remaining
    gs = {
        "myPos": my_pos,
        "curPos": greater_pos,
        "greaterPos": greater_pos,
        "greaterAction": TWT_GREATER,
        "handCards": list(hand_cards or HAND_5STAR_8),
        "actionList": list(action_list or _build_action_list()),
        "curRank": cur_rank,
        "selfRank": "A",
        "oppoRank": cur_rank,
        "numofplayers": numofplayers,
        "publicInfo": [{"rest": n} for n in numofplayers],
        "_role": "主攻",
    }
    return gs


def _preprocess(gs):
    """运行 EndgamePreprocessor 并注入 finish_type 触发 self_sprint。"""
    EndgamePreprocessor().preprocess(gs)
    ec = gs["_endgame_context"]
    enemy = ec.get("enemies", {}).get(gs["greaterPos"], {})
    if enemy:
        if "finish_type" not in enemy:
            enemy["finish_type"] = "ThreeWithTwo"
        if "finish_rank_value" not in enemy:
            # C5 finish 更小 → 触发 self_sprint trigger
            enemy["finish_rank_value"] = 4
    return gs


# ════════════════════════════════════════════
#  GUA-150 self_sprint_priority
# ════════════════════════════════════════════

class TestGua150SelfSprintPriority:
    """GUA-150：self_sprint 让道误判修复 — 比较 self/teammate 冲刺路径长度。"""

    def test_self_shorter_chooses_lead_action(self):
        """self_hands=2 ≤ teammate_hands=3 → 选 Single/B 夺权，不 PASS（核心场景）"""
        gs = _build_state()
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        # mock teammate_sprint=True（pos=2 是 teammate）
        d._estimate_player_sprint_capability = lambda pos, _gs: pos == 2
        d._has_teammate_bomb_family = lambda *a, **kw: False
        # mock num_rounds 比较
        d._estimate_self_num_rounds = lambda _gs: 2
        d._estimate_player_num_rounds = lambda pos, _gs: 3 if pos == 2 else 0
        # GUA-150 可靠性检查 mock：视 teammate 手数估计为可靠
        d._check_teammate_estimate_reliable = lambda pos, _gs: pos == 2

        result = d._q1_double_second_priority(
            gs, gs["actionList"], ec, 1, ec["enemies"][1],
        )
        assert result is not None, "应返回非 None 动作"
        idx, act = result
        assert act[0] == "Single", f"期望 Single（夺权），实际 {act[0]}"
        assert idx == 1, f"期望 idx=1（Single/B[SB]），实际 idx={idx}"

    def test_self_longer_passes_for_teammate(self):
        """self_hands=5 > teammate_hands=2 → PASS 让 teammate 拿第二"""
        gs = _build_state()
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        d._estimate_player_sprint_capability = lambda pos, _gs: pos == 2
        d._has_teammate_bomb_family = lambda *a, **kw: False
        d._estimate_self_num_rounds = lambda _gs: 5
        d._estimate_player_num_rounds = lambda pos, _gs: 2 if pos == 2 else 0
        d._check_teammate_estimate_reliable = lambda pos, _gs: pos == 2

        result = d._q1_double_second_priority(
            gs, gs["actionList"], ec, 1, ec["enemies"][1],
        )
        assert result is not None
        idx, act = result
        assert act[0] == "PASS", f"self 路径更长时应 PASS，实际 {act[0]}"

    def test_teammate_unreliable_falls_through(self):
        """teammate_hands 推断不可靠（MemoryTracker 无数据）→ 降级出牌夺权；无 TWT 时返回 None"""
        gs = _build_state()
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        d._estimate_player_sprint_capability = lambda pos, _gs: pos == 2
        d._has_teammate_bomb_family = lambda *a, **kw: False
        d._estimate_self_num_rounds = lambda _gs: 2
        d._estimate_player_num_rounds = lambda pos, _gs: 0  # 未知
        # 不 mock _check_teammate_estimate_reliable → 走真实实现（无 MemoryTracker → False）

        result = d._q1_double_second_priority(
            gs, gs["actionList"], ec, 1, ec["enemies"][1],
        )
        # actionList 无 TWT → 返回 None（不 PASS 让道）
        assert result is None, "teammate 推断不可靠且无 TWT 时应返回 None（不 PASS）"

    def test_no_non_bomb_candidate_passes(self):
        """actionList 仅含 PASS + Bomb → PASS 保留炸弹（无 lead 候选）"""
        gs = _build_state(action_list=[list(PASS_ACT), list(BOMB_8_5STAR)])
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        d._estimate_player_sprint_capability = lambda pos, _gs: pos == 2
        d._has_teammate_bomb_family = lambda *a, **kw: False
        d._estimate_self_num_rounds = lambda _gs: 2
        d._estimate_player_num_rounds = lambda pos, _gs: 3 if pos == 2 else 0
        d._check_teammate_estimate_reliable = lambda pos, _gs: pos == 2

        result = d._q1_double_second_priority(
            gs, gs["actionList"], ec, 1, ec["enemies"][1],
        )
        assert result is not None
        idx, act = result
        assert act[0] == "PASS", "无非炸非 PASS 候选时应 PASS 保留炸弹"

    def test_self_equal_teammate_chooses_lead(self):
        """self_hands=3 == teammate_hands=3 → 选 lead（≤ 包含等于）"""
        gs = _build_state()
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        d._estimate_player_sprint_capability = lambda pos, _gs: pos == 2
        d._has_teammate_bomb_family = lambda *a, **kw: False
        d._estimate_self_num_rounds = lambda _gs: 3
        d._estimate_player_num_rounds = lambda pos, _gs: 3 if pos == 2 else 0
        d._check_teammate_estimate_reliable = lambda pos, _gs: pos == 2

        result = d._q1_double_second_priority(
            gs, gs["actionList"], ec, 1, ec["enemies"][1],
        )
        assert result is not None
        idx, act = result
        assert act[0] == "Single", "self_hands == teammate_hands 时应选 lead"

    def test_no_teammate_sprint_falls_through_to_else(self):
        """teammate_sprint=False → 走原 else 分支（跟 min TWT 或 None）"""
        # 这个 actionList 无 TWT，应返回 None
        gs = _build_state()
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        # teammate_sprint=False
        d._estimate_player_sprint_capability = lambda pos, _gs: False
        d._has_teammate_bomb_family = lambda *a, **kw: False

        result = d._q1_double_second_priority(
            gs, gs["actionList"], ec, 1, ec["enemies"][1],
        )
        # actionList 无 TWT，应返回 None（保持原行为）
        assert result is None, "teammate_sprint=False 且无 TWT 时应返回 None"
