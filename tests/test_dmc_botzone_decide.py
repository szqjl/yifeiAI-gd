# -*- coding: utf-8 -*-
"""V9 DMC Botzone 决策单测。"""

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from src.v.nn.inference.dmc_botzone_decide import (  # noqa: E402
    DmcBotzoneDecider,
    load_dmc_model,
    move_to_botzone_response,
)
from src.v.nn.inference.botzone_mirror import BotzoneMirror  # noqa: E402
from src.v.nn.training.fd_env import ensure_fabledan_importable  # noqa: E402

ensure_fabledan_importable()
from fabledan.combos import gen_moves  # noqa: E402


def _deal_req(your_id: int = 0) -> dict:
    return {
        "stage": "deal",
        "your_id": your_id,
        "deliver": list(range(27)),
        "global": {"level": "2"},
    }


def _play_req(history=None) -> dict:
    return {
        "stage": "play",
        "your_id": 0,
        "global": {"level": "2"},
        "done": [],
        "history": history or [],
        "pass_on": -1,
    }


def test_load_dmc_model_missing_returns_rule(monkeypatch):
    monkeypatch.setattr(
        "src.v.nn.inference.dmc_botzone_decide._repo_weight_candidates",
        lambda: (),
    )
    model, kind = load_dmc_model("/nonexistent/dmc.npz")
    assert model is None
    assert kind == "rule"


def test_decider_deal_returns_empty():
    decider = DmcBotzoneDecider()
    out = decider.handle_full_input({"requests": [_deal_req()], "responses": []})
    assert out == []


def test_decider_play_returns_valid_response():
    decider = DmcBotzoneDecider()
    full = {"requests": [_deal_req(), _play_req()], "responses": [[]]}
    out = decider.handle_full_input(full)
    assert isinstance(out, list)
    assert len(out) == 2
    assert isinstance(out[0], list)
    assert isinstance(out[1], list)


def test_mirror_obs_matches_legal():
    mirror = BotzoneMirror()
    mirror.feed_request(_deal_req())
    mirror.feed_request(_play_req())
    lead = mirror.lead_to_beat()
    legal = gen_moves(mirror.hand, mirror.lv, lead)
    obs = mirror.obs(legal, lead)
    assert len(obs["hand"]) == 27
    assert obs["legal"] == legal


def test_move_to_botzone_pass():
    from fabledan.combos import PASS_MOVE

    assert move_to_botzone_response(PASS_MOVE) == [[], []]


@pytest.mark.skipif(
    not Path("models/dmc_v8_bridge_A150.npz").exists(),
    reason="需要本地 Layer2 权重",
)
def test_decider_with_a150_weights():
    decider = DmcBotzoneDecider(weights_path="models/dmc_v8_bridge_A150.npz")
    assert decider.model is not None
    assert decider.model_label.startswith("dmc:")
    full = {"requests": [_deal_req(), _play_req()], "responses": [[]]}
    out = decider.handle_full_input(full)
    assert isinstance(out, list)
