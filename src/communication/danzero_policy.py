# -*- coding: utf-8 -*-
"""
DanZeroPolicy - v7Dan vs DanZero 批跑中 DanZero 侧（client3/client4）的决策策略。

当前为【占位骨架】：decide() 恒返回 0（actionList 首项 = PASS 或最小牌）。
后续接入 DanZero 模型时，在此替换为真实推理：
- 模型源码/权重：submit-paper/Danzero_plus（actor_torch/actor.py，DMC Q-net + PPO）
- 输入契约：见 docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md §12
  （567 维 state、合法动作编码、Top-2 采样；动作枚举与 v1006 平台 actionList 对应）
- 平台适配：本仓库 v1006 批跑（ws://127.0.0.1:23456/game/client3|client4）

注：DanZero 是队B（对手）侧，不写 game_records_v7dan 牌谱（牌谱由队A v7dan 记录）。
"""
import ast
from typing import Optional

# 兼容导入：模型权重加载后将在此注册（默认禁用）
_LOADED = False


class DanZeroPolicy:
    """DanZero 决策策略（骨架：恒选 actionList[0]，保证批跑可跑通）。"""

    def __init__(self, user_info: str) -> None:
        self.user_info = user_info
        self.log_prefix = f"[{user_info}:danzero]"

    def decide(self, data: dict) -> int:
        """
        决策入口：输入平台 act 消息（已 preprocess），返回 actIndex。
        tribute/back 阶段 actionList 首项即唯一送牌，恒取 0。
        """
        if not _LOADED:
            return 0
        # TODO(danzero): 模型就绪后按 §12 契约实现 567 维 state 编码 + Top-2 采样
        return 0

    def preprocess(self, data: dict) -> dict:
        """平台字符串字段（curAction/greaterAction/handCards 偶发为 str）转 list。"""
        for field in ("curAction", "greaterAction", "handCards"):
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = ast.literal_eval(data[field])
                except (ValueError, SyntaxError):
                    pass
        return data


def load_danzero_model(_weights_path: Optional[str] = None) -> bool:
    """
    加载 DanZero 权重并启用真实推理（骨架未实现，恒 False）。
    就绪后：设置 _LOADED = True 并注册决策函数。
    """
    return _LOADED
