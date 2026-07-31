# -*- coding: utf-8 -*-
"""
DanZeroPolicy - v7Dan vs DanZero 批跑中 DanZero 侧（client3/client4）的决策策略。

已接入【真实 DanZero（DMC 版）模型】：加载 models/danzero/q_network.ckpt，
对每个合法动作构造 567 维 state 并 argmax Q 取 actIndex（DanZero+ 论文 DMC 方法）。
源码参考：offline_platform/danzero_plus/（wintest/torch/client1.py 状态机 + DMC Q-net）。

- tribute / back 阶段走 client1 规则（不喂模型）。
- notify 消息（beginning/play/episodeOver）由 DanZeroNN.preprocess 更新状态机。
- DanZero 是队B（对手）侧，不写 game_records_v7dan 牌谱（牌谱由队A v7dan 记录）。
"""
from __future__ import annotations

from typing import List

from danzero_nn import DanZeroNN


class DanZeroPolicy:
    """DanZero 决策策略（真实 DMC Q-net 推理）。"""

    def __init__(self, user_info: str) -> None:
        self.user_info = user_info
        self.log_prefix = f"[{user_info}:danzero]"
        self.nn = DanZeroNN(user_info)

    def preprocess(self, data: dict) -> dict:
        """平台消息预处理：notify 更新状态机，act 透传。"""
        self.nn.preprocess(data)
        return data

    def decide(self, data: dict) -> int:
        """
        决策入口：输入平台 act 消息（已 preprocess），返回 actIndex。
        - play：真实模型推理（合法动作逐行编码 567 维 state，argmax Q）
        - tribute / back：client1 规则
        模型未就绪时降级：取首个非 PASS（占位骨架行为），保证不会死锁。
        """
        if not self.nn.ready:
            return _first_playable_index(data.get("actionList") or [])
        return self.nn.decide(data)


def _first_playable_index(action_list: List[list]) -> int:
    """取首个非 PASS 动作的 actIndex（占位骨架行为，模型未就绪时兜底）。"""
    for idx, action in enumerate(action_list):
        if not isinstance(action, list) or not action:
            continue
        if action[0] not in ("PASS", "pass"):
            return idx
    return 0
