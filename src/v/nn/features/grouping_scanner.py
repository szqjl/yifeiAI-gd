# -*- coding: utf-8 -*-
"""
V7 组牌质量中间表示 — grouping_scanner 9 维（GUA-054，2026-06-17 实施）

设计原则（v4 教训 + 6 大组牌核心原则）：
  1. **9 维独立软信号**：每维 0~1 归一化连续值，**不引入 if-else 硬规则**，
     不预设权重（v4 教训：6 因素权重 25+20+20+15+10+10 静态权重撞 lalala SOTA 上限）
  2. **§7.4 升格硬约束**：V7-internal 实现，禁止 `from src.m.m3 import ...` 任何形式
  3. **纯函数式**：输入 hand_cards + curRank，输出 9 维 list，推理延迟 < 1ms
  4. **连续可微**：每维都是连续值，让 V7 NN 自己学权重

9 维特征（v4 经验 + 6 大组牌原则）：

  0: bomb_count        炸弹结构数 / 上限 → "炸弹平衡"原则（v4 经验：m 数阈值）
  1: sequence_count    顺子/连对/钢板候选数 / 上限 → "牌型连贯"原则
  2: triple_count      三张结构数 / 上限 → "牌型连贯"原则
  3: pair_count        对子结构数 / 上限 → "牌型连贯"原则
  4: single_count      散牌数（去单化原则反向） / 上限 → "去单化"原则
  5: longest_run       最长连续 rank 数 / 12 → "牌型连贯"原则
  6: wild_flexibility  逢人配数 / 2 → "逢人配留变化"原则（v4 经验：留变化）
  7: round_efficiency  1 - single_count（出牌轮次效率） → "减少轮次"原则
  8: hand_strength     高级牌(BJ+RJ+级牌)数 / 6 → "小火大轮次"原则（牌力基础）

GUA-054 实施前 v4 教训（V7-实施方案.md / 掼蛋AI客户端架构方案.md §3.3.6）：
  - v4 ActionSpaceOptimizer 用启发式 Top-K 解决 5000+ 动作空间，但因
    Top-K 后精细评估仍是规则而撞 lalala SOTA 上限
  - 本模块**不**做硬规则加权，**只**输出 9 维独立软信号供 V7 NN 拼接
"""

from __future__ import annotations

from typing import Dict, List, Any
from collections import Counter

# ── 常量 ──────────────────────────────────────────────
GROUPING_SCORE_DIM = 9
SUITS = ("S", "H", "D", "C")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")
JOKERS = ("BJ", "RJ")
ALL_RANKS = RANKS + JOKERS  # 15 种 rank
HAND_SIZE_LIMIT = 27  # 每人最多 27 张

# 各维度归一化上限（基于 27 张手牌结构密度的经验值）
NORM_BOMB_MAX = 4.0         # 4 个炸弹 → 1.0
NORM_SEQUENCE_MAX = 3.0     # 3 个顺子/连对/钢板 → 1.0
NORM_TRIPLE_MAX = 3.0       # 3 个三张 → 1.0
NORM_PAIR_MAX = 4.0         # 4 个对子 → 1.0
NORM_SINGLE_MAX = 9.0       # 9 张散牌 → 1.0（27 张牌理论散牌最多 27）
NORM_LONGEST_RUN_MAX = 12.0 # A=12 是最长可能
NORM_WILD_MAX = 2.0         # 逢人配最多 2 张
NORM_HIGH_MAX = 6.0         # 高级牌 6 张（2 王 + 4 张级牌）


# ── 牌面解析辅助 ──────────────────────────────────────

def _parse_rank(card: str) -> str:
    """从 'S2' / 'BJ' 提取 rank。"""
    if card in JOKERS:
        return card
    if len(card) >= 2 and card[0] in SUITS:
        return card[1:]
    return card


def _parse_suit(card: str) -> str:
    """从 'S2' 提取花色。"""
    if len(card) >= 2 and card[0] in SUITS:
        return card[0]
    return ""


def _is_wild(card: str, cur_rank: str) -> bool:
    """判断是否为逢人配（H+curRank）。"""
    return card == f"H{cur_rank}"


# ── 结构计数辅助 ──────────────────────────────────────

def _count_bombs(hand_cards: List[str], cur_rank: str) -> int:
    """
    统计炸弹结构数（4+ 同 rank 不含逢人配）。
    4 张同 rank = 1 炸；5 张同 rank = 2 炸（含 4 炸 + 1 单）；6 张 = 3 炸...；
    简化：4 张以上同 rank 每多 1 张多 1 炸。
    """
    rank_counts = Counter(_parse_rank(c) for c in hand_cards if not _is_wild(c, cur_rank))
    bombs = 0
    for rank, cnt in rank_counts.items():
        if cnt >= 4:
            bombs += cnt - 3  # 4 张 = 1 炸，5 张 = 2 炸...
    return bombs


def _count_sequences(hand_cards: List[str], cur_rank: str) -> int:
    """
    统计顺子/连对/钢板候选数。
    简化：连续 5+ 不同花不同 rank → 1 顺子。
    3 连对 → 1 连对（3 个对子）。
    2 连三 → 1 钢板（2 个三张）。
    """
    # 排除逢人配后，按 rank 聚合
    non_wild = [c for c in hand_cards if not _is_wild(c, cur_rank)]
    rank_counts = Counter(_parse_rank(c) for c in non_wild)

    # 找连续 rank
    rank_indices = sorted(
        RANKS.index(r) for r in rank_counts.keys()
        if r in RANKS and rank_counts[r] >= 1
    )
    if not rank_indices:
        return 0

    # 计算最长连续段 + 连续段总数（贪心）
    sequences = 0
    i = 0
    while i < len(rank_indices):
        j = i
        while j + 1 < len(rank_indices) and rank_indices[j + 1] == rank_indices[j] + 1:
            j += 1
        seg_len = j - i + 1
        if seg_len >= 5:
            # 顺子（每 5 张一段，可重叠截断）
            sequences += max(1, seg_len - 4)
        i = j + 1

    # 额外计 3 连对
    pair_runs = 0
    i = 0
    pair_rank_indices = sorted(
        RANKS.index(r) for r in rank_counts.keys()
        if r in RANKS and rank_counts[r] >= 2
    )
    while i < len(pair_rank_indices):
        j = i
        while j + 1 < len(pair_rank_indices) and pair_rank_indices[j + 1] == pair_rank_indices[j] + 1:
            j += 1
        if j - i + 1 >= 3:
            pair_runs += 1
        i = j + 1

    # 额外计 2 连三
    trips_runs = 0
    i = 0
    trips_rank_indices = sorted(
        RANKS.index(r) for r in rank_counts.keys()
        if r in RANKS and rank_counts[r] >= 3
    )
    while i < len(trips_rank_indices):
        j = i
        while j + 1 < len(trips_rank_indices) and trips_rank_indices[j + 1] == trips_rank_indices[j] + 1:
            j += 1
        if j - i + 1 >= 2:
            trips_runs += 1
        i = j + 1

    return sequences + pair_runs + trips_runs


def _count_triples(hand_cards: List[str], cur_rank: str) -> int:
    """三张数（不计逢人配）。"""
    non_wild = [c for c in hand_cards if not _is_wild(c, cur_rank)]
    rank_counts = Counter(_parse_rank(c) for c in non_wild)
    return sum(1 for cnt in rank_counts.values() if cnt >= 3)


def _count_pairs(hand_cards: List[str], cur_rank: str) -> int:
    """对子数（不计逢人配，不与三张重复计）。"""
    non_wild = [c for c in hand_cards if not _is_wild(c, cur_rank)]
    rank_counts = Counter(_parse_rank(c) for c in non_wild)
    return sum(1 for cnt in rank_counts.values() if cnt == 2)


def _count_singles(hand_cards: List[str], cur_rank: str) -> int:
    """散牌数（去单化原则反向：1 张的 rank 数 = 散牌结构数）。"""
    non_wild = [c for c in hand_cards if not _is_wild(c, cur_rank)]
    rank_counts = Counter(_parse_rank(c) for c in non_wild)
    return sum(1 for cnt in rank_counts.values() if cnt == 1)


def _longest_run(hand_cards: List[str], cur_rank: str) -> int:
    """最长连续 rank 数（A=12 是最长可能）。"""
    non_wild = [c for c in hand_cards if not _is_wild(c, cur_rank)]
    rank_counts = Counter(_parse_rank(c) for c in non_wild)
    rank_indices = sorted(
        RANKS.index(r) for r in rank_counts.keys()
        if r in RANKS and rank_counts[r] >= 1
    )
    if not rank_indices:
        return 0
    longest = 1
    cur = 1
    for i in range(1, len(rank_indices)):
        if rank_indices[i] == rank_indices[i - 1] + 1:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 1
    return longest


def _count_wilds(hand_cards: List[str], cur_rank: str) -> int:
    """逢人配数（H+curRank 数）。"""
    return sum(1 for c in hand_cards if _is_wild(c, cur_rank))


def _high_card_strength(hand_cards: List[str], cur_rank: str) -> int:
    """高级牌数：BJ + RJ + curRank 各花色持有数。"""
    cnt = 0
    for c in hand_cards:
        if c in JOKERS:
            cnt += 1
        elif _parse_rank(c) == cur_rank and not _is_wild(c, cur_rank):
            cnt += 1
    return cnt


# ── 主入口 ────────────────────────────────────────────

def extract_grouping_score(
    game_state: Dict[str, Any],
) -> List[float]:
    """
    从游戏状态提取 9 维组牌质量软信号（GUA-054）。

    9 维特征（每维 0~1 归一化连续值）：

      0: bomb_count        — 炸弹结构数 / NORM_BOMB_MAX（炸弹平衡）
      1: sequence_count    — 顺子/连对/钢板候选数 / NORM_SEQUENCE_MAX（牌型连贯）
      2: triple_count      — 三张结构数 / NORM_TRIPLE_MAX（牌型连贯）
      3: pair_count        — 对子结构数 / NORM_PAIR_MAX（牌型连贯）
      4: single_count      — 散牌结构数 / NORM_SINGLE_MAX（去单化反向）
      5: longest_run       — 最长连续 rank 数 / NORM_LONGEST_RUN_MAX
      6: wild_flexibility  — 逢人配数 / NORM_WILD_MAX（逢人配留变化）
      7: round_efficiency  — 1 - single_count_norm（出牌轮次效率）
      8: hand_strength     — 高级牌数 / NORM_HIGH_MAX（牌力基础）

    Args:
        game_state: 游戏状态字典，必含 handCards，可选 curRank

    Returns:
        9 维 float list，范围 [0.0, 1.0]
    """
    hand_cards: List[str] = game_state.get("handCards", []) or []
    cur_rank: str = str(game_state.get("curRank", "2"))

    if not isinstance(hand_cards, list):
        hand_cards = []

    # 计算各维原始值
    raw_bomb = _count_bombs(hand_cards, cur_rank)
    raw_seq = _count_sequences(hand_cards, cur_rank)
    raw_triple = _count_triples(hand_cards, cur_rank)
    raw_pair = _count_pairs(hand_cards, cur_rank)
    raw_single = _count_singles(hand_cards, cur_rank)
    raw_longest = _longest_run(hand_cards, cur_rank)
    raw_wild = _count_wilds(hand_cards, cur_rank)
    raw_high = _high_card_strength(hand_cards, cur_rank)

    # 归一化到 [0, 1]
    norm_bomb = min(raw_bomb / NORM_BOMB_MAX, 1.0)
    norm_seq = min(raw_seq / NORM_SEQUENCE_MAX, 1.0)
    norm_triple = min(raw_triple / NORM_TRIPLE_MAX, 1.0)
    norm_pair = min(raw_pair / NORM_PAIR_MAX, 1.0)
    norm_single = min(raw_single / NORM_SINGLE_MAX, 1.0)
    norm_longest = min(raw_longest / NORM_LONGEST_RUN_MAX, 1.0)
    norm_wild = min(raw_wild / NORM_WILD_MAX, 1.0)
    norm_high = min(raw_high / NORM_HIGH_MAX, 1.0)
    # round_efficiency = 1 - single_count（出牌轮次越少越好）
    norm_round_eff = 1.0 - norm_single

    return [
        norm_bomb,
        norm_seq,
        norm_triple,
        norm_pair,
        norm_single,
        norm_longest,
        norm_wild,
        norm_round_eff,
        norm_high,
    ]


def get_grouping_score_dim() -> int:
    """返回 grouping_score 维度（= 9）。"""
    return GROUPING_SCORE_DIM
