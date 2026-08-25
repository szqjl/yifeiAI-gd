# -*- coding: utf-8 -*-
"""V8 自学习 step-c：FableDan 仿真 + V8 actionList 双路径自对弈 PoC。

对比两条样本管线吞吐与桥接成功率：
  A) fd_native   — FableDan encode_flat + MC 回报（train_demo 同款）
  B) fd_v8_bridge — FableDan 引擎 + V8 ActionListGenerator + V8TrainingSample

用法（仓库根目录）：
    python scripts/analysis/fabledan_v8_selfplay_poc.py
    python scripts/analysis/fabledan_v8_selfplay_poc.py --episodes 30 --json-out tmp/step_c.json

真源：docs/reasearch/fabledan-train-demo-样本观测.md
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO = Path(__file__).resolve().parents[2]
_FABLE = _REPO / "external" / "FableDan"
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
if str(_FABLE) not in sys.path:
    sys.path.insert(0, str(_FABLE))

from fabledan.agents import RandomAgent  # noqa: E402
from fabledan.encode import encode_flat  # noqa: E402
from fabledan.engine import play_round  # noqa: E402

from src.v.nn.training.fabledan_v8_bridge import (  # noqa: E402
    build_v8_sample,
    generate_v8_action_list,
    obs_to_v8_context,
    v8_action_to_fd_index,
)


@dataclass
class RouteStats:
    route: str
    episodes: int
    samples: int
    seconds: float
    map_failures: int = 0
    episodes_completed: int = 0

    @property
    def samples_per_s(self) -> float:
        return self.samples / self.seconds if self.seconds > 0 else 0.0

    @property
    def episodes_per_s(self) -> float:
        return self.episodes_completed / self.seconds if self.seconds > 0 else 0.0


class _FdNativeCollector:
    def __init__(self, rng: random.Random, buf: list):
        self.rng = rng
        self.buf = buf

    def act(self, obs):
        legal = obs["legal"]
        if len(legal) >= 2:
            idx = self.rng.randrange(len(legal))
            X = encode_flat(obs, legal[idx])
            self.buf.append((X, obs["player"]))
            return idx
        return self.rng.randrange(len(legal))


class _V8BridgeCollector:
    def __init__(self, rng: random.Random, buf: list, stats: Dict[str, int]):
        self.rng = rng
        self.buf = buf
        self.stats = stats

    def act(self, obs):
        legal = obs["legal"]
        if len(legal) < 2:
            return self.rng.randrange(len(legal))
        ctx = obs_to_v8_context(obs)
        action_list = generate_v8_action_list(ctx)
        mappable: List[tuple[int, int]] = []
        for v8_idx, action in enumerate(action_list):
            fd_idx = v8_action_to_fd_index(legal, action)
            if fd_idx is not None:
                mappable.append((v8_idx, fd_idx))
        if mappable:
            v8_idx, fd_idx = self.rng.choice(mappable)
            self.stats["map_ok"] += 1
            sample = build_v8_sample(obs, v8_idx, action_list)
            sample.chosen_fd_index = fd_idx
        else:
            self.stats["map_failures"] += 1
            fd_idx = self.rng.randrange(len(legal))
            v8_idx = 0
            sample = build_v8_sample(obs, v8_idx, action_list)
            sample.chosen_fd_index = fd_idx
        self.buf.append(sample)
        return fd_idx


def _run_episodes(
    episodes: int,
    seed: int,
    route: str,
) -> tuple[RouteStats, List[Any]]:
    rng = random.Random(seed)
    all_samples: List[Any] = []
    map_failures = 0
    t0 = time.perf_counter()
    completed = 0

    for _ in range(episodes):
        buf: list = []
        stats = {"map_failures": 0, "map_ok": 0}
        if route == "fd_native":
            agents = [_FdNativeCollector(rng, buf) for _ in range(4)]
        else:
            agents = [_V8BridgeCollector(rng, buf, stats) for _ in range(4)]

        rewards, _, _ = play_round(
            agents,
            rng=random.Random(rng.getrandbits(48)),
        )
        completed += 1
        if route == "fd_native":
            for X, player in buf:
                all_samples.append({"z_mc": rewards[player] / 3.0, "dim": int(X.shape[0])})
        else:
            map_failures += stats["map_failures"]
            for s in buf:
                s.z_mc = rewards[s.player] / 3.0
                all_samples.append(s.to_dict())

    elapsed = time.perf_counter() - t0
    return RouteStats(
        route=route,
        episodes=episodes,
        samples=len(all_samples),
        seconds=elapsed,
        map_failures=map_failures,
        episodes_completed=completed,
    ), all_samples


def _print_report(a: RouteStats, b: RouteStats, examples: List[dict]) -> None:
    print("=== step-c: FableDan 仿真 + V8 桥接自对弈 PoC ===\n")
    for s in (a, b):
        print(f"[{s.route}]")
        print(f"  episodes={s.episodes_completed}  samples={s.samples}")
        print(f"  time={s.seconds:.2f}s  "
              f"{s.samples_per_s:.0f} samples/s  {s.episodes_per_s:.1f} ep/s")
        if s.route == "fd_v8_bridge":
            ok = s.samples - s.map_failures
            rate = 100.0 * ok / max(s.samples, 1)
            print(f"  v8->fd 可映射决策: {ok}/{s.samples} ({rate:.1f}%)  "
                  f"无映射回退={s.map_failures}")
        print()

    if b.samples_per_s > 0 and a.samples_per_s > 0:
        ratio = b.samples_per_s / a.samples_per_s
        print(f"吞吐比 fd_v8_bridge / fd_native = {ratio:.2f}x")
    print("\n--- V8 样本样例（前 2 条）---")
    for ex in examples[:2]:
        print(json.dumps(ex, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    stats_a, _ = _run_episodes(args.episodes, args.seed, "fd_native")
    stats_b, samples_b = _run_episodes(args.episodes, args.seed + 1, "fd_v8_bridge")

    _print_report(stats_a, stats_b, samples_b)

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "fd_native": asdict(stats_a),
            "fd_v8_bridge": asdict(stats_b),
            "throughput_ratio": (
                stats_b.samples_per_s / stats_a.samples_per_s
                if stats_a.samples_per_s > 0 else None
            ),
            "sample_examples": samples_b[:3],
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON -> {out}")


if __name__ == "__main__":
    main()
