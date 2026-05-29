# -*- coding: utf-8 -*-
"""One-off: regenerate decision/ backward-compat shims after m3 Phase 2 move."""
from pathlib import Path

SHIM = '''# -*- coding: utf-8 -*-
"""Backward compatibility shim — use ``{new}`` instead."""
from {new} import *  # noqa: F401,F403
'''

M1_MAP = {
    "rule_based_decision_engine_m1": "m.m1.rule_based_decision_engine_m1",
    "stage_router": "m.m1.stage_router",
    "phase_handlers": "m.m1.phase_handlers",
    "intelligent_router": "m.m1.intelligent_router",
    "strategy_engine": "m.m1.strategy_engine",
    "enhanced_priority_system": "m.m1.enhanced_priority_system",
    "history_tracker": "m.m1.history_tracker",
    "endgame_planner": "m.m1.endgame_planner",
    "teammate_opportunity_finder": "m.m1.teammate_opportunity_finder",
    "hand_structure_analyzer": "m.m1.hand_structure_analyzer",
    "enhanced_collaboration": "m.m1.enhanced_collaboration",
}
M2_MAP = {
    "rule_based_decision_engine_m2": "m.m2.rule_based_decision_engine_m2",
    "phase_handlers_m2": "m.m2.phase_handlers_m2",
}
M3_MAP = {
    "m3_decision_engine": "m.m3.m3_decision_engine",
    "m3_utils": "m.m3.m3_utils",
}
V_MAP = {
    "hybrid_decision_engine_v4": "v.learn.hybrid_decision_engine_v4",
    "hybrid_decision_engine_v5": "v.learn.hybrid_decision_engine_v5",
    "yf_v5_stage5_decision_engine": "v.learn.yf_v5_stage5_decision_engine",
    "ultimate_win_rate_engine_v7": "v.nn.ultimate_win_rate_engine_v7",
}

dec = Path(__file__).resolve().parents[2] / "src" / "decision"
for name, target in {**M1_MAP, **M2_MAP, **M3_MAP, **V_MAP}.items():
    (dec / f"{name}.py").write_text(SHIM.format(new=target), encoding="utf-8")
print("shims written:", len(M1_MAP) + len(M2_MAP) + len(M3_MAP) + len(V_MAP))
