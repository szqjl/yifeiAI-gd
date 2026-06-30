# -*- coding: utf-8 -*-
"""
V7 阶段调度（dispatch_by_stage）— GUA-089

依据 `docs/analysis/v7-kpi-vs-m3-vs-lalala-2026-06-29.md` \u00A77.1-7.4 \u8bbe\u8ba1\u3002

\u6838\u5fc3\u601d\u8def\uff1a
  \u00b7 V7 \u4e3a\u300c\u51b3\u7b56\u5c42\u300d\u3001\u300c\u63a8\u65ad\u5c42\u300d\u3001\u300c\u8bb0\u5fc6\u5c42\u300d\u4e09\u5c42\u67b6\u6784\uff0c\u672c\u6a21\u5757\u662f Layer 3 \u5165\u53e3
  \u00b7 \u6309\u624b\u724c\u5f20\u6570\u5207 3 \u9636\u6bb5\uff1a>20\u3001\u3010 6-20 \u3011\u3001\u22645
  \u00b7 \u6bcf\u9636\u6bb5\u6709\u5b9a\u4e49\u597d\u7684 Guard \u5b50\u96c6\uff08STAGE_RULE_MAP\uff09\u4e0e\u5f15\u64ce\u5165\u53e3\uff08STAGE_ENGINE_MAP\uff09
  \u00b7 \u300cLayer 3 \u4e0d\u8bfb actions \u5386\u53f2\u300d\u2014\u2014\u907f\u514d M3 GUA-036 \u5806\u53e0\u5d29\uff08\u00a77.9.3 \u5173\u952e\u7ea6\u675f\uff09

\u672c\u6a21\u5757\u4ec5\u63d0\u4f9b\u5206\u53d1\u67b6\u6784\uff1b\u5404\u9636\u6bb5\u7684\u300c\u51b3\u7b56\u51fd\u6570\u300d\u7531 GUA-090/091/092 \u5404\u81ea\u63a5\u5165\u3002
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple


# \u9636\u6bb5\u6807\u8bc6\u5e38\u91cf
STAGE_0_1 = "stage_0_1"  # \u5f00\u5c40\u7ec4\u724c + \u89d2\u8272\u5b9a\u4f4d
STAGE_2 = "stage_2"      # \u4e2d\u671f\u52a8\u6001
STAGE_3 = "stage_3"      # \u6b8b\u5c40\u51b3\u80dc


# \u9636\u6bb5\u624b\u724c\u5f20\u6570\u8fb9\u754c\uff08\u00a77.1-7.3\uff09
# \u6839\u636e hand_size \u5224\u5b9a\u9636\u6bb5\uff1a>20 \u8d70\u5f00\u5c40\uff1b\u22645 \u8d70\u6b8b\u5c40\uff1b\u4e2d\u95f4\u4e3a\u4e2d\u671f
STAGE_HAND_SIZE_BOUNDS: Dict[str, Tuple[int, int]] = {
    # stage      (min_inclusive, max_inclusive)
    STAGE_0_1: (21, 27),   # \u5f00\u5c40\u7ec4\u724c + \u89d2\u8272\uff1a21-27 \u5f20
    STAGE_2:   (6,  20),   # \u4e2d\u671f\u52a8\u6001\uff1a6-20 \u5f20
    STAGE_3:   (0,  5),    # \u6b8b\u5c40\u51b3\u80dc\uff1a\u22645 \u5f20
}


# \u9636\u6bb5\u542f\u7528\u7684 Guard \u5b50\u96c6\uff08\u00a77.1.3 / 7.2.3 / 7.3.3\uff09
# \u6ce8\u610f\uff1aR13\u300c\u5e73\u53f0\u70b8\u5f39\u5408\u6cd5\u6027\u300d\u5728 v7_guards.py \u4e2d\u5c1a\u672a\u5b9e\u73b0\uff0c\u672c\u8868\u4e0d\u5305\u542b
#       \u9636\u6bb5 0+1 \u4ec5\u542f\u7528 R10/R11/R14\uff08R12 \u4e3a R12 \u4e0d\u542b\u5408\u7406\uff0c\u00a77.1.3 \u8bf4\u300c\u9636\u6bb5 0 \u4e0d\u62c6\u724c\u300d\uff09
#       \u9636\u6bb5 2 \u5168\u5957 14 \u6761\uff08\u00a77.2.3\uff09
#       \u9636\u6bb5 3 \u7cbe\u7b80\u5230 R08/R11/R14\uff08R13 \u540c\u6837\u672a\u5b9e\u73b0\u4e34\u65f6\u8df3\u8fc7\uff09
STAGE_RULE_MAP: Dict[str, List[str]] = {
    STAGE_0_1: ["R10_no_lead_bomb", "R11_unbeatable_card_throttle", "R14_no_break_pattern_when_lead"],
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
    STAGE_3: ["R08_feed_teammate_single", "R11_unbeatable_card_throttle", "R14_no_break_pattern_when_lead"],
}


# \u9636\u6bb5\u5f15\u64ce\u5165\u53e3\u6620\u5c04\uff08\u00a77.1.4 / 7.2.4 / 7.3.4\uff09
# \u9636\u6bb5 0+1 \u4e0e\u9636\u6bb5 2 \u7684\u300c\u4e13\u7528\u51b3\u7b56\u51fd\u6570\u300d\u4ecd\u5728 GUA-090/091 \u672a\u5b9e\u73b0\uff0c\u8fd4\u56de None
# \u9636\u6bb5 3 \u4f7f\u7528\u73b0\u6709\u6b8b\u5c40\u7ba1\u7ebf EndgameDecider\uff08GUA-078\uff09
STAGE_ENGINE_MAP: Dict[str, Optional[str]] = {
    STAGE_0_1: None,                              # GUA-090 \u672a\u5b00
    STAGE_2:   None,                              # GUA-091 \u672a\u5b00
    STAGE_3:   "src.v.nn.endgame.endgame_decide.EndgameDecider",
}


# \u9636\u6bb5\u63cf\u8ff0\uff08\u4ec5\u4f9b\u65e5\u5fd7/\u8c03\u8bd5\u4f7f\u7528\uff09
STAGE_DESCRIPTIONS: Dict[str, str] = {
    STAGE_0_1: "\u5f00\u5c40\u7ec4\u724c + \u89d2\u8272\u5b9a\u4f4d\uff08\u624b\u724c\u301021-27\u3011\uff09",
    STAGE_2:   "\u4e2d\u671f\u52a8\u6001\uff08\u624b\u724c 6-20 \u5f20\uff09",
    STAGE_3:   "\u6b8b\u5c40\u51b3\u80dc\uff08\u624b\u724c \u22645 \u5f20\uff09",
}


def _dispatch_by_stage(my_hand_size: int, cur_rank: Any = "2") -> str:
    """
    \u6309\u624b\u724c\u5f20\u6570\u8fd4\u56de\u5f53\u524d\u9636\u6bb5\u3002

    \u53c2\u6570\uff1a
      my_hand_size\uff1a\u5f53\u524d\u5b9d\u8d1d\u5e95\u724c\u5f20\u6570\uff080-27\uff09
      cur_rank\uff1a\u5f53\u524d\u7ea7\u724c\uff08\u4f20\u5165\u53c2\u6570\u4f46\u672c\u7248\u672a\u4f7f\u7528\u2014\u2014\u7559\u4f5c GUA-094 IP \u8f93\u5165\uff09

    \u8fd4\u56de\uff1a
      STAGE_0_1 / STAGE_2 / STAGE_3
    """
    if my_hand_size < 0:
        raise ValueError(f"my_hand_size must be >= 0, got {my_hand_size}")
    if my_hand_size >= 21:
        return STAGE_0_1
    if my_hand_size >= 6:
        return STAGE_2
    return STAGE_3


def get_enabled_rules(stage: str) -> List[str]:
    """\u8fd4\u56de\u8be5\u9636\u6bb5\u5b9e\u9645\u542f\u7528\u7684 Guard ID \u5217\u8868\u3002\u9636\u6bb5\u672a\u77e5\u2192\u7a7a\u5217\u8868\u3002"""
    return list(STAGE_RULE_MAP.get(stage, []))


def get_engine_entry(stage: str) -> Optional[Callable]:
    """
    \u8fd4\u56de\u8be5\u9636\u6bb5\u7684\u5f15\u64ce\u5165\u53e3\u51fd\u6570\uff08\u52a8\u6001 import\uff09\u3002

    \u5f53\u524d\u53ea\u6709 STAGE_3 \u6709\u5b9e\u9645\u5165\u53e3\uff08EndgameDecider\uff09\u3002
    \u5176\u4ed6\u9636\u6bb5\u8fd4\u56de None\uff0c\u8c03\u7528\u8005\u9700\u4e3b\u52a8\u68c0\u67e5\u3002
    """
    path = STAGE_ENGINE_MAP.get(stage)
    if not path:
        return None
    # \u52a8\u6001 import "src.v.nn.endgame.endgame_decide.EndgameDecider"
    try:
        module_path, _, class_name = path.rpartition(".")
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name, None)
    except Exception:
        # \u8fdb\u5165\u5931\u8d25\u4e0d\u5d29\u2014\u2014\u8c03\u7528\u8005\u9700 catch
        return None


def stage_bounds() -> Dict[str, Tuple[int, int]]:
    """\u8fd4\u56de\u9636\u6bb5\u8fb9\u754c\u8868\u7684\u62f7\u8d1d\uff08\u9632\u6b62\u88ab\u5916\u90e8\u4fee\u6539\uff09\u3002"""
    return dict(STAGE_HAND_SIZE_BOUNDS)


def stage_description(stage: str) -> str:
    return STAGE_DESCRIPTIONS.get(stage, f"<unknown stage: {stage}>")

