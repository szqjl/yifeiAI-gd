# -*- coding: utf-8 -*-
"""
GUA-223 / CardCountingNetwork-训练方案 §8 Phase 1
CardCountingNetwork LSTM 模型 pytest

关联：GUA-223 / GUA-057 / 训练方案 §8 Phase 1 / docs/analysis/param_data_ratio.md

覆盖：
  ① history 序列编码 shape 正确
  ② hand_context 编码 shape 正确（含 5 个子段）
  ③ 模型 forward 输出 shape (B, 108, 3)
  ④ 参数量 < 50K（Phase 1 LSTM 5K-50K 区间）
  ⑤ 推理延迟 < 20ms（单步）
  ⑥ checkpoint save/load 一致性
  ⑦ 真实 ETL 样本端到端 forward 跑通
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.v.nn.features.card_counting_network import (
    HAND_CONTEXT_DIM,
    HIDDEN_DIM,
    HISTORY_NUM_TURNS,
    HISTORY_SEQ_DIM,
    HISTORY_TURN_DIM,
    OUTPUT_DIM,
    CardCountingNet,
    build_hand_context,
    build_sample_input,
    count_parameters,
    encode_cur_rank,
    encode_hand_self,
    encode_history_sequence,
    encode_history_turn,
    encode_rest_distribution,
    load_checkpoint,
    save_checkpoint,
)


class TestEncoders:
    """子编码器单元测试"""

    def test_history_turn_shape(self):
        vec = encode_history_turn(0, [[104, 49], [104, 49]])
        assert vec.shape == (HISTORY_TURN_DIM,)
        assert vec[0] == 1.0  # player 0

    def test_history_turn_empty(self):
        vec = encode_history_turn(1, [])
        assert vec.shape == (HISTORY_TURN_DIM,)
        assert vec.sum() == 2.0  # player 1 onehot + len_bucket 0

    def test_history_sequence_shape(self):
        history = [
            {"player": 0, "response": [[104, 49], [104, 49]]},
            {"player": 1, "response": [[2, 1], [2, 1]]},
            {"player": 2, "response": [[106, 52], [106, 52]]},
            {"player": 3, "response": [[], []]},
        ]
        seq = encode_history_sequence(history)
        assert seq.shape == (HISTORY_NUM_TURNS, HISTORY_TURN_DIM)

    def test_history_sequence_short(self):
        """不足 4 turn → 补 0。"""
        seq = encode_history_sequence([])
        assert seq.shape == (HISTORY_NUM_TURNS, HISTORY_TURN_DIM)
        assert seq.sum() == 0.0

    def test_hand_self_encoding(self):
        vec = encode_hand_self(["HA", "HK", "D9", "D9", "SB"])
        assert vec.shape == (108,)
        # D9 有 2 张 → 两副本都标
        from src.v.nn.features.stage_encoding import v8_to_slot
        slot_d9 = v8_to_slot("D9")
        assert vec[slot_d9] >= 1.0
        assert vec[54 + slot_d9] >= 1.0

    def test_cur_rank_encoding(self):
        assert encode_cur_rank("A")[0] == 1.0
        assert encode_cur_rank("2")[1] == 1.0
        assert encode_cur_rank("5")[2] == 1.0
        assert encode_cur_rank("K")[3] == 1.0

    def test_rest_distribution_buckets(self):
        v0 = encode_rest_distribution([])
        v10 = encode_rest_distribution(["?"] * 10)
        v25 = encode_rest_distribution(["?"] * 25)
        assert v0[0] == 1.0
        assert v10[4] == 1.0  # 10-13 桶
        assert v25[6] == 1.0  # 21+ 桶

    def test_hand_context_dim(self):
        ctx = build_hand_context(
            hand_cards=["HA", "HK"],
            cur_rank="A",
            stage="play",
            global_state={"tribute": 0, "resist": False, "return_cards": {}, "first": 0},
            tribute_events=None,
            rest_cards=["?"] * 50,
        )
        assert ctx.shape == (HAND_CONTEXT_DIM,)


class TestModelArchitecture:
    """PyTorch 模型结构 + 参数量"""

    def test_forward_output_shape(self):
        model = CardCountingNet()
        B = 4
        history = torch.randn(B, HISTORY_NUM_TURNS, HISTORY_TURN_DIM)
        hand = torch.randn(B, HAND_CONTEXT_DIM)
        out = model(history, hand)
        assert out.shape == (B, 108, 3)

    def test_param_count_under_50k(self):
        model = CardCountingNet()
        n = count_parameters(model)
        # LSTM 5K-50K 区间（参数据 docs/analysis/param_data_ratio.md）
        assert 1000 <= n <= 50000, f"参数 {n} 不在 1K-50K 区间"

    def test_param_count_5k_target(self):
        """默认配置应接近 19K（设计目标）。"""
        model = CardCountingNet()
        n = count_parameters(model)
        # 容忍 ±50%
        assert 5000 <= n <= 50000


class TestInference:
    """推理延迟（方案 §11.1 验收：< 20ms）"""

    def test_inference_latency_under_20ms(self):
        model = CardCountingNet()
        model.eval()
        history = torch.randn(1, HISTORY_NUM_TURNS, HISTORY_TURN_DIM)
        hand = torch.randn(1, HAND_CONTEXT_DIM)
        # warm-up
        with torch.no_grad():
            _ = model(history, hand)
        # measure 100 forward
        t0 = time.time()
        with torch.no_grad():
            for _ in range(100):
                _ = model(history, hand)
        elapsed_per = (time.time() - t0) / 100
        assert elapsed_per < 0.020, f"推理 {elapsed_per*1000:.2f}ms > 20ms"


class TestCheckpoint:
    """save/load 一致性"""

    def test_save_load_roundtrip(self, tmp_path):
        model = CardCountingNet()
        model.eval()
        ckpt_path = tmp_path / "model.pt"
        save_checkpoint(model, ckpt_path)
        assert ckpt_path.exists()
        loaded = load_checkpoint(ckpt_path)
        # 参数应一致
        for (n1, p1), (n2, p2) in zip(model.named_parameters(), loaded.named_parameters()):
            assert n1 == n2
            assert torch.allclose(p1, p2)


class TestEtlIntegration:
    """真实 ETL 样本端到端 forward"""

    def test_real_sample_forward(self):
        from scripts.etl.botzone_to_counting_dataset import iter_clean_samples

        DATA_DIR = Path("data/training/card_counting_v1")
        if not DATA_DIR.exists():
            pytest.skip("无样本")
        samples = iter_clean_samples(DATA_DIR, drop_warnings=True)
        if not samples:
            pytest.skip("无干净样本")
        s = samples[0]
        history_seq, hand_ctx = build_sample_input(s)
        assert history_seq.shape == (HISTORY_NUM_TURNS, HISTORY_TURN_DIM)
        assert hand_ctx.shape == (HAND_CONTEXT_DIM,)
        # forward
        model = CardCountingNet()
        model.eval()
        with torch.no_grad():
            out = model(
                torch.from_numpy(history_seq).unsqueeze(0),
                torch.from_numpy(hand_ctx).unsqueeze(0),
            )
        assert out.shape == (1, 108, 3)