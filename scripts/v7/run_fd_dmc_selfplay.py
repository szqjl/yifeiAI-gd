# -*- coding: utf-8 -*-
"""GUA-039a：fd_native DMC 自对弈训练 CLI（FableDan engine + NumPy MLP）。

用法（仓库根目录）：
    python scripts/v7/run_fd_dmc_selfplay.py --cycles 10 --episodes-per-cycle 50
    python scripts/v7/run_fd_dmc_selfplay.py --cycles 5 --eval-every 2 --out models/dmc_fd_native.npz

V8 部署：``fd_v8_bridge`` / ``mixed`` 采样时，训练内 eval 默认双路径上报
（``fd_native`` + ``fd_v8_bridge``）；可用 ``--eval-infer-route`` 覆盖。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.v.nn.training.dmc_eval import (  # noqa: E402
    EvalInferRoute,
    eval_vs_rule,
    format_eval_line,
    resolve_eval_infer_routes,
)
from src.v.nn.training.fd_env import ensure_fabledan_importable  # noqa: E402
from src.v.nn.training.learner import DMCLearner, LearnerConfig  # noqa: E402

ensure_fabledan_importable()


def main() -> None:
    ap = argparse.ArgumentParser(description="GUA-039a fd_native DMC self-play")
    ap.add_argument("--cycles", type=int, default=10)
    ap.add_argument("--episodes-per-cycle", type=int, default=50)
    ap.add_argument("--buffer", type=int, default=60_000)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--train-steps", type=int, default=2)
    ap.add_argument("--eps", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--sample-route",
        choices=("fd_native", "fd_v8_bridge", "mixed"),
        default="fd_native",
        help="采样路径：fd_native / fd_v8_bridge / mixed",
    )
    ap.add_argument("--out", default="models/dmc_fd_native.npz")
    ap.add_argument("--eval-every", type=int, default=0, help="每 N cycle 评估 vs RuleAgent")
    ap.add_argument("--eval-games", type=int, default=40)
    ap.add_argument(
        "--eval-infer-route",
        choices=("fd_native", "fd_v8_bridge", "both"),
        default=None,
        help="训练内 eval 推理路径；默认 fd_v8_bridge/mixed 双路径，fd_native 仅 native",
    )
    ap.add_argument("--resume", default="")
    ap.add_argument(
        "--export-v8-jsonl",
        default="",
        help="fd_v8_bridge/mixed 时，每 cycle 追加导出 V8 样本 JSONL",
    )
    ap.add_argument(
        "--metrics-jsonl",
        default="",
        help="每 cycle 追加训练指标（loss/buffer/eval_wr 等）",
    )
    args = ap.parse_args()

    eval_infer_route: Optional[EvalInferRoute] = args.eval_infer_route
    eval_infer_routes = resolve_eval_infer_routes(
        eval_infer_route,
        args.sample_route,
    )

    cfg = LearnerConfig(
        buffer_capacity=args.buffer,
        batch_size=args.batch,
        train_steps_per_cycle=args.train_steps,
        eps=args.eps,
        seed=args.seed,
        sample_route=args.sample_route,
    )
    if args.resume and Path(args.resume).exists():
        learner = DMCLearner.load(args.resume, cfg)
        print(f"resumed from {args.resume}", flush=True)
    else:
        learner = DMCLearner(cfg)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    export_v8_path = Path(args.export_v8_jsonl) if args.export_v8_jsonl else None
    metrics_path = Path(args.metrics_jsonl) if args.metrics_jsonl else None
    if export_v8_path and export_v8_path.exists() and args.sample_route != "fd_native":
        export_v8_path.unlink()
    if metrics_path and metrics_path.exists():
        metrics_path.unlink()
    t_start = time.perf_counter()
    total_v8_exported = 0
    best_wr = 0.0
    best_wr_fd_native: Optional[float] = None
    best_wr_fd_v8_bridge: Optional[float] = None

    for cycle in range(1, args.cycles + 1):
        stat = learner.run_cycle(
            cycle,
            args.episodes_per_cycle,
            seed=args.seed + cycle * 1000,
        )
        print(
            f"cycle {stat.cycle}  route={stat.sample_route}  +{stat.samples_added} samples  "
            f"v8_meta={stat.v8_samples}  buf={stat.buffer_size}  loss={stat.loss:.4f}  "
            f"collect={stat.collect_sec:.2f}s train={stat.train_sec:.2f}s",
            flush=True,
        )
        learner.save(out_path)

        if export_v8_path and stat.v8_samples > 0:
            n = learner.export_v8_samples(export_v8_path, append=cycle > 1)
            total_v8_exported += n

        eval_result = None
        if args.eval_every > 0 and cycle % args.eval_every == 0:
            eval_result = eval_vs_rule(
                learner.model,
                games=args.eval_games,
                seed=7,
                infer_routes=eval_infer_routes,
            )
            best_wr = max(best_wr, eval_result.primary_wr)
            if "fd_native" in eval_result.win_rates:
                wr = eval_result.win_rates["fd_native"]
                best_wr_fd_native = wr if best_wr_fd_native is None else max(best_wr_fd_native, wr)
            if "fd_v8_bridge" in eval_result.win_rates:
                wr = eval_result.win_rates["fd_v8_bridge"]
                best_wr_fd_v8_bridge = (
                    wr if best_wr_fd_v8_bridge is None else max(best_wr_fd_v8_bridge, wr)
                )
            line = "  " + format_eval_line(eval_result)
            if eval_result.v8_stats is not None and eval_result.v8_stats.decisions:
                line += (
                    f"  v8_map={eval_result.v8_stats.map_rate * 100:.1f}%"
                    f"  fallback={eval_result.v8_stats.v8_fallback}"
                )
            print(line, flush=True)

        if metrics_path:
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
            row = {
                "cycle": stat.cycle,
                "route": stat.sample_route,
                "samples_added": stat.samples_added,
                "buffer_size": stat.buffer_size,
                "total_samples": learner.stats.total_samples,
                "total_episodes": learner.stats.total_episodes,
                "loss": None if np.isnan(stat.loss) else stat.loss,
                "collect_sec": stat.collect_sec,
                "train_sec": stat.train_sec,
                "eval_wr": (
                    None if eval_result is None else eval_result.primary_wr
                ),
                "eval_wr_fd_native": (
                    None
                    if eval_result is None
                    else eval_result.win_rates.get("fd_native")
                ),
                "eval_wr_fd_v8_bridge": (
                    None
                    if eval_result is None
                    else eval_result.win_rates.get("fd_v8_bridge")
                ),
                "best_wr": best_wr if eval_result is not None else None,
                "best_wr_fd_native": best_wr_fd_native,
                "best_wr_fd_v8_bridge": best_wr_fd_v8_bridge,
            }
            with metrics_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    elapsed = time.perf_counter() - t_start
    sps = learner.stats.total_samples / max(elapsed, 1e-9)
    print(
        f"done: {learner.stats.total_episodes} episodes  "
        f"{learner.stats.total_samples} samples  {sps:.0f} samples/s  "
        f"saved {out_path}",
        flush=True,
    )
    if export_v8_path and total_v8_exported:
        print(f"v8 jsonl: {total_v8_exported} rows -> {export_v8_path}", flush=True)
    if metrics_path:
        summary = f"metrics: {metrics_path}  best_wr({eval_infer_routes[-1] if len(eval_infer_routes) == 1 else 'v8'})={best_wr:.1%}"
        if best_wr_fd_native is not None and best_wr_fd_v8_bridge is not None:
            summary = (
                f"metrics: {metrics_path}  "
                f"best_wr(fd_v8_bridge)={best_wr_fd_v8_bridge:.1%}  "
                f"best_wr(fd_native)={best_wr_fd_native:.1%}"
            )
        elif best_wr_fd_native is not None:
            summary = f"metrics: {metrics_path}  best_wr(fd_native)={best_wr_fd_native:.1%}"
        print(summary, flush=True)


if __name__ == "__main__":
    main()
