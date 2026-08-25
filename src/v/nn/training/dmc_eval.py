# -*- coding: utf-8 -*-
"""DMC 模型 vs RuleAgent 评估（fd_native / fd_v8_bridge 推理路径）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Sequence, Tuple

from .actor import InferenceStats, SampleRoute, make_inference_agent
from .dmc_mlp import DmcMlp
from .fd_env import ensure_fabledan_importable

ensure_fabledan_importable()
from fabledan.agents import RuleAgent  # noqa: E402
from fabledan.evaluate import evaluate  # noqa: E402

InferRoute = Literal["fd_native", "fd_v8_bridge"]
EvalInferRoute = Literal["fd_native", "fd_v8_bridge", "both"]


@dataclass
class EvalVsRuleResult:
    win_rates: dict[str, float]
    avg_rewards: dict[str, float]
    v8_stats: Optional[InferenceStats] = None

    @property
    def primary_route(self) -> InferRoute:
        if "fd_v8_bridge" in self.win_rates:
            return "fd_v8_bridge"
        return "fd_native"

    @property
    def primary_wr(self) -> float:
        return self.win_rates[self.primary_route]


def resolve_eval_infer_routes(
    eval_infer_route: Optional[EvalInferRoute],
    sample_route: SampleRoute,
) -> Tuple[InferRoute, ...]:
    """解析训练内 eval 应跑的推理路径。

    默认：``fd_v8_bridge`` / ``mixed`` 采样时双路径都报；``fd_native`` 采样时仅 native。
    """
    if eval_infer_route == "both":
        return ("fd_native", "fd_v8_bridge")
    if eval_infer_route in ("fd_native", "fd_v8_bridge"):
        return (eval_infer_route,)
    if sample_route in ("fd_v8_bridge", "mixed"):
        return ("fd_native", "fd_v8_bridge")
    return ("fd_native",)


def eval_vs_rule(
    model: DmcMlp,
    *,
    games: int = 40,
    seed: int = 7,
    infer_routes: Sequence[InferRoute],
) -> EvalVsRuleResult:
    win_rates: dict[str, float] = {}
    avg_rewards: dict[str, float] = {}
    v8_stats: Optional[InferenceStats] = None

    for route in infer_routes:
        stats = InferenceStats() if route == "fd_v8_bridge" else None
        agent = make_inference_agent(model, route, stats=stats)
        wr, avg_r = evaluate(
            lambda a=agent: a,
            lambda: RuleAgent(),
            games=games,
            seed=seed,
        )
        win_rates[route] = wr
        avg_rewards[route] = avg_r
        if stats is not None:
            v8_stats = stats

    return EvalVsRuleResult(
        win_rates=win_rates,
        avg_rewards=avg_rewards,
        v8_stats=v8_stats,
    )


def format_eval_line(result: EvalVsRuleResult) -> str:
    parts = [
        f"({route}): {result.win_rates[route]:.1%}"
        for route in sorted(result.win_rates.keys())
    ]
    return "eval vs rule  " + "  ".join(parts)
