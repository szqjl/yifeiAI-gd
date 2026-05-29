# -*- coding: utf-8
"""V 挂接门禁：所有 V 主线引擎须满足 IDecisionProvider v1.0。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contracts import assert_v_integration_gate
from v.learn import HybridDecisionEngineV4, HybridDecisionEngineV5, YF_V5_Stage5_DecisionEngine
from v.nn import UltimateWinRateEngineV7


@pytest.mark.unit
@pytest.mark.parametrize(
    "factory",
    [
        lambda: HybridDecisionEngineV4(player_id=0, config={}),
        lambda: HybridDecisionEngineV5(player_id=0, config={}),
        lambda: YF_V5_Stage5_DecisionEngine(player_id=0),
        lambda: UltimateWinRateEngineV7(player_id=0),
    ],
    ids=["v4", "v5", "v5_stage5", "v7"],
)
def test_v_engines_pass_integration_gate(factory):
    engine = factory()
    assert_v_integration_gate(engine, label=type(engine).__name__)
