# -*- coding: utf-8 -*-
"""GUA-072 M5：_rule_memory_vec 接入 BC 训练与推理特征对齐。"""

import numpy as np

from src.v.nn.features.rule_card_counter import RULE_MEMORY_DIM
from src.v.nn.training.bc_dataset import (
    EFFECTIVE_FEATURE_DIM,
    RULE_MEMORY_DIM as BC_RULE_MEMORY_DIM,
    TARGET_FEATURE_DIM,
    _build_rule_memory_features,
    _reconstruct_features_from_full_state,
    rule_memory_feature_start,
)


def _sample_full_state():
    return {
        "handCards": ["S3", "S4", "S5", "H3", "H5", "C2", "D2"],
        "actionList": [["Single", "3", ["S3"]], ["PASS"]],
        "actionList_size": 2,
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 1,
        "curRank": "2",
        "stage": "play",
        "history": [
            {
                "pos": 1,
                "action": ["Single", "2", ["H2"]],
                "context": {"greaterPos": -1},
            },
            {
                "pos": 0,
                "action": ["PASS"],
                "context": {
                    "greaterAction": ["Single", "2", ["H2"]],
                    "greaterPos": 1,
                },
            },
        ],
    }


class TestRuleMemoryTrainingPipeline:
    def test_effective_feature_dim_includes_rule_memory(self):
        assert BC_RULE_MEMORY_DIM == RULE_MEMORY_DIM == 12
        assert EFFECTIVE_FEATURE_DIM == 124 + 64 + 8 + 33 + 12

    def test_rule_memory_start_offset(self):
        assert rule_memory_feature_start(False) == 229
        assert rule_memory_feature_start(True) == 244

    def test_build_rule_memory_features_non_zero_with_hand(self):
        vec = _build_rule_memory_features(_sample_full_state())
        assert len(vec) == RULE_MEMORY_DIM
        assert any(x != 0.0 for x in vec)

    def test_reconstruct_features_writes_rule_memory_slice(self):
        fs = _sample_full_state()
        features = _reconstruct_features_from_full_state(fs)
        assert features is not None
        assert features.shape == (TARGET_FEATURE_DIM,)
        rm_start = rule_memory_feature_start(False)
        rm_slice = features[rm_start:rm_start + RULE_MEMORY_DIM]
        built = np.array(_build_rule_memory_features(fs), dtype=np.float32)
        np.testing.assert_allclose(rm_slice, built, rtol=1e-5)
        assert np.all(features[EFFECTIVE_FEATURE_DIM:] == 0)
