# -*- coding: utf-8 -*-
"""GUA-039a DMC Learner：replay_buffer + fd_native Actor 训练循环。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal, Optional, Union

import numpy as np

from .actor import SampleRoute, collect_episodes
from .dmc_mlp import DmcMlp
from .replay_buffer import ReplayBuffer


@dataclass
class LearnerConfig:
    buffer_capacity: int = 60_000
    batch_size: int = 512
    train_steps_per_cycle: int = 2
    min_buffer_for_train: int = 2048
    lr: float = 3e-4
    hidden: int = 256
    eps: float = 0.10
    seed: int = 0
    sample_route: SampleRoute = "fd_native"


@dataclass
class CycleStats:
    cycle: int
    episodes: int
    samples_added: int
    buffer_size: int
    loss: float
    collect_sec: float
    train_sec: float
    sample_route: str = "fd_native"
    v8_samples: int = 0


@dataclass
class TrainRunStats:
    cycles: int = 0
    total_samples: int = 0
    total_episodes: int = 0
    history: List[CycleStats] = field(default_factory=list)


class DMCLearner:
    """Danzero 风格 DMC：MC 回报 z 回归 Q(s,a)。"""

    def __init__(self, config: Optional[LearnerConfig] = None):
        self.config = config or LearnerConfig()
        self.model = DmcMlp(
            hidden=self.config.hidden,
            seed=self.config.seed,
            lr=self.config.lr,
        )
        self.buffer = ReplayBuffer(
            capacity=self.config.buffer_capacity,
            feature_dim=self.model.feature_dim,
        )
        self.rng = np.random.default_rng(self.config.seed)
        self.stats = TrainRunStats()
        self.last_v8_samples: List = []

    def ingest_episodes(self, n_episodes: int, seed: Optional[int] = None) -> int:
        batches = collect_episodes(
            n_episodes,
            self.model,
            route=self.config.sample_route,
            eps=self.config.eps,
            seed=seed if seed is not None else int(self.rng.integers(0, 2**31)),
        )
        added = 0
        v8_count = 0
        self.last_v8_samples = []
        for ep in batches:
            for feat, z in ep.labeled_samples():
                self.buffer.add(feat, z)
                added += 1
            if ep.v8_samples:
                v8_count += len(ep.v8_samples)
                self.last_v8_samples.extend(ep.v8_samples)
        self.stats.total_episodes += n_episodes
        self.stats.total_samples += added
        self._last_v8_count = v8_count
        return added

    def export_v8_samples(
        self,
        path: Union[str, Path],
        *,
        append: bool = False,
    ) -> int:
        """导出 `last_v8_samples` 为 JSONL（Botzone actionList 对照）。"""
        from pathlib import Path as _Path

        from .fabledan_v8_bridge import export_v8_samples as _export

        return _export(self.last_v8_samples, _Path(path), append=append)

    def train_step(self) -> float:
        x, z = self.buffer.sample(self.config.batch_size, self.rng)
        return self.model.train_batch(x, z)

    def train_steps(self, n_steps: int) -> float:
        if self.buffer.size < self.config.min_buffer_for_train:
            return float("nan")
        losses = [self.train_step() for _ in range(n_steps)]
        return float(np.mean(losses))

    def run_cycle(
        self,
        cycle: int,
        episodes_per_cycle: int,
        seed: Optional[int] = None,
    ) -> CycleStats:
        t0 = time.perf_counter()
        added = self.ingest_episodes(episodes_per_cycle, seed=seed)
        collect_sec = time.perf_counter() - t0

        t1 = time.perf_counter()
        loss = self.train_steps(self.config.train_steps_per_cycle)
        train_sec = time.perf_counter() - t1

        stat = CycleStats(
            cycle=cycle,
            episodes=episodes_per_cycle,
            samples_added=added,
            buffer_size=self.buffer.size,
            loss=loss,
            collect_sec=collect_sec,
            train_sec=train_sec,
            sample_route=self.config.sample_route,
            v8_samples=getattr(self, "_last_v8_count", 0),
        )
        self.stats.cycles += 1
        self.stats.history.append(stat)
        return stat

    def save(self, path: str | Path) -> None:
        self.model.save(path)

    @classmethod
    def load(cls, path: str | Path, config: Optional[LearnerConfig] = None) -> "DMCLearner":
        learner = cls(config)
        learner.model = DmcMlp.load(path, hidden=learner.config.hidden, lr=learner.config.lr)
        return learner
