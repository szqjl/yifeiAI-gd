# -*- coding: utf-8 -*-
"""M 平台层：通信、记录、WebSocket、规则常量。V 系列允许依赖的唯一 M 代码区（除 contracts）。"""

from communication.game_recorder import (
    GameRecorder,
    ensure_my_pos_int,
    normalize_action_list,
    normalize_cards_to_string_list,
    sync_pass_counters,
)
from communication.websocket_manager import WebSocketManager
from game_logic.guandan_constants import CARDS_PER_PLAYER, DEFAULT_REST_CARDS

__all__ = [
    "GameRecorder",
    "ensure_my_pos_int",
    "normalize_action_list",
    "normalize_cards_to_string_list",
    "sync_pass_counters",
    "WebSocketManager",
    "CARDS_PER_PLAYER",
    "DEFAULT_REST_CARDS",
]
