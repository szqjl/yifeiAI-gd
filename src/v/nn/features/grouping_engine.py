# -*- coding: utf-8 -*-
"""
GUA-061→GUA-062 GroupingEngine — M3 组牌逻辑提取 + v2 升级（静态回收评估+灵活性+真回溯）。

设计约束（§7.4 升格硬约束）：
  - 纯函数，无类状态，无 if-else 硬规则决策
  - V7-internal：禁止 `from src.m.m3 import ...`
  - 多方案枚举（6 策略，STRAIGHT_FIRST 已融入 SF_FIRST Phase 1c）+ 独立评分 + 特征向量输出
  - 推理延迟 < 5ms（108 张手牌最坏情况）

GUA-062 v2 升级（2026-06-18）：
  - P0-A：静态回收评估（方案中牌型兜底大牌比例，文档权重 0.3）
  - P0-B：灵活性评分（牌型多样性 + 方案差异性，文档权重 0.2）
  - P0-C：评分公式 4 维加权（炸弹0.3+手数0.2+回收0.3+灵活0.2）
  - P1：牌力计分 + 角色定位（登基牌+3/普通炸+2/赘牌-1）
  - P2：真回溯多方案（4 策略 + NO_STRAIGHTS + ALL_COMBOS = 6 方案，STRAIGHT_FIRST 融入 SF_FIRST）

核心流程：
  1. 手牌 → 按 rank 分组 → 基础结构识别（Single/Pair/Trips/Bomb）
  2. 多策略枚举：BOMB_FIRST / BALANCED / ROUND_OPTIMAL / NO_STRAIGHTS / ALL_COMBOS / SF_FIRST（STRAIGHT_FIRST 已融入）
  3. 独立评分（4 维加权 + 牌力 + 角色）
  4. 输出 best_plan + plans + 24 维特征向量

与 grouping_scanner.py (GUA-054) 的关系：
  - grouping_scanner: 9 维软信号（统计计数，不枚举方案）
  - grouping_engine:  24 维特征（6 方案枚举 + 方案级特征）
  - grouping_scanner 保留作为兼容基线，grouping_engine 作为增强替代
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Optional, NamedTuple
from collections import Counter
from dataclasses import dataclass, field
import copy

# ── 常量 ──────────────────────────────────────────────────
SUITS = ("S", "H", "D", "C")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")
JOKERS = ("SB", "HR")  # 平台原生：SB=小王, HR=大王
ALL_RANKS = RANKS + ("SB", "HR")

# 旧编码兼容（BJ→SB, RJ→HR，用于历史训练数据读取）
_LEGACY_NORMALIZE = {"BJ": "SB", "RJ": "HR"}

# 特征维度
GROUPING_ENGINE_DIM = 24  # 24 维方案级组牌特征

# 归一化上限
NORM_MAX_BOMBS = 4.0
NORM_MAX_STRAIGHTS = 3.0
NORM_MAX_PAIRS = 6.0
NORM_MAX_SINGLES = 12.0
NORM_MAX_LONGEST_RUN = 12.0
NORM_MAX_WILDS = 2.0
NORM_MAX_ROUNDS = 20.0
NORM_MAX_THREE_PAIRS = 2.0
NORM_MAX_POWER = 12.0

# ── 数据结构 ──────────────────────────────────────────────

@dataclass
class GroupingPlan:
    """一个组牌方案。"""
    singles: List[str] = field(default_factory=list)        # 单张列表
    pairs: List[List[str]] = field(default_factory=list)    # 对子列表
    trips: List[List[str]] = field(default_factory=list)    # 三张列表
    bombs: List[List[str]] = field(default_factory=list)    # 炸弹列表
    straights: List[List[str]] = field(default_factory=list)       # 顺子列表
    straight_flushes: List[List[str]] = field(default_factory=list) # 同花顺列表
    three_pairs: List[List[List[str]]] = field(default_factory=list) # 三连对（每项含3个对子）
    three_with_twos: List[object] = field(default_factory=list)     # 三带二 [(trip, pair), ...]
    steel_plates: List[List[List[str]]] = field(default_factory=list) # 钢板（连续三张对）
    wild_cards: List[str] = field(default_factory=list)     # 逢人配
    cur_rank: str = "2"                                     # 当前级牌

    # 派生指标
    strategy: str = "balanced"
    score: float = 0.0

    # GUA-062 v2 评分子分
    bomb_score: float = 0.0          # 牌力分（归一化 power_score / NORM_MAX_POWER），权重 0.3
    rounds_score: float = 0.0        # 手数 0.2
    recovery_score: float = 0.0      # 静态回收评估 0.3
    flexibility_score: float = 0.0   # 灵活性 0.1
    de_singleton_score: float = 0.0  # 去单化 0.1（单张越少越高）
    power_score: int = 0             # 牌力计分
    role: str = ""                   # 角色定位（超强主攻/主攻/助攻/超弱）

    def num_rounds(self) -> int:
        """出完所有牌所需轮数。"""
        r = 0
        r += len(self.straight_flushes)
        r += len(self.straights)
        r += len(self.bombs)
        r += len(self.trips)
        r += len(self.pairs)
        r += len(self.singles)
        r += len(self.three_pairs)
        r += len(self.three_with_twos)
        r += len(self.steel_plates)
        return r

    def to_dict(self) -> Dict:
        """转为字典（供下游使用）。"""
        d = {
            "Single": self.singles,
            "Pair": [list(p) for p in self.pairs],
            "Trips": [list(t) for t in self.trips],
            "Bomb": [list(b) for b in self.bombs],
            "Straight": [list(s) for s in self.straights],
            "StraightFlush": [list(sf) for sf in self.straight_flushes],
        }
        if self.three_pairs:
            d["ThreePair"] = [[list(pr) for pr in tp] for tp in self.three_pairs]
        if self.three_with_twos:
            d["ThreeWithTwo"] = [[list(twt[0]), list(twt[1])] for twt in self.three_with_twos]
        if self.steel_plates:
            d["SteelPlate"] = [[list(t) for t in sp] for sp in self.steel_plates]
        return d

    # ── GUA-063 Phase 1: card-level grouping mask ──────────────────

    def to_card_mask(self) -> Tuple[Dict[str, tuple], Dict[int, str]]:
        """构建牌级组牌掩码，供前置过滤使用。

        返回 (mask, group_type_map)：
          mask: Dict[card_str, (group_id, is_core, group_size)]
            - group_id:   同组牌共享同一 ID，散牌/单张 = -1
            - is_core:    1.0 = 核心不可轻拆（炸弹/同花顺），0.0 = 普通牌型
            - group_size: 该组共有几张牌（用于判断是否完整打出）
          group_type_map: Dict[group_id, type_string]
            - type_string: "bomb"/"straight_flush"/"straight"/"trips"/"pair"
              /"trip_in_three_with_two"/"pair_in_three_with_two"
              /"pair_in_three_pair"/"trip_in_steel_plate"

        核心牌型判定（GUA-063 修复 2026-06-18 + GUA-070 子结构拆分 2026-06-19）：
          - bombs / straight_flushes → is_core=1.0
          - straights / trips → is_core=1.0（掼蛋牌理：顺子和三张是结构化牌型，不可轻拆）
          - three_with_twos → 拆分为 trip_in_three_with_two + pair_in_three_with_two，各自 is_core=1.0
          - three_pairs → 拆分为 3 × pair_in_three_pair，各自 is_core=1.0
          - steel_plates → 拆分为 2 × trip_in_steel_plate，各自 is_core=1.0
          - pairs → is_core=0.0（普通对子可重配）
          - 散牌（singles / 未消耗的 wild_cards）→ group_id=-1, is_core=0.0, group_size=1
        """
        mask: Dict[str, tuple] = {}
        group_type_map: Dict[int, str] = {}

        # ── 收集所有牌组 ──
        # groups: List[(cards, is_core, type_string)]
        groups: List[Tuple[List[str], bool, str]] = []

        # 核心牌型（炸弹/同花顺）
        for b in self.bombs:
            groups.append((list(b), True, "bomb"))
        for sf in self.straight_flushes:
            groups.append((list(sf), True, "straight_flush"))

        # 结构化牌型（顺子/三张 → is_core=1.0，GUA-063）
        for s in self.straights:
            groups.append((list(s), True, "straight"))
        for t in self.trips:
            groups.append((list(t), True, "trips"))
        for p in self.pairs:
            groups.append((list(p), False, "pair"))
        for tp in self.three_pairs:
            # GUA-070 同款：三连对拆分为 3 个独立对子子组
            # 每个 pair 各自 is_core=True，防止拆三连对拿对子单出静默放行
            for pair in tp:
                groups.append((list(pair), True, "pair_in_three_pair"))
        for twt in self.three_with_twos:
            # GUA-070: 三带二拆分为 trip + pair 两个独立子组
            # trip 和 pair 各自 is_core=True，防止拆对子/拆三张静默放行
            groups.append((list(twt[0]), True, "trip_in_three_with_two"))
            groups.append((list(twt[1]), True, "pair_in_three_with_two"))
        for sp in self.steel_plates:
            # GUA-070 同款：钢板拆分为 2 个独立三张子组
            # 每个 trip 各自 is_core=True，防止拆钢板拿三张单出静默放行
            for trip in sp:
                groups.append((list(trip), True, "trip_in_steel_plate"))

        # 散牌（单张 / 未消耗逢人配）
        for s in self.singles:
            mask[s] = (-1, 0.0, 1)

        # ── 分配 group_id ──
        gid = 0
        for group_cards, is_core, type_str in groups:
            gsize = len(group_cards)
            is_core_f = 1.0 if is_core else 0.0
            group_type_map[gid] = type_str
            for card in group_cards:
                mask[card] = (gid, is_core_f, gsize)
            gid += 1

        return mask, group_type_map


# ── 牌面解析 ──────────────────────────────────────────────


def _parse_rank(card: str) -> str:
    """从 'S2' / 'SB' 提取 rank，统一 '10' → 'T'。"""
    if card in JOKERS:
        return card
    # 归一化旧编码兼容（BJ→SB, RJ→HR）
    card = _LEGACY_NORMALIZE.get(card, card)
    if card in JOKERS:
        return card
    if len(card) >= 2 and card[0] in SUITS:
        raw = card[1:]
        return 'T' if raw == '10' else raw  # 规范化 10 → T
    return card


def _parse_suit(card: str) -> str:
    """从 'S2' 提取花色。"""
    if len(card) >= 2 and card[0] in SUITS:
        return card[0]
    return ""


def _is_wild(card: str, cur_rank: str) -> bool:
    """判断是否为逢人配（H+curRank）。"""
    return card == f"H{cur_rank}"


def _card_rank_value(card: str, cur_rank: str) -> int:
    """
    返回牌的相对大小值（用于排序）。
    cur_rank → 15, B → 16, R → 17, 其余按 2..A → 2..14
    """
    r = _parse_rank(card)
    if r == "B":
        return 16
    if r == "R":
        return 17
    if r == cur_rank:
        return 15
    idx_map = {r: i + 2 for i, r in enumerate(RANKS)}
    return idx_map.get(r, 0)


# ── 手牌基础分组 ──────────────────────────────────────────

def _rank_groups(hand_cards: List[str], cur_rank: str) -> Dict[str, List[str]]:
    """
    将手牌按 rank+花色分组。
    返回 {rank: [cards]}，逢人配单独标记为 wild。
    """
    groups: Dict[str, List[str]] = {}
    wilds = []
    for c in hand_cards:
        if _is_wild(c, cur_rank):
            wilds.append(c)
            continue
        r = _parse_rank(c)
        if r not in groups:
            groups[r] = []
        groups[r].append(c)
    groups["__wild__"] = wilds
    return groups


def _basic_classify(groups: Dict[str, List[str]]) -> Tuple[
    List[str], List[List[str]], List[List[str]], List[List[str]]
]:
    """从 rank 分组做基础分类：Single/Pair/Trips/Bomb。"""
    singles: List[str] = []
    pairs: List[List[str]] = []
    trips: List[List[str]] = []
    bombs: List[List[str]] = []

    for rank, cards in groups.items():
        if rank == "__wild__":
            continue
        n = len(cards)
        if n == 1:
            singles.extend(cards)
        elif n == 2:
            pairs.append(cards)
        elif n == 3:
            trips.append(cards)
        elif n >= 4:
            bombs.append(cards)

    return singles, pairs, trips, bombs


def _classify_no_bombs(groups: Dict[str, List[str]]) -> Tuple[
    List[str], List[List[str]], List[List[str]]
]:
    """同类 _basic_classify, 但 n>=4 的牌拆分为对子/三张/单张, 永不生成炸弹。
    用于拆弹后剩余牌回收, 避免 _basic_classify 重新组弹后被丢弃吞牌。"""
    singles: List[str] = []
    pairs: List[List[str]] = []
    trips: List[List[str]] = []

    for rank, cards in groups.items():
        if rank == "__wild__":
            continue
        n = len(cards)
        i = 0
        # 优先组三张
        while i + 3 <= n:
            trips.append(cards[i:i + 3])
            i += 3
        # 再组对子
        while i + 2 <= n:
            pairs.append(cards[i:i + 2])
            i += 2
        # 余下单张
        while i < n:
            singles.append(cards[i])
            i += 1

    return singles, pairs, trips

# ── 三连对检测 ──────────────────────────────────────────────

def _detect_three_pairs(
    pairs: List[List[str]], cur_rank: str,
) -> Tuple[List[List[List[str]]], List[List[str]]]:
    """从对子中检测三连对（3 个连续 rank 的对子组成连对）。
    返回 (three_pair_groups, remaining_pairs)。
    每 3 个连续对子组成一组三连对，贪婪取 3 跳 3。"""
    if len(pairs) < 3:
        return [], pairs[:]

    # 按 rank 值排序对子
    sorted_pairs = sorted(pairs, key=lambda p: _card_rank_value(p[0], cur_rank))

    # 只保留标准 rank 的对子（过滤大小王等非常规 rank），同时记录 sorted_pairs 索引
    valid: List[Tuple[int, int, List[str]]] = []  # (sp_idx, rank_idx, pair)
    for sp_idx, p in enumerate(sorted_pairs):
        r = _parse_rank(p[0])
        if r in RANKS:
            valid.append((sp_idx, RANKS.index(r), p))

    if len(valid) < 3:
        return [], pairs[:]

    three_pair_groups: List[List[List[str]]] = []
    used_sp_indices: set = set()

    # A→2 包接：A(12)→2(0)→3(1) 组成 AA-22-33 三连对
    valid_indices = [v[1] for v in valid]  # RANKS index
    if valid_indices[-1] == RANKS.index('A') and valid_indices[0] == RANKS.index('2'):
        if len(valid) >= 3 and valid_indices[1] == RANKS.index('3'):
            # AA-22-33
            three_pair_groups.append([valid[-1][2], valid[0][2], valid[1][2]])
            used_sp_indices.update([valid[-1][0], valid[0][0], valid[1][0]])

    i = 0
    while i + 3 <= len(valid):
        if i in used_sp_indices or i + 1 in used_sp_indices or i + 2 in used_sp_indices:
            i += 1
            continue
        _, idx1, pair1 = valid[i]
        _, idx2, pair2 = valid[i + 1]
        _, idx3, pair3 = valid[i + 2]
        if idx2 == idx1 + 1 and idx3 == idx2 + 1:
            # 三连对
            three_pair_groups.append([pair1, pair2, pair3])
            used_sp_indices.update([valid[i][0], valid[i + 1][0], valid[i + 2][0]])
            i += 3
        else:
            i += 1

    # 剩余对子（用 sorted_pairs 的真实索引排除）
    remaining = [p for sp_idx, p in enumerate(sorted_pairs) if sp_idx not in used_sp_indices]

    return three_pair_groups, remaining


# ── 三带二检测 ──────────────────────────────────────────────

def _detect_three_with_two(
    trips: List[List[str]], pairs: List[List[str]], cur_rank: str,
) -> Tuple[List[Tuple[List[str], List[str]]], List[List[str]], List[List[str]]]:
    """
    从三张和对子中检测三带二。
    返回 (three_with_twos, remaining_trips, remaining_pairs)。
    贪心匹配：每个 trip 搭配一个 pair，消耗 5 张牌 → 1 轮（相比 trip+pair 单独出省 1 轮）。
    """
    if not trips or not pairs:
        return [], trips[:], pairs[:]

    remaining_trips = [t[:] for t in trips]
    remaining_pairs = [p[:] for p in pairs]
    three_with_twos: List[Tuple[List[str], List[str]]] = []

    # 贪心：按 rank 排序三张（从高到低优先消耗大牌 trip）
    sorted_trips = sorted(remaining_trips, key=lambda t: _card_rank_value(t[0], cur_rank), reverse=True)
    for trip in sorted_trips:
        if remaining_pairs:
            pair = remaining_pairs.pop(0)
            three_with_twos.append((trip, pair))
            remaining_trips.remove(trip)
        else:
            break

    return three_with_twos, remaining_trips, remaining_pairs


# ── 钢板检测（连续三张对）─────────────────────────────────

def _detect_steel_plate(
    trips: List[List[str]], cur_rank: str,
) -> Tuple[List[List[List[str]]], List[List[str]]]:
    """
    从三张中检测钢板（连续两个三张，如 333-444）。
    返回 (steel_plates, remaining_trips)。
    消耗 6 张牌 → 1 轮（相比 2 个独立 trip 省 1 轮）。
    含 A→2 包接检测（AAA-222）。
    """
    if len(trips) < 2:
        return [], trips[:]

    sorted_trips = sorted(trips, key=lambda t: _card_rank_value(t[0], cur_rank))

    valid: List[Tuple[int, List[str]]] = []
    for t in sorted_trips:
        r = _parse_rank(t[0])
        if r in RANKS:
            valid.append((RANKS.index(r), t))

    if len(valid) < 2:
        return [], trips[:]

    steel_plates: List[List[List[str]]] = []
    consumed_ids: set = set()

    # A→2 包接：A(12)→2(0) 组成 AAA-222 钢板
    if valid[-1][0] == RANKS.index('A') and valid[0][0] == RANKS.index('2'):
        steel_plates.append([valid[-1][1], valid[0][1]])
        consumed_ids.add(id(valid[-1][1]))
        consumed_ids.add(id(valid[0][1]))

    i = 0
    while i + 2 <= len(valid):
        t1, t2 = valid[i][1], valid[i + 1][1]
        if id(t1) in consumed_ids or id(t2) in consumed_ids:
            i += 1
            continue
        idx1, idx2 = valid[i][0], valid[i + 1][0]
        if idx2 == idx1 + 1:
            steel_plates.append([t1, t2])
            consumed_ids.add(id(t1))
            consumed_ids.add(id(t2))
            i += 2
        else:
            i += 1

    # 剩余三张（未消耗的）
    remaining = [t for t in sorted_trips if id(t) not in consumed_ids]

    return steel_plates, remaining


def _rank_to_value(rank_char: str) -> int:
    """将纯 rank 字符转为数值（用于大小比较，不含级牌特殊处理）。"""
    if rank_char in ("SB",):  # 小王
        return 16
    if rank_char in ("HR",):  # 大王
        return 17
    idx_map = {r: i + 2 for i, r in enumerate(RANKS)}
    return idx_map.get(rank_char, 0)


# ── 顺子检测 ──────────────────────────────────────────────

def _detect_straights(
    singles: List[str], pairs: List[List[str]], trips: List[List[str]],
    cur_rank: str, wilds: List[str],
) -> Tuple[List[List[str]], List[str], List[List[str]], List[List[str]], List[str]]:
    """
    从剩余牌中检测顺子（支持逢人配填补缺口）。
    返回 (straights, remaining_singles, remaining_pairs, remaining_trips, remaining_wilds)。
    贪心策略：找最长连续 rank 段 → 5 张窗口扫描 → 缺口用 wilds 填补。

    GUA-063 去小单化策略（2026-06-18）：
    - 窗口扫描从低→高（而非高→低）。原因：
      ① 掼蛋核心原则：去小单化——越小的单越难顺掉，组顺子首要目标就是吸收小单。
        如手牌 2-7 六连张，优先组 2-6 而非 3-7，把大单 7 留给其他组合（对子/三带二）。
      ② 大顺子的压制力在动态出牌中体现（逼炸/盖牌），初始组牌不应为此牺牲去小单化。
      ③ 单牌有灵活性——大单（8-K-A）比小单（2-3-4）更容易找到搭档形成对子或三条。
    """
    # 构建 rank 计数（不含 wild）
    card_by_rank: Dict[str, List[str]] = {}
    for s in singles:
        r = _parse_rank(s)
        card_by_rank.setdefault(r, []).append(s)
    for p_list in pairs:
        r = _parse_rank(p_list[0])
        card_by_rank.setdefault(r, []).extend(p_list)
    for t_list in trips:
        r = _parse_rank(t_list[0])
        card_by_rank.setdefault(r, []).extend(t_list)

    # 排序 rank（级牌可参与顺子组合）
    rank_indices = []
    for r in RANKS:
        if r in card_by_rank:
            rank_indices.append(r)

    available_wilds = len(wilds)
    if len(rank_indices) + available_wilds < 5:
        return [], singles[:], pairs[:], trips[:], list(wilds)

    # 找最长连续 rank 段
    best_start = 0
    best_len = 0
    best_is_wrap = False  # A→2 包接标志
    i = 0
    while i < len(rank_indices):
        j = i
        while j + 1 < len(rank_indices):
            cur_idx = RANKS.index(rank_indices[j])
            nxt_idx = RANKS.index(rank_indices[j + 1])
            if nxt_idx == cur_idx + 1:
                j += 1
            else:
                break
        seg_len = j - i + 1
        if seg_len > best_len:
            best_len = seg_len
            best_start = i
        i = j + 1

    # A→2 包接：A 可作为 1，连接 A→2→3→... 的段
    # rank_indices 按 RANKS 顺序 (2...A)，如果尾有 A 且首有 2，则包接段 = 尾段 + 首段
    wrap_tail_len = 0  # 从 A 往前数连续 rank 数
    wrap_head_len = 0  # 从 2 往后数连续 rank 数
    if (len(rank_indices) > 1 and rank_indices[-1] == 'A' and rank_indices[0] == '2'
            and 'A' in card_by_rank and '2' in card_by_rank):
        # 尾段：从 A 往前（A, K, Q, ...）
        wrap_tail_len = 1
        for ti in range(len(rank_indices) - 2, -1, -1):
            if RANKS.index(rank_indices[ti]) == RANKS.index(rank_indices[ti + 1]) - 1:
                wrap_tail_len += 1
            else:
                break
        # 首段：从 2 往后（2, 3, 4, ...）
        wrap_head_len = 1
        for hi in range(1, len(rank_indices)):
            if RANKS.index(rank_indices[hi]) == RANKS.index(rank_indices[hi - 1]) + 1:
                wrap_head_len += 1
            else:
                break
        wrap_len = wrap_tail_len + wrap_head_len
        if wrap_len > best_len:
            best_len = wrap_len
            best_is_wrap = True

    # 若最长段 + wilds 都不够 5，无顺子
    if best_len + available_wilds < 5:
        return [], singles[:], pairs[:], trips[:], list(wilds)

    # 统计每种牌面出现次数
    total_available: Counter[str] = Counter()
    for r in rank_indices:
        for c in card_by_rank[r]:
            total_available[c] += 1

    straights: List[List[str]] = []
    used_cards: Counter[str] = Counter()
    wilds_consumed = 0

    # 从最长段取顺子（从低到高，去小单化：优先吸收小牌组顺子，剩大单更易处理）
    if best_is_wrap:
        # 包接段：尾段 (....A) + 首段 (2,3,...)
        tail_start = len(rank_indices) - wrap_tail_len
        seg_ranks = rank_indices[tail_start:] + rank_indices[:wrap_head_len]
    else:
        seg_ranks = rank_indices[best_start:best_start + best_len]
    pos = 0
    pos_max = len(seg_ranks) - 5
    while pos <= pos_max:
        window_ranks = seg_ranks[pos:pos + 5]
        # A→2 包接段：A 只能当 1 用（窗口第一位），跳过 A 在中间/末尾的无效窗口
        if best_is_wrap and 'A' in window_ranks and window_ranks[0] != 'A':
            pos += 1
            continue
        straight_cards = []
        tentative: Counter[str] = Counter()
        tent_wilds_used = 0
        success = True

        for r in window_ranks:
            if r in card_by_rank:
                found = False
                for c in card_by_rank[r]:
                    if used_cards.get(c, 0) + tentative.get(c, 0) < total_available.get(c, 0):
                        straight_cards.append(c)
                        tentative[c] += 1
                        found = True
                        break
                if not found:
                    # 缺牌 → 尝试 wild
                    if wilds_consumed + tent_wilds_used < available_wilds:
                        straight_cards.append(wilds[wilds_consumed + tent_wilds_used])
                        tent_wilds_used += 1
                    else:
                        success = False
                        break
            else:
                # rank 不在 card_by_rank → 用 wild 填补
                if wilds_consumed + tent_wilds_used < available_wilds:
                    straight_cards.append(wilds[wilds_consumed + tent_wilds_used])
                    tent_wilds_used += 1
                else:
                    success = False
                    break

        if success and len(straight_cards) == 5:
            straights.append(straight_cards)
            used_cards.update(tentative)
            wilds_consumed += tent_wilds_used
        pos += 1

    # 剩余牌重新分类
    rem_used = Counter(used_cards)
    rem = []
    for c in singles + [x for p in pairs for x in p] + [x for t in trips for x in t]:
        if rem_used.get(c, 0) > 0:
            rem_used[c] -= 1
        else:
            rem.append(c)
    rem_groups = _rank_groups(rem, cur_rank)
    rem_singles, rem_pairs, rem_trips, rem_bombs = _basic_classify(rem_groups)
    for bomb in rem_bombs:
        rem_singles.extend(bomb)

    remaining_wilds = wilds[wilds_consumed:]
    return straights, rem_singles, rem_pairs, rem_trips, remaining_wilds


def _detect_straight_flushes(
    singles: List[str], pairs: List[List[str]], trips: List[List[str]],
    cur_rank: str, wilds: List[str],
    return_idx: int = 0,
) -> Tuple[List[List[str]], List[str], List[List[str]], List[List[str]], List[str]]:
    """
    从剩余牌中检测同花顺（支持逢人配填补缺口）。
    返回 (straight_flushes, remaining_singles, remaining_pairs, remaining_trips, remaining_wilds)。
    wilds 视为任意花色，可填补同花顺中缺 1 张的 4+1 场景。

    所有候选按 (wild 数升序, 最大自然牌面升序) 排序，
    优先消耗低价值牌组同花顺，高价值牌留给升炸。
    return_idx 选择第 N 个候选（0=最优, 1=次优, ...），不存在返回空。
    """
    # 按花色分拣
    by_suit: Dict[str, List[str]] = {s: [] for s in SUITS}
    all_cards = singles[:]
    for p in pairs:
        all_cards.extend(p)
    for t in trips:
        all_cards.extend(t)

    for c in all_cards:
        suit = _parse_suit(c)
        if suit in by_suit:
            by_suit[suit].append(c)

    total_sf: Counter[str] = Counter(all_cards)
    available_wilds = len(wilds)

    # 收集所有可行的同花顺候选（不立即消费 wild）
    # 每个候选记录：(suit_cards, wild_indices_used, min_natural_rank_val)
    Candidate = Tuple[List[str], List[int], int]  # cards, wild_indices, min_rank_val
    all_candidates: List[Candidate] = []

    for suit, cards in by_suit.items():
        if len(cards) + available_wilds < 5:
            continue
        sorted_cards = sorted(cards, key=lambda c: _card_rank_value(c, cur_rank))
        rank_list = [_parse_rank(c) for c in sorted_cards if _parse_rank(c) in RANKS]
        unique_ranks = sorted(set(rank_list), key=lambda r: RANKS.index(r))

        rank_set = set(rank_list)

        # 要尝试的候选窗口列表：[(target_ranks, label)]
        candidates: List[Tuple[List[str], str]] = []

        # 正常连续段
        for start in range(len(unique_ranks)):
            first_r = unique_ranks[start]
            first_idx = RANKS.index(first_r)
            if first_idx + 4 >= len(RANKS):
                break
            target_ranks = [RANKS[first_idx + k] for k in range(5)]
            candidates.append((target_ranks, "normal"))

        # A→2 包接：A 下放当 1，尝试 A-2-3-4-5
        if 'A' in rank_set and '2' in rank_set:
            candidates.append((['A', '2', '3', '4', '5'], "wrap"))

        for target_ranks, _label in candidates:
            have_in_suit = sum(1 for r in target_ranks if r in rank_set)
            need_wilds = 5 - have_in_suit
            if need_wilds > available_wilds:
                continue

            # 尝试组成同花顺（独立于其他候选）
            sf_cards = []
            tent_local: Counter[str] = Counter()
            tent_wild_indices: List[int] = []
            ok = True
            for r in target_ranks:
                if r in rank_set:
                    found = False
                    for c in sorted_cards:
                        if (_parse_rank(c) == r and
                                tent_local.get(c, 0) < total_sf.get(c, 0)):
                            sf_cards.append(c)
                            tent_local[c] += 1
                            found = True
                            break
                    if not found:
                        ok = False
                        break
                else:
                    # 缺 rank → 用 wild 顶
                    wi = len(tent_wild_indices)  # 使用第 wi 个 wild
                    if wi < available_wilds:
                        sf_cards.append(wilds[wi])
                        tent_wild_indices.append(wi)
                    else:
                        ok = False
                        break

            if ok and len(sf_cards) == 5:
                # 用最低自然牌面做比较键：低牌组SF，高牌留炸弹
                min_natural_rank = min(
                    _card_rank_value(c, cur_rank)
                    for c in sf_cards
                    if c not in set(wilds)
                )
                all_candidates.append((sf_cards, tent_wild_indices, min_natural_rank))

    if not all_candidates:
        return [], singles[:], pairs[:], trips[:], list(wilds)

    # 排序：wild 数升序 → 最低自然牌面升序（优先用低牌组 SF）
    all_candidates.sort(key=lambda x: (len(x[1]), x[2]))

    if return_idx >= len(all_candidates):
        return [], singles[:], pairs[:], trips[:], list(wilds)

    best_cards, best_wild_indices, _ = all_candidates[return_idx]
    sf_list = [best_cards]
    used_non_wild = Counter(
        c for c in best_cards if c not in set(wilds)
    )
    wilds_consumed = len(best_wild_indices)

    # 剩余牌（逐张扣除已用牌）
    rem_used = Counter(used_non_wild)
    rem = []
    for c in all_cards:
        if rem_used.get(c, 0) > 0:
            rem_used[c] -= 1
        else:
            rem.append(c)
    rem_groups = _rank_groups(rem, cur_rank)
    rem_singles, rem_pairs, rem_trips, rem_bombs = _basic_classify(rem_groups)
    for bomb in rem_bombs:
        rem_singles.extend(bomb)

    remaining_wilds = wilds[wilds_consumed:]
    return sf_list, rem_singles, rem_pairs, rem_trips, remaining_wilds


# ── GUA-062 v2 评分辅助函数 ───────────────────────────────

def _has_bigger_straight_in_plan(straight: List[str], plan: "GroupingPlan", cur_rank: str) -> bool:
    """检查 plan 中是否有比给定顺子更大的同类顺子。"""
    if not plan.straights:
        return False
    my_lowest = min(_card_rank_value(c, cur_rank) for c in straight)
    for s in plan.straights:
        if s == straight:
            continue
        their_lowest = min(_card_rank_value(c, cur_rank) for c in s)
        if their_lowest > my_lowest:
            return True
    return False


def _has_bigger_trip_in_plan(trip: List[str], plan: "GroupingPlan", cur_rank: str) -> bool:
    """检查 plan 中是否有比给定三带二更大的三带二。"""
    if not plan.trips:
        return False
    my_val = _card_rank_value(trip[0], cur_rank)
    for t in plan.trips:
        if t == trip:
            continue
        their_val = _card_rank_value(t[0], cur_rank)
        if their_val > my_val:
            return True
    return False


def _score_recovery_static(plan: "GroupingPlan", cur_rank: str) -> float:
    """
    GUA-062 P0-A：组牌阶段静态回收评估。

    评估方案中各类牌型有多少有兜底大牌（方案质量打分）。
    ⚠️ 不是出牌阶段的 K 原则实时判断，只是静态评估方案质量。

    豁免牌型（不纳入评估）：
      - 炸弹：本身就是压制手段
      - 同花顺：顶级牌型，几乎不可能被更大同花顺压制
      - 钢板/木板/三连对/三张：稀有牌型，天然难被压制
    """
    scores = []
    k_val = _rank_to_value("K")

    # 单张兜底：K 以上单牌占比
    if plan.singles:
        big = sum(1 for s in plan.singles if _card_rank_value(s, cur_rank) >= k_val)
        scores.append(big / len(plan.singles))

    # 对子兜底：KK 以上对子占比
    if plan.pairs:
        big = sum(1 for p in plan.pairs if _card_rank_value(p[0], cur_rank) >= k_val)
        scores.append(big / len(plan.pairs))

    # 顺子兜底：有更大顺子的比例
    if plan.straights:
        recoverable = sum(
            1 for s in plan.straights
            if _has_bigger_straight_in_plan(s, plan, cur_rank)
        )
        scores.append(recoverable / len(plan.straights))

    # 三带二兜底：有更大三带二的比例
    if plan.trips:
        recoverable = sum(
            1 for t in plan.trips
            if _has_bigger_trip_in_plan(t, plan, cur_rank)
        )
        scores.append(recoverable / len(plan.trips))

    if not scores:
        return 0.5  # 无需要兜底的牌型 → 默认中等

    return sum(scores) / len(scores)


def _score_flexibility(plan: "GroupingPlan", all_plans: List["GroupingPlan"]) -> float:
    """
    GUA-062 P0-B：灵活性评分。

    两个维度：
      1. 牌型多样性：有多少种不同牌型（0~6 类，不含单张 — 单张是短板非多样性）
      2. 方案差异性：与兄弟方案的炸弹数/轮数差异
    """
    # 牌型多样性（单张不参与 — 去单化：单张是缺陷，不是多样性优势）
    types = sum([
        1 if plan.pairs else 0,
        1 if plan.trips else 0,
        1 if plan.bombs else 0,
        1 if plan.straights else 0,
        1 if plan.straight_flushes else 0,
        1 if plan.three_pairs else 0,
    ])
    type_div = types / 6.0

    # 方案差异性（与其他方案比较）
    if len(all_plans) > 1:
        others = [p for p in all_plans if p is not plan]
        if others:
            other_bombs = [len(p.bombs) for p in others]
            other_rounds = [p.num_rounds() for p in others]
            bomb_diff = abs(len(plan.bombs) - sum(other_bombs) / len(other_bombs))
            round_diff = abs(plan.num_rounds() - sum(other_rounds) / len(other_rounds))
            plan_diff = min((bomb_diff / 4.0 + round_diff / 10.0) / 2.0, 1.0)
        else:
            plan_diff = 0.0
    else:
        plan_diff = 0.0

    return (type_div + plan_diff) / 2.0


def _score_power(plan: "GroupingPlan", cur_rank: str) -> int:
    """
    GUA-062 P1：牌力计分（基于 04_card_grouping_skills.md §一 + V7 增强）。

    加分项：
      - 登基牌炸弹 +3（同花顺 / 5头+炸 / 4个级牌）
      - 普通四头炸 +2
      - 6张及以上炸弹 +3
      - 四大天王（2大王+2小王） +4/组
      - 逢人配（百搭）+1/张（配成炸弹/同花顺不再重复加分）
      - 登基牌 +1（大王 / 对级牌）
      - 稀有牌型 +1（三连对）

    减分项（每满足一类扣 1 分，多张多组叠加扣）：
      - 单张：＜10 的孤立单张，每张 -1
      - 对子：＜对6 孤立小对子（无三带二组合），每组 -1
      - 三带二：＜4 小三头带对，每组 -1
      - 组合：6及以下小顺子 / 小木板 / 小钢板，每组 -1
    """
    score = 0

    # ═══════════════════════════════════
    # 加分项
    # ═══════════════════════════════════

    # 登基牌炸弹 +3：同花顺
    score += len(plan.straight_flushes) * 3

    # 炸弹计分
    for b in plan.bombs:
        n = len(b)
        if n >= 6:
            score += 3          # 6张及以上炸弹
        elif n == 5:
            score += 3          # 5头炸（登基牌炸弹）
        elif n == 4:
            # 4头炸：区分登基炸 vs 普通炸
            if all(_parse_rank(c) == cur_rank for c in b):
                score += 3      # 4个级牌
            else:
                score += 2      # 普通四头炸

    # 四大天王 +4：2大王 + 2小王（统计方案中所有 JOKER 牌）
    def _count_jokers(plan: "GroupingPlan") -> tuple:
        """统计方案中大王(HR)和小王(SB)的总张数。
        遍历 singles / pairs / bombs / trips 等所有结构。"""
        rj_total = 0
        bj_total = 0
        # 需要遍历的牌容器
        containers = [
            plan.singles,
            *plan.pairs,
            *plan.bombs,
            *plan.straights,
            *plan.straight_flushes,
            *plan.trips,
        ]
        for tp in plan.three_pairs:
            containers.extend(tp)  # 每个三连对有 3 个对子
        for sp in plan.steel_plates:
            containers.extend(sp)
        for twt in plan.three_with_twos:
            containers.append(twt[0])
            containers.append(twt[1])
        for container in containers:
            for card in container:
                r = _parse_rank(card)
                if r in ("HR",):
                    rj_total += 1
                elif r in ("SB",):
                    bj_total += 1
        return rj_total, bj_total

    rj_count, bj_count = _count_jokers(plan)
    if rj_count >= 2 and bj_count >= 2:
        score += 4

    # 逢人配（百搭）：未配入炸弹/同花顺的 +1/张
    # plan.wild_cards 中是未被消耗的逢人配
    score += len(plan.wild_cards)

    # 登基牌 +1：大王（每张 +1）
    score += rj_count

    # 登基牌 +1：对级牌
    for p in plan.pairs:
        if _parse_rank(p[0]) == cur_rank:
            score += 1

    # 稀有牌型 +1：三连对
    score += len(plan.three_pairs)

    # GUA-069 举一反三 (2026-06-19): 钢板（连续三张对）也应计入牌力
    # 钢板消耗 6 张牌 → 1 轮，相比 2 个独立 trip 省 1 轮，属于稀有牌型
    # 例如 888-999 钢板 = +1（防止因不记分导致 role 被低估）
    score += len(plan.steel_plates)

    # ═══════════════════════════════════
    # 减分项
    # ═══════════════════════════════════

    # 收集三带二中已消耗的对子（用于排除被三带二保护的对子）
    twt_pair_ids: set = set()
    for twt in plan.three_with_twos:
        # twt = (trip, pair)
        pair = twt[1]
        twt_pair_ids.add(tuple(sorted(pair)))

    # 逢人配集合（排除在单张减分之外）
    wild_set = set(plan.wild_cards)

    # 单张：＜10 的孤立单张，每张 -1
    for s in plan.singles:
        if s in wild_set:
            continue  # 百搭不计为小单张
        r = _parse_rank(s)
        if r in ("HR", "SB"):
            continue  # 王不计为小单张
        if _card_rank_value(s, cur_rank) < _rank_to_value("T"):  # T=10, rank 2~9
            score -= 1

    # 对子：＜对6 孤立小对子（无三带二组合），每组 -1
    rank6_threshold = _rank_to_value("6")
    for p in plan.pairs:
        if tuple(sorted(p)) in twt_pair_ids:
            continue  # 已在三带二中，受保护不扣
        r = _parse_rank(p[0])
        if r in ("HR", "SB"):
            continue  # 王对子不扣
        if _card_rank_value(p[0], cur_rank) < rank6_threshold:
            score -= 1

    # 三带二：＜4 小三头带对，每组 -1
    rank4_threshold = _rank_to_value("4")
    for twt in plan.three_with_twos:
        trip = twt[0]
        if _card_rank_value(trip[0], cur_rank) < rank4_threshold:
            score -= 1

    # 组合：6及以下小顺子 / 小木板 / 小钢板，每组 -1
    rank6_limit = _rank_to_value("6")
    for s in plan.straights:
        max_val = max(_card_rank_value(c, cur_rank) for c in s)
        if max_val <= rank6_limit:
            score -= 1

    for tp in plan.three_pairs:
        # tp = [[pair1], [pair2], [pair3]] — 每个对子 2 张，共 6 张
        all_cards = [c for pair in tp for c in pair]
        max_val = max(_card_rank_value(c, cur_rank) for c in all_cards)
        if max_val <= rank6_limit:
            score -= 1

    # GUA-070: 移除小钢板减分 — 钢板不论大小都是加分项（稀有牌型，天然难被压制）
    return score


def determine_role(power_score: int) -> str:
    """
    GUA-062 P1：根据牌力分确定角色。

    角色映射（2026-06-19 调优：降阈让 yf 更积极）：
      - ≥7 → 超强主攻
      - 4-6 → 主攻
      - 1-3 → 助攻
      - <1 → 超弱
    """
    if power_score >= 7:
        return "超强主攻"
    elif power_score >= 4:
        return "主攻"
    elif power_score >= 1:
        return "助攻"
    else:
        return "超弱"


# ── 方案评分（GUA-062 v2 升级） ────────────────────────────

def _score_de_singleton(plan: "GroupingPlan") -> float:
    """
    去单化评分（CG-G11）：单张越少越好。

    归一化：27 张手牌理论最多 27 张单张，正常范围 0~10。
    用 max(0, 1 - singles/10) 夹到 [0, 1]。
    0 张单张 = 满分 1.0；10+ 张单张 = 0。
    """
    n_singles = len(plan.singles)
    return max(0.0, 1.0 - n_singles / 10.0)


def _score_plan_v2(plan: "GroupingPlan", all_plans: List["GroupingPlan"]) -> None:
    """
    GUA-062 P0-C：文档标准 5 维加权评分。

    权重调优 2026-06-18：
      - 牌力分 0.3（含炸弹+同花顺+登基牌+稀有牌型-减分，归一化到 NORM_MAX_POWER）
      - 手数 0.3
      - 静态回收评估 0.1
      - 灵活性 0.1
      - 去单化 0.2
    """
    n_rounds = plan.num_rounds()

    # 牌力计分 + 角色定位（先算，因为总分用它）
    plan.power_score = _score_power(plan, plan.cur_rank)
    plan.role = determine_role(plan.power_score)

    # 牌力分 0.3（替代原炸弹数，同花顺/登基炸/普通炸统一纳入牌力）
    plan.bomb_score = min(plan.power_score / NORM_MAX_POWER, 1.0)

    # 手数 0.3（轮次越少越好）
    plan.rounds_score = max(0.0, 1.0 - n_rounds / NORM_MAX_ROUNDS)

    # 静态回收评估 0.1
    plan.recovery_score = _score_recovery_static(plan, plan.cur_rank)

    # 灵活性 0.1（已不含单张 — 去单化路径 A）
    plan.flexibility_score = _score_flexibility(plan, all_plans)

    # 去单化 0.2（路径 B — 显式惩罚单张多）
    plan.de_singleton_score = _score_de_singleton(plan)

    # 5 维加权总分
    plan.score = (
        0.3 * plan.bomb_score +
        0.3 * plan.rounds_score +
        0.1 * plan.recovery_score +
        0.1 * plan.flexibility_score +
        0.2 * plan.de_singleton_score
    )


# ── 方案枚举 ──────────────────────────────────────────────

def _upgrade_bombs_with_wilds(
    trips: List[List[str]], wilds: List[str],
) -> Tuple[List[List[str]], List[List[str]], List[str]]:
    """用逢人配将三张升级为四头炸（三张+1 wild=4头炸）。
    返回 (new_bombs, remaining_trips, remaining_wilds)。
    """
    if not wilds or not trips:
        return [], trips[:], list(wilds)

    new_bombs: List[List[str]] = []
    wilds_consumed = 0
    rem_trips = list(trips)

    for trip in trips:
        if wilds_consumed < len(wilds):
            new_bombs.append(trip + [wilds[wilds_consumed]])
            wilds_consumed += 1
        else:
            break

    remaining_trips = rem_trips[len(new_bombs):]
    remaining_wilds = wilds[wilds_consumed:]
    return new_bombs, remaining_trips, remaining_wilds


def _build_plan(
    singles: List[str], pairs: List[List[str]], trips: List[List[str]],
    bombs: List[List[str]], straights: List[List[str]],
    straight_flushes: List[List[str]], three_pairs: List[List[List[str]]],
    wilds: List[str],
    cur_rank: str, strategy: str,
    three_with_twos: List[Tuple[List[str], List[str]]] | None = None,
    steel_plates: List[List[List[str]]] | None = None,
) -> GroupingPlan:
    """构建一个 GroupingPlan，对牌型内排序。"""
    plan = GroupingPlan(cur_rank=cur_rank, strategy=strategy)
    plan.singles = sorted(singles, key=lambda c: _card_rank_value(c, cur_rank))
    plan.pairs = sorted(pairs, key=lambda p: _card_rank_value(p[0], cur_rank))
    plan.trips = sorted(trips, key=lambda t: _card_rank_value(t[0], cur_rank))
    plan.bombs = sorted(bombs, key=lambda b: _card_rank_value(b[0], cur_rank))
    plan.straights = sorted(straights, key=lambda s: _card_rank_value(s[0], cur_rank))
    plan.straight_flushes = sorted(straight_flushes, key=lambda sf: _card_rank_value(sf[0], cur_rank))
    plan.three_pairs = sorted(three_pairs, key=lambda tp: _card_rank_value(tp[0][0], cur_rank))
    if three_with_twos:
        plan.three_with_twos = sorted(three_with_twos, key=lambda twt: _card_rank_value(twt[0][0], cur_rank))
    if steel_plates:
        plan.steel_plates = sorted(steel_plates, key=lambda sp: _card_rank_value(sp[0][0], cur_rank))
    plan.wild_cards = list(wilds)
    # 未消耗的癞子作为单张加入 singles（癞子可单独出牌）
    if wilds:
        plan.singles = sorted(
            plan.singles + list(wilds),
            key=lambda c: _card_rank_value(c, cur_rank),
        )
    return plan


def _enumerate_plans(
    hand_cards: List[str], cur_rank: str,
) -> List[GroupingPlan]:
    """
    GUA-062 P2：多策略枚举组牌方案（含回溯变体）+ SF_FIRST 主力策略。

    策略（共 6 个，STRAIGHT_FIRST 已融入 SF_FIRST Phase 1c）:
      - SF_FIRST:      同花顺优先（天然→wild→拆≤1炸→炸弹→平级循环）★ 主力
      - BOMB_FIRST:    优先保留炸弹（不拆炸弹去组顺子）
      - BALANCED:      平衡方案（先组顺子再组炸弹）
      - ROUND_OPTIMAL: 最少轮次（优先牌型组合）
      - NO_STRAIGHTS:  不组任何顺子/同花顺（最小组牌，P2 回溯变体）
      - ALL_COMBOS:    拆一切组复杂牌型（最大组牌，P2 回溯变体）

    返回 6 个方案（去重后可能 4-6 个有效方案）。
    """
    groups = _rank_groups(hand_cards, cur_rank)
    wilds = groups.get("__wild__", [])
    del groups["__wild__"]

    singles, pairs, trips, bombs = _basic_classify(groups)
    plans: List[GroupingPlan] = []

    # ── 策略 0: SF_FIRST — 同花顺优先（天然→配牌→拆≤1炸→炸弹）→ 平级去单化循环 ──
    # 设计规范 2026-06-18 v2:
    #   1. Phase 1: 同花顺检测（天然→wild→拆≤1炸辅助），非必要不拆两个炸
    #   2. Phase 2: 剩余牌重组炸弹
    #   3. Phase 3-5: Multi-pass 平级循环 — 三连对/钢板/顺子/三带二/对子 无先后顺序
    #   Phase 1b 枚举所有可行同花顺候选（不同花色/不同 rank），各生成一个方案
    sf_bomb4 = []   # 4-card bombs (reserved, can sacrifice 1 for SF)
    sf_bomb5 = []   # 5+ card bombs (safe to break → 4 remain)
    sf_nb = []      # non-bomb cards (<4 per rank)
    for rank, cards in groups.items():
        n = len(cards)
        if n >= 5:
            sf_bomb5.extend(cards)
        elif n == 4:
            sf_bomb4.extend(cards)
        else:
            sf_nb.extend(cards)

    # Phase 1: SF detection
    sf_cards = sf_nb + sf_bomb5
    sf_cg = _rank_groups(sf_cards, cur_rank)
    del sf_cg["__wild__"]
    sf_cs, sf_cp, sf_ct, sf_cb = _basic_classify(sf_cg)
    for bb in sf_cb:
        sf_cs.extend(bb)  # flatten any accidental 4+ groups from 5plus cards

    # 1a: Natural SF (no wilds, no bombs touched)
    sf_nat, sf_n1, sf_p1, sf_t1, sf_w1 = _detect_straight_flushes(
        sf_cs, sf_cp, sf_ct, cur_rank, [])

    def _make_sf_first_plan(
        nat: List[List[str]], wild: List[List[str]],
        rem_singles: List[str], rem_pairs: List[List[str]],
        rem_trips: List[List[str]], rem_wilds: List[str],
        bomb4_pool: List[str],
    ) -> GroupingPlan:
        """Phase 2-5: 从 SF 消耗后的剩余牌生成完整方案。"""
        sf_all_rem = (rem_singles +
                      [x for p in rem_pairs for x in p] +
                      [x for t in rem_trips for x in t] +
                      bomb4_pool)
        sf_rg = _rank_groups(sf_all_rem, cur_rank)
        del sf_rg["__wild__"]
        sf_rs, sf_rp, sf_rt, sf_rbombs = _basic_classify(sf_rg)

        sf_straights: List[List[str]] = []
        sf_tp: List[List[List[str]]] = []
        sf_sp: List[List[List[str]]] = []
        sf_twt: List[Tuple[List[str], List[str]]] = []
        sf_rw = list(rem_wilds)
        sf_s = list(sf_rs)
        sf_p = [p[:] for p in sf_rp]
        sf_t = [t[:] for t in sf_rt]

        MAX_OUTER_PASS = 20
        for _pass_outer in range(MAX_OUTER_PASS):
            prev_total = len(sf_s) + sum(len(p) for p in sf_p) * 2 + sum(len(t) for t in sf_t) * 3

            new_tp, sf_p = _detect_three_pairs(sf_p, cur_rank)
            sf_tp.extend(new_tp)

            new_sp, sf_t = _detect_steel_plate(sf_t, cur_rank)
            sf_sp.extend(new_sp)

            MAX_INNER_PASS = 20
            for _pass_inner in range(MAX_INNER_PASS):
                new_st, sf_s, sf_p, sf_t, sf_rw = _detect_straights(
                    sf_s, sf_p, sf_t, cur_rank, sf_rw)
                if not new_st:
                    break
                sf_straights.extend(new_st)

            new_twt, sf_t, sf_p = _detect_three_with_two(sf_t, sf_p, cur_rank)
            sf_twt.extend(new_twt)

            rank_map: Dict[str, List[str]] = {}
            for c in sf_s:
                r = _parse_rank(c)
                rank_map.setdefault(r, []).append(c)
            sf_s = []
            for r, cards in rank_map.items():
                while len(cards) >= 2:
                    sf_p.append([cards.pop(0), cards.pop(0)])
                sf_s.extend(cards)

            curr_total = len(sf_s) + sum(len(p) for p in sf_p) * 2 + sum(len(t) for t in sf_t) * 3
            if curr_total >= prev_total:
                break

        sf_up, sf_t, sf_rw = _upgrade_bombs_with_wilds(sf_t, sf_rw)
        all_sf = nat + wild
        return _build_plan(sf_s, sf_p, sf_t, sf_rbombs + sf_up,
                           sf_straights, all_sf, sf_tp, sf_rw, cur_rank, "SF_FIRST",
                           three_with_twos=sf_twt, steel_plates=sf_sp)

    # 1b: Wild-assisted SF — 枚举所有候选同花顺
    sf_plans_with_sf: List[GroupingPlan] = []
    for sf_idx in range(10):
        sf_w, sf_n, sf_p, sf_t, sf_rw = _detect_straight_flushes(
            sf_n1, sf_p1, sf_t1, cur_rank, wilds, return_idx=sf_idx)
        if not sf_w:
            break
        plan = _make_sf_first_plan(sf_nat, sf_w, sf_n, sf_p, sf_t, sf_rw, sf_bomb4)
        sf_plans_with_sf.append(plan)

    # 1c: Bomb-assisted SF — 非必要不拆两个炸弹组同花顺（≤1 bomb）
    if not sf_plans_with_sf and sf_bomb4:
        bomb4_sorted = sorted(sf_bomb4, key=lambda c: _card_rank_value(c, cur_rank))
        sacrifice = bomb4_sorted[:4]  # 1 bomb = 4 cards
        bomb4_rem = bomb4_sorted[4:]

        bc_singles = sf_n1 + sacrifice
        bc_pairs = [p[:] for p in sf_p1]
        bc_trips = [t[:] for t in sf_t1]

        # Try natural SF with bomb cards
        bc_sf_nat, bc_s1, bc_p1, bc_t1, _ = _detect_straight_flushes(
            bc_singles, bc_pairs, bc_trips, cur_rank, [])

        # Try wild-assisted SF (enumerate candidates)
        for sf_idx in range(10):
            bc_sf_w, bc_s2, bc_p2, bc_t2, bc_w2 = _detect_straight_flushes(
                bc_s1, bc_p1, bc_t1, cur_rank, wilds, return_idx=sf_idx)
            if not bc_sf_w:
                break
            plan = _make_sf_first_plan(bc_sf_nat, bc_sf_w, bc_s2, bc_p2, bc_t2, bc_w2, bomb4_rem)
            sf_plans_with_sf.append(plan)

    if sf_plans_with_sf:
        plans.extend(sf_plans_with_sf)
    else:
        # 无同花顺：用原始逻辑生成基底方案
        plan = _make_sf_first_plan([], [], sf_n1, sf_p1, sf_t1, sf_w1, sf_bomb4)
        plans.append(plan)

    # ── 策略 1: BOMB_FIRST — 完整保留炸弹，三连对→同花顺→顺子→wilds升炸（SF优先用wilds） ──
    bf_singles, bf_pairs, bf_trips = singles[:], pairs[:], trips[:]
    bf_three_pairs, bf_rem_pairs = _detect_three_pairs(bf_pairs, cur_rank)
    bf_sf, bf_s1, bf_p1, bf_t1, bf_wilds1 = _detect_straight_flushes(
        bf_singles, bf_rem_pairs, bf_trips, cur_rank, wilds)
    bf_straights, bf_s2, bf_p2, bf_t2, bf_wilds2 = _detect_straights(
        bf_s1, bf_p1, bf_t1, cur_rank, bf_wilds1)
    bf_new_bombs, bf_rem_trips, bf_wilds3 = _upgrade_bombs_with_wilds(bf_t2, bf_wilds2)

    plan = _build_plan(bf_s2, bf_p2, bf_rem_trips, bombs[:] + bf_new_bombs,
                       bf_straights, bf_sf, bf_three_pairs, bf_wilds3, cur_rank, "BOMB_FIRST")
    plans.append(plan)

    # ── 策略 2: STRAIGHT_FIRST — 已注释（拆弹逻辑已融入 SF_FIRST Phase 1c） ──
    # sf_three_pairs, sf_rem_pairs = _detect_three_pairs(pairs[:], cur_rank)
    # sf_all_singles = singles[:]
    # for b in bombs:
    #     sf_all_singles.extend(b)
    #
    # sf_sf, sf_s1, sf_p1, sf_t1, sf_wilds1 = _detect_straight_flushes(
    #     sf_all_singles, sf_rem_pairs, trips[:], cur_rank, wilds)
    # sf_straights, sf_s2, sf_p2, sf_t2, sf_wilds2 = _detect_straights(
    #     sf_s1, sf_p1, sf_t1, cur_rank, sf_wilds1)
    #
    # rem_all = sf_s2 + [x for p in sf_p2 for x in p] + [x for t in sf_t2 for x in t]
    # rem_groups = _rank_groups(rem_all, cur_rank)
    # del rem_groups["__wild__"]
    # sf_rem_s, sf_rem_p, sf_rem_t, sf_new_bombs = _basic_classify(rem_groups)
    # sf_up_bombs, sf_rem_t2, sf_wilds3 = _upgrade_bombs_with_wilds(sf_rem_t, sf_wilds2)
    #
    # plan = _build_plan(sf_rem_s, sf_rem_p, sf_rem_t2, sf_new_bombs + sf_up_bombs,
    #                    sf_straights, sf_sf, sf_three_pairs, sf_wilds3, cur_rank, "STRAIGHT_FIRST")
    # plans.append(plan)

    # ── 策略 3: BALANCED — 保留炸弹，三连对→同花顺→顺子→wilds升炸（SF优先用wilds） ──
    bal_singles, bal_pairs, bal_trips = singles[:], pairs[:], trips[:]
    bal_three_pairs, bal_rem_pairs = _detect_three_pairs(bal_pairs, cur_rank)
    bal_sf, bal_s1, bal_p1, bal_t1, bal_wilds1 = _detect_straight_flushes(
        bal_singles, bal_rem_pairs, bal_trips, cur_rank, wilds)
    bal_straights, bal_s2, bal_p2, bal_t2, bal_wilds2 = _detect_straights(
        bal_s1, bal_p1, bal_t1, cur_rank, bal_wilds1)
    bal_new_bombs, bal_rem_trips, bal_wilds3 = _upgrade_bombs_with_wilds(bal_t2, bal_wilds2)

    plan = _build_plan(bal_s2, bal_p2, bal_rem_trips, bombs[:] + bal_new_bombs,
                       bal_straights, bal_sf, bal_three_pairs, bal_wilds3, cur_rank, "BALANCED")
    plans.append(plan)

    # ── 策略 4: ROUND_OPTIMAL — 三连对优先→拆弹→同花顺→顺子→wilds升炸（SF优先用wilds） ──
    ro_three_pairs, ro_rem_pairs = _detect_three_pairs(pairs[:], cur_rank)
    ro_all_singles = singles[:]
    for b in bombs:
        ro_all_singles.extend(b)

    ro_sf, ro_s1, ro_p1, ro_t1, ro_wilds1 = _detect_straight_flushes(
        ro_all_singles, ro_rem_pairs, trips[:], cur_rank, wilds)
    ro_straights, ro_s2, ro_p2, ro_t2, ro_wilds2 = _detect_straights(
        ro_s1, ro_p1, ro_t1, cur_rank, ro_wilds1)

    rem_all = ro_s2 + [x for p in ro_p2 for x in p] + [x for t in ro_t2 for x in t]
    rem_groups = _rank_groups(rem_all, cur_rank)
    del rem_groups["__wild__"]
    ro_rem_s, ro_rem_p, ro_rem_t, ro_new_bombs = _basic_classify(rem_groups)
    ro_up_bombs, ro_rem_t2, ro_wilds3 = _upgrade_bombs_with_wilds(ro_rem_t, ro_wilds2)

    plan = _build_plan(ro_rem_s, ro_rem_p, ro_rem_t2, ro_new_bombs + ro_up_bombs,
                       ro_straights, ro_sf, ro_three_pairs, ro_wilds3, cur_rank, "ROUND_OPTIMAL")
    plans.append(plan)

    # ── P2 回溯变体 5: NO_STRAIGHTS — 三连对(含trip降级)→顺子→升炸 ──
    # trip 降级规则：若某 rank 有 trip 但无 pair，将 trip 拆为 pair+single
    # 以扩展三连对搜索空间（如 999 trip 拆为 99+9，启用 778899 三连对）
    ns_singles_base = list(singles)
    ns_pairs_base = list(pairs)
    ns_trips_base = list(trips)

    # Step 1: trips 拆为 pair + single
    tp_idx_to_leftover: Dict[int, str] = {}
    tp_pair_set: set = set()  # frozenset of trip-pair
    for i, t in enumerate(ns_trips_base):
        pair = sorted(t, key=lambda c: _card_rank_value(c, cur_rank))[:2]
        # 用 Counter 差值取 leftover（处理重复牌如 C2,C2）
        leftover_counts = Counter(t) - Counter(pair)
        leftover = list(leftover_counts.elements())[0]
        ns_pairs_base.append(pair)
        tp_idx_to_leftover[i] = leftover
        tp_pair_set.add(frozenset(pair))

    # Step 2: 检测三连对
    ns_three_pairs, ns_rem_pairs = _detect_three_pairs(ns_pairs_base, cur_rank)

    # Step 3: 分类 remaining pairs → 还原未消耗的 trip
    ns_restored_trips: List[List[str]] = []
    ns_extra_singles: List[str] = []
    ns_real_pairs: List[List[str]] = []

    for rp in ns_rem_pairs:
        key = frozenset(rp)
        if key in tp_pair_set:
            # 此 pair 来自 trip → 恢复为完整 trip
            ns_restored_trips.append(rp + [next(
                tp_idx_to_leftover[i] for i, t in enumerate(ns_trips_base)
                if frozenset(sorted(t, key=lambda c: _card_rank_value(c, cur_rank))[:2]) == key
            )])
        else:
            ns_real_pairs.append(rp)

    # Step 4: 被三连对消耗的 trip-pair，其 leftover 加入 singles
    consumed_tp = set()
    for tp in ns_three_pairs:
        for pr in tp:
            consumed_tp.add(frozenset(pr))
    for key in consumed_tp:
        if key in tp_pair_set:
            for i, t in enumerate(ns_trips_base):
                tp_key = frozenset(sorted(t, key=lambda c: _card_rank_value(c, cur_rank))[:2])
                if tp_key == key:
                    ns_extra_singles.append(tp_idx_to_leftover[i])
                    break

    ns_all_singles = ns_singles_base + ns_extra_singles

    # ── 变体 5a: trips 不参与顺子（保留给 wild 升炸） ──
    ns_straights_a: List[List[str]] = []
    ns_s_a, ns_p_a = ns_all_singles, ns_real_pairs
    MAX_ST_PASS = 10
    for _ in range(MAX_ST_PASS):
        new_st, ns_s_a, ns_p_a, _, _ = _detect_straights(
            ns_s_a, ns_p_a, [], cur_rank, [])
        if not new_st:
            break
        ns_straights_a.extend(new_st)
    ns_new_bombs_a, ns_rem_trips_a, ns_wr_a = _upgrade_bombs_with_wilds(ns_restored_trips, wilds)
    plan_a = _build_plan(ns_s_a, ns_p_a, ns_rem_trips_a, bombs[:] + ns_new_bombs_a,
                         ns_straights_a, [], ns_three_pairs, ns_wr_a, cur_rank,
                         "NO_STRAIGHTS")
    plans.append(plan_a)

    # ── 变体 5b: trips 可参与顺子（如无单 9 仅 10-K，AAA 出 1 张 A 组 10-A 顺子） ──
    ns_straights_b: List[List[str]] = []
    ns_s_b, ns_p_b, ns_t_b = ns_all_singles, ns_real_pairs, ns_restored_trips
    for _ in range(MAX_ST_PASS):
        new_st, ns_s_b, ns_p_b, ns_t_b, _ = _detect_straights(
            ns_s_b, ns_p_b, ns_t_b, cur_rank, [])
        if not new_st:
            break
        ns_straights_b.extend(new_st)
    ns_new_bombs_b, ns_rem_trips_b, ns_wr_b = _upgrade_bombs_with_wilds(ns_t_b, wilds)
    plan_b = _build_plan(ns_s_b, ns_p_b, ns_rem_trips_b, bombs[:] + ns_new_bombs_b,
                         ns_straights_b, [], ns_three_pairs, ns_wr_b, cur_rank,
                         "NO_STRAIGHTS")
    plans.append(plan_b)

    # ── P2 回溯变体 6: ALL_COMBOS — 三连对→拆弹→同花顺→双重顺子→wilds升炸（SF优先用wilds） ──
    ac_three_pairs, ac_rem_pairs = _detect_three_pairs(pairs[:], cur_rank)
    ac_all_singles = singles[:]
    for b in bombs:
        ac_all_singles.extend(b)

    ac_sf, ac_s1, ac_p1, ac_t1, ac_wilds1 = _detect_straight_flushes(
        ac_all_singles, ac_rem_pairs, trips[:], cur_rank, wilds)
    ac_straights, ac_s2, ac_p2, ac_t2, ac_wilds2 = _detect_straights(
        ac_s1, ac_p1, ac_t1, cur_rank, ac_wilds1)
    ac_straights2, ac_s3, ac_p3, ac_t3, ac_wilds3 = _detect_straights(
        ac_s2, ac_p2, ac_t2, cur_rank, ac_wilds2)
    ac_all_straights = ac_straights + ac_straights2

    rem_all = ac_s3 + [x for p in ac_p3 for x in p] + [x for t in ac_t3 for x in t]
    rem_groups = _rank_groups(rem_all, cur_rank)
    del rem_groups["__wild__"]
    ac_rem_s, ac_rem_p, ac_rem_t, ac_new_bombs = _basic_classify(rem_groups)
    ac_up_bombs, ac_rem_t2, ac_wilds4 = _upgrade_bombs_with_wilds(ac_rem_t, ac_wilds3)

    plan = _build_plan(ac_rem_s, ac_rem_p, ac_rem_t2, ac_new_bombs + ac_up_bombs,
                       ac_all_straights, ac_sf, ac_three_pairs, ac_wilds4, cur_rank, "ALL_COMBOS")
    plans.append(plan)

    # ── v2 评分：生成全部方案后统一评分（灵活性需要跨方案比较） ──
    for p in plans:
        _score_plan_v2(p, plans)

    return plans


# ── 特征提取 ──────────────────────────────────────────────

def _extract_features(
    plans: List[GroupingPlan], hand_cards: List[str], cur_rank: str,
) -> List[float]:
    """
    从枚举方案中提取 24 维组牌特征向量。
    
    维度设计（24 维，0~1 归一化）：
      0:  best_plan_score          — 最优方案分
      1:  best_num_rounds_norm     — 最优方案轮数归一化
      2:  best_bomb_count_norm     — 最优方案炸弹数
      3:  best_straight_count_norm — 最优方案顺子+同花顺数
      4:  best_trip_count_norm     — 最优方案三张数
      5:  best_pair_count_norm     — 最优方案对子数
      6:  best_single_count_norm   — 最优方案单张数（去单化反向）
      7:  best_strategy_id         — 最优方案策略 ID / 6（6 策略）
      8:  score_variance           — 方案间评分方差
      9:  n_plans                  — 方案数 / 6（最多 6 方案）
     10:  bomb_score_range         — 各方案炸弹数极差 / 4
     11:  rounds_range_norm        — 各方案轮数极差 / 10
     12:  best_has_sf              — 最优方案有同花顺 → 1
     13:  best_has_straight        — 最优方案有顺子 → 1
     14:  wild_count_norm          — 逢人配数 / 2
     15:  longest_run_norm         — 最长连续 rank 数 / 12
     16:  control_card_norm        — 控场牌 (SB+HR+curRank) 数 / 6
     17:  avg_bomb_level_norm      — 炸弹平均等级 / 15
     18:  plan_stability           — 首末方案分差 → 稳定性
     19:  best_rounds_vs_worst     — 最优 vs 最差轮数差
     20:  strategy_agreement       — 有多少方案选了同策略 / n_plans
     21:  max_possible_rounds_norm — 最优轮数 / 手牌总数
     22:  struct_density           — (对子+三张+顺子) / 手牌数
     23:  card_utilization         — 已分组牌 / 总手牌
    """
    if not plans:
        return [0.0] * GROUPING_ENGINE_DIM

    plans_sorted = sorted(plans, key=lambda p: p.score, reverse=True)
    best = plans_sorted[0]
    worst = plans_sorted[-1]
    n = len(hand_cards)

    # 基本特征
    f = [0.0] * GROUPING_ENGINE_DIM
    f[0] = best.score
    f[1] = 1.0 - min(best.num_rounds() / max(n, 1), 1.0)
    f[2] = min(len(best.bombs) / NORM_MAX_BOMBS, 1.0)
    f[3] = min((len(best.straights) + len(best.straight_flushes)) / NORM_MAX_STRAIGHTS, 1.0)
    f[4] = min(len(best.trips) / 3.0, 1.0)
    f[5] = min(len(best.pairs) / NORM_MAX_PAIRS, 1.0)
    f[6] = max(0.0, 1.0 - len(best.singles) / max(n, 1))

    strategy_ids = {"SF_FIRST": 0, "BOMB_FIRST": 1, "BALANCED": 2,
                    "ROUND_OPTIMAL": 3, "NO_STRAIGHTS": 4, "ALL_COMBOS": 5}
    f[7] = strategy_ids.get(best.strategy, 0) / 6.0

    # 方案多样性
    scores = [p.score for p in plans_sorted]
    f[8] = min(max(0.0, (max(scores) - min(scores)) if len(scores) > 1 else 0.0) * 5, 1.0)
    f[9] = min(len(plans) / 6.0, 1.0)

    bomb_counts = [len(p.bombs) for p in plans_sorted]
    f[10] = min((max(bomb_counts) - min(bomb_counts)) / NORM_MAX_BOMBS, 1.0) if bomb_counts else 0.0

    round_counts = [p.num_rounds() for p in plans_sorted]
    f[11] = min((max(round_counts) - min(round_counts)) / 10.0, 1.0) if round_counts else 0.0

    f[12] = 1.0 if len(best.straight_flushes) > 0 else 0.0
    f[13] = 1.0 if len(best.straights) > 0 else 0.0

    # 手牌全局特征
    wilds = sum(1 for c in hand_cards if _is_wild(c, cur_rank))
    f[14] = min(wilds / NORM_MAX_WILDS, 1.0)

    # 最长连续 rank
    rank_set = set()
    for c in hand_cards:
        r = _parse_rank(c)
        if r in RANKS:
            rank_set.add(RANKS.index(r))
    sorted_ranks = sorted(rank_set)
    longest = 1
    cur = 1
    for i in range(1, len(sorted_ranks)):
        if sorted_ranks[i] == sorted_ranks[i - 1] + 1:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 1
    f[15] = min(longest / NORM_MAX_LONGEST_RUN, 1.0) if sorted_ranks else 0.0

    # 控场牌
    control = sum(1 for c in hand_cards if _parse_rank(c) in ("B", "R") or _parse_rank(c) == cur_rank)
    f[16] = min(control / 6.0, 1.0)

    # 平均炸弹等级
    if best.bombs:
        avg_level = sum(_card_rank_value(b[0], cur_rank) for b in best.bombs) / len(best.bombs)
        f[17] = min(avg_level / 15.0, 1.0)
    else:
        f[17] = 0.0

    # 方案稳定性
    f[18] = max(0.0, 1.0 - (best.score - worst.score) * 2) if len(plans_sorted) > 1 else 1.0

    # 最优 vs 最差轮数（clamp：最优可能轮数更多但总分更高）
    rounds_diff = best.num_rounds() - worst.num_rounds()
    f[19] = max(0.0, min(1.0, 0.5 + rounds_diff / max(n, 1) * 0.5))

    # 策略一致性
    strategy_counts = Counter(p.strategy for p in plans_sorted)
    f[20] = max(strategy_counts.values()) / len(plans_sorted)

    # 最优轮数 / 手牌总数
    f[21] = 1.0 - min(best.num_rounds() / max(n, 1), 1.0)

    # 结构密度
    struct_count = (len(best.trips) + len(best.pairs) + len(best.straights) +
                    len(best.straight_flushes) + len(best.three_pairs))
    f[22] = min(struct_count / max(n, 1) * 3, 1.0)

    # 牌利用率
    used = (len(best.singles) + sum(len(p) for p in best.pairs) +
            sum(len(t) for t in best.trips) + sum(len(b) for b in best.bombs) +
            sum(len(s) for s in best.straights) + sum(len(sf) for sf in best.straight_flushes) +
            sum(sum(len(pr) for pr in tp) for tp in best.three_pairs))
    f[23] = min(used / max(n, 1), 1.0)

    return f


# ── 主入口 ────────────────────────────────────────────────

def enumerate_groupings(
    hand_cards: List[str],
    cur_rank: str = "2",
) -> Tuple[GroupingPlan, List[GroupingPlan]]:
    """
    枚举所有组牌方案并返回最优方案 + 全部方案。

    Args:
        hand_cards: 手牌列表，格式 ["S2", "H3", "C3", "SB", ...]
        cur_rank:   当前级牌，默认 "2"

    Returns:
        (best_plan, all_plans)
          - best_plan:  评分最高的 GroupingPlan
          - all_plans:  所有方案（按评分降序）
    """
    if not hand_cards:
        empty = GroupingPlan(cur_rank=cur_rank, strategy="empty")
        return empty, [empty]

    plans = _enumerate_plans(hand_cards, cur_rank)
    plans.sort(key=lambda p: p.score, reverse=True)
    return plans[0], plans


def extract_grouping_features(
    hand_cards: List[str],
    cur_rank: str = "2",
) -> List[float]:
    """
    提取 24 维组牌特征向量（GUA-062 v2 增强版）。

    先枚举多方案（6 策略含回溯变体）→ 4 维加权评分 → 提取方案级+多样性特征。
    纯函数，无状态，推理延迟 < 5ms。

    Args:
        hand_cards: 手牌列表
        cur_rank:   当前级牌

    Returns:
        24 维 float list，范围 [0.0, 1.0]
    """
    _, plans = enumerate_groupings(hand_cards, cur_rank)
    return _extract_features(plans, hand_cards, cur_rank)


def get_grouping_engine_dim() -> int:
    """返回 grouping_engine 特征维度（= 24）。"""
    return GROUPING_ENGINE_DIM


# ── 兼容接口：与 old grouping_scanner 同名函数 ────────────

def extract_grouping_score(
    hand_cards: List[str],
    cur_rank: str = "2",
) -> List[float]:
    """
    兼容 grouping_scanner.extract_grouping_score 的接口。
    返回 24 维特征向量（原 grouping_scanner 返回 9 维）。
    """
    return extract_grouping_features(hand_cards, cur_rank)
