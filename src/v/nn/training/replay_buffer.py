# -*- coding: utf-8 -*-
"""GUA-039a FIFO 经验回放（DMC 蒙特卡洛目标）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ReplayBuffer:
    """环形缓冲：存储 (feature, z_mc) 对。"""

    capacity: int
    feature_dim: int

    def __post_init__(self) -> None:
        self._x = np.zeros((self.capacity, self.feature_dim), dtype=np.float32)
        self._z = np.zeros(self.capacity, dtype=np.float32)
        self._n = 0
        self._ptr = 0

    @property
    def size(self) -> int:
        return self._n

    @property
    def full(self) -> bool:
        return self._n >= self.capacity

    def add(self, feature: np.ndarray, target: float) -> None:
        i = self._ptr
        self._x[i] = feature
        self._z[i] = np.float32(target)
        self._ptr = (self._ptr + 1) % self.capacity
        self._n = min(self._n + 1, self.capacity)

    def add_many(self, features: np.ndarray, targets: np.ndarray) -> None:
        for row, z in zip(features, targets):
            self.add(row, float(z))

    def sample(self, batch_size: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
        if self._n == 0:
            raise RuntimeError("replay buffer is empty")
        bs = min(batch_size, self._n)
        idx = rng.integers(0, self._n, size=bs)
        return self._x[idx].copy(), self._z[idx].copy()

    def clear(self) -> None:
        self._n = 0
        self._ptr = 0
