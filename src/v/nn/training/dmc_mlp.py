# -*- coding: utf-8 -*-
"""GUA-039a DMC 价值网络：NumPy MLP（fd_native encode_flat 167 维）。"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .fd_env import ensure_fabledan_importable

ensure_fabledan_importable()
from fabledan.encode import FLAT_DIM  # noqa: E402


class DmcMlp:
    """ReLU MLP：FLAT_DIM -> hidden -> hidden -> 1，手动 Adam。"""

    def __init__(self, hidden: int = 256, seed: int = 0, lr: float = 3e-4):
        self.hidden = hidden
        self.lr = lr
        self.t = 0
        rng = np.random.default_rng(seed)

        def init(fan_in: int, fan_out: int) -> np.ndarray:
            return (rng.standard_normal((fan_in, fan_out)) *
                    np.sqrt(2.0 / fan_in)).astype(np.float32)

        self.W = [init(FLAT_DIM, hidden), init(hidden, hidden), init(hidden, 1)]
        self.b = [
            np.zeros(hidden, np.float32),
            np.zeros(hidden, np.float32),
            np.zeros(1, np.float32),
        ]
        self.mW = [np.zeros_like(w) for w in self.W]
        self.vW = [np.zeros_like(w) for w in self.W]
        self.mb = [np.zeros_like(b) for b in self.b]
        self.vb = [np.zeros_like(b) for b in self.b]

    @property
    def feature_dim(self) -> int:
        return FLAT_DIM

    def forward(self, x: np.ndarray) -> tuple[np.ndarray, tuple]:
        if x.ndim == 1:
            x = x[None, :]
        h1 = np.maximum(x @ self.W[0] + self.b[0], 0)
        h2 = np.maximum(h1 @ self.W[1] + self.b[1], 0)
        out = h2 @ self.W[2] + self.b[2]
        return out[:, 0], (x, h1, h2)

    def predict(self, x: np.ndarray) -> np.ndarray:
        q, _ = self.forward(x)
        return q

    def train_batch(self, x: np.ndarray, z: np.ndarray) -> float:
        q, (x0, h1, h2) = self.forward(x)
        err = (q - z)[:, None]
        loss = float(np.mean(err ** 2))
        batch = x.shape[0]
        g_out = 2.0 * err / batch
        gW2 = h2.T @ g_out
        gb2 = g_out.sum(0)
        g_h2 = g_out @ self.W[2].T
        g_h2[h2 <= 0] = 0
        gW1 = h1.T @ g_h2
        gb1 = g_h2.sum(0)
        g_h1 = g_h2 @ self.W[1].T
        g_h1[h1 <= 0] = 0
        gW0 = x0.T @ g_h1
        gb0 = g_h1.sum(0)
        self._adam([gW0, gW1, gW2], [gb0, gb1, gb2])
        return loss

    def _adam(self, gW, gb, beta1=0.9, beta2=0.999, eps=1e-8) -> None:
        self.t += 1
        lr_t = self.lr * np.sqrt(1 - beta2 ** self.t) / (1 - beta1 ** self.t)
        for i in range(3):
            self.mW[i] = beta1 * self.mW[i] + (1 - beta1) * gW[i]
            self.vW[i] = beta2 * self.vW[i] + (1 - beta2) * gW[i] ** 2
            self.W[i] -= lr_t * self.mW[i] / (np.sqrt(self.vW[i]) + eps)
            self.mb[i] = beta1 * self.mb[i] + (1 - beta1) * gb[i]
            self.vb[i] = beta2 * self.vb[i] + (1 - beta2) * gb[i] ** 2
            self.b[i] -= lr_t * self.mb[i] / (np.sqrt(self.vb[i]) + eps)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        arrs = {
            "kind": np.array("dmc_mlp_flat"),
            "feature_dim": np.array(FLAT_DIM),
            "t": np.array(self.t),
            "W0": self.W[0], "W1": self.W[1], "W2": self.W[2],
            "b0": self.b[0], "b1": self.b[1], "b2": self.b[2],
        }
        for i in range(3):
            arrs[f"mW{i}"] = self.mW[i]
            arrs[f"vW{i}"] = self.vW[i]
            arrs[f"mb{i}"] = self.mb[i]
            arrs[f"vb{i}"] = self.vb[i]
        np.savez_compressed(path, **arrs)

    @classmethod
    def load(cls, path: str | Path, hidden: int = 256, lr: float = 3e-4) -> "DmcMlp":
        z = np.load(path)
        m = cls(hidden=hidden, lr=lr)
        m.W = [z["W0"].copy(), z["W1"].copy(), z["W2"].copy()]
        m.b = [z["b0"].copy(), z["b1"].copy(), z["b2"].copy()]
        if "t" in z.files:
            m.t = int(z["t"])
            for i in range(3):
                m.mW[i] = z[f"mW{i}"].copy()
                m.vW[i] = z[f"vW{i}"].copy()
                m.mb[i] = z[f"mb{i}"].copy()
                m.vb[i] = z[f"vb{i}"].copy()
        return m
