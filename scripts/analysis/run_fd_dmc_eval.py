# -*- coding: utf-8 -*-
"""DMC 权重 vs RuleAgent 评估（fd_native / fd_v8_bridge 推理路径）。

用法（仓库根目录）：
    python scripts/analysis/run_fd_dmc_eval.py \\
        --model models/dmc_fd_native_A150.npz \\
        --infer-route fd_v8_bridge --games 100 --seeds 7,42,123
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.v.nn.training.dmc_eval import eval_vs_rule as eval_vs_rule_once  # noqa: E402
from src.v.nn.training.dmc_mlp import DmcMlp  # noqa: E402
from src.v.nn.training.fd_env import ensure_fabledan_importable  # noqa: E402

ensure_fabledan_importable()


def _parse_seeds(raw: str) -> list[int]:
    return [int(s.strip()) for s in raw.split(",") if s.strip()]


def evaluate_route(
    model_path: Path,
    *,
    infer_route: str,
    games: int,
    seeds: list[int],
) -> None:
    model = DmcMlp.load(model_path)
    print(f"model: {model_path}")
    print(f"infer_route: {infer_route}  opponent: RuleAgent  games/seed: {games}\n")

    win_rates: list[float] = []
    for seed in seeds:
        result = eval_vs_rule_once(
            model,
            games=games,
            seed=seed,
            infer_routes=(infer_route,),
        )
        wr = result.win_rates[infer_route]
        avg_r = result.avg_rewards[infer_route]
        stats = result.v8_stats
        win_rates.append(wr)
        line = f"seed={seed:3d}  win_rate={wr * 100:5.1f}%  avg_reward={avg_r:+.3f}"
        if stats is not None and stats.decisions:
            line += (
                f"  v8_map={stats.map_rate * 100:.1f}%"
                f"  fallback={stats.v8_fallback}"
            )
        print(line)

    mean = statistics.mean(win_rates) * 100
    stdev = statistics.pstdev(win_rates) * 100 if len(win_rates) > 1 else 0.0
    print(
        f"\n{len(seeds)}-seed summary: mean={mean:.1f}%  stdev={stdev:.1f}pp  "
        f"min={min(win_rates) * 100:.1f}%  max={max(win_rates) * 100:.1f}%"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="DMC model eval vs RuleAgent")
    ap.add_argument("--model", required=True, help="DmcMlp .npz 权重路径")
    ap.add_argument(
        "--infer-route",
        choices=("fd_native", "fd_v8_bridge"),
        default="fd_v8_bridge",
        help="推理路径：fd_native 或 V8 actionList（fd_v8_bridge）",
    )
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--seeds", default="7,42,123", help="逗号分隔 seed 列表")
    args = ap.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        raise SystemExit(f"model not found: {model_path}")

    evaluate_route(
        model_path,
        infer_route=args.infer_route,
        games=args.games,
        seeds=_parse_seeds(args.seeds),
    )


if __name__ == "__main__":
    main()
