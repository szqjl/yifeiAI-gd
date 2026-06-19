# -*- coding: utf-8 -*-
"""
V7 局面信念状态分类器 — 套路一原型（GUA-037a 扩展）

输出：4 维局面类型 soft 向量：
  [进攻型, 防守型, 观望型, 保对家型]

用法嵌入：
  - _extract_features() 在 188-191 索引位写入本模块输出
  - 不依赖 torch，纯 numpy 启发式分类
  - 后续可替换为学习型分类器

局面类型定义：
  0 - 进攻型 (aggressive):   手牌强，该冲
  1 - 防守型 (defensive):    手牌弱，该送对家
  2 - 观望型 (waiting):      局势不明，等信号
  3 - 保对家型 (protect):    对家快走完，我掩护
"""

import numpy as np
from typing import Dict, List, Any, Optional

# ── 常量 ──
SITUATION_DIM = 4

SITUATION_AGGRESSIVE = 0  # 进攻型
SITUATION_DEFENSIVE  = 1  # 防守型
SITUATION_WAITING    = 2  # 观望型
SITUATION_PROTECT    = 3  # 保对家型

SITUATION_NAMES = ["aggressive", "defensive", "waiting", "protect"]

# 54 种牌型
SUITS = ["S", "H", "D", "C"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
JOKERS = ["SB", "HR"]  # 平台原生王编码：SB=小王, HR=大王
HIGH_RANKS = {"A", "K", "Q", "J"}  # 高牌判定


def _count_bombs(hand_cards: List[str]) -> int:
    """统计手牌中炸弹数（4 张同点数 + 王炸）。"""
    rank_counts = {r: 0 for r in RANKS}
    joker_count = 0
    for card in hand_cards:
        if card in JOKERS:
            joker_count += 1
        elif len(card) >= 2:
            rank = card[1:]
            if rank in rank_counts:
                rank_counts[rank] += 1
    bomb_count = sum(1 for c in rank_counts.values() if c >= 4)
    if joker_count >= 2:
        bomb_count += 1
    return bomb_count


def _count_high_cards(hand_cards: List[str]) -> int:
    """统计高牌（A/K/Q/J）数量。"""
    count = 0
    for card in hand_cards:
        if len(card) >= 2 and card[1:] in HIGH_RANKS:
            count += 1
    return count


def _count_jokers(hand_cards: List[str]) -> int:
    """统计王数量。"""
    return sum(1 for c in hand_cards if c in JOKERS)


def _estimate_my_strength(hand_cards: List[str], cur_rank: str) -> float:
    """
    估计自己的牌力 0~1。
    基于炸弹数 + 高牌数 + 王 + 级牌持有 + handCard 数量。
    """
    if not hand_cards:
        return 0.0
    bomb_score = min(_count_bombs(hand_cards) / 3.0, 1.0) * 0.30
    high_score = min(_count_high_cards(hand_cards) / 8.0, 1.0) * 0.20
    joker_score = min(_count_jokers(hand_cards) / 2.0, 1.0) * 0.15
    # 持有红心级牌加分
    trump_score = 0.15 if f"H{cur_rank}" in hand_cards else 0.0
    # 手牌少（接近走完）加分
    hand_count = len(hand_cards)
    cards_left_score = max(0.0, 1.0 - hand_count / 27.0) * 0.20
    return min(bomb_score + high_score + joker_score + trump_score + cards_left_score, 1.0)


def _get_partner_card_count(game_state: Dict[str, Any]) -> Optional[int]:
    """从 history 最后一步获取队友剩余牌数。"""
    history = game_state.get("history", [])
    if not history:
        return None
    my_pos = game_state.get("myPos", 0)
    partner_pos = (my_pos + 2) % 4
    # 从最近的 history 条目中获取 numofplayers
    for h in reversed(history):
        numofplayers = h.get("numofplayers")
        if isinstance(numofplayers, (list, tuple)) and len(numofplayers) >= 4:
            return numofplayers[partner_pos]
    return None


def _get_opponent_min_card_count(game_state: Dict[str, Any]) -> Optional[int]:
    """从 history 获取对手（两家）的最小剩余牌数（压迫感指标）。"""
    history = game_state.get("history", [])
    if not history:
        return None
    my_pos = game_state.get("myPos", 0)
    opp1 = (my_pos + 1) % 4
    opp2 = (my_pos + 3) % 4
    for h in reversed(history):
        numofplayers = h.get("numofplayers")
        if isinstance(numofplayers, (list, tuple)) and len(numofplayers) >= 4:
            return min(numofplayers[opp1], numofplayers[opp2])
    return None


def _estimate_partner_strength(partner_cards: Optional[int]) -> float:
    """
    估计对家牌力 0~1。
    按剩余牌数反推（越少越接近走完 = 越强）。
    """
    if partner_cards is None:
        return 0.5  # 未知则中性
    return max(0.0, 1.0 - partner_cards / 27.0)


def _estimate_opponent_pressure(
    opponent_min_cards: Optional[int],
    oppo_rank: str,
    self_rank: str,
) -> float:
    """
    估计对手压迫感 0~1。
    对手剩余牌越少 + 对手级牌领先于我 → 压迫感高。
    """
    score = 0.0
    if opponent_min_cards is not None:
        # 对手牌少 → 快走完 → 压迫
        score += max(0.0, 1.0 - opponent_min_cards / 27.0) * 0.6
    # 级牌对比
    rank_order = {r: i for i, r in enumerate(RANKS)}
    oppo_idx = rank_order.get(oppo_rank, 6)
    self_idx = rank_order.get(self_rank, 6)
    if oppo_idx > self_idx:
        score += 0.4  # 对手级牌领先
    elif oppo_idx < self_idx:
        score -= 0.1  # 我级牌领先
    return float(np.clip(score, 0.0, 1.0))


def extract_situation_vector(game_state: Dict[str, Any]) -> np.ndarray:
    """
    提取 4 维局面类型 soft 向量。

    Args:
        game_state: 游戏状态字典

    Returns:
        shape=(4,) float32 数组，和为 1.0（soft 分类）
    """
    hand_cards = game_state.get("handCards", [])
    if not isinstance(hand_cards, list):
        hand_cards = []
    cur_rank = str(game_state.get("curRank", "2"))
    my_pos = game_state.get("myPos", 0)
    self_rank = str(game_state.get("selfRank", "2"))
    oppo_rank = str(game_state.get("oppoRank", "2"))

    my_strength = _estimate_my_strength(hand_cards, cur_rank)
    partner_cards = _get_partner_card_count(game_state)
    partner_strength = _estimate_partner_strength(partner_cards)
    opponent_min = _get_opponent_min_card_count(game_state)
    opponent_pressure = _estimate_opponent_pressure(opponent_min, oppo_rank, self_rank)

    hand_count = len(hand_cards)
    bomb_count = _count_bombs(hand_cards)

    scores = [0.0, 0.0, 0.0, 0.0]

    # ── 保对家型 (protect) ──
    # 对家牌很少（<=8）→ 该掩护
    if partner_cards is not None and partner_cards <= 8:
        scores[SITUATION_PROTECT] = max(0.2, 1.0 - partner_cards / 8.0 * 0.5)
    elif partner_cards is not None and partner_cards <= 12:
        scores[SITUATION_PROTECT] = 0.3

    # ── 进攻型 (aggressive) ──
    # 牌力强 + 炸弹多 + 手牌少 + 非保对家场景
    if my_strength > 0.6 and scores[SITUATION_PROTECT] < 0.5:
        base = my_strength
        # 手牌少（快走完）加成
        if hand_count <= 10:
            base += 0.2
        # 有炸弹加成
        if bomb_count >= 2:
            base += 0.1
        scores[SITUATION_AGGRESSIVE] = min(base, 1.0)

    # ── 防守型 (defensive) ──
    # 牌力弱 + 对手压迫感强 + 我方级牌落后
    if my_strength < 0.35:
        base = (1.0 - my_strength) * 0.6
        # 对手压迫加成
        if opponent_pressure > 0.5:
            base += 0.2
        # 手牌多（防守态）
        if hand_count > 18:
            base += 0.1
        scores[SITUATION_DEFENSIVE] = min(base, 1.0)
    elif opponent_pressure > 0.7 and my_strength < 0.5:
        # 对手压迫极强时，即使中等牌力也偏防守
        scores[SITUATION_DEFENSIVE] = opponent_pressure * 0.5

    # ── 观望型 (waiting) ──
    # 默认：不属于以上三者 → 观望
    # 计算观望分 = 1 - max(其他)
    max_other = max(scores[SITUATION_AGGRESSIVE],
                    scores[SITUATION_DEFENSIVE],
                    scores[SITUATION_PROTECT])
    scores[SITUATION_WAITING] = max(0.0, 1.0 - max_other)

    # ── Softmax 归一化 ──
    arr = np.array(scores, dtype=np.float64)
    # 使用温度 1.0 的 softmax
    exp_scores = np.exp(arr - np.max(arr))
    result = exp_scores / exp_scores.sum()

    return result.astype(np.float32)
