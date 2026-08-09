# -*- coding: utf-8 -*-
"""
GUA-223 / CardCountingNetwork-训练方案 §8 Phase 0 ⑤
stage_onehot + tribute_transfer_events 编码器 pytest

覆盖：
  ① stage_to_onehot 标准 7 类
  ② stage 未知 → 全 0 向量（不抛异常）
  ③ tribute_events_to_vec 定长 padding（不足 5 事件补零、超 5 截断）
  ④ 单事件字段缺漏 → 部分 onehot
  ⑤ build_input_features 总长 342 维
  ⑥ infer_stage_from_global 推断（tribute/anti-tribute/back/play/beginning）
  ⑦ Botzone log sample 真实场景跑通（端到端）
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.v.nn.features.stage_encoding import (
    STAGE_DIM,
    STAGE_NAMES,
    TRIBUTE_EVENT_VEC_DIM,
    TRIBUTE_MAX_EVENTS,
    TRIBUTE_VEC_DIM,
    build_input_features,
    infer_stage_from_global,
    stage_to_onehot,
    stages_to_onehots,
    tribute_event_to_vec,
    tribute_events_to_vec,
)


class TestStageOneHot:
    def test_7_stages_onehot(self):
        for s in STAGE_NAMES:
            vec = stage_to_onehot(s)
            assert vec.shape == (7,)
            assert vec.sum() == 1.0
            assert vec[STAGE_NAMES.index(s)] == 1.0

    def test_unknown_stage_zero(self):
        vec = stage_to_onehot("unknown_stage")
        assert vec.shape == (7,)
        assert vec.sum() == 0.0  # 全 0

    def test_stages_to_onehots_matrix(self):
        stages = ["play", "tribute", "back"]
        mat = stages_to_onehots(stages)
        assert mat.shape == (3, 7)
        assert mat[0, STAGE_NAMES.index("play")] == 1.0


class TestTributeEvents:
    def test_empty_event_zero_vec(self):
        from src.v.nn.features.stage_encoding import _empty_event
        v = _empty_event()
        assert v.shape == (TRIBUTE_EVENT_VEC_DIM,)
        assert v.sum() == 0.0

    def test_single_event(self):
        ev = {"type": "tribute", "from_seat": 0, "to_seat": 2, "card": "D2"}
        vec = tribute_event_to_vec(ev)
        assert vec.shape == (TRIBUTE_EVENT_VEC_DIM,)
        assert vec[0] == 1.0  # type tribute
        assert vec[5 + 0] == 1.0  # from seat 0
        assert vec[9 + 2] == 1.0  # to seat 2
        # D2 = value 1 (A=0) × 4 + suit 1 (D) = 5; slot 5
        assert vec[13 + 5] == 1.0

    def test_padding_short(self):
        events = [{"type": "tribute", "from_seat": 1, "to_seat": 3, "card": "H2"}]
        vec = tribute_events_to_vec(events)
        assert vec.shape == (TRIBUTE_VEC_DIM,)
        # 第 1 段（事件 0）应有一处非零；其余 4 段应全 0
        seg0 = vec[:TRIBUTE_EVENT_VEC_DIM]
        seg_rest = vec[TRIBUTE_EVENT_VEC_DIM:]
        assert seg0.sum() > 0
        assert seg_rest.sum() == 0.0

    def test_truncate_long(self):
        events = [{"type": "tribute", "from_seat": 0, "to_seat": 1, "card": "D2"}] * 10
        vec = tribute_events_to_vec(events)
        # 超过 TRIBUTE_MAX_EVENTS=5 的部分应被截断
        assert vec.shape == (TRIBUTE_VEC_DIM,)
        # 5 段全非零
        for i in range(TRIBUTE_MAX_EVENTS):
            seg = vec[i * TRIBUTE_EVENT_VEC_DIM: (i + 1) * TRIBUTE_EVENT_VEC_DIM]
            assert seg.sum() > 0

    def test_missing_fields(self):
        ev = {"type": "back"}  # 缺 from_seat/to_seat/card
        vec = tribute_event_to_vec(ev)
        assert vec.shape == (TRIBUTE_EVENT_VEC_DIM,)
        # type=back 应在位置 1 = 1
        assert vec[1] == 1.0
        # from_seat/to_seat/card 应全 0
        assert vec[5:9].sum() == 0
        assert vec[9:13].sum() == 0
        assert vec[13:].sum() == 0


class TestBuildFeatures:
    def test_total_dim_342(self):
        feats = build_input_features(stage="play", global_state=None, tribute_events=None)
        assert feats.shape == (STAGE_DIM + TRIBUTE_VEC_DIM,)  # 7 + 335 = 342
        assert feats.dtype == np.float32

    def test_with_real_events(self):
        events = [
            {"type": "tribute", "from_seat": 1, "to_seat": 3, "card": "H2"},
            {"type": "back", "from_seat": 3, "to_seat": 1, "card": "S2"},
        ]
        feats = build_input_features(stage="back", global_state=None, tribute_events=events)
        assert feats.shape == (342,)
        # stage=back → vec[3] = 1
        assert feats[3] == 1.0


class TestInferStage:
    def test_default_beginning(self):
        assert infer_stage_from_global({}) == "beginning"
        assert infer_stage_from_global(None) == "beginning"

    def test_tribute(self):
        gs = {"tribute": 1, "resist": False, "return_cards": {}}
        assert infer_stage_from_global(gs) == "tribute"

    def test_anti_tribute(self):
        gs = {"tribute": 1, "resist": True, "return_cards": {}}
        assert infer_stage_from_global(gs) == "anti-tribute"

    def test_back(self):
        gs = {"tribute": 0, "resist": False, "return_cards": {"foo": "bar"}}
        assert infer_stage_from_global(gs) == "back"

    def test_play(self):
        gs = {"tribute": 0, "resist": False, "return_cards": {}, "first": 0}
        assert infer_stage_from_global(gs) == "play"


class TestEtlIntegration:
    """从 ETL 输出的真实样本构造 stage 输入（端到端）"""

    def test_real_sample_stage_infer(self):
        from pathlib import Path
        from scripts.etl.botzone_to_counting_dataset import iter_clean_samples

        DATA_DIR = Path("data/training/card_counting_v1")
        if not DATA_DIR.exists():
            pytest.skip("无样本")
        samples = iter_clean_samples(DATA_DIR, drop_warnings=True)
        if not samples:
            pytest.skip("无干净样本")
        s = samples[0]
        feats = build_input_features(
            stage=s["stage"],
            global_state=s["global_state"],
            tribute_events=None,
        )
        assert feats.shape == (342,)
        # stage 应该是 'play'（V8 在线对局 99% 是 play 阶段）
        assert s["stage"] == "play"
        assert feats[STAGE_NAMES.index("play")] == 1.0