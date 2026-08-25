# -*- coding: utf-8 -*-
"""Dual-GPU DMC trainer: central batched GPU inference (DanLM-style).

Processes:
  - N actor processes (CPU): run `ring` concurrent rounds each via RingRunner,
    send batched decision requests to the inference server, push finished
    episodes to the learner.
  - 1 inference server process (GPU `--infer-device`): batches all pending
    decisions across actors into single forward passes; refreshes weights
    every cycle.
  - main process = learner (GPU `--device`): replay buffer + gradient steps,
    checkpointing, eval vs rule baseline & frozen snapshot, and automatic
    export/packaging of a ready-to-upload botzone zip whenever eval improves.

Typical run on a 2x5090 box:
    python -m fabledan.train_fast --out ckpts/fast1 --actors 24 ^
        --device cuda:1 --infer-device cuda:0
Resume:
    python -m fabledan.train_fast --out ckpts/fast1 --resume ckpts/fast1/latest.pt
"""

import argparse
import os
import queue as pyqueue
import random
import time
import zipfile

import numpy as np

try:
    import torch
    import torch.multiprocessing as mp
except ImportError as e:
    raise SystemExit("PyTorch required: pip install torch") from e

from .encode import FEAT_DIM
from .model_torch import FableDanNet, ModelConfig, export_npz, save_ckpt
from .train import Replay


# ---------------------------------------------------------------------------
# actor process
# ---------------------------------------------------------------------------

def actor_proc(actor_id, req_q, resp_q, sample_q, stop_ev, ring, eps, top_k, seed):
    from .ring import RingRunner
    runner = RingRunner(ring=ring, seed=seed, eps=eps, top_k=top_k)
    while not stop_ev.is_set():
        reqs = runner.collect_requests()
        # one message per actor: (actor_id, [(slot, toks, feats), ...])
        req_q.put((actor_id, reqs))
        try:
            results = resp_q.get(timeout=60)
        except pyqueue.Empty:
            continue
        runner.step(dict(results))
        eps_out = runner.pop_episodes()
        if eps_out:
            sample_q.put(eps_out)


# ---------------------------------------------------------------------------
# inference server process
# ---------------------------------------------------------------------------

def infer_server(cfg_dict, req_q, resp_qs, weight_q, stop_ev, device,
                 max_decisions, stats_every):
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = True
    use_amp = str(device).startswith("cuda")
    cfg = ModelConfig.from_dict(cfg_dict)
    model = FableDanNet(cfg).to(device).eval()
    sd = weight_q.get()
    model.load_state_dict(sd)
    n_req = 0
    n_dec = 0
    n_fwd = 0
    t_last = time.time()
    while not stop_ev.is_set():
        # weight refresh (non-blocking)
        try:
            while True:
                sd = weight_q.get_nowait()
                model.load_state_dict(sd)
        except pyqueue.Empty:
            pass
        # gather a batch of actor messages
        msgs = []
        ndec = 0
        try:
            m = req_q.get(timeout=0.5)
            msgs.append(m)
            ndec += len(m[1])
            while ndec < max_decisions:
                m = req_q.get_nowait()
                msgs.append(m)
                ndec += len(m[1])
        except pyqueue.Empty:
            pass
        if not msgs:
            continue
        # build batch
        all_toks, all_feats, counts, route = [], [], [], []
        for actor_id, reqs in msgs:
            for slot, toks, feats in reqs:
                all_toks.append(toks)
                all_feats.append(feats)
                counts.append(feats.shape[0])
                route.append((actor_id, slot))
        B = len(all_toks)
        maxlen = max(len(t) for t in all_toks)
        T = np.zeros((B, maxlen), dtype=np.int64)
        L = np.zeros(B, dtype=np.int64)
        for j, t in enumerate(all_toks):
            T[j, :len(t)] = t
            L[j] = len(t)
        Fcat = np.concatenate(all_feats, axis=0)
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16,
                                             enabled=use_amp):
            tT = torch.from_numpy(T).to(device, non_blocking=True)
            tL = torch.from_numpy(L).to(device, non_blocking=True)
            tF = torch.from_numpy(Fcat).to(device, non_blocking=True)
            ctx, _ = model.encode_seq(tT, tL)
            cnt = torch.tensor(counts, device=device)
            ctx_rep = ctx.repeat_interleave(cnt, dim=0)
            hemb = model.hand_mlp(tF)
            q = model.q_head(torch.cat([ctx_rep, hemb], dim=-1))[:, 0]
            q = q.float().cpu().numpy()
        # split and route
        per_actor = {}
        off = 0
        for (actor_id, slot), c in zip(route, counts):
            per_actor.setdefault(actor_id, []).append((slot, q[off:off + c]))
            off += c
        for actor_id, results in per_actor.items():
            resp_qs[actor_id].put(results)
        n_req += len(msgs)
        n_dec += B
        n_fwd += 1
        if time.time() - t_last > stats_every:
            print("[infer] %.0f decisions/s, avg batch %.0f decisions "
                  "(%.1f actor msgs)" % (n_dec / (time.time() - t_last),
                                         n_dec / max(n_fwd, 1),
                                         n_req / max(n_fwd, 1)), flush=True)
            n_req = n_dec = n_fwd = 0
            t_last = time.time()


# ---------------------------------------------------------------------------
# packaging (auto botzone zip)
# ---------------------------------------------------------------------------

BOT_MODULES = ["__init__.py", "cards.py", "combos.py", "engine.py",
               "encode.py", "model_np.py", "agents.py", "train_demo.py",
               "evaluate.py"]


def pack_botzone_zip(weights_npz, out_zip):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bot_src = os.path.join(root, "botzone", "bot_fabledan.py")
    os.makedirs(os.path.dirname(out_zip), exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(bot_src, "__main__.py")
        for m in BOT_MODULES:
            z.write(os.path.join(root, "fabledan", m), "fabledan/" + m)
        z.write(weights_npz, "fabledan_weights.npz")
    return os.path.getsize(out_zip)


# ---------------------------------------------------------------------------
# learner / main
# ---------------------------------------------------------------------------

def run_eval(model, device, games, opponent="rule", opp_model=None, seed=123):
    from .agents import RuleAgent, TorchAgent
    from .evaluate import evaluate
    make_b = (lambda: RuleAgent()) if opponent == "rule" else \
        (lambda: TorchAgent(opp_model, device=device))
    wr, _ = evaluate(lambda: TorchAgent(model, device=device), make_b,
                     games=games, seed=seed)
    return wr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="ckpts/fast1")
    ap.add_argument("--resume", default="")
    ap.add_argument("--actors", type=int, default=max(4, (os.cpu_count() or 8) - 6))
    ap.add_argument("--ring", type=int, default=16)
    ap.add_argument("--cycles", type=int, default=10**9)
    ap.add_argument("--buffer", type=int, default=262144)
    ap.add_argument("--diversity", type=int, default=2)
    ap.add_argument("--steps-per-cycle", type=int, default=16)
    ap.add_argument("--batch", type=int, default=4096)
    ap.add_argument("--micro-batch", type=int, default=1024,
                    help="gradient-accumulation chunk size (memory bound)")
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--eps", type=float, default=0.02)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--ntp-weight", type=float, default=0.02)
    ap.add_argument("--belief-weight", type=float, default=0.05,
                    help="aux loss: predict opponents' hidden hands (0=off)")
    ap.add_argument("--n-blocks", type=int, default=4)
    ap.add_argument("--eval-cycles", type=int, default=25)
    ap.add_argument("--eval-games", type=int, default=60)
    ap.add_argument("--ckpt-cycles", type=int, default=5)
    ap.add_argument("--snapshot-cycles", type=int, default=500,
                    help="frozen self snapshot refresh for shadow eval")
    ap.add_argument("--device", default="cuda:1" if torch.cuda.device_count() > 1
                    else ("cuda:0" if torch.cuda.is_available() else "cpu"))
    ap.add_argument("--infer-device", default="cuda:0"
                    if torch.cuda.is_available() else "cpu")
    ap.add_argument("--max-decisions", type=int, default=1024,
                    help="max decisions per inference batch")
    ap.add_argument("--max-hours", type=float, default=0,
                    help="auto-stop after N hours: save ckpt, export npz, "
                         "pack upload zip (0 = run forever)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    device = args.device
    torch.backends.cuda.matmul.allow_tf32 = True
    use_amp = str(device).startswith("cuda")
    cfg = ModelConfig(n_blocks=args.n_blocks, ntp_weight=args.ntp_weight)
    model = FableDanNet(cfg).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    start_cycle, total_samples = 0, 0
    if args.resume:
        ck = torch.load(args.resume, map_location=device, weights_only=False)
        model.load_state_dict(ck["model"])
        if ck.get("optimizer"):
            opt.load_state_dict(ck["optimizer"])
        start_cycle = ck["meta"].get("cycle", 0)
        total_samples = ck["meta"].get("total_samples", 0)
        print("resumed cycle %d, %d samples" % (start_cycle, total_samples))

    mp.set_start_method("spawn", force=True)
    req_q = mp.Queue(maxsize=4096)
    sample_q = mp.Queue(maxsize=4096)
    weight_q = mp.Queue(maxsize=4)
    resp_qs = [mp.Queue(maxsize=8) for _ in range(args.actors)]
    stop_ev = mp.Event()

    server = mp.Process(target=infer_server,
                        args=(cfg.to_dict(), req_q, resp_qs, weight_q,
                              stop_ev, args.infer_device, args.max_decisions,
                              30.0), daemon=True)
    server.start()

    actors = []
    for a in range(args.actors):
        p = mp.Process(target=actor_proc,
                       args=(a, req_q, resp_qs[a], sample_q, stop_ev,
                             args.ring, args.eps, args.top_k, 7000 + a),
                       daemon=True)
        p.start()
        actors.append(p)

    def push_weights():
        sd = {k: v.detach().cpu() for k, v in model.state_dict().items()}
        try:
            weight_q.put_nowait(sd)
        except pyqueue.Full:
            pass

    weight_q.put({k: v.detach().cpu() for k, v in model.state_dict().items()})

    replay = Replay(args.buffer, belief_dim=45 if args.belief_weight > 0 else 0)
    rng = np.random.default_rng(0)
    cycle_budget = args.buffer // args.diversity
    best_wr = 0.0
    milestone_95 = False
    snapshot = None
    t_start = time.time()

    for cycle in range(start_cycle, args.cycles):
        got = 0
        t0 = time.time()
        while got < cycle_budget:
            ep = sample_q.get()
            for toks, feat, z, bel in ep:
                replay.add(toks, feat, z, bel)
            got += len(ep)
        total_samples += got
        t_collect = time.time() - t0

        t0 = time.time()
        model.train()
        losses = []
        mb = max(1, min(args.micro_batch, args.batch))
        n_chunks = (args.batch + mb - 1) // mb
        for _ in range(args.steps_per_cycle):
            T0, L0, F0, Z0, BEL0 = replay.sample(args.batch, rng)
            opt.zero_grad(set_to_none=True)
            step_loss = 0.0
            for c in range(n_chunks):
                s, e = c * mb, min((c + 1) * mb, args.batch)
                T = torch.from_numpy(T0[s:e]).to(device)
                L = torch.from_numpy(L0[s:e]).to(device)
                F = torch.from_numpy(F0[s:e]).to(device).unsqueeze(1)
                Z = torch.from_numpy(Z0[s:e]).to(device)
                with torch.autocast("cuda", dtype=torch.bfloat16,
                                    enabled=use_amp):
                    q, hid = model(T, L, F)
                    loss_q = torch.nn.functional.mse_loss(q[:, 0].float(), Z)
                    loss = loss_q
                    if cfg.ntp_weight > 0:
                        loss = loss + cfg.ntp_weight * model.ntp_loss(T, hid)
                    if args.belief_weight > 0 and BEL0 is not None:
                        idx_last = (L - 1).clamp(min=0)
                        ctx = hid[torch.arange(hid.shape[0], device=device),
                                  idx_last]
                        bel_t = torch.from_numpy(BEL0[s:e]).to(device)
                        loss = loss + args.belief_weight * \
                            model.belief_loss(ctx.float(), bel_t)
                ((e - s) / args.batch * loss).backward()
                step_loss += loss_q.item() * (e - s) / args.batch
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            losses.append(step_loss)
        model.eval()
        t_train = time.time() - t0
        push_weights()

        sps = total_samples / (time.time() - t_start + 1e-9)
        print("cycle %d  samples %s  loss %.4f  collect %.1fs train %.1fs  "
              "%.0f samples/s" % (cycle, f"{total_samples:,}",
                                  float(np.mean(losses)), t_collect, t_train,
                                  sps), flush=True)

        meta = {"cycle": cycle + 1, "total_samples": total_samples}
        if (cycle + 1) % args.ckpt_cycles == 0:
            save_ckpt(model, opt, meta, os.path.join(args.out, "latest.pt"))
        if args.snapshot_cycles and (cycle + 1) % args.snapshot_cycles == 0:
            snapshot = FableDanNet(cfg).to(device)
            snapshot.load_state_dict(model.state_dict())
            snapshot.eval()
        if (cycle + 1) % args.eval_cycles == 0:
            wr = run_eval(model, device, args.eval_games, "rule")
            msg = "  eval vs rule: %.1f%%" % (wr * 100)
            if snapshot is not None:
                wr_s = run_eval(model, device, args.eval_games, "self",
                                opp_model=snapshot)
                msg += "  vs snapshot(-%d cyc): %.1f%%" % (
                    args.snapshot_cycles, wr_s * 100)
            print(msg, flush=True)
            if wr >= best_wr:
                best_wr = wr
                save_ckpt(model, opt, meta, os.path.join(args.out, "best.pt"))
                npz = os.path.join(args.out, "best.npz")
                export_npz(model, npz)
                zip_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "dist", "fabledan_bot_ready.zip")
                size = pack_botzone_zip(npz, zip_path)
                print("  [打包] %s (%.1f MB) — 可直接上传 botzone (python3)"
                      % (zip_path, size / 1e6), flush=True)
            if wr >= 0.95 and not milestone_95:
                milestone_95 = True
                print("\n" + "=" * 64 +
                      "\n  里程碑: vs rule >= 95%%! 现在就值得上传第一版:\n"
                      "  dist/fabledan_bot_ready.zip -> botzone GuanDan, "
                      "编译器选 python3\n" + "=" * 64 + "\n", flush=True)

        if args.max_hours > 0 and time.time() - t_start >= args.max_hours * 3600:
            print("\n[到时收尾] 已运行 %.1f 小时，做最终评估与打包..."
                  % ((time.time() - t_start) / 3600), flush=True)
            save_ckpt(model, opt, meta, os.path.join(args.out, "latest.pt"))
            wr = run_eval(model, device, max(args.eval_games, 100), "rule")
            save_ckpt(model, opt, meta, os.path.join(args.out, "final.pt"))
            npz = os.path.join(args.out, "final.npz")
            export_npz(model, npz)
            zip_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "dist", "fabledan_bot_ready.zip")
            size = pack_botzone_zip(npz, zip_path)
            print("[完成] vs rule %.1f%% | 上传文件: %s (%.1f MB)\n"
                  "下次续训: python -m fabledan.train_fast --out %s "
                  "--resume %s" % (wr * 100, zip_path, size / 1e6, args.out,
                                   os.path.join(args.out, "latest.pt")),
                  flush=True)
            break

    stop_ev.set()
    for p in actors + [server]:
        p.terminate()


if __name__ == "__main__":
    main()
