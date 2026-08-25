# -*- coding: utf-8 -*-
"""Pure-numpy DMC demo trainer (no PyTorch needed).

Trains a small MLP Q-network with manual backprop via self-play.
This exists to (a) verify the whole RL pipeline end-to-end in any
environment, and (b) produce a real (weak) model for testing the
botzone bot. Serious training: use fabledan.train (PyTorch).
"""

import argparse
import random
import time

import numpy as np

from .encode import FLAT_DIM, encode_flat
from .engine import play_round


class NumpyMLP:
    """MLP with ReLU, manual backprop, Adam. Layers: FLAT_DIM->h->h->1."""

    def __init__(self, hidden=256, seed=0, lr=3e-4):
        rng = np.random.default_rng(seed)
        def init(fan_in, fan_out):
            return (rng.standard_normal((fan_in, fan_out)) *
                    np.sqrt(2.0 / fan_in)).astype(np.float32)
        self.W = [init(FLAT_DIM, hidden), init(hidden, hidden), init(hidden, 1)]
        self.b = [np.zeros(hidden, np.float32), np.zeros(hidden, np.float32),
                  np.zeros(1, np.float32)]
        self.lr = lr
        self.t = 0
        self.mW = [np.zeros_like(w) for w in self.W]
        self.vW = [np.zeros_like(w) for w in self.W]
        self.mb = [np.zeros_like(b) for b in self.b]
        self.vb = [np.zeros_like(b) for b in self.b]

    def forward(self, X):
        h1 = np.maximum(X @ self.W[0] + self.b[0], 0)
        h2 = np.maximum(h1 @ self.W[1] + self.b[1], 0)
        out = h2 @ self.W[2] + self.b[2]
        return out[:, 0], (X, h1, h2)

    def train_batch(self, X, z):
        q, (X0, h1, h2) = self.forward(X)
        err = (q - z)[:, None]                      # [B,1]
        loss = float(np.mean(err ** 2))
        B = X.shape[0]
        g_out = 2.0 * err / B
        gW2 = h2.T @ g_out
        gb2 = g_out.sum(0)
        g_h2 = g_out @ self.W[2].T
        g_h2[h2 <= 0] = 0
        gW1 = h1.T @ g_h2
        gb1 = g_h2.sum(0)
        g_h1 = g_h2 @ self.W[1].T
        g_h1[h1 <= 0] = 0
        gW0 = X0.T @ g_h1
        gb0 = g_h1.sum(0)
        self._adam([gW0, gW1, gW2], [gb0, gb1, gb2])
        return loss

    def _adam(self, gW, gb, beta1=0.9, beta2=0.999, eps=1e-8):
        self.t += 1
        lr_t = self.lr * np.sqrt(1 - beta2 ** self.t) / (1 - beta1 ** self.t)
        for i in range(3):
            self.mW[i] = beta1 * self.mW[i] + (1 - beta1) * gW[i]
            self.vW[i] = beta2 * self.vW[i] + (1 - beta2) * gW[i] ** 2
            self.W[i] -= lr_t * self.mW[i] / (np.sqrt(self.vW[i]) + eps)
            self.mb[i] = beta1 * self.mb[i] + (1 - beta1) * gb[i]
            self.vb[i] = beta2 * self.vb[i] + (1 - beta2) * gb[i] ** 2
            self.b[i] -= lr_t * self.mb[i] / (np.sqrt(self.vb[i]) + eps)

    def save(self, path):
        arrs = dict(kind=np.array("mlp_flat"), t=np.array(self.t),
                    W0=self.W[0], W1=self.W[1], W2=self.W[2],
                    b0=self.b[0], b1=self.b[1], b2=self.b[2])
        for i in range(3):
            arrs["mW%d" % i] = self.mW[i]; arrs["vW%d" % i] = self.vW[i]
            arrs["mb%d" % i] = self.mb[i]; arrs["vb%d" % i] = self.vb[i]
        np.savez_compressed(path, **arrs)

    @classmethod
    def load(cls, path):
        z = np.load(path)
        m = cls()
        m.W = [z["W0"].copy(), z["W1"].copy(), z["W2"].copy()]
        m.b = [z["b0"].copy(), z["b1"].copy(), z["b2"].copy()]
        if "t" in z.files:
            m.t = int(z["t"])
            for i in range(3):
                m.mW[i] = z["mW%d" % i].copy(); m.vW[i] = z["vW%d" % i].copy()
                m.mb[i] = z["mb%d" % i].copy(); m.vb[i] = z["vb%d" % i].copy()
        return m


class MLPAgent:
    def __init__(self, model, eps=0.0, rng=None, collect=None):
        self.model = model
        self.eps = eps
        self.rng = rng or random.Random()
        self.collect = collect

    def act(self, obs):
        X = np.stack([encode_flat(obs, m) for m in obs["legal"]])
        q, _ = self.model.forward(X)
        if self.eps > 0 and self.rng.random() < self.eps:
            idx = self.rng.randrange(len(obs["legal"]))
        else:
            idx = int(np.argmax(q))
        if self.collect is not None:
            self.collect.append((X[idx], obs["player"]))
        return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=3000)
    ap.add_argument("--out", default="ckpts/demo_mlp.npz")
    ap.add_argument("--eps", type=float, default=0.10)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--buffer", type=int, default=60000)
    ap.add_argument("--eval-every", type=int, default=500)
    ap.add_argument("--eval-games", type=int, default=60)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--resume", default="")
    args = ap.parse_args()

    if args.resume and __import__("os").path.exists(args.resume):
        model = NumpyMLP.load(args.resume)
        print("resumed from", args.resume, flush=True)
    else:
        model = NumpyMLP(seed=args.seed)
    rng = random.Random(args.seed)
    nrng = np.random.default_rng(args.seed)
    bufX = np.zeros((args.buffer, FLAT_DIM), np.float32)
    bufZ = np.zeros(args.buffer, np.float32)
    n, ptr = 0, 0
    t0 = time.time()
    losses = []
    for ep in range(1, args.episodes + 1):
        collect = []
        agent = MLPAgent(model, eps=args.eps, rng=rng, collect=collect)
        rewards, _, _ = play_round([agent] * 4,
                                   rng=random.Random(rng.getrandbits(48)))
        for X, player in collect:
            bufX[ptr] = X
            bufZ[ptr] = rewards[player] / 3.0
            ptr = (ptr + 1) % args.buffer
            n = min(n + 1, args.buffer)
        if n >= 4 * args.batch:
            for _ in range(2):
                idx = nrng.integers(0, n, args.batch)
                losses.append(model.train_batch(bufX[idx], bufZ[idx]))
        if ep % args.eval_every == 0:
            from .agents import RandomAgent, RuleAgent
            from .evaluate import evaluate
            wr_rand, _ = evaluate(lambda: MLPAgent(model),
                                  lambda: RandomAgent(0),
                                  games=args.eval_games, seed=7)
            wr_rule, _ = evaluate(lambda: MLPAgent(model),
                                  lambda: RuleAgent(),
                                  games=args.eval_games, seed=7)
            print("ep %d  loss %.4f  vs-random %.0f%%  vs-rule %.0f%%  (%.0fs)"
                  % (ep, np.mean(losses[-200:]) if losses else -1,
                     wr_rand * 100, wr_rule * 100, time.time() - t0),
                  flush=True)
            model.save(args.out)
    model.save(args.out)
    print("saved", args.out)


if __name__ == "__main__":
    main()
