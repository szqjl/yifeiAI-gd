# -*- coding: utf-8 -*-
"""
V7 阶段调度（dispatch_by_stage）— GUA-089

依据 `docs/analysis/v7-kpi-vs-m3-vs-lalala-2026-06-29.md` §7.1-7.4 设计。

核心思路：
  · V7 为「决策层」、「推断层」、「记忆层」三层架构，本模块是 Layer 3 入口
  · 按手牌张数切 4 阶段：27 / 21-26 / 11-20 / 0-10
  · 每阶段有定义好的 Guard 子集（STAGE_RULE_MAP）与引擎入口（STAGE_ENGINE_MAP）
  · 「Layer 3 不读 actions 历史」——避免 M3 GUA-036 堆叠崩溃（§7.9.3 关键约束）

本模块仅提供分发架构；各阶段的「决策函数」由 GUA-090/091/092 各自接入。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple


# 阶段标识常量（2026-07-05 四阶段修订）
STAGE_0 = "stage_0"      # 27 张：开局组牌 + 角色定位
STAGE_1 = "stage_1"      # 21-26 张：初期动态
STAGE_2 = "stage_2"      # 11-20 张：中期动态
STAGE_3 = "stage_3"      # 0-10 张：残局决胜（EndgameDecider）

# 旧名兼容：stage_0_1 已拆为 stage_0 + stage_1
STAGE_0_1 = STAGE_1


# 阶段手牌张数边界
STAGE_HAND_SIZE_BOUNDS: Dict[str, Tuple[int, int]] = {
    # stage      (min_inclusive, max_inclusive)
    STAGE_0: (27, 27),   # 满手：组牌 + 角色
    STAGE_1: (21, 26),   # 初期动态
    STAGE_2: (11, 20),   # 中期动态
    STAGE_3: (0, 10),    # 残局（与 EndgamePreprocessor max_end_card=10 对齐）
}

# 阶段 0/1 共用的轻量 Guard（R12 不含：阶段 0 不拆牌；R13 尚未实现）
_OPENING_GUARD_RULES = [
    "R10_no_lead_bomb",
    "R11_unbeatable_card_throttle",
    "R14_no_break_pattern_when_lead",
]

# 阶段启用的 Guard 子集（§7.1.3 / 7.2.3 / 7.3.3）
STAGE_RULE_MAP: Dict[str, List[str]] = {
    STAGE_0: list(_OPENING_GUARD_RULES),
    STAGE_1: list(_OPENING_GUARD_RULES),
    STAGE_2: [
        "R01_no_bomb_for_single",
        "R02_minimal_bomb",
        "R03_passive_no_pass",
        "R04_single_b_non_pass",
        "R05_teammate_no_bomb",
        "R06_no_break_structure_pair",
        "R07_teammate_yield",
        "R08_feed_teammate_single",
        "R09_feed_teammate_5",
        "R10_no_lead_bomb",
        "R11_unbeatable_card_throttle",
        "R12_min_pair_in_three_with_two",
        "R14_no_break_pattern_when_lead",
    ],
    STAGE_3: [
        "R08_feed_teammate_single",
        "R11_unbeatable_card_throttle",
        "R14_no_break_pattern_when_lead",
    ],
}


# 阶段引擎入口映射（§7.1.4 / 7.2.4 / 7.3.4）
STAGE_ENGINE_MAP: Dict[str, Optional[str]] = {
    STAGE_0: None,
    STAGE_1: None,
    STAGE_2: None,
    STAGE_3: "src.v.nn.endgame.endgame_decide.EndgameDecider",
}


# 阶段描述（仅供日志/调试使用）
STAGE_DESCRIPTIONS: Dict[str, str] = {
    STAGE_0: "开局组牌 + 角色定位（手牌 27 张）",
    STAGE_1: "初期动态（手牌 21-26 张）",
    STAGE_2: "中期动态（手牌 11-20 张）",
    STAGE_3: "残局决胜（手牌 0-10 张，EndgameDecider）",
}


def _dispatch_by_stage(my_hand_size: int, cur_rank: Any = "2") -> str:
    """
    按手牌张数返回当前阶段。

    参数：
      my_hand_size：当前宝贝底牌张数（0-27）
      cur_rank：当前级牌（传入参数但本版未使用——留作 GUA-094 IP 输入）

    返回：
      STAGE_0 / STAGE_1 / STAGE_2 / STAGE_3

    切点（27 优先 stage_0，不与 stage_1 重叠）：
      >=27 → stage_0
      >=21 → stage_1
      >=11 → stage_2
      else → stage_3
    """
    if my_hand_size < 0:
        raise ValueError(f"my_hand_size must be >= 0, got {my_hand_size}")
    if my_hand_size >= 27:
        return STAGE_0
    if my_hand_size >= 21:
        return STAGE_1
    if my_hand_size >= 11:
        return STAGE_2
    return STAGE_3


def get_enabled_rules(stage: str) -> List[str]:
    """返回该阶段实际启用的 Guard ID 列表。阶段未知→空列表。"""
    return list(STAGE_RULE_MAP.get(stage, []))


def get_engine_entry(stage: str) -> Optional[Callable]:
    """
    返回该阶段的引擎入口函数（动态 import）。

    当前只有 STAGE_3 有实际入口（EndgameDecider）。
    其他阶段返回 None，调用者需主动检查。
    """
    path = STAGE_ENGINE_MAP.get(stage)
    if not path:
        return None
    try:
        module_path, _, class_name = path.rpartition(".")
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name, None)
    except Exception:
        return None


def stage_bounds() -> Dict[str, Tuple[int, int]]:
    """返回阶段边界表的拷贝（防止被外部修改）。"""
    return dict(STAGE_HAND_SIZE_BOUNDS)


def stage_description(stage: str) -> str:
    return STAGE_DESCRIPTIONS.get(stage, f"<unknown stage: {stage}>")
