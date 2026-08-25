# -*- coding: utf-8 -*-
"""GUA-039a fd_native DMC 基础设施单测。"""

import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from src.v.nn.training.actor import collect_episode
from src.v.nn.training.dmc_mlp import DmcMlp
from src.v.nn.training.learner import DMCLearner, LearnerConfig
from src.v.nn.training.replay_buffer import ReplayBuffer


def test_replay_buffer_ring():
    buf = ReplayBuffer(capacity=4, feature_dim=3)
    for i in range(6):
        buf.add(np.array([i, i + 1, i + 2], dtype=np.float32), float(i))
    assert buf.size == 4
    x, z = buf.sample(2, np.random.default_rng(0))
    assert x.shape == (2, 3)
    assert z.shape == (2,)


def test_dmc_mlp_train_reduces_loss():
    model = DmcMlp(hidden=32, seed=1, lr=1e-2)
    rng = np.random.default_rng(0)
    x = rng.standard_normal((64, model.feature_dim)).astype(np.float32)
    z = rng.standard_normal(64).astype(np.float32)
    l0 = model.train_batch(x, z)
    l1 = model.train_batch(x, z)
    assert l1 <= l0


def test_collect_episode_labels():
    ep = collect_episode(model=None, eps=1.0, seed=42)
    assert ep.features
    samples = ep.labeled_samples()
    zs = {round(z, 3) for _, z in samples}
    assert zs <= {-1.0, -0.667, -0.333, 0.333, 0.667, 1.0}
    for feat, _ in samples:
        assert feat.shape[0] == ep.features[0].shape[0]


def test_learner_one_cycle():
    cfg = LearnerConfig(
        buffer_capacity=10_000,
        batch_size=64,
        train_steps_per_cycle=2,
        min_buffer_for_train=32,
        hidden=32,
        eps=0.5,
        seed=99,
    )
    learner = DMCLearner(cfg)
    stat = learner.run_cycle(1, episodes_per_cycle=3, seed=123)
    assert stat.samples_added > 0
    assert stat.buffer_size == stat.samples_added
    assert not np.isnan(stat.loss)


def test_learner_v8_bridge_cycle():
    cfg = LearnerConfig(
        buffer_capacity=10_000,
        batch_size=64,
        train_steps_per_cycle=2,
        min_buffer_for_train=32,
        hidden=32,
        eps=0.5,
        seed=99,
        sample_route="fd_v8_bridge",
    )
    learner = DMCLearner(cfg)
    stat = learner.run_cycle(1, episodes_per_cycle=2, seed=123)
    assert stat.samples_added > 0
    assert stat.v8_samples == stat.samples_added
    assert learner.last_v8_samples
    assert learner.last_v8_samples[0].feature is not None
    assert not np.isnan(stat.loss)


def test_learner_save_load(tmp_path):
    learner = DMCLearner(LearnerConfig(hidden=32, min_buffer_for_train=8, batch_size=8))
    learner.run_cycle(1, episodes_per_cycle=2, seed=1)
    path = tmp_path / "dmc.npz"
    learner.save(path)
    loaded = DMCLearner.load(path, LearnerConfig(hidden=32))
    x = np.zeros((1, loaded.model.feature_dim), dtype=np.float32)
    q1 = learner.model.predict(x)
    q2 = loaded.model.predict(x)
    np.testing.assert_allclose(q1, q2)


def test_v8_bridge_inference_agent():
    import random

    from fabledan.engine import play_round

    from src.v.nn.training.actor import (
        FdNativeInferenceAgent,
        InferenceStats,
        V8BridgeInferenceAgent,
    )

    model = DmcMlp(hidden=32, seed=0)
    rng = random.Random(7)
    stats = InferenceStats()
    agents = [
        V8BridgeInferenceAgent(model, stats=stats),
        FdNativeInferenceAgent(model),
        V8BridgeInferenceAgent(model, stats=stats),
        FdNativeInferenceAgent(model),
    ]
    play_round(agents, rng=random.Random(rng.getrandbits(48)))
    assert stats.decisions > 0
    assert stats.map_rate > 0.5


def test_resolve_eval_infer_routes_defaults():
    from src.v.nn.training.dmc_eval import resolve_eval_infer_routes

    assert resolve_eval_infer_routes(None, "fd_native") == ("fd_native",)
    assert resolve_eval_infer_routes(None, "fd_v8_bridge") == (
        "fd_native",
        "fd_v8_bridge",
    )
    assert resolve_eval_infer_routes("both", "fd_native") == (
        "fd_native",
        "fd_v8_bridge",
    )
    assert resolve_eval_infer_routes("fd_v8_bridge", "fd_native") == ("fd_v8_bridge",)


def test_eval_vs_rule_dual_routes():
    from src.v.nn.training.dmc_eval import eval_vs_rule

    model = DmcMlp(hidden=32, seed=0)
    result = eval_vs_rule(
        model,
        games=4,
        seed=1,
        infer_routes=("fd_native", "fd_v8_bridge"),
    )
    assert set(result.win_rates) == {"fd_native", "fd_v8_bridge"}
    assert 0.0 <= result.primary_wr <= 1.0
    assert result.v8_stats is not None
