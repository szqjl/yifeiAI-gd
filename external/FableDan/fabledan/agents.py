# -*- coding: utf-8 -*-
"""Agents: Random, greedy Rule baseline, and numpy-model agent."""

import random

import numpy as np

from .combos import (BOMB, PASS, ROCKET, SFLUSH, SINGLE, PAIR, TRIPLE)
from .encode import encode_decision


class RandomAgent:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def act(self, obs):
        return self.rng.randrange(len(obs["legal"]))


class RuleAgent:
    """Greedy heuristic: lead with longest/smallest combo, follow with the
    smallest beating move; avoid breaking bombs unless few cards left."""

    def act(self, obs):
        legal = obs["legal"]
        lead = obs["lead"]
        if lead is None or lead.type == PASS:
            # leading: prefer long non-bomb combos with small key
            def lead_score(i):
                m = legal[i]
                bombish = m.is_bombish()
                return (1 if bombish else 0, -m.size, m.key)
            return min(range(len(legal)), key=lead_score)
        # following: smallest beating move, prefer non-bomb; pass if only
        # bombs and many cards left
        cand = [(i, m) for i, m in enumerate(legal) if m.type != PASS]
        if not cand:
            return 0
        nonbomb = [(i, m) for i, m in cand if not m.is_bombish()]
        if nonbomb:
            return min(nonbomb, key=lambda im: (im[1].key, im[1].size))[0]
        # only bombs can beat: use one if our team is behind, else 30%
        left = obs["left"]
        me = obs["player"]
        opp_min = min(left[(me + 1) % 4], left[(me + 3) % 4])
        if opp_min <= 8 or len(obs["hand"]) <= 10:
            return min(cand, key=lambda im: (im[1].bomb_tier(), im[1].key))[0]
        return 0  # pass


class NumpyAgent:
    """Greedy w.r.t. numpy model Q-values."""

    def __init__(self, model, eps=0.0, rng=None):
        self.model = model
        self.eps = eps
        self.rng = rng or random.Random()

    def act(self, obs):
        if self.eps > 0 and self.rng.random() < self.eps:
            return self.rng.randrange(len(obs["legal"]))
        toks, feats = encode_decision(obs)
        q = self.model.q_values(toks, feats)
        return int(np.argmax(q))


class TorchAgent:
    """Greedy w.r.t. torch model (used inside training actors / eval)."""

    def __init__(self, model, device="cpu", eps=0.0, top_k=0, rng=None):
        import torch
        self.torch = torch
        self.model = model.to(device).eval()
        self.device = device
        self.eps = eps
        self.top_k = top_k
        self.rng = rng or random.Random()

    def act(self, obs):
        import torch
        from .encode import pad_tokens
        toks, feats = encode_decision(obs)
        n = len(obs["legal"])
        if self.eps > 0 and self.rng.random() < self.eps:
            if self.top_k and self.top_k > 1:
                pass  # fall through to model, sample among top-k below
            else:
                return self.rng.randrange(n)
        with torch.no_grad():
            t = torch.tensor([toks], dtype=torch.long, device=self.device)
            ln = torch.tensor([len(toks)], device=self.device)
            f = torch.tensor(feats[None], dtype=torch.float32,
                             device=self.device)
            q, _ = self.model(t, ln, f)
            q = q[0].cpu().numpy()
        if self.eps > 0 and self.top_k and self.top_k > 1 \
                and self.rng.random() < self.eps:
            k = min(self.top_k, n)
            top = np.argsort(q)[-k:]
            return int(self.rng.choice(list(top)))
        return int(np.argmax(q))
