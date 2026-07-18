# -*- coding: utf-8 -*-
"""MemoryV2 与现有 MemoryTracker/决策状态的窄适配层。"""
from __future__ import annotations

from typing import Any, Dict, List

from .memory_v2 import MemoryV2


class MemoryV2Adapter:
    """把 tracker 的公开事件转换为 MemoryV2 的推断输入。"""

    def __init__(self, my_seat: int, cur_rank: str):
        self.memory = MemoryV2(my_seat=my_seat, cur_rank=cur_rank)

    def sync(self, game_state: Dict[str, Any], tracker: Any = None) -> MemoryV2:
        hand_counts = {}
        public_info = game_state.get("publicInfo", [])
        if isinstance(public_info, list):
            for seat, info in enumerate(public_info[:4]):
                if isinstance(info, dict) and info.get("rest") is not None:
                    try:
                        hand_counts[seat] = max(0, min(27, int(info["rest"])))
                    except (TypeError, ValueError):
                        pass
        if tracker is not None:
            hand_counts.update({int(k): int(v) for k, v in getattr(tracker, "hand_counts", {}).items()})
            history = list(getattr(tracker, "play_history", []))
        else:
            history = []
        if not hand_counts:
            hand_counts[game_state.get("myPos", 0)] = len(game_state.get("handCards", []) or [])
        self.memory.update_hand_counts(hand_counts)
        actions: List[Dict[str, Any]] = []
        for item in history:
            if not isinstance(item, dict):
                continue
            cards = item.get("cards", []) or []
            if cards:
                actions.append({
                    "cur_pos": item.get("seat", item.get("pos", -1)),
                    "cur_action": [item.get("action_type", "Unknown"), item.get("rank", ""), cards],
                })
        self.memory.update_from_actions(actions)
        return self.memory

    def score_action(self, action: List[Any], game_state: Dict[str, Any], tracker: Any = None) -> int:
        """返回有限幅度的 MemoryV2 软评分，正值偏好，负值规避。"""
        memory = self.sync(game_state, tracker)
        action_type = str(action[0]) if action else ""
        if action_type == "PASS":
            return 0
        cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else []
        if not cards:
            return 0
        safety = memory.check_my_action_safety([str(card) for card in cards])
        score = 0
        risk = float(safety.get("suppression_prob", 0.0) or 0.0)
        if action_type not in ("Bomb", "StraightFlush"):
            score -= min(180, int(round(risk * 180)))
        send_window = memory.is_partner_send_window()
        greater_pos = game_state.get("greaterPos", -1)
        partner = (int(game_state.get("myPos", 0)) + 2) % 4
        if send_window is not None and greater_pos == partner:
            score += 90
        return score
