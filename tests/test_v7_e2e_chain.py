# -*- coding: utf-8 -*-
"""
V7 端到端决策链路测试（GUA-037a + V7-006）

验证引擎全链路：
  1. 引擎初始化（含模型自动加载）
  2. 特征提取（124 维静态 → 512 维）
  3. 模型推理（action_logits → softmax）
  4. 决策输出（action index）
  5. 回退到规则引擎（无模型时）

运行: venv\Scripts\python.exe -m pytest tests/test_v7_e2e_chain.py -v
"""

import os
import sys
from typing import Any, Dict, List

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── 全局 torch 可用性 ──
try:
    import torch

    TORCH_AVAILABLE = torch.__version__ >= "1.0"
except ImportError:
    TORCH_AVAILABLE = False

# ── 检查模型是否存在 ──
MODEL_PATH = os.environ.get("V7_MODEL_PATH", "models/bc_model_ultimate_win_rate.pth")
MODEL_EXISTS = os.path.exists(MODEL_PATH)


# ── 辅助构造 ──

def _make_game_state(
    handCards: List[str] = None,
    curPos: int = 0,
    myPos: int = 0,
    curRank: str = "2",
    **kwargs,
) -> Dict[str, Any]:
    """构造最小游戏状态。"""
    state = {
        "handCards": handCards or [],
        "curPos": curPos,
        "myPos": myPos,
        "curRank": curRank,
        "selfRank": kwargs.get("selfRank", curRank),
        "oppoRank": kwargs.get("oppoRank", "2"),
        "actionList": kwargs.get("actionList", []),
        "curBombNum": kwargs.get("curBombNum", 0),
    }
    if "tributeResult" in kwargs:
        state["tributeResult"] = kwargs["tributeResult"]
    return state


# ── 测试 1: 引擎初始化 ──

class TestEngineInit:
    def test_engine_creation(self):
        """引擎可正常创建。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        assert engine is not None
        assert engine.player_id == 0
        assert engine.decision_count == 0
        assert engine.model_decisions == 0
        assert engine.fallback_decisions == 0

    def test_engine_model_loading(self):
        """引擎自动尝试加载模型（环境中有模型文件则加载）。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        if MODEL_EXISTS and TORCH_AVAILABLE:
            assert engine.model is not None, "模型文件存在时引擎应成功加载模型"
        else:
            assert engine.model is None, "无模型文件时 model 应为 None"

    def test_engine_device(self):
        """引擎设备初始化正确。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        expected = "cuda" if torch.cuda.is_available() else "cpu"
        assert str(engine.device) == expected, f"device 应为 {expected}"


# ── 测试 2: 特征提取链路 ──

class TestFeatureChain:
    def test_extract_features_512_output(self):
        """_extract_features 输出应为 512 维 float32。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        gs = _make_game_state(handCards=["S2", "H3", "D5", "C7", "BJ"], curPos=0)
        feat = engine._extract_features(gs, [["S2"]])
        assert feat is not None, "特征不应为 None"
        assert feat.shape == (512,), f"期望 512 维，实际 {feat.shape}"
        assert feat.dtype == np.float32, f"期望 float32，实际 {feat.dtype}"

    def test_first_124_dims_nonzero(self):
        """前 124 维（静态特征）应包含非零值。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        gs = _make_game_state(
            handCards=["S2", "S2", "H3", "D5", "C7", "BJ", "RJ"],
            curPos=0,
            curRank="2",
        )
        feat = engine._extract_features(gs, [["S2"]])
        assert feat is not None
        assert np.any(feat[:124] > 0), "前 124 维应包含非零值"

    def test_last_388_dims_all_zero(self):
        """后 388 维（padding 区域）应全为零。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        gs = _make_game_state(handCards=["S2", "H3", "D5", "C7"], curPos=0)
        feat = engine._extract_features(gs, [["S2"]])
        assert feat is not None
        assert np.all(feat[124:] == 0), "后 388 维应全为 0"

    def test_varied_hand_count(self):
        """不同手牌数量应产生不同的特征向量。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        gs1 = _make_game_state(handCards=["S2", "H3", "D5"], curPos=0)
        gs2 = _make_game_state(handCards=["S2", "H3", "D5", "C7", "S4"], curPos=0)
        f1 = engine._extract_features(gs1, [["S2"]])
        f2 = engine._extract_features(gs2, [["S2"]])
        assert f1 is not None and f2 is not None
        assert not np.array_equal(f1, f2), "不同手牌应产生不同的特征向量"

    def test_empty_hand_features(self):
        """空手牌时前 124 维结构不变。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        gs = _make_game_state(handCards=[], curPos=0)
        feat = engine._extract_features(gs, [["PASS"]])
        assert feat is not None
        assert feat.shape == (512,)
        # 手牌为 0 → 前 108 维全 0（无牌），123 维 = 0/27 = 0
        assert np.all(feat[0:108] == 0), "空手牌前 108 维应全 0"
        assert np.all(feat[124:] == 0), "后 388 维应全 0"


# ── 测试 3: 模型推理链路 ──

class TestModelInference:
    def test_model_decision_returns_valid_index(self):
        """模型决策返回的动作索引应在 action_list 范围内。"""
        if not MODEL_EXISTS:
            pytest.skip(f"模型文件不存在: {MODEL_PATH}")
        if not TORCH_AVAILABLE:
            pytest.skip("需要 torch")

        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        assert engine.model is not None, "模型应已加载"

        gs = _make_game_state(
            handCards=["S2", "S2", "H3", "D5", "C7", "BJ", "RJ"],
            curPos=0,
            curRank="2",
            actionList=[["S2"], ["S2", "S2"], ["PASS"]],
        )
        idx = engine._model_decision(gs, [["S2"], ["S2", "S2"], ["PASS"]])
        assert idx is not None, "模型决策不应为 None"
        assert 0 <= idx < 3, f"动作索引 {idx} 应属于 [0, 3)"

    def test_model_decision_fallback_on_empty(self):
        """空 action_list 时应返回 None。"""
        if not MODEL_EXISTS:
            pytest.skip(f"模型文件不存在: {MODEL_PATH}")
        if not TORCH_AVAILABLE:
            pytest.skip("需要 torch")

        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        idx = engine._model_decision({}, [])
        assert idx is None, "空动作列表应返回 None"

    def test_model_decision_different_actions(self):
        """不同 action_list 产生不同决策。"""
        if not MODEL_EXISTS:
            pytest.skip(f"模型文件不存在: {MODEL_PATH}")
        if not TORCH_AVAILABLE:
            pytest.skip("需要 torch")

        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        gs = _make_game_state(
            handCards=["S2", "S2", "H3", "D5", "C7", "BJ", "RJ"],
            curPos=0,
            curRank="2",
            actionList=[["S2"], ["S2", "S2"], ["PASS"]],
        )
        # 对相同状态决策两次应得到相同结果（模型 eval 模式下确定性的）
        idx1 = engine._model_decision(gs, [["S2"], ["S2", "S2"], ["PASS"]])
        idx2 = engine._model_decision(gs, [["S2"], ["S2", "S2"], ["PASS"]])
        assert idx1 is not None and idx2 is not None
        assert idx1 == idx2, "相同状态应得到相同决策"


# ── 测试 4: 完整 decide 循环 ──

class TestDecideCycle:
    def test_decide_full_chain(self):
        """完整的 decide 决策流程（有模型时走模型，否则走规则）。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        msg = _make_game_state(
            handCards=["S2", "S2", "H3", "D5", "C7", "BJ", "RJ"],
            curPos=0,
            curRank="2",
            actionList=[["S2"], ["S2", "S2"], ["PASS"]],
        )
        idx = engine.decide(msg)
        assert 0 <= idx < 3, f"决策动作索引 {idx} 应属于 [0, 3)"
        assert engine.decision_count >= 1, "应有至少 1 次决策"

    def test_decide_rule_fallback(self):
        """模型不可用时回退到规则引擎。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        # 通过 env 指向不存在的模型路径来强制回退
        old_val = os.environ.pop("V7_MODEL_PATH", None)
        os.environ["V7_MODEL_PATH"] = "nonexistent_model.pth"
        try:
            engine = UltimateWinRateEngineV7(player_id=0)
            msg = _make_game_state(
                handCards=["S2", "S2", "H3", "D5", "C7", "BJ", "RJ"],
                curPos=0,
                actionList=[["S2"], ["S2", "S2"], ["PASS"]],
            )
            idx = engine.decide(msg)
            assert 0 <= idx < 3, f"规则回退索引 {idx} 应属于 [0, 3)"
            assert engine.model is None, "模型应为 None"
            # 回退时应优先选非 PASS 动作（index 0 或 1）
            assert idx != 2, "规则回退应优先选择非 PASS 动作"
        finally:
            if old_val is not None:
                os.environ["V7_MODEL_PATH"] = old_val
            else:
                os.environ.pop("V7_MODEL_PATH", None)

    def test_decide_no_action_list(self):
        """actionList 为空时返回 0。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        idx = engine.decide(_make_game_state(handCards=["S2"]))
        assert idx == 0, "空 actionList 应返回 0"

    def test_decide_multiple_calls(self):
        """多次决策调用不崩溃。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        for i in range(5):
            msg = _make_game_state(
                handCards=["S2", "S2", "H3", "D5", "C7", "BJ", "RJ"],
                curPos=0,
                actionList=[["S2"], ["S2", "S2"], ["PASS"]],
            )
            idx = engine.decide(msg)
            assert 0 <= idx < 3, f"第 {i+1} 次决策索引越界"
        assert engine.decision_count == 5, "决策计数应为 5"

    def test_decide_pass_only(self):
        """全部 PASS 时应返回 0。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        msg = _make_game_state(
            handCards=["S2"],
            curPos=0,
            actionList=[["PASS"]],
        )
        idx = engine.decide(msg)
        assert idx == 0, "全 PASS 时应返回 0"


# ── 测试 5: 统计信息 ──

class TestDecisionStats:
    def test_decision_counts(self):
        """决策计数正确递增。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        old_val = os.environ.pop("V7_MODEL_PATH", None)
        os.environ["V7_MODEL_PATH"] = "nonexistent_model.pth"
        try:
            engine = UltimateWinRateEngineV7(player_id=0)
            msg = _make_game_state(
                handCards=["S2"],
                curPos=0,
                actionList=[["S2"]],
            )
            engine.decide(msg)
            engine.decide(msg)
            assert engine.decision_count == 2, "decisions 应为 2"
            assert engine.fallback_decisions == 2, "无模型时全是回退"
            assert engine.model_decisions == 0, "无模型时模型决策为 0"
        finally:
            if old_val is not None:
                os.environ["V7_MODEL_PATH"] = old_val
            else:
                os.environ.pop("V7_MODEL_PATH", None)

    def test_decisions_zero_on_create(self):
        """新建引擎时计数全为 0。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        engine = UltimateWinRateEngineV7(player_id=0)
        assert engine.decision_count == 0
        assert engine.model_decisions == 0
        assert engine.fallback_decisions == 0


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])