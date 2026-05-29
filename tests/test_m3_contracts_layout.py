# -*- coding: utf-8
"""M3 目录迁移与 IDecisionProvider 契约冒烟测试。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contracts import (
    DECISION_PROVIDER_CONTRACT_VERSION,
    DecisionProviderAdapter,
    is_decision_provider,
)
from m.m1 import RuleBasedDecisionEngineM1
from m.m2 import RuleBasedDecisionEngineM2
from m.m3 import M3DecisionEngine, M3DecisionProvider
from m.platform import GameRecorder, WebSocketManager
from v.learn import HybridDecisionEngineV4, HybridDecisionEngineV5
from v.nn import UltimateWinRateEngineV7


@pytest.mark.unit
def test_contract_version_is_draft():
    assert DECISION_PROVIDER_CONTRACT_VERSION == "0.1-draft"


@pytest.mark.unit
def test_m1_m2_m3_satisfy_decision_provider():
    assert is_decision_provider(RuleBasedDecisionEngineM1(player_id=0))
    assert is_decision_provider(RuleBasedDecisionEngineM2(player_id=2))
    assert is_decision_provider(M3DecisionProvider(player_id=1))
    # 遗留引擎仅 on_message，不经契约；新代码请用 M3DecisionProvider
    assert not is_decision_provider(M3DecisionEngine(player_id=1))


@pytest.mark.unit
def test_v_learn_v_nn_import_and_decide_callable():
    v4 = HybridDecisionEngineV4(player_id=0, config={})
    v5 = HybridDecisionEngineV5(player_id=0, config={})
    v7 = UltimateWinRateEngineV7(player_id=0)
    for engine in (v4, v5, v7):
        assert callable(engine.decide)


@pytest.mark.unit
def test_platform_reexports():
    assert GameRecorder is not None
    assert WebSocketManager is not None


@pytest.mark.unit
def test_decision_provider_adapter():
    inner = RuleBasedDecisionEngineM1(player_id=3)
    wrapped = DecisionProviderAdapter(inner, player_id=3)
    assert is_decision_provider(wrapped)
    assert wrapped.player_id == 3
