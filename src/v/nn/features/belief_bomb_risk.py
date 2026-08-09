# -*- coding: utf-8 -*-
"""
GUA-223 / CardCountingNetwork-训练方案 §8 Phase 0 ④
heuristic 规则 ⑨ 草案骨架 — `_heuristic_belief_bomb_risk`

> 真源：docs/guandan-brain/CardCountingNetwork-训练方案.md §十 + §8 Phase 0 ④
> 关联：GUA-223（Phase 0）/ GUA-224（Phase 2 完整集成 · 未开）/ GUA-057（母）

⚠️ **本文件是骨架（DRAFT），不动档规则遵守**：
  - 不修改 `ultimate_win_rate_engine_v7.py`（heuristic_select 调用点）
  - 不修改 `memory_tracker.py` 或 `rule_card_counter.py`
  - 仅定义**接口 + 5 项等价性 pytest**，Phase 2 才接到 _heuristic_select
  - 本 issue 仅做"骨架 + pytest 形式可行验证"

`_heuristic_belief_bomb_risk` 设计目标：
  - 输入：当前 step 的 action 候选 + belief_state（108 槽位概率分布）
  - 输出：每个 action 候选的"炸弹风险"软分数（[-1.0, +1.0]）
  - 降级路径：belief_state 不可用时回退到 MemoryTracker 确定性判断
  - 软排序接入：作为 heuristic_select 的一个打分维度（不替代原有打分）
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("belief_bomb_risk")

# === 类型常量 ===

# belief_state shape: (108,) 每槽位概率 ∈ [0, 1]
BeliefState = np.ndarray  # shape (108,)

# belief 置信度阈值（低于此值视为"NN 异常/不可用"）
BELIEF_CONFIDENCE_THRESHOLD = 0.5

# 各状态的概率分配索引（与 ETL ground_truth 一致）
STATE_MY_HAND = 0
STATE_PLAYED = 1
STATE_REST = 2


# === 核心接口（草案） ===

def heuristic_belief_bomb_risk(
    action_cards: List[str],
    belief_state: Optional[BeliefState],
    rest_distribution: Optional[Dict[str, float]] = None,
) -> float:
    """给定 action 候选 + NN 信念状态，返回"炸后对手仍能压我"的风险分。

    Args:
        action_cards: 候选动作的 V8 字符串牌列表（如 ['HA', 'HK', 'HQ', 'HJ', 'HT']）
        belief_state: NN 输出的 108 槽位概率分布 shape (108,)，
                       None 或置信度不足时回退到 rest_distribution
        rest_distribution: 降级路径——rest_distribution[rank_str] = 0.0~1.0
                          （基于 MemoryTracker.card_state 确定性概率）

    Returns:
        float ∈ [-1.0, +1.0]：
          +1.0 = 高风险（对手极可能有反制炸弹）
          -1.0 = 低风险（对手几乎无反制炸弹）
          0.0 = 中性或不可判断

    草案算法（DRAFT · 等价性 pytest 锁行为）：
      1. 遍历 action_cards 各 rank，找出"可能被对手压制的 rank"
      2. 用 belief_state[rest_slot_idx] 累加对手有反制牌的概率
      3. 阈值化：prob > 0.5 → risk += 1；prob > 0.8 → risk += 2
      4. 归一化到 [-1, +1]
      5. 降级路径：belief_state=None 或 L2 norm < BELIEF_CONFIDENCE_THRESHOLD →
         用 rest_distribution 替代

    降级保证（等价性 pytest 锁）：
      - belief_state 不可用时输出必须等于基于 rest_distribution 的结果
      - 降级路径必须返回 0.0 ~ 1.0 之间的"安全中位值"或与 deterministic 等价
    """
    if not action_cards:
        return 0.0  # 无候选动作

    # === 降级路径：belief_state 不可用 ===
    if belief_state is None or _is_belief_low_confidence(belief_state):
        logger.debug("降级到 rest_distribution 路径")
        return _fallback_bomb_risk(action_cards, rest_distribution)

    # === 主路径：基于 belief_state ===
    # 草案伪代码（等价性 pytest 已锁住输出格式；具体打分权重可 Phase 2 调）
    risk = 0.0
    for card in action_cards:
        # 简化：每个 action 牌的 rank → 检查对手是否可能有反制
        rank = _card_rank(card)
        opponent_suppress_prob = _opponent_suppress_probability(rank, belief_state)
        if opponent_suppress_prob > 0.8:
            risk += 2.0
        elif opponent_suppress_prob > 0.5:
            risk += 1.0

    # 归一化
    norm = risk / max(len(action_cards) * 2.0, 1.0)
    return float(np.clip(norm * 2.0 - 1.0, -1.0, 1.0))


# === 辅助函数 ===

def _is_belief_low_confidence(belief_state: BeliefState) -> bool:
    """检测 belief_state 是否置信度不足（NN 异常/未就绪）。"""
    if belief_state.shape != (108,):
        return True
    # L2 norm 太低 → 退化为均匀分布（无信息）
    norm = float(np.linalg.norm(belief_state))
    if norm < BELIEF_CONFIDENCE_THRESHOLD:
        return True
    # 包含 NaN/Inf → 不可用
    if not np.all(np.isfinite(belief_state)):
        return True
    return False


def _card_rank(card: str) -> str:
    """从 V8 字符串牌提取 rank（如 'HA' → 'A'）。"""
    if len(card) == 2:
        return card[1]
    elif card in ("SB", "HR"):
        return card
    return card[-1]


def _opponent_suppress_probability(rank: str, belief_state: BeliefState) -> float:
    """根据 belief_state 推断"对手仍有反制 rank 的概率"。

    简化版：检查所有 > rank 的 rank 是否在 belief 的 REST 状态。
    """
    # 真实实现需要 rank 字典比较；这里用 stub：返回平均 REST 概率
    rest_mask = belief_state[54:108]  # 第 2 副本（简化：只查副本 1）
    return float(rest_mask.mean())


def _fallback_bomb_risk(
    action_cards: List[str],
    rest_distribution: Optional[Dict[str, float]],
) -> float:
    """降级路径：基于 MemoryTracker 确定性概率。

    rest_distribution 来自 rule_card_counter.get_bomb_stats() 等接口。
    """
    if rest_distribution is None:
        # 无任何信息 → 返回 0.0 中性值
        return 0.0
    risk = 0.0
    for card in action_cards:
        rank = _card_rank(card)
        if rank in rest_distribution:
            p = rest_distribution[rank]
            if p > 0.8:
                risk += 2.0
            elif p > 0.5:
                risk += 1.0
    norm = risk / max(len(action_cards) * 2.0, 1.0)
    return float(np.clip(norm * 2.0 - 1.0, -1.0, 1.0))