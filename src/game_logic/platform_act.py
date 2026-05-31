# -*- coding: utf-8 -*-
"""v1006 平台 act 消息辅助：indexRange  clamp、字段规范化。"""

from __future__ import annotations

from typing import Any, List, Optional


def normalize_pos(value: Any, default: int = -1) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_play_act_fields(data: dict) -> None:
    """将 curPos/greaterPos 的 None 规范为 -1（说明书 tribute/back 可能出现 None）。"""
    if not isinstance(data, dict):
        return
    data["curPos"] = normalize_pos(data.get("curPos"), -1)
    data["greaterPos"] = normalize_pos(data.get("greaterPos"), -1)


def clamp_act_index(
    idx: Any,
    action_list: List,
    index_range: Optional[Any] = None,
) -> int:
    """按 actionList 长度与 indexRange（含端点） clamp 回包索引。"""
    if not action_list:
        return 0
    try:
        chosen = int(idx)
    except (TypeError, ValueError):
        chosen = 0
    upper = len(action_list) - 1
    if index_range is not None:
        try:
            upper = min(upper, int(index_range))
        except (TypeError, ValueError):
            pass
    return max(0, min(chosen, upper))
