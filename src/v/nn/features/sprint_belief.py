# -*- coding: utf-8 -*-
"""GUA-077 / MEM-M07：残局冲刺信念（SprintBelief）。

供 ``RuleCardCounter.get_sprint_belief()`` 产出；``SprintStepPicker`` 消费。
组牌 ``play_sequence`` 只描述己方结构，敌情门控由此模块供给。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SprintBelief:
    """残局冲刺步序门控所需的信念快照。"""

    # 单张
    my_single_is_field_max: Dict[str, bool] = field(default_factory=dict)
    enemy_can_beat_single: Dict[int, Dict[str, bool]] = field(default_factory=dict)
    probe_single_rank: Optional[str] = None

    # 三带二（平台 ThreeWithTwo）
    enemy_can_beat_twt: Dict[int, Dict[str, bool]] = field(default_factory=dict)
    any_enemy_can_beat_twt: Dict[str, bool] = field(default_factory=dict)
    enemy_twt_unlikely: Dict[int, bool] = field(default_factory=dict)

    # 炸弹
    enemy_bomb_risk_on_lead: float = 1.0
    my_bomb_beats_field: bool = False

    # 敌剩张
    enemy_min_remaining: int = 27
    enemy_any_remaining_eq_1: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """注入 ``game_state['_sprint_belief']`` 或 trace 日志。"""
        return {
            "my_single_is_field_max": dict(self.my_single_is_field_max),
            "enemy_can_beat_single": {
                seat: dict(ranks) for seat, ranks in self.enemy_can_beat_single.items()
            },
            "probe_single_rank": self.probe_single_rank,
            "enemy_can_beat_twt": {
                seat: dict(ranks) for seat, ranks in self.enemy_can_beat_twt.items()
            },
            "any_enemy_can_beat_twt": dict(self.any_enemy_can_beat_twt),
            "enemy_twt_unlikely": dict(self.enemy_twt_unlikely),
            "enemy_bomb_risk_on_lead": self.enemy_bomb_risk_on_lead,
            "my_bomb_beats_field": self.my_bomb_beats_field,
            "enemy_min_remaining": self.enemy_min_remaining,
            "enemy_any_remaining_eq_1": self.enemy_any_remaining_eq_1,
        }
