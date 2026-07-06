# -*- coding: utf-8 -*-
"""
GUA-117 / Q1：队友剩张 → assist_prefer 单一真源。

消费方：EndgamePreprocessor、EndgameDecider Q2、R09、stage_assist_feed。
"""

from typing import List


def assist_prefer_for(teammate_remaining: int) -> List[str]:
    """队友剩 N 张时，允许投喂的 V7 ACTION_TYPE 列表（按优先序）。"""
    if teammate_remaining == 1:
        return ["Single"]
    if teammate_remaining == 2:
        return ["Pair"]
    if teammate_remaining == 3:
        return ["Trips", "Pair", "Single"]
    if teammate_remaining == 4:
        return ["Pair", "Single"]
    if teammate_remaining == 5:
        return ["Straight", "ThreeWithTwo", "Single"]
    return []


def assist_is_close(teammate_remaining: int) -> bool:
    """残局 Q2 / prefer 喂牌：队友进入「接近头游」张数段。"""
    return 1 <= teammate_remaining <= 5
