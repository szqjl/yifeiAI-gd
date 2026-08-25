# -*- coding: utf-8 -*-
"""DMC self-play training (PyTorch). Run on your GPU machine.

Cycle-based (DanLM-style): each cycle actors collect fresh samples with the
latest weights, learner does S gradient steps on the FIFO replay buffer,
then weights are broadcast to actors.

Usage (Windows/Linux):
    python -m fabledan.train --out ckpts/run1
    python -m fabledan.train --out ckpts/run1 --resume ckpts/run1/latest.pt
"""

import argparse
import os
import random
import time

import numpy as np

try:
    import torch
    import torch.multiprocessing as mp
except ImportError as e:
    raise SystemExit("PyTorch required for training: pip install torch") from e

from .encode import FEAT_DIM, MAX_SEQ, encode_decision
from .engine import play_round
from .model_torch import FableDanNet, ModelConfig, export_npz, save_ckpt


# ---------------------------------------------------------------------------
# actor
# ---------------------------------------------------------------------------

class _ActorPolicy:
    """eps-greedy/top-k policy over the local model copy."""

    def __init__(self, model, eps, top_k, rng):
        self.model = model
        self.eps = eps
        self.top_k = top_k
        self.rng = rng
        self.samples = []          # (toks, feat_of_chosen, player)

    def act(self, obs):
        toks, feats = encode_decision(obs)
        n = feats.shape[0]
        with torch.no_grad():
            t = torch.tensor([toks], dtype=torch.long)
            ln = torch.tensor([len(toks)])
            f = torch.tensor(feats[None], dtype=torch.float32)
            q, _ = self.model(t, ln, f)
            q = q[0].numpy()
        if self.eps > 0 and self.rng.random() < self.eps:
            if self.top_k > 1:
                k = min(self.top_k, n)
                idx = int(self.rng.choice(list(np.argsort(q)[-k:])))
            else:
                idx = self.rng.randrange(n)
        else:
            idx = int(np.argmax(q))
        self.samples.append((toks, feats[idx], obs["player"]))
        return idx


def actor_proc(actor_id, cfg_dict, weight_q, sample_q, stop_ev, seed):
    torch.set_num_threads(1)
    cfg = ModelConfig.from_dict(cfg_dict)
    model = FableDanNet(cfg)
    model.eval()
    rng = random.Random(seed)
    eps = cfg_dict.get("_eps", 0.02)
    top_k = cfg_dict.get("_top_k", 10)
    sd = weight_q.get()                      # initial weights
    model.load_state_dict(sd)
    while not stop_ev.is_set():
        # non-blocking weight refresh
        try:
            while True:
                sd = weight_q.get_nowait()
                model.load_state_dict(sd)
        except Exception:
            pass
        pol = _ActorPolicy(model, eps, top_k, rng)
        agents = [pol, pol, pol, pol]
        rewards, ranking, _ = play_round(agents, rng=random.Random(rng.getrandbits(48)))
        out = []
        for toks, feat, player in pol.samples:
            z = rewards[player] / 3.0
            out.append((np.asarray(toks, dtype=np.int16), feat, np.float32(z)))
        sample_q.put(out)


# ---------------------------------------------------------------------------
# replay buffer
# ---------------------------------------------------------------------------

class Replay:
    def __init__(self, capacity, belief_dim=0):
        self.capacity = capacity
        self.toks = [None] * capacity
        self.feat = np.zeros((capacity, FEAT_DIM), dtype=np.float32)
        self.targ = np.zeros(capacity, dtype=np.float32)
        self.belief_dim = belief_dim
        if belief_dim:
            self.belief = np.zeros((capacity, belief_dim), dtype=np.float32)
        self.n = 0
        self.ptr = 0

    def add(self, toks, feat, targ, belief=None):
        i = self.ptr
        self.toks[i] = toks
        self.feat[i] = feat
        self.targ[i] = targ
        if self.belief_dim and belief is not None:
            self.belief[i] = belief
        self.ptr = (self.ptr + 1) % self.capacity
        self.n = min(self.n + 1, self.capacity)

    def sample(self, bs, rng):
        idx = rng.integers(0, self.n, size=bs)
        toks = [self.toks[i] for i in idx]
        maxlen = max(len(t) for t in toks)
        T = np.zeros((bs, maxlen), dtype=np.int64)
        L = np.zeros(bs, dtype=np.int64)
        for j, t in enumerate(toks):
            T[j, :len(t)] = t
            L[j] = len(t)
        B = self.belief[idx] if self.belief_dim else None
        return T, L, self.feat[idx], self.targ[idx], B


# ---------------------------------------------------------------------------
# learner
# ---------------------------------------------------------------------------

def quick_eval(model, games=100, seed=123):
    """Greedy model (team A) vs RuleAgent. Returns win rate."""
    from .agents import RuleAgent, TorchAgent
    from .evaluate import evaluate
    model_cpu = FableDanNet(model.cfg)
    model_cpu.load_state_dict({k: v.cpu() for k, v in model.state_dict().items()})
    wr, _ = evaluate(lambda: TorchAgent(model_cpu), lambda: RuleAgent(),
                     games=games, seed=seed)
    return wr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="ckpts/run1")
    ap.add_argument("--resume", default="")
    ap.add_argument("--actors", type=int, default=max(2, (os.cpu_count() or 4) - 2))
    ap.add_argument("--cycles", type=int, default=1000000)
    ap.add_argument("--buffer", type=int, default=131072)
    ap.add_argument("--diversity", type=int, default=2)
    ap.add_argument("--steps-per-cycle", type=int, default=16)
    ap.add_argument("--batch", type=int, default=2048)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--eps", type=float, default=0.02)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--ntp-weight", type=float, default=0.02)
    ap.add_argument("--eval-cycles", type=int, default=20)
    ap.add_argument("--ckpt-cycles", type=int, default=10)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--n-blocks", type=int, default=4)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    device = args.device
    cfg = ModelConfig(n_blocks=args.n_blocks, ntp_weight=args.ntp_weight)
    model = FableDanNet(cfg).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    start_cycle = 0
    total_samples = 0
    if args.resume:
        ck = torch.load(args.resume, map_location=device, weights_only=False)
        model.load_state_dict(ck["model"])
        if ck.get("optimizer"):
            opt.load_state_dict(ck["optimizer"])
        start_cycle = ck["meta"].get("cycle", 0)
        total_samples = ck["meta"].get("total_samples", 0)
        print(f"resumed from {args.resume} at cycle {start_cycle}")

    mp.set_start_method("spawn", force=True)
    weight_qs = [mp.Queue(maxsize=4) for _ in range(args.actors)]
    sample_q = mp.Queue(maxsize=256)
    stop_ev = mp.Event()
    cfg_dict = cfg.to_dict()
    cfg_dict["_eps"] = args.eps
    cfg_dict["_top_k"] = args.top_k
    procs = []
    for a in range(args.actors):
        p = mp.Process(target=actor_proc,
                       args=(a, cfg_dict, weight_qs[a], sample_q, stop_ev,
                             1000 + a), daemon=True)
        p.start()
        procs.append(p)

    def broadcast():
        sd = {k: v.detach().cpu() for k, v in model.state_dict().items()}
        for q in weight_qs:
            try:
                q.put_nowait(sd)
            except Exception:
                pass

    broadcast()
    replay = Replay(args.buffer)
    rng = np.random.default_rng(0)
    cycle_budget = args.buffer // args.diversity
    best_wr = 0.0
    t_start = time.time()

    for cycle in range(start_cycle, args.cycles):
        # ---- collect ----
        got = 0
        t0 = time.time()
        while got < cycle_budget:
            ep = sample_q.get()
            for toks, feat, z in ep:
                replay.add(toks, feat, z)
            got += len(ep)
        total_samples += got
        t_collect = time.time() - t0

        # ---- train ----
        t0 = time.time()
        model.train()
        losses = []
        for _ in range(args.steps_per_cycle):
            T, L, F, Z, _B = replay.sample(args.batch, rng)
            T = torch.from_numpy(T).to(device)
            L = torch.from_numpy(L).to(device)
            F = torch.from_numpy(F).to(device).unsqueeze(1)
            Z = torch.from_numpy(Z).to(device)
            q, hid = model(T, L, F)
            loss_q = torch.nn.functional.mse_loss(q[:, 0], Z)
            loss = loss_q
            if cfg.ntp_weight > 0:
                loss = loss + cfg.ntp_weight * model.ntp_loss(T, hid)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            losses.append(loss_q.item())
        model.eval()
        t_train = time.time() - t0
        broadcast()

        sps = total_samples / (time.time() - t_start + 1e-9)
        print(f"cycle {cycle}  samples {total_samples}  "
              f"loss {np.mean(losses):.4f}  collect {t_collect:.1f}s  "
              f"train {t_train:.1f}s  {sps:.0f} samples/s", flush=True)

        meta = {"cycle": cycle + 1, "total_samples": total_samples}
        if (cycle + 1) % args.ckpt_cycles == 0:
            save_ckpt(model, opt, meta, os.path.join(args.out, "latest.pt"))
        if (cycle + 1) % args.eval_cycles == 0:
            wr = quick_eval(model, games=60)
            print(f"  eval vs rule: {wr:.1%}", flush=True)
            if wr >= best_wr:
                best_wr = wr
                save_ckpt(model, opt, meta, os.path.join(args.out, "best.pt"))
                export_npz(model, os.path.join(args.out, "best.npz"))

    stop_ev.set()
    for p in procs:
        p.terminate()


if __name__ == "__main__":
    main()
