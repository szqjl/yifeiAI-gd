# -*- coding: utf-8 -*-
"""
V7 静态特征工程 — state_牌态 124 维

维度分段（STATIC_STATE_DIM = 124）：
  0–107:   手牌 one-hot（54 类 × 2 副 = 108 维）
            对每种牌型用 2 维表示数量：0 张=[0,0], 1 张=[1,0], 2 张=[1,1]
  108–116: 级牌/红心配 9 维
            [108] curRank 归一化 (0~1)
            [109] selfRank 归一化
            [110] oppoRank 归一化
            [111] 红心配标志（持有 H+curRank）
            [112] Joker 标志（持有 RJ/BJ）
            [113-116] curRank 各花色计数归一化 [S,H,D,C]
  117–122: 主动被动/阶段/炸弹/贡局/队友 6 维
            [117] 主动/被动标志（本方或队友 curPos）
            [118-120] 游戏阶段 one-hot：[贡牌, 出牌, 结束]
            [121] curBombNum 归一化
            [122] 贡局标志（tributeResult 存在）
  123:     handCards 计数 1 维（归一化至 0~27 张）

注：actionList 牌型 one-hot 15 维不计入本模块，后移到 GUA-037b 拼接层。
"""

import numpy as np
from typing import Dict, List, Any

# ── 常量 ──────────────────────────────────────────────
STATIC_STATE_DIM = 124

# 54 种牌型定义（52 花色牌 + 2 王）
SUITS = ["S", "H", "D", "C"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
JOKERS = ["BJ", "RJ"]

CARD_TYPES: List[str] = []
for rank in RANKS:
    for suit in SUITS:
        CARD_TYPES.append(f"{suit}{rank}")
CARD_TYPES.extend(JOKERS)  # 54 种

RANK_VALUE_MAP: Dict[str, int] = {r: i for i, r in enumerate(RANKS)}  # 0-12
MAX_HAND_SIZE = 27  # 每人 27 张


# ── 编码函数 ──────────────────────────────────────────

def encode_hand_cards_108(hand_cards: List[str]) -> List[float]:
    """
    手牌 108 维 one-hot 编码。

    对 54 种牌型，每种用 2 维表示持有数量：
      [0, 0] = 0 张
      [1, 0] = 1 张
      [1, 1] = 2 张
    """
    counts = {ct: 0 for ct in CARD_TYPES}
    for card in hand_cards:
        if card in counts:
            counts[card] += 1

    features: List[float] = []
    for ct in CARD_TYPES:
        c = counts[ct]
        features.append(1.0 if c >= 1 else 0.0)
        features.append(1.0 if c >= 2 else 0.0)
    return features


def encode_rank_value(rank_str: str) -> float:
    """将等级字符串（2~A）映射为 [0, 1] 归一化值。"""
    if rank_str in RANK_VALUE_MAP:
        return RANK_VALUE_MAP[rank_str] / (len(RANKS) - 1)
    return 0.0


def has_heart_cur_rank(hand_cards: List[str], cur_rank: str) -> float:
    """是否持有红心配（万能牌）: H + curRank。"""
    return 1.0 if f"H{cur_rank}" in hand_cards else 0.0


def has_joker(hand_cards: List[str]) -> float:
    """是否持有王（BJ 或 RJ）。"""
    for card in hand_cards:
        if card in JOKERS:
            return 1.0
    return 0.0


def encode_rank_suit_counts(hand_cards: List[str], cur_rank: str) -> List[float]:
    """
    curRank 在各花色的持有计数（4 维），归一化至 [0, 1]。
    每花色最多 2 张，除以 2.0 归一化。
    """
    counts = {s: 0 for s in SUITS}
    for card in hand_cards:
        if len(card) >= 2 and card[0] in SUITS and card[1:] == cur_rank:
            counts[card[0]] += 1
    return [min(c / 2.0, 1.0) for c in counts.values()]


def _detect_game_phase(game_state: Dict[str, Any]) -> str:
    """
    检测游戏阶段。

    Returns:
        "tribute" — 贡牌阶段（tributeResult 存在）
        "play"    — 出牌阶段（默认）
        "end"     — 结束阶段（无 actionList 或 handCards 为空）
    """
    if game_state.get("tributeResult"):
        return "tribute"
    hand_cards = game_state.get("handCards", [])
    action_list = game_state.get("actionList", [])
    cur_pos = game_state.get("curPos", -1)
    if not hand_cards and cur_pos < 0:
        return "end"
    return "play"


# ── 主入口 ────────────────────────────────────────────

def extract_static_features(game_state: Dict[str, Any]) -> np.ndarray:
    """
    从游戏状态提取 124 维静态特征向量。

    Args:
        game_state: 游戏状态字典，包含以下 key：
            - handCards: List[str]
            - myPos / curPos: int
            - curRank / selfRank / oppoRank: str
            - curBombNum: int（可选）
            - tributeResult: Any（可选，存在即表示贡牌阶段）

    Returns:
        shape=(124,) 的 float32 numpy 数组。
    """
    features = [0.0] * STATIC_STATE_DIM

    # ── 0-107: 手牌 one-hot 108 维 ──
    hand_cards: List[str] = game_state.get("handCards", [])
    if not isinstance(hand_cards, list):
        hand_cards = []
    hand_108 = encode_hand_cards_108(hand_cards)
    for i, v in enumerate(hand_108):
        features[i] = v

    # ── 108-116: 级牌/红心配 9 维 ──
    cur_rank = game_state.get("curRank", "2")
    self_rank = game_state.get("selfRank", "2")
    oppo_rank = game_state.get("oppoRank", "2")

    features[108] = encode_rank_value(cur_rank)
    features[109] = encode_rank_value(self_rank)
    features[110] = encode_rank_value(oppo_rank)
    features[111] = has_heart_cur_rank(hand_cards, cur_rank)
    features[112] = has_joker(hand_cards)

    rank_suit = encode_rank_suit_counts(hand_cards, cur_rank)
    for i, v in enumerate(rank_suit):
        features[113 + i] = v

    # ── 117-122: 主动被动/阶段/炸弹/贡局 6 维 ──
    my_pos = game_state.get("myPos", 0)
    cur_pos = game_state.get("curPos", -1)
    partner_pos = (my_pos + 2) % 4

    # 117: 主动/被动标志（轮到本方或队友出牌）
    features[117] = 1.0 if (cur_pos == my_pos or cur_pos == partner_pos) else 0.0

    # 118-120: 游戏阶段 one-hot
    phase = _detect_game_phase(game_state)
    if phase == "tribute":
        features[118] = 1.0
    elif phase == "play":
        features[119] = 1.0
    else:
        features[120] = 1.0

    # 121: curBombNum（归一化，上限 10）
    features[121] = min(game_state.get("curBombNum", 0) / 10.0, 1.0)

    # 122: 贡局标志
    features[122] = 1.0 if game_state.get("tributeResult") else 0.0

    # ── 123: handCards 计数 1 维（归一化，上限 27 张） ──
    features[123] = min(len(hand_cards) / MAX_HAND_SIZE, 1.0)

    return np.array(features, dtype=np.float32)