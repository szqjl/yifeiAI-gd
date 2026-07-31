# -*- coding: utf-8 -*-
"""
DanZeroPolicy - v7Dan vs DanZero 批跑中 DanZero 侧（client3/client4）的决策策略。

当前为【占位骨架】：优先选 actionList 中首个非 PASS 动作（最小牌贪心），
全部 PASS 才选 0 —— 保证 DanZero 会主动出牌、批跑有意义。
后续接入 DanZero 模型时，在此替换为真实推理：
- 模型源码/权重：submit-paper/Danzero_plus（actor_torch/actor.py，DMC Q-net + PPO）
- 输入契约：见 docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md §12
  （567 维 state、合法动作编码、Top-2 采样；动作枚举与 v1006 平台 actionList 对应）
- 平台适配：本仓库 v1006 批跑（ws://127.0.0.1:23456/game/client3|client4）

注：DanZero 是队B（对手）侧，不写 game_records_v7dan 牌谱（牌谱由队A v7dan 记录）。
"""
import ast
from typing import List, Optional

# 兼容导入：模型权重加载后将在此注册（默认禁用）
_LOADED = False

_PASS_TYPES = ("PASS", "pass")


def _first_playable_index(action_list: List[list]) -> int:
    """
    取首个非 PASS 动作的 actIndex。
    v1006 actionList 首项恒为 PASS（可不出时），恒选 0 会永久 PASS；
    取首个非 PASS 使占位策略具备「能出就出最小牌」的基础行为。
    """
    for idx, action in enumerate(action_list):
        if not isinstance(action, list) or not action:
            continue
        action_type = action[0]
        if action_type not in _PASS_TYPES:
            return idx
    return 0


class DanZeroPolicy:
    """DanZero 决策策略（骨架：最小牌贪心，保证主动出牌）。"""

    def __init__(self, user_info: str) -> None:
        self.user_info = user_info
        self.log_prefix = f"[{user_info}:danzero]"

    def decide(self, data: dict) -> int:
        """
        决策入口：输入平台 act 消息（已 preprocess），返回 actIndex。
        tribute/back 阶段 actionList 首项即唯一送牌，也走同一逻辑（无 PASS 则取 0）。
        """
        if _LOADED:
            # TODO(danzero): 模型就绪后按 §12 契约实现 567 维 state 编码 + Top-2 采样
            return 0
        action_list = data.get("actionList") or []
        if not isinstance(action_list, list):
            return 0
        return _first_playable_index(action_list)
