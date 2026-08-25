# -*- coding: utf-8 -*-
"""FableDan ↔ V8 桥接层单测。"""

import random
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_FABLE = _REPO / "external" / "FableDan"
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_FABLE))

from fabledan.agents import RandomAgent  # noqa: E402
from fabledan.engine import play_round  # noqa: E402

from src.v.nn.training.fabledan_v8_bridge import (  # noqa: E402
    build_v8_sample,
    generate_v8_action_list,
    obs_to_v8_context,
    v8_action_to_fd_index,
)


class _ObsCollector:
    def __init__(self, buf):
        self.inner = RandomAgent(0)
        self.buf = buf

    def act(self, obs):
        if len(obs["legal"]) >= 2:
            self.buf.append(obs)
        return self.inner.act(obs)


def _collect_obs(n_episodes: int = 3) -> list:
    out = []
    rng = random.Random(99)
    for _ in range(n_episodes):
        buf = []
        agents = [_ObsCollector(buf) for _ in range(4)]
        play_round(agents, rng=random.Random(rng.getrandbits(48)))
        out.extend(buf)
    return out


def test_obs_to_v8_context_hand_size():
    obs_list = _collect_obs(2)
    assert obs_list
    for obs in obs_list[:5]:
        ctx = obs_to_v8_context(obs)
        assert len(ctx.hand_v8) == len(obs["hand"])
        assert ctx.cur_rank in ("A", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K")


def test_v8_action_list_non_empty():
    obs_list = _collect_obs(2)
    for obs in obs_list[:10]:
        ctx = obs_to_v8_context(obs)
        actions = generate_v8_action_list(ctx)
        assert actions
        assert actions[0][0] in (
            "PASS", "Single", "Pair", "Trips", "ThreeWithTwo", "Straight",
            "ThreePair", "TwoTrips", "Bomb", "StraightFlush",
        )


def test_v8_to_fd_roundtrip_rate():
    """随机 V8 候选应大多能映射回 FableDan legal。"""
    obs_list = _collect_obs(5)
    ok, fail = 0, 0
    for obs in obs_list:
        ctx = obs_to_v8_context(obs)
        actions = generate_v8_action_list(ctx)
        for a in actions[: min(20, len(actions))]:
            idx = v8_action_to_fd_index(obs["legal"], a)
            if idx is not None:
                ok += 1
            else:
                fail += 1
    assert ok > 0
    assert ok / max(ok + fail, 1) >= 0.5


def test_build_v8_sample_fields():
    obs_list = _collect_obs(1)
    obs = obs_list[0]
    ctx = obs_to_v8_context(obs)
    actions = generate_v8_action_list(ctx)
    s = build_v8_sample(obs, 0, actions)
    assert s.cur_rank == ctx.cur_rank
    assert s.chosen_action == actions[0]
    assert s.n_v8_legal == len(actions)


def test_export_v8_samples_jsonl(tmp_path):
    from src.v.nn.training.fabledan_v8_bridge import export_v8_samples, v8_sample_to_export_record
    from src.v.nn.training.learner import DMCLearner, LearnerConfig

    learner = DMCLearner(LearnerConfig(sample_route="fd_v8_bridge", hidden=32, batch_size=8))
    learner.run_cycle(1, episodes_per_cycle=1, seed=7)
    assert learner.last_v8_samples
    out = tmp_path / "v8.jsonl"
    n = learner.export_v8_samples(out)
    assert n == len(learner.last_v8_samples)
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == n
    import json
    row = json.loads(lines[0])
    assert row["action_list"]
    assert row["chosen_action"]
    assert "hand_v8" in row
    rec = v8_sample_to_export_record(learner.last_v8_samples[0])
    assert rec["chosen_v8_index"] == row["chosen_v8_index"]
