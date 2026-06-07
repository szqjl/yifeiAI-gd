# -*- coding: utf-8 -*-
"""
V7-native P0 Guard 壳（GUA-045）

V7-R01–R06：filter_action_list() 在模型推理前过滤，validate_decision() 在模型后校验。
禁止 import src.m.m3.*；仅依赖标准库 + numpy。
"""

from .v7_guards import (
    filter_action_list,
    validate_decision,
    get_action_type,
    is_bomb,
    is_straight_flush,
    get_action_rank,
    get_card_value,
    CARD_RANK_ORDER,
    # 牌型常量
    ACTION_TYPE_PASS,
    ACTION_TYPE_SINGLE,
    ACTION_TYPE_PAIR,
    ACTION_TYPE_TRIPS,
    ACTION_TYPE_BOMB,
    ACTION_TYPE_STRAIGHT_FLUSH,
    ACTION_TYPE_THREE_PAIR,
    ACTION_TYPE_TWO_TRIPS,
    ACTION_TYPE_THREE_WITH_TWO,
    ACTION_TYPE_STRAIGHT,
    ACTION_TYPE_FREE,
)

__all__ = [
    "filter_action_list",
    "validate_decision",
    "get_action_type",
    "is_bomb",
    "is_straight_flush",
    "get_action_rank",
    "get_card_value",
    "CARD_RANK_ORDER",
    # 牌型常量
    "ACTION_TYPE_PASS",
    "ACTION_TYPE_SINGLE",
    "ACTION_TYPE_PAIR",
    "ACTION_TYPE_TRIPS",
    "ACTION_TYPE_BOMB",
    "ACTION_TYPE_STRAIGHT_FLUSH",
    "ACTION_TYPE_THREE_PAIR",
    "ACTION_TYPE_TWO_TRIPS",
    "ACTION_TYPE_THREE_WITH_TWO",
    "ACTION_TYPE_STRAIGHT",
    "ACTION_TYPE_FREE",
]