# -*- coding: utf-8 -*-
"""V9 轻量 DMC Botzone 决策（V8 actionList + NumPy MLP）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from src.v.nn.inference.botzone_mirror import BotzoneMirror
from src.v.nn.training.dmc_mlp import DmcMlp
from src.v.nn.training.fabledan_v8_bridge import (
    generate_v8_action_list,
    list_mappable_v8_actions,
    obs_to_v8_context,
)
from src.v.nn.training.fd_env import ensure_fabledan_importable

ensure_fabledan_importable()
from fabledan.agents import RuleAgent  # noqa: E402
from fabledan.combos import PASS, claim_ids, gen_moves  # noqa: E402
from fabledan.encode import encode_flat  # noqa: E402
from fabledan.engine import default_return_card, forced_tribute_card  # noqa: E402

DEFAULT_WEIGHT_CANDIDATES = (
    "data/dmc_v9_weights.npz",
    "data/dmc_v8_bridge_A150.npz",
    "data/dmc_fd_native_A150.npz",
)


def _repo_weight_candidates() -> Tuple[str, ...]:
    root = Path(__file__).resolve().parents[4]
    extra = (
        str(root / "models" / "dmc_v8_bridge_A150.npz"),
        str(root / "models" / "dmc_fd_native_A150.npz"),
    )
    return DEFAULT_WEIGHT_CANDIDATES + extra


def load_dmc_model(weights_path: Optional[str] = None) -> Tuple[Optional[DmcMlp], str]:
    """加载 DMC 权重；缺失时返回 (None, 'rule')。"""
    candidates: List[str] = []
    if weights_path:
        candidates.append(weights_path)
    candidates.extend(_repo_weight_candidates())
    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            z = np.load(path)
            hidden = int(z["W0"].shape[1])
            model = DmcMlp.load(path, hidden=hidden)
            return model, f"dmc:{Path(path).name}"
        except Exception:
            continue
    return None, "rule"


def move_to_botzone_response(mv) -> list:
    if mv.type == PASS:
        return [[], []]
    return [list(mv.cards), list(claim_ids(mv))]


def _pick_fd_index_v8_bridge(obs: dict, model: DmcMlp) -> int:
    """V8 actionList 枚举 + 可映射着法 DMC argmax（V9 部署内联，无 actor 模块）。"""
    legal = obs["legal"]
    ctx = obs_to_v8_context(obs)
    action_list = generate_v8_action_list(ctx)
    mappable = list_mappable_v8_actions(obs, action_list)
    if mappable:
        feats = np.stack([row[2] for row in mappable])
        q = model.predict(feats)
        pick = int(np.argmax(q))
        return mappable[pick][1]
    feats = np.stack([encode_flat(obs, m) for m in legal])
    q = model.predict(feats)
    return int(np.argmax(q))


def choose_play(mirror: BotzoneMirror, model: Optional[DmcMlp]) -> list:
    lead = mirror.lead_to_beat()
    legal = gen_moves(mirror.hand, mirror.lv, lead)
    obs = mirror.obs(legal, lead)
    if len(legal) == 1:
        return move_to_botzone_response(legal[0])
    if model is not None:
        fd_idx = _pick_fd_index_v8_bridge(obs, model)
        return move_to_botzone_response(legal[fd_idx])
    mv = legal[RuleAgent().act(obs)]
    return move_to_botzone_response(mv)


def respond_stage(mirror: BotzoneMirror, req: dict, model: Optional[DmcMlp]) -> list:
    stage = req.get("stage")
    if stage == "deal":
        return []
    if stage == "tribute":
        return [forced_tribute_card(mirror.hand, mirror.lv)]
    if stage == "return":
        return [default_return_card(mirror.hand, mirror.lv)]
    if stage == "play":
        return choose_play(mirror, model)
    return []


class DmcBotzoneDecider:
    """V9 Botzone 决策器：全量重放 + V8 actionList DMC 推理。"""

    def __init__(self, weights_path: Optional[str] = None) -> None:
        self.model, self.model_kind = load_dmc_model(weights_path)
        self._mirror = BotzoneMirror()
        self._incremental = False

    @property
    def model_label(self) -> str:
        return self.model_kind

    def handle_full_input(self, full_input: dict) -> list:
        if not isinstance(full_input, dict):
            return [[], []]

        if "requests" in full_input:
            self._mirror = BotzoneMirror()
            self._incremental = True
            reqs = full_input.get("requests") or []
            resps = full_input.get("responses") or []
            for i in range(len(resps)):
                self._mirror.feed_request(reqs[i], resps[i])
            if len(resps) >= len(reqs):
                return [[], []]
            cur = reqs[len(resps)]
        else:
            if not self._incremental:
                self._mirror = BotzoneMirror()
            cur = full_input

        self._mirror.feed_request(cur)
        action = respond_stage(self._mirror, cur, self.model)
        stage = cur.get("stage")
        if stage and stage != "deal":
            self._mirror.apply_my_response(stage, action)
        return action
