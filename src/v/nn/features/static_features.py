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

GUA-050（v7-re-eval-2026-06.md §2.2）：局面信念向量 8 维，在引擎 512 中放置于 dynamic 之后（188–195）。
STATIC_STATE_DIM 保持 124（不扩）；belief 由 extract_state_belief() 独立返回，引擎拼接。
"""

import numpy as np
from typing import Dict, List, Any

# ── 常量 ──────────────────────────────────────────────
STATIC_STATE_DIM = 124
BELIEF_DIM = 8          # GUA-050: 局面信念向量

# 54 种牌型定义（52 花色牌 + 2 王）
SUITS = ["S", "H", "D", "C"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
JOKERS = ["SB", "HR"]  # 平台原生王编码：SB=小王, HR=大王

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


# ── GUA-050: 局面信念向量 8 维 ───────────────────────

def extract_state_belief(game_state: Dict[str, Any]) -> List[float]:
    """
    从游戏状态提取 8 维局面信念向量（GUA-050）。

    Belief 维度（v7-re-eval-2026-06.md §2.2）：
      0: my_strength         — 自己牌力 0~1（基于手牌炸弹/王/级牌估算）
      1: partner_strength    — 对家牌力 0~1（基于对家剩牌推断）
      2: opponent_pressure   — 对手压迫程度 0~1（对手剩牌少/我方劣势）
      3: level_progress      — 级牌进度（selfRank - oppoRank，归一化至 -5~5→0~1）
      4: trump_ready         — 是否有级牌/王/炸弹（0/1）
      5: bomb_count          — 我方剩余炸弹数（归一化至 0~1）
      6: opponent_bomb_risk  — 推断对手有炸弹的概率（0~1）
      7: last_card_meaning   — 上家出牌信号（0=无关/1=压力/0.5=常规）

    Args:
        game_state: 游戏状态字典

    Returns:
        8 维 float list
    """
    hand_cards: List[str] = game_state.get("handCards", [])
    cur_rank = game_state.get("curRank", "2")
    self_rank = game_state.get("selfRank", "2")
    oppo_rank = game_state.get("oppoRank", "2")
    cur_bomb_num = game_state.get("curBombNum", 0)
    public_info = game_state.get("publicInfo", {})
    my_pos = game_state.get("myPos", 0)

    # 0: my_strength — 炸弹/王/级牌密度
    num_bombs = sum(1 for card in hand_cards if hand_cards.count(card) >= 4)
    has_joker_flag = any(c in JOKERS for c in hand_cards)
    has_trump = has_heart_cur_rank(hand_cards, cur_rank)
    my_strength = min((num_bombs * 0.2 + has_joker_flag * 0.3 + has_trump * 0.1), 1.0)

    # 1: partner_strength — 对家剩牌越少越强
    partner_pos = (my_pos + 2) % 4
    partner_rest = public_info.get(str(partner_pos), {}).get("rest", 27)
    partner_strength = 1.0 - min(partner_rest / 27.0, 1.0)

    # 2: opponent_pressure — 对手剩牌少/我方落后
    oppo1_rest = public_info.get(str((my_pos + 1) % 4), {}).get("rest", 27)
    oppo2_rest = public_info.get(str((my_pos + 3) % 4), {}).get("rest", 27)
    min_oppo_rest = min(oppo1_rest, oppo2_rest)
    self_rank_val = RANK_VALUE_MAP.get(self_rank, 0)
    oppo_rank_val = RANK_VALUE_MAP.get(oppo_rank, 0)
    rank_gap = self_rank_val - oppo_rank_val
    opponent_pressure = min((1.0 - min_oppo_rest / 27.0) * 0.6 + max(-rank_gap / 13.0, 0) * 0.4, 1.0)

    # 3: level_progress — 级牌进度（-5~5 → 0~1）
    norm_gap = (self_rank_val - oppo_rank_val + 5) / 10.0
    level_progress = max(0.0, min(norm_gap, 1.0))

    # 4: trump_ready — 有级牌或王
    trump_ready = 1.0 if (has_trump > 0 or has_joker_flag) else 0.0

    # 5: bomb_count — 我方炸弹数归一化
    bomb_count = min(cur_bomb_num / 10.0, 1.0)

    # 6: opponent_bomb_risk — 对手未出炸弹+进度推测
    bombs_played = public_info.get("bombsPlayed", 0)
    total_bombs = 8  # 假设全桌最多 8 炸
    remaining_bombs = max(total_bombs - bombs_played - cur_bomb_num, 0)
    game_progress = 1.0 - min(partner_rest / 27.0, 1.0)
    opponent_bomb_risk = min(remaining_bombs / total_bombs * game_progress * 1.5, 1.0)

    # 7: last_card_meaning — 上家出牌信号
    last_action = game_state.get("curAction", [])
    if not last_action or last_action == ["PASS"]:
        last_card_meaning = 0.0
    else:
        action_type = last_action[0] if isinstance(last_action, list) else "UNKNOWN"
        strong_types = {"Bomb", "Rocket", "Straight", "ThreePair", "TwoTrips"}
        last_card_meaning = 0.5 if action_type in strong_types else 0.25

    return [
        my_strength,
        partner_strength,
        opponent_pressure,
        level_progress,
        trump_ready,
        bomb_count,
        opponent_bomb_risk,
        last_card_meaning,
    ]


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