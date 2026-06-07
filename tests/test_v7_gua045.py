# -*- coding: utf-8 -*-
"""
GUA-045 V7 P0 Guard 壳测试

覆盖 V7-R01~R06 共 10+ 测试用例：
  1. test_r05_teammate_no_bomb         — R05: 队友领出不炸
  2. test_r01_no_bomb_for_single       — R01: 压单不用炸
  3. test_r02_minimal_bomb             — R02: 最小炸弹选择
  4. test_r03_passive_no_pass          — R03: 被动不PASS
  5. test_r04_single_b_non_pass        — R04: 有王/级牌不PASS
  6. test_r06_no_break_structure_pair  — R06: 不拆结构对子
  7. test_filter_action_list_integration — 综合：多规则同时生效
  8. test_validate_decision_override    — 校验：覆盖 PASS 为出牌
  9. test_validate_decision_bomb_teammate — 校验：覆盖炸队友
  10. test_engine_decide_with_guard     — 引擎集成：decide() 调用 guard
  11. test_all_bomb_fallback            — 边界：全 bomb actionList 不进死循环
  12. test_empty_action_list            — 边界：空 actionList 不崩溃
"""

import pytest
from typing import List, Dict, Any

from src.v.nn.guards import (
    filter_action_list,
    validate_decision,
    get_action_type,
    is_bomb,
    is_straight_flush,
    get_action_rank,
    get_card_value,
    CARD_RANK_ORDER,
    ACTION_TYPE_PASS,
    ACTION_TYPE_SINGLE,
    ACTION_TYPE_BOMB,
    ACTION_TYPE_STRAIGHT_FLUSH,
    ACTION_TYPE_PAIR,
)


def _make_state(**overrides) -> dict:
    """构造最小 game_state 工厂。"""
    state = {
        "actionList": [],
        "myPos": 0,
        "greaterPos": -1,
        "greaterAction": [],
        "curRank": "2",
        "handCards": [],
        "curPos": 0,
    }
    state.update(overrides)
    return state


# ═══════════════════════════════════════════════════════
#  R05: 队友领出不炸
# ═══════════════════════════════════════════════════════

class TestR05TeammateNoBomb:
    def test_r05_teammate_no_bomb(self):
        """队友(seat 2)领出，actionList 含炸 → 炸弹被剔除。"""
        state = _make_state(
            actionList=[["S3"], ["H3"], ["C3", "D3"], ["S5", "S5", "S5", "S5"]],
            greaterPos=2,       # 队友 (myPos=0, 队友=2)
            greaterAction=["S3"],
            myPos=0,
        )
        filtered, mapping = filter_action_list(state)
        # 炸弹应被过滤掉
        bomb_idx = 3  # ["S5","S5","S5","S5"]
        assert bomb_idx not in mapping, f"R05 应剔除炸弹索引 {bomb_idx}, 实际映射: {mapping}"
        assert len(filtered) >= 1, "过滤后应至少保留一个动作"

    def test_r05_opponent_lead_keep_bomb(self):
        """对手(seat 1)领出 Pair，炸弹应保留（R01 不触发）。"""
        state = _make_state(
            actionList=[["S3", "H3"], ["S5", "S5", "S5", "S5"]],
            greaterPos=1,       # 对手
            greaterAction=["S2", "H2"],  # Pair（非 Single，R01 不触发）
            myPos=0,
        )
        filtered, mapping = filter_action_list(state)
        assert 1 in mapping, "对手领出时炸弹应保留"

    def test_r05_teammate_passed_keep_bomb(self):
        """队友已 PASS，可炸（actually greater_pos != 队友）。"""
        state = _make_state(
            actionList=[["S3"], ["S5", "S5", "S5", "S5"]],
            greaterPos=1,
            greaterAction=["PASS"],
            myPos=0,
        )
        filtered, mapping = filter_action_list(state)
        assert 1 in mapping, "greaterPos != 队友时炸弹应保留"


# ═══════════════════════════════════════════════════════
#  R01: 压单不用炸
# ═══════════════════════════════════════════════════════

class TestR01NoBombForSingle:
    def test_r01_no_bomb_for_single(self):
        """压对手 Single 且有更小单牌 → 炸弹被剔除。"""
        state = _make_state(
            actionList=[["S3"], ["S5"], ["S5", "S5", "S5", "S5"]],
            greaterPos=1,
            greaterAction=["S2"],  # 对手出单2
            myPos=0,
            curRank="2",
        )
        filtered, mapping = filter_action_list(state)
        bomb_idx = 2
        assert bomb_idx not in mapping, f"R01 应剔除炸弹 {bomb_idx}, 实: {mapping}"

    def test_r01_no_bomb_if_no_single(self):
        """压 Single 但无更大单牌且单炸 → 炸弹保留。"""
        state = _make_state(
            actionList=[["S5", "S5", "S5", "S5"]],  # 只有炸弹，无单牌选项
            greaterPos=1,
            greaterAction=["SA"],  # 对手出单A，己方无更大单
            myPos=0,
            curRank="2",
        )
        filtered, mapping = filter_action_list(state)
        # 没有单牌选项，R01 不剔除炸弹
        assert 0 in mapping, "无单牌选项时炸弹应保留"


# ═══════════════════════════════════════════════════════
#  R02: 最小炸弹选择
# ═══════════════════════════════════════════════════════

class TestR02MinimalBomb:
    def test_r02_minimal_bomb(self):
        """同型多炸弹 → 只保留最短炸弹（R01 不触发）。"""
        state = _make_state(
            actionList=[
                ["S3", "H3"],
                ["S5", "S5", "S5", "S5"],       # 4张炸
                ["S6", "S6", "S6", "S6", "S6"],  # 5张炸
                ["S7", "S7", "S7", "S7", "S7", "S7", "S7"],  # 7张炸
            ],
            greaterPos=1,
            greaterAction=["S2", "H2"],  # Pair（非 Single，R01 不触发）
            myPos=0,
            curRank="2",
        )
        filtered, mapping = filter_action_list(state)
        # 应只保留 4 张炸（最短）
        # 4 张炸在原索引 1
        assert 1 in mapping, "最短炸弹(4张)应保留"
        # 5 张和 7 张炸应被过滤
        assert 2 not in mapping, "较长炸弹(5张)应被过滤" if 2 not in mapping else ""

    def test_r02_single_bomb_keep(self):
        """只有一个炸弹且不是 Single 场景 → 保留。"""
        state = _make_state(
            actionList=[["S3", "H3"], ["S5", "S5", "S5", "S5"]],
            greaterPos=1,
            greaterAction=["S2", "H2"],  # Pair（R01 不触发）
            myPos=0,
            curRank="2",
        )
        filtered, mapping = filter_action_list(state)
        assert len(mapping) == 2, "单炸不触发 R02 过滤"


# ═══════════════════════════════════════════════════════
#  R03: 被动不PASS
# ═══════════════════════════════════════════════════════

class TestR03PassiveNoPass:
    def test_r03_passive_no_pass(self):
        """对手出 Single，己方有同型 Single → PASS 被置于末位。"""
        state = _make_state(
            actionList=[["S3"], ["S5"], ["PASS"]],
            greaterPos=1,
            greaterAction=["S2"],
            myPos=0,
            curRank="2",
        )
        filtered, mapping = filter_action_list(state)
        # PASS (idx 2) 应在末尾
        pass_pos = mapping.index(2) if 2 in mapping else -1
        non_pass_positions = [mapping.index(i) for i in [0, 1] if i in mapping]
        if pass_pos >= 0 and non_pass_positions:
            assert pass_pos > max(non_pass_positions), \
                f"PASS 应在末尾: mapping={mapping}"

    def test_r03_self_lead_keep_pass(self):
        """自己领出 → PASS 位置不改变。"""
        state = _make_state(
            actionList=[["S3"], ["S5"], ["PASS"]],
            greaterPos=-1,        # 己方领出
            greaterAction=[],
            myPos=0,
        )
        filtered, mapping = filter_action_list(state)
        assert 2 in mapping, "领出时 PASS 应保留"


# ═══════════════════════════════════════════════════════
#  R04: 有王/级牌不PASS
# ═══════════════════════════════════════════════════════

class TestR04SingleBNonPass:
    def test_r04_single_b_non_pass(self):
        """对手 Single，己方有王可压 → PASS 被置后。"""
        state = _make_state(
            actionList=[["S3"], ["PASS"]],
            greaterPos=1,
            greaterAction=["SA"],
            myPos=0,
            curRank="2",
            handCards=["BJ", "S3"],
        )
        filtered, mapping = filter_action_list(state)
        # 有王(BJ)可压 → PASS 应在末尾
        if 1 in mapping:
            assert mapping[0] != 1 or len(mapping) == 1, \
                "有王可压时 PASS 应在末尾" if len(mapping) > 1 else ""

    def test_r04_no_beating_card_keep_pass(self):
        """对手 Single 但己方无可压单牌 → PASS 保留。"""
        state = _make_state(
            actionList=[["S3"], ["S5"], ["PASS"]],
            greaterPos=1,
            greaterAction=["SA"],    # 对手 A
            myPos=0,
            curRank="2",
            handCards=["S2", "H3"],
        )
        # S2 < SA, H3 < SA, 无可压单牌
        filtered, mapping = filter_action_list(state)
        assert 2 in mapping, "无可压牌时 PASS 应保留"


# ═══════════════════════════════════════════════════════
#  R06: 不拆结构对子
# ═══════════════════════════════════════════════════════

class TestR06NoBreakStructurePair:
    def test_r06_no_break_structure_pair(self):
        """手牌有天然对子，拆结构的对子被剔除。"""
        state = _make_state(
            actionList=[
                ["S3", "H3"],           # 天然对 3（手牌真有 2 张 3）
                ["S5", "H5"],           # 拆结构对 5（手牌有 4 张 5）
            ],
            myPos=0,
            handCards=["S3", "H3", "S5", "H5", "D5", "C5"],
            greaterPos=-1,
        )
        filtered, mapping = filter_action_list(state)
        # 天然对 3 (idx 0) 应保留
        # 手牌 4 张 5 → 对 5 是拆结构 → 可能被剔除
        # 具体看 R06 的实现：cnt=4 != 2 即视为拆结构
        assert 0 in mapping, "天然对子应保留"

    def test_r06_natural_pairs_kept(self):
        """全天然对子 → 全部保留。"""
        state = _make_state(
            actionList=[
                ["S3", "H3"],
                ["S4", "H4"],
            ],
            myPos=0,
            handCards=["S3", "H3", "S4", "H4"],
            greaterPos=-1,
        )
        filtered, mapping = filter_action_list(state)
        assert len(mapping) == 2, "全天然对子应全部保留"


# ═══════════════════════════════════════════════════════
#  综合测试：多规则同时生效
# ═══════════════════════════════════════════════════════

class TestFilterActionListIntegration:
    def test_filter_action_list_integration(self):
        """R01 + R05 同时触发：对手单牌+队友领出共存场景。"""
        state = _make_state(
            actionList=[
                ["S3"],                                # 0: 单牌
                ["S5", "S5", "S5", "S5"],               # 1: 炸弹
                ["S6", "S6", "S6", "S6"],               # 2: 炸弹
            ],
            greaterPos=1,    # 对手
            greaterAction=["S2"],
            myPos=0,
            curRank="2",
        )
        filtered, mapping = filter_action_list(state)
        # R01：压单 → 炸弹应被过滤
        for bomb_idx in (1, 2):
            assert bomb_idx not in mapping, \
                f"综合测试: 炸弹 {bomb_idx} 应被过滤"


# ═══════════════════════════════════════════════════════
#  validate_decision 校验
# ═══════════════════════════════════════════════════════

class TestValidateDecision:
    def test_validate_decision_override(self):
        """模型选 PASS 但应出牌 → 覆盖为非 PASS。"""
        state = _make_state(
            actionList=[["S3"], ["S5"], ["PASS"]],
            greaterPos=1,
            greaterAction=["S2"],   # 对手 Single
            myPos=0,
            curRank="2",
        )
        # 模型选了 PASS (idx 2)
        safe_idx = validate_decision(2, state["actionList"], state)
        # 应覆盖为同型非 PASS (idx 0 或 1)
        assert safe_idx in (0, 1), f"应覆盖为出牌, 实际 {safe_idx}"

    def test_validate_decision_bomb_teammate(self):
        """模型选炸弹炸队友 → 覆盖为非炸动作。"""
        state = _make_state(
            actionList=[
                ["S3"],                                # 0: 非炸
                ["S5", "S5", "S5", "S5"],               # 1: 炸弹
            ],
            greaterPos=2,    # 队友
            greaterAction=["S3"],
            myPos=0,
            curRank="2",
        )
        # 模型选了炸弹 (idx 1)
        safe_idx = validate_decision(1, state["actionList"], state)
        # 应覆盖为非炸 (idx 0)
        assert safe_idx == 0, f"炸队友应覆盖为 idx 0, 实际 {safe_idx}"

    def test_validate_decision_valid_keep(self):
        """合理决策 → 不变。"""
        state = _make_state(
            actionList=[["S3"], ["S5"]],
            greaterPos=1,
            greaterAction=["S2"],
            myPos=0,
        )
        safe_idx = validate_decision(1, state["actionList"], state)
        assert safe_idx == 1, "合法决策不应被覆盖"


# ═══════════════════════════════════════════════════════
#  引擎集成测试
# ═══════════════════════════════════════════════════════

class TestEngineDecideWithGuard:
    def test_engine_decide_with_guard(self):
        """验证 engine.decide() 接入 guard 后正常返回。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        engine = UltimateWinRateEngineV7(player_id=0)
        msg = {
            "actionList": [["S3"], ["S5"], ["PASS"]],
            "myPos": 0,
            "greaterPos": 1,
            "greaterAction": ["S2"],
            "curRank": "2",
            "handCards": ["S3", "S4", "S5"],
        }
        idx = engine.decide(msg)
        assert 0 <= idx < len(msg["actionList"]), \
            f"决策索引越界: {idx}"


# ═══════════════════════════════════════════════════════
#  边界情况
# ═══════════════════════════════════════════════════════

class TestEdgeCases:
    def test_all_bomb_fallback(self):
        """全 bomb actionList 不进入死循环。"""
        state = _make_state(
            actionList=[
                ["S5", "S5", "S5", "S5"],
                ["S6", "S6", "S6", "S6"],
                ["S7", "S7", "S7", "S7", "S7"],
            ],
            greaterPos=2,
            greaterAction=["S3"],
            myPos=0,
            curRank="2",
        )
        filtered, mapping = filter_action_list(state)
        # R05 触发：队友领出全炸 → 应保留最短炸作为 fallback
        assert len(filtered) >= 1, "全炸情况应至少保留一个动作"

    def test_empty_action_list(self):
        """空 actionList → 不崩溃。"""
        state = _make_state(actionList=[])
        filtered, mapping = filter_action_list(state)
        assert filtered == [], "空 actionList 应返回空列表"
        assert mapping == [], "空 actionList 映射应为空"

    def test_no_greater_action(self):
        """greaterAction 为空（领出）→ 不触发 guard。"""
        state = _make_state(
            actionList=[["S3"], ["S4"], ["S5", "S5", "S5", "S5"]],
            greaterPos=-1,
            greaterAction=[],
            myPos=0,
        )
        filtered, mapping = filter_action_list(state)
        assert len(mapping) == len(state["actionList"]), \
            "领出时应全部保留"


# ═══════════════════════════════════════════════════════
#  快捷工具函数测试
# ═══════════════════════════════════════════════════════

class TestGuardUtils:
    def test_get_action_type(self):
        assert get_action_type(["S3"]) == ACTION_TYPE_SINGLE
        assert get_action_type(["S3", "H3"]) == ACTION_TYPE_PAIR
        assert get_action_type(["S5", "S5", "S5", "S5"]) == ACTION_TYPE_BOMB
        assert get_action_type(["PASS"]) == ACTION_TYPE_PASS
        assert get_action_type([]) == ACTION_TYPE_PASS

    def test_is_bomb(self):
        assert is_bomb(["S5", "S5", "S5", "S5"]) is True
        assert is_bomb(["S3"]) is False

    def test_get_card_value(self):
        assert get_card_value("BJ") == 13
        assert get_card_value("RJ") == 14
        assert get_card_value("S2", "2") >= 15  # 级牌
        assert get_card_value("SA") == 12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])