# -*- coding: utf-8 -*-
"""GUA-039a Actor：FableDan 自对弈采样（fd_native / fd_v8_bridge）。"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

import numpy as np

from .dmc_mlp import DmcMlp
from .fabledan_v8_bridge import (
    V8TrainingSample,
    build_v8_sample,
    generate_v8_action_list,
    list_mappable_v8_actions,
    obs_to_v8_context,
)
from .fd_env import ensure_fabledan_importable

ensure_fabledan_importable()
from fabledan.encode import encode_flat  # noqa: E402
from fabledan.engine import play_round  # noqa: E402

SampleRoute = Literal["fd_native", "fd_v8_bridge", "mixed"]


@dataclass
class InferenceStats:
    """V8 actionList 推理统计（评估用）。"""

    decisions: int = 0
    v8_mapped: int = 0
    v8_fallback: int = 0

    @property
    def map_rate(self) -> float:
        if self.decisions == 0:
            return 0.0
        return self.v8_mapped / self.decisions


class FdNativeInferenceAgent:
    """fd_native 合法着 + DMC argmax（无探索、无 buffer）。"""

    def __init__(self, model: DmcMlp):
        self.model = model

    def act(self, obs) -> int:
        legal = obs["legal"]
        if len(legal) == 1:
            return 0
        feats = np.stack([encode_flat(obs, m) for m in legal])
        q = self.model.predict(feats)
        return int(np.argmax(q))


class V8BridgeInferenceAgent:
    """V8 ActionListGenerator 枚举 + 可映射着法 DMC argmax。"""

    def __init__(
        self,
        model: DmcMlp,
        stats: Optional[InferenceStats] = None,
    ):
        self.model = model
        self.stats = stats

    def act(self, obs) -> int:
        legal = obs["legal"]
        n = len(legal)
        if n == 1:
            return 0
        if self.stats is not None:
            self.stats.decisions += 1

        ctx = obs_to_v8_context(obs)
        action_list = generate_v8_action_list(ctx)
        mappable = list_mappable_v8_actions(obs, action_list)
        if mappable:
            if self.stats is not None:
                self.stats.v8_mapped += 1
            feats = np.stack([row[2] for row in mappable])
            q = self.model.predict(feats)
            pick = int(np.argmax(q))
            return mappable[pick][1]

        if self.stats is not None:
            self.stats.v8_fallback += 1
        feats = np.stack([encode_flat(obs, m) for m in legal])
        q = self.model.predict(feats)
        return int(np.argmax(q))


def make_inference_agent(
    model: DmcMlp,
    route: SampleRoute,
    stats: Optional[InferenceStats] = None,
):
    if route == "fd_v8_bridge":
        return V8BridgeInferenceAgent(model, stats=stats)
    if route == "fd_native":
        return FdNativeInferenceAgent(model)
    raise ValueError(f"unsupported inference route: {route}")


@dataclass
class EpisodeBatch:
    """单副牌采样；z 在副末回填。"""

    features: List[np.ndarray]
    players: List[int]
    rewards: List[int]
    ranking: List[int]
    route: str = "fd_native"
    v8_samples: List[V8TrainingSample] = field(default_factory=list)

    def labeled_samples(self) -> List[Tuple[np.ndarray, float]]:
        out: List[Tuple[np.ndarray, float]] = []
        for feat, player in zip(self.features, self.players):
            z = self.rewards[player] / 3.0
            out.append((feat, z))
        return out


class _FdNativeAgent:
    def __init__(
        self,
        model: Optional[DmcMlp],
        eps: float,
        rng: random.Random,
        buf: list,
    ):
        self.model = model
        self.eps = eps
        self.rng = rng
        self.buf = buf

    def act(self, obs) -> int:
        legal = obs["legal"]
        n = len(legal)
        if n == 1:
            return 0
        feats = [encode_flat(obs, m) for m in legal]
        if self.model is not None and not (self.eps > 0 and self.rng.random() < self.eps):
            q = self.model.predict(np.stack(feats))
            idx = int(np.argmax(q))
        else:
            idx = self.rng.randrange(n)
        if n >= 2:
            self.buf.append((np.asarray(feats[idx], dtype=np.float32), obs["player"]))
        return idx


class _V8BridgeAgent:
    def __init__(
        self,
        model: Optional[DmcMlp],
        eps: float,
        rng: random.Random,
        buf: list,
    ):
        self.model = model
        self.eps = eps
        self.rng = rng
        self.buf = buf

    def act(self, obs) -> int:
        legal = obs["legal"]
        n = len(legal)
        if n == 1:
            return 0
        ctx = obs_to_v8_context(obs)
        action_list = generate_v8_action_list(ctx)
        mappable = list_mappable_v8_actions(obs, action_list)
        if not mappable:
            idx = self.rng.randrange(n)
            if n >= 2:
                feat = np.asarray(encode_flat(obs, legal[idx]), dtype=np.float32)
                self.buf.append((feat, obs["player"], None))
            return idx

        if self.model is not None and not (self.eps > 0 and self.rng.random() < self.eps):
            feats = np.stack([row[2] for row in mappable])
            q = self.model.predict(feats)
            pick = int(np.argmax(q))
        else:
            pick = self.rng.randrange(len(mappable))
        v8_idx, fd_idx, feat = mappable[pick]
        sample = build_v8_sample(obs, v8_idx, action_list)
        sample.feature = feat
        if n >= 2:
            self.buf.append((feat, obs["player"], sample))
        return fd_idx


def _run_episode(
    model: Optional[DmcMlp],
    *,
    route: SampleRoute,
    eps: float,
    seed: Optional[int],
) -> EpisodeBatch:
    rng = random.Random(seed)
    buf: list = []
    if route == "fd_v8_bridge":
        agent_cls = _V8BridgeAgent
        route_name = "fd_v8_bridge"
    else:
        agent_cls = _FdNativeAgent
        route_name = "fd_native"
    agents = [agent_cls(model, eps, rng, buf) for _ in range(4)]
    rewards, ranking, _ = play_round(
        agents,
        rng=random.Random(rng.getrandbits(48)),
    )
    features, players, v8_samples = [], [], []
    for item in buf:
        feat, player = item[0], item[1]
        features.append(np.asarray(feat, dtype=np.float32))
        players.append(player)
        if len(item) > 2 and item[2] is not None:
            sample: V8TrainingSample = item[2]
            sample.z_mc = rewards[player] / 3.0
            v8_samples.append(sample)
    return EpisodeBatch(
        features=features,
        players=players,
        rewards=list(rewards),
        ranking=list(ranking),
        route=route_name,
        v8_samples=v8_samples,
    )


def collect_episode(
    model: Optional[DmcMlp] = None,
    *,
    route: SampleRoute = "fd_native",
    eps: float = 0.10,
    seed: Optional[int] = None,
) -> EpisodeBatch:
    return _run_episode(model, route=route, eps=eps, seed=seed)


def collect_episodes(
    n_episodes: int,
    model: Optional[DmcMlp] = None,
    *,
    route: SampleRoute = "fd_native",
    eps: float = 0.10,
    seed: int = 0,
) -> List[EpisodeBatch]:
    rng = random.Random(seed)
    batches: List[EpisodeBatch] = []
    for _ in range(n_episodes):
        ep_route: SampleRoute = route
        if route == "mixed":
            ep_route = "fd_v8_bridge" if rng.random() < 0.5 else "fd_native"
        batches.append(
            _run_episode(
                model,
                route=ep_route,
                eps=eps,
                seed=rng.getrandbits(48),
            )
        )
    return batches
