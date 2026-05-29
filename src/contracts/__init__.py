# -*- coding: utf-8 -*-
"""M3 稳定契约：V 系列仅应依赖本包与 src/m/platform。"""

from .decision_provider import (
    DECISION_PROVIDER_CONTRACT_VERSION,
    V_INTEGRATION_GATE_ENABLED,
    ActMessage,
    IDecisionProvider,
    DecisionProviderAdapter,
    is_decision_provider,
    assert_v_integration_gate,
)

__all__ = [
    "DECISION_PROVIDER_CONTRACT_VERSION",
    "V_INTEGRATION_GATE_ENABLED",
    "ActMessage",
    "IDecisionProvider",
    "DecisionProviderAdapter",
    "is_decision_provider",
    "assert_v_integration_gate",
]
