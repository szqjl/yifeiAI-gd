# -*- coding: utf-8 -*-
"""
GUA-037b 动态特征工程测试

覆盖 8+ 测试用例：
  1. test_seq_len_zero            — 空序列输出 64 维全零
  2. test_seq_len_one             — 单步序列正确编码
  3. test_seq_len_eight           — 8 步序列编码
  4. test_seq_len_twenty          — 20 步序列（最大长度）
  5. test_seq_len_over_max        — 超长序列截断至 20
  6. test_pass_step               — 含 PASS 步的序列
  7. test_combined_dimension      — 拼接后维度 = 124 + 64 = 188
  8. test_combined_value_range    — 拼接特征在合理范围内
  9. test_engine_integration      — 引擎 _extract_features 输出 512 维含动态特征
"""

import numpy as np
import pytest

from src.v.nn.features.dynamic_features import (
    extract_dynamic_features,
    extract_combined_features,
    build_history_sequence,
    lstm_encode,
    DYNAMIC_HIDDEN_DIM,
    MAX_SEQ_LEN,
    SEQ_STEP_DIM,
)
from src.v.nn.features.static_features import extract_static_features, STATIC_STATE_DIM


# ── 工具 ──────────────────────────────────────────────

def _make_game_state(**overrides) -> dict:
    """构造最小 game_state 工厂。"""
    state = {
        "handCards": [],
        "myPos": 0,
        "curPos": 0,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "actionList": [["S3"]],
        "curBombNum": 0,
        "history": [],
    }
    state.update(overrides)
    return state


def _make_history_step(
    action="Single", action_rank="3", cur_pos=0, numofplayers=None
) -> dict:
    """构造一条出牌历史记录。"""
    return {
        "curAction": [action, action_rank] if action != "PASS" else ["PASS"],
        "curPos": cur_pos,
        "numofplayers": numofplayers or [27, 27, 27, 27],
    }


# ── 1. 序列长度 0 ──

class TestSeqLenZero:
    def test_empty_history(self):
        """空历史 → 64 维全零 hidden。"""
        gs = _make_game_state(history=[])
        feat = extract_dynamic_features(gs)
        assert feat.shape == (DYNAMIC_HIDDEN_DIM,)
        assert np.allclose(feat, 0.0), "空历史应输出全零 hidden"


# ── 2. 序列长度 1 ──

class TestSeqLenOne:
    def test_single_step(self):
        """单步出牌历史编码。"""
        gs = _make_game_state(
            myPos=0,
            history=[_make_history_step(action="Single", action_rank="3", cur_pos=0)],
        )
        feat = extract_dynamic_features(gs)
        assert feat.shape == (DYNAMIC_HIDDEN_DIM,)
        assert not np.allclose(feat, 0.0), "单步非空历史不应全零"


# ── 3. 序列长度 8 ──

class TestSeqLenEight:
    def test_eight_steps(self):
        """8 步出牌历史编码。"""
        history = [_make_history_step(action="Single", action_rank=str(r % 9 + 2), cur_pos=i % 4)
                   for i, r in enumerate(range(8))]
        gs = _make_game_state(myPos=0, history=history)
        feat = extract_dynamic_features(gs)
        assert feat.shape == (DYNAMIC_HIDDEN_DIM,)
        assert not np.allclose(feat, 0.0)


# ── 4. 序列长度 20（最大） ──

class TestSeqLenTwenty:
    def test_twenty_steps(self):
        """20 步（最大长度）序列编码。"""
        history = [_make_history_step(action="Single", action_rank=str(r % 9 + 2), cur_pos=i % 4)
                   for i, r in enumerate(range(20))]
        gs = _make_game_state(myPos=0, history=history)
        feat = extract_dynamic_features(gs)
        assert feat.shape == (DYNAMIC_HIDDEN_DIM,)
        assert not np.allclose(feat, 0.0)


# ── 5. 超长序列截断 ──

class TestSeqTruncation:
    def test_over_max_truncated(self):
        """超长序列（30 步）截断至 20。"""
        history = [_make_history_step(action="Single", action_rank=str(r % 9 + 2), cur_pos=i % 4)
                   for i, r in enumerate(range(30))]
        gs = _make_game_state(myPos=0, history=history)
        feat = extract_dynamic_features(gs)
        assert feat.shape == (DYNAMIC_HIDDEN_DIM,)
        # 验证只取了最后 20 步（通过 build_history_sequence 确认）
        seq = build_history_sequence(history, 0)
        assert seq.shape[0] == MAX_SEQ_LEN, f"期望 {MAX_SEQ_LEN} 步，实际 {seq.shape[0]}"


# ── 6. 含 PASS 步 ──

class TestPassStep:
    def test_sequence_with_pass(self):
        """包含 PASS 步的序列正确编码。"""
        history = [
            _make_history_step(action="Single", action_rank="5", cur_pos=0),
            _make_history_step(action="PASS", action_rank="", cur_pos=1),
            _make_history_step(action="Single", action_rank="7", cur_pos=2),
        ]
        gs = _make_game_state(myPos=0, history=history)
        feat = extract_dynamic_features(gs)
        assert feat.shape == (DYNAMIC_HIDDEN_DIM,)
        assert not np.allclose(feat, 0.0)

        # 验证 PASS 步的 one-hot：第 0 位应为 1
        seq = build_history_sequence(history, 0)
        assert seq.shape[0] == 3
        assert seq[1][0] == 1.0, "PASS 步 one-hot[0] 应为 1"
        assert seq[1][1] == 0.0, "PASS 步 one-hot[1] 应为 0"


# ── 7. 拼接维度 ──

class TestCombinedDimension:
    def test_combined_188(self):
        """静态 + 动态 = 188 维。"""
        gs = _make_game_state(
            myPos=0,
            handCards=["S2", "H3"],
            history=[_make_history_step(action="Single", action_rank="3", cur_pos=0)],
        )
        static = extract_static_features(gs)
        combined = extract_combined_features(gs, static)
        expected = STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM
        assert combined.shape == (expected,), f"期望 {expected} 维，实际 {combined.shape}"
        assert combined.dtype == np.float32


# ── 8. 拼接值范围 ──

class TestCombinedValueRange:
    def test_static_part_unchanged(self):
        """拼接后前 124 维与原始静态特征一致。"""
        gs = _make_game_state(
            myPos=0,
            handCards=["S2", "H3", "BJ", "D5", "D5"],
            curRank="5",
            curBombNum=2,
            history=[_make_history_step(action="Single", action_rank="3", cur_pos=0)],
        )
        static = extract_static_features(gs)
        combined = extract_combined_features(gs, static)
        assert np.allclose(combined[:STATIC_STATE_DIM], static)

    def test_dynamic_part_nonzero_with_history(self):
        """有历史时动态部分非全零。"""
        gs = _make_game_state(
            myPos=0,
            history=[_make_history_step(action="Single", action_rank="3", cur_pos=0)],
        )
        static = extract_static_features(gs)
        combined = extract_combined_features(gs, static)
        dynamic_part = combined[STATIC_STATE_DIM:]
        assert not np.allclose(dynamic_part, 0.0), "有历史时动态部分不应全零"


# ── 9. Engine 集成测试 ──

torch_available = False
try:
    import torch
    torch_available = True
except ImportError:
    pass


@pytest.mark.skipif(not torch_available, reason="需要 torch")
class TestEngineIntegration:
    def test_engine_output_512_with_dynamic(self):
        """engine._extract_features 输出仍为 512 维。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        engine = UltimateWinRateEngineV7(player_id=0)
        gs = _make_game_state(
            handCards=["S2", "H3"],
            myPos=0,
            history=[_make_history_step(action="Single", action_rank="3", cur_pos=0)],
        )
        feat = engine._extract_features(gs, [["S2"]])
        assert feat is not None
        assert feat.shape == (512,), f"期望 512 维，实际 {feat.shape}"

    def test_engine_dynamic_part_nonzero(self):
        """引擎输出中 124-187 维动态特征非全零（有历史时）。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        engine = UltimateWinRateEngineV7(player_id=0)
        gs = _make_game_state(
            handCards=["S2", "H3"],
            myPos=0,
            history=[_make_history_step(action="Single", action_rank="3", cur_pos=0)],
        )
        feat = engine._extract_features(gs, [["S2"]])
        dynamic_part = feat[STATIC_STATE_DIM:STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM]
        assert not np.allclose(dynamic_part, 0.0), \
            "有历史时引擎输出 124-187 维动态特征不应全零"

    def test_engine_dynamic_zero_without_history(self):
        """无历史时动态特征为全零（回退行为）。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        engine = UltimateWinRateEngineV7(player_id=0)
        gs = _make_game_state(
            handCards=["S2", "H3"],
            myPos=0,
            history=[],
        )
        feat = engine._extract_features(gs, [["S2"]])
        dynamic_part = feat[STATIC_STATE_DIM:STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM]
        assert np.allclose(dynamic_part, 0.0), \
            "无历史时动态特征应为全零"

    def test_engine_static_part_unchanged(self):
        """引擎输出前 124 维与独立提取的静态特征一致。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        engine = UltimateWinRateEngineV7(player_id=0)
        gs = _make_game_state(
            handCards=["S2", "BJ", "H5", "H5"],
            curRank="5",
            curBombNum=2,
            myPos=0,
            history=[_make_history_step(action="Single", action_rank="3", cur_pos=0)],
        )
        feat = engine._extract_features(gs, [["S2"]])
        static = extract_static_features(gs)
        assert np.allclose(feat[:STATIC_STATE_DIM], static), "前 124 维应与静态特征一致"


# ── 10. build_history_sequence 单元测试 ──

class TestBuildHistorySequence:
    def test_empty_history(self):
        """空列表返回 (0, 8) 数组。"""
        seq = build_history_sequence([], 0)
        assert seq.shape == (0, SEQ_STEP_DIM)

    def test_step_dimension(self):
        """每步 8 维特征。"""
        history = [_make_history_step()]
        seq = build_history_sequence(history, 0)
        assert seq.shape == (1, SEQ_STEP_DIM), f"期望 (1, 8)，实际 {seq.shape}"

    def test_action_type_onehot_single(self):
        """Single action → onehot[1]=1。"""
        history = [_make_history_step(action="Single")]
        seq = build_history_sequence(history, 0)
        assert seq[0][0] == 0.0, "Single 不应在 PASS 位"
        assert seq[0][1] == 1.0, "Single 应在 Single 位"

    def test_action_type_onehot_pass(self):
        """PASS action → onehot[0]=1。"""
        history = [_make_history_step(action="PASS")]
        seq = build_history_sequence(history, 0)
        assert seq[0][0] == 1.0, "PASS 位应为 1"


# ── 11. lstm_encode 单元测试 ──

class TestLSTMEncode:
    def test_empty_seq(self):
        """空序列返回全零 hidden。"""
        hidden = lstm_encode(np.zeros((0, SEQ_STEP_DIM), dtype=np.float32))
        assert hidden.shape == (DYNAMIC_HIDDEN_DIM,)
        assert np.allclose(hidden, 0.0)

    def test_single_step(self):
        """单步序列返回非零 hidden。"""
        seq = np.random.randn(1, SEQ_STEP_DIM).astype(np.float32) * 0.1
        hidden = lstm_encode(seq)
        assert hidden.shape == (DYNAMIC_HIDDEN_DIM,)
        assert not np.allclose(hidden, 0.0)

    def test_deterministic(self):
        """相同输入 → 相同输出（确定性）。"""
        seq = np.random.randn(3, SEQ_STEP_DIM).astype(np.float32) * 0.1
        h1 = lstm_encode(seq)
        h2 = lstm_encode(seq)
        assert np.allclose(h1, h2), "LSTM 应输出确定性结果"
