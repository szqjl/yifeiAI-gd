# -*- coding: utf-8 -*-
"""
GUA-051 稠密 Reward 信号 — 9 种中间 reward。

背景：纯输赢 reward（+1/-1 或 +2/-1）在长序列掼蛋对局中过于稀疏，
信用分配困难（套路文档 §4）。本模块在每步决策后附加中间 reward，
使模型能更快收敛。

Reward 清单（GUA-051）：
  1. play_success    +0.05   出牌成功（非 PASS 动作执行）
  2. wind_catch      +0.10   接风（greaterPos 从对方转到本方/队友）
  3. guan_dan        +0.30   掼蛋标记（出牌后手牌 ≤ 6 张）
  4. level_control   +0.20   级牌控制（击败对手级牌/保持级牌优势）
  5. coordination    +0.10   配合（队友出牌后本方顺势跟同牌型）
  6. feed_partner    +0.15   送对家（队友剩 ≤3 张时喂牌）
  7. bomb            ±0.50   炸弹使用（_is_good_bomb：正向；_is_waste：负向）
  8. self_upgrade    +2.00   本方升级（notify episodeOver 本方升）
  9. opponent_upgrade -1.00   对方升级（notify episodeOver 对方升）
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("reward")

# ── Reward 常量 ────────────────────────────────────────

PLAY_SUCCESS_REWARD = 0.05
WIND_CATCH_REWARD = 0.10
GUAN_DAN_REWARD = 0.30
LEVEL_CONTROL_REWARD = 0.20
COORDINATION_REWARD = 0.10
FEED_PARTNER_REWARD = 0.15
GOOD_BOMB_REWARD = 0.50
WASTE_BOMB_REWARD = -0.50
SELF_UPGRADE_REWARD = 2.00
OPPONENT_UPGRADE_REWARD = -1.00

# ── 单步 reward ────────────────────────────────────────


def compute_step_reward(
    *,
    action: List[Any] | None = None,
    action_list: List[List[Any]] | None = None,
    hand_cards: List[str] | None = None,
    hand_count: int = 27,
    my_pos: int = 0,
    cur_pos: int = -1,
    greater_pos: int = -1,
    prev_greater_pos: int = -1,
    numofs: Dict[str, int] | None = None,
    cur_bomb_num: int = 0,
    bomb_used: bool = False,
    stage: str = "",
    cur_rank: str = "",
    self_rank: str = "",
    oppo_rank: str = "",
    guandan_state: bool = False,
) -> Dict[str, float]:
    """计算单步稠密 reward。

    所有参数可选（默认 0），调用方只需传入有值的字段。

    Returns:
        {"play_success": float, "wind_catch": float, ..., "total": float}
    """
    rewards: Dict[str, float] = {}
    action = action or []
    action_list = action_list or []
    hand_cards = hand_cards or []
    numofs = numofs or {}
    is_pass = (not action) or (isinstance(action, list) and len(action) > 0 and action[0] == "PASS")
    is_play_stage = stage in (None, "", "play")

    # 1. 出牌成功
    if not is_pass and is_play_stage:
        rewards["play_success"] = PLAY_SUCCESS_REWARD
    else:
        rewards["play_success"] = 0.0

    # 2. 接风
    if (not is_pass and is_play_stage and
            prev_greater_pos != -1 and
            greater_pos != -1 and
            prev_greater_pos != greater_pos):
        prev_team = prev_greater_pos % 2
        cur_team = greater_pos % 2
        if prev_team != my_pos % 2 and cur_team == my_pos % 2:
            rewards["wind_catch"] = WIND_CATCH_REWARD
        else:
            rewards["wind_catch"] = 0.0
    else:
        rewards["wind_catch"] = 0.0

    # 3. 掼蛋标记（手牌 ≤ 6）
    if hand_count <= 6 and not is_pass:
        rewards["guan_dan"] = GUAN_DAN_REWARD
    else:
        rewards["guan_dan"] = 0.0

    # 4. 级牌控制
    level_reward = 0.0
    if not is_pass and is_play_stage and cur_rank:
        if _is_level_card(action, cur_rank):
            level_reward = LEVEL_CONTROL_REWARD * 0.5
        # 保持级牌优势
        if self_rank and oppo_rank:
            sr = _rank_to_num(self_rank)
            op = _rank_to_num(oppo_rank)
            if sr > op:
                level_reward += LEVEL_CONTROL_REWARD * 0.5
    rewards["level_control"] = level_reward

    # 5. 配合（跟队友同牌型）
    if (not is_pass and is_play_stage and
            cur_pos != my_pos and
            prev_greater_pos != -1 and
            prev_greater_pos % 2 == my_pos % 2):
        rewards["coordination"] = COORDINATION_REWARD
    else:
        rewards["coordination"] = 0.0

    # 6. 送对家
    partner_rest = numofs.get("numoffri", 27)
    if (not is_pass and is_play_stage and
            partner_rest <= 3 and
            prev_greater_pos != -1 and
            prev_greater_pos % 2 == my_pos % 2):
        rewards["feed_partner"] = FEED_PARTNER_REWARD
    else:
        rewards["feed_partner"] = 0.0

    # 7. 炸弹
    if bomb_used and not is_pass:
        if _is_good_bomb(hand_cards, action, cur_bomb_num, hand_count):
            rewards["bomb"] = GOOD_BOMB_REWARD
        else:
            rewards["bomb"] = WASTE_BOMB_REWARD
    else:
        rewards["bomb"] = 0.0

    # 8. 本方升级 / 对方升级（外部传入 episode 结束信号）
    rewards["self_upgrade"] = 0.0
    rewards["opponent_upgrade"] = 0.0

    rewards["total"] = sum(rewards.values())
    return rewards


def compute_episode_reward(
    self_upgraded: bool = False,
    opponent_upgraded: bool = False,
) -> Dict[str, float]:
    """计算 episode（副）结束时的升/降级 reward。

    Returns:
        {"self_upgrade": float, "opponent_upgrade": float, "total": float}
    """
    rewards: Dict[str, float] = {
        "self_upgrade": SELF_UPGRADE_REWARD if self_upgraded else 0.0,
        "opponent_upgrade": OPPONENT_UPGRADE_REWARD if opponent_upgraded else 0.0,
    }
    rewards["total"] = sum(rewards.values())
    return rewards


# ── 辅助函数 ────────────────────────────────────────────


def _is_level_card(action: List[Any], cur_rank: str) -> bool:
    """判断出牌是否包含级牌。"""
    if len(action) < 3:
        return False
    cards = action[2] if isinstance(action[2], list) else []
    target = f"{cur_rank.upper()}"
    for c in cards:
        if isinstance(c, str) and c[1:] == target:
            return True
        if isinstance(c, str) and c == target:
            return True
    return False


def _is_good_bomb(
    hand_cards: List[str],
    action: List[Any],
    cur_bomb_num: int,
    hand_count: int,
) -> bool:
    """判断炸弹使用是否合理。

    正向场景：手牌 ≤ 10 且炸弹后一手可清完。
    负向场景：炸队友、炸无意义、有更小压制却用炸弹。
    """
    if not action or len(action) < 1:
        return False
    action_type = action[0] if isinstance(action[0], str) else ""
    if action_type not in ("Bomb", "StraightFlush"):
        return False

    if hand_count <= 10 and cur_bomb_num <= 2:
        return True
    return False


def _rank_to_num(rank: str) -> int:
    """级牌字符串转数值（2=2, 3=3, ..., 10=10, J=11, Q=12, K=13, A=14）。"""
    rank_map = {
        "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
        "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
    }
    return rank_map.get(rank.upper(), 0)


# ── Reward 累加器（用于整个 episode 或 batch）─────────────


class RewardAccumulator:
    """累加 episode/副 内的稠密 reward。

    用法：
        acc = RewardAccumulator()
        acc.add_step_reward(...)
        acc.add_step_reward(...)
        episode_extra = compute_episode_reward(self_upgraded=True)
        acc.add_episode_reward(episode_extra)
        total = acc.total
    """

    def __init__(self):
        self._step_rewards: List[Dict[str, float]] = []
        self._episode_rewards: List[Dict[str, float]] = []

    def add_step_reward(self, reward_dict: Dict[str, float]) -> None:
        self._step_rewards.append(reward_dict)

    def add_episode_reward(self, reward_dict: Dict[str, float]) -> None:
        self._episode_rewards.append(reward_dict)

    @property
    def total(self) -> float:
        return sum(r["total"] for r in self._step_rewards) + \
               sum(r["total"] for r in self._episode_rewards)

    @property
    def breakdown(self) -> Dict[str, float]:
        keys = ["play_success", "wind_catch", "guan_dan", "level_control",
                "coordination", "feed_partner", "bomb",
                "self_upgrade", "opponent_upgrade"]
        totals = {k: 0.0 for k in keys}
        for r in self._step_rewards + self._episode_rewards:
            for k in keys:
                totals[k] += r.get(k, 0.0)
        totals["total"] = sum(totals.values())
        return totals

    def reset(self) -> None:
        self._step_rewards.clear()
        self._episode_rewards.clear()
