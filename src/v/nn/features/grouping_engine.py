# -*- coding: utf-8 -*-
"""
GUA-061→GUA-062 GroupingEngine — M3 组牌逻辑提取 + v2 升级（静态回收评估+灵活性+真回溯）。

设计约束（§7.4 升格硬约束）：
  - 纯函数，无类状态，无 if-else 硬规则决策
  - V7-internal：禁止 `from src.m.m3 import ...`
  - 多方案枚举（统一新流水线）+ 独立评分 + Top 3 输出（GUA-074）
  - 推理延迟 < 5ms（108 张手牌最坏情况）

2026-06-20 重构：统一新流水线
  所有策略统一使用：
    1. 同花顺检测（天然 → wild辅助，枚举所有 SF 候选）
    2. 拆弹 → singles 池（≤10 小炸可拆，J/Q/K/A 炸保护；**仅在 _make_plan_from_sf Step2、break_bombs=True 时执行**，不在 SF 池预拆）
    3. wild → 升炸（逢人配固化炸弹，避免被顺子/三带二消耗）
    4. {} 多 pass 循环（三带二 ↔ 三连对 / 顺子 可换序，见 GUA-109
       THREE_PAIR_FIRST / STRAIGHT_BEFORE_TWT；
       默认三带二 → 顺子1 → 顺子2 → 三连对 → 钢板
       → trip降级+三连对扩展+trip恢复 → 单张合并对子）
    5. 剩余牌重分类
  生成方案：每个 SF 候选 → SF_FIRST/ROUND_OPTIMAL/ALL_COMBOS ×3
  无 SF 时 → BOMB_FIRST/ROUND_OPTIMAL/ALL_COMBOS ×3（基准）

GUA-062 v2 升级（2026-06-18）：
  - P0-A：静态回收评估（方案中牌型兜底大牌比例，文档权重 0.3）
  - P0-B：灵活性评分（牌型多样性 + 方案差异性，文档权重 0.2）
  - P0-C：评分公式 5 维加权（牌力0.3+手数0.3+回收0.1+灵活0.1+去单化0.2）
  - P1：牌力计分 + 角色定位（登基牌+3/普通炸+2/赘牌-1）
  - P2：真回溯多方案（3 策略 × SF候选 枚举）

与 grouping_scanner.py (GUA-054) 的关系：
  - grouping_scanner: 9 维软信号（统计计数，不枚举方案）
  - grouping_engine:  24 维特征（多方案枚举 + 方案级特征）
  - grouping_scanner 保留作为兼容基线，grouping_engine 作为增强替代
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple, Optional, NamedTuple
from collections import Counter
from dataclasses import dataclass, field
import copy
import warnings
from functools import lru_cache

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
NORM_MAX_POWER = 10.0

# GUA-084：5+ 同点炸弹至少保留 4 张为炸
BOMB_CORE_MIN = 4

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

    def to_card_mask(self) -> Tuple[Dict[str, tuple], Dict[int, str], Dict[int, List[str]]]:
        """构建牌级组牌掩码，供前置过滤使用。

        返回 (mask, group_type_map, group_members)：
          mask: Dict[card_str, (group_id, is_core, group_size)]
            - 同牌串多枚（如双 SQ）共 key，lookup 仍可用；**张数/成员以 group_members 为准**
          group_type_map: Dict[group_id, type_string]
          group_members: Dict[group_id, List[str]] — 保留重复牌串的多集合真源（4~8 星炸等）
            - type_string: "Bomb"/"StraightFlush"/"straight"/"trips"/"pair"
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
        group_members: Dict[int, List[str]] = {}

        # ── 收集所有牌组 ──
        # groups: List[(cards, is_core, type_string)]
        groups: List[Tuple[List[str], bool, str]] = []

        # 核心牌型（炸弹/同花顺）
        for b in self.bombs:
            groups.append((list(b), True, "Bomb"))
        for sf in self.straight_flushes:
            groups.append((list(sf), True, "StraightFlush"))

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
            group_members.setdefault(-1, []).append(s)

        # ── 分配 group_id ──
        gid = 0
        for group_cards, is_core, type_str in groups:
            gsize = len(group_cards)
            is_core_f = 1.0 if is_core else 0.0
            group_type_map[gid] = type_str
            group_members[gid] = list(group_cards)
            for card in group_cards:
                mask[card] = (gid, is_core_f, gsize)
            gid += 1

        return mask, group_type_map, group_members


# ── 牌面解析 ──────────────────────────────────────────────


@lru_cache(maxsize=256)
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


@lru_cache(maxsize=256)
def _parse_suit(card: str) -> str:
    """从 'S2' 提取花色。"""
    if len(card) >= 2 and card[0] in SUITS:
        return card[0]
    return ""


@lru_cache(maxsize=256)
def _is_wild(card: str, cur_rank: str) -> bool:
    """判断是否为逢人配（H+curRank）。"""
    return card == f"H{cur_rank}"


@lru_cache(maxsize=256)
def _card_rank_value(card: str, cur_rank: str) -> int:
    """
    返回牌的相对大小值（用于排序）。
    cur_rank → 15, B → 16, R → 17, 其余按 2..A → 2..14
    """
    r = _parse_rank(card)
    if r in ("SB", "B"):
        return 16
    if r in ("HR", "R"):
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


def _split_bomb_for_break(
    bomb: List[str], peel_count: int, cur_rank: str,
) -> Tuple[List[str], List[str]]:
    """GUA-084: 保留 ≥4 张炸核；peel_count=0 时整炸保留。"""
    sorted_bomb = sorted(bomb, key=lambda c: (_card_rank_value(c, cur_rank), c))
    n = len(sorted_bomb)
    if peel_count <= 0 or n <= BOMB_CORE_MIN:
        return sorted_bomb, []
    max_peel = n - BOMB_CORE_MIN
    peel_count = min(peel_count, max_peel)
    keep_n = n - peel_count
    return sorted_bomb[:keep_n], sorted_bomb[keep_n:]


def _break_bombs_into_pool(
    reserved_bombs: List[List[str]],
    *,
    break_bombs: bool,
    cur_rank: str,
    large_bomb_peel: int,
    safe_to_break_fn,
) -> Tuple[List[List[str]], List[str]]:
    """GUA-084 Step2：n≥5 限量 peel；n≤4 且可拆则整炸进 singles。"""
    if not break_bombs:
        return [b[:] for b in reserved_bombs], []
    remaining: List[List[str]] = []
    peeled_singles: List[str] = []
    for rb in reserved_bombs:
        n = len(rb)
        if n > BOMB_CORE_MIN:
            kept, peeled = _split_bomb_for_break(rb, large_bomb_peel, cur_rank)
            remaining.append(kept)
            peeled_singles.extend(peeled)
        elif safe_to_break_fn(rb):
            peeled_singles.extend(rb)
        else:
            remaining.append(rb[:])
    return remaining, peeled_singles


def _bomb_core_ranks(bombs: List[List[str]]) -> Set[str]:
    return {_parse_rank(b[0]) for b in bombs if len(b) >= BOMB_CORE_MIN}


def _pool_rank_counts(
    singles: List[str], pairs: List[List[str]], trips: List[List[str]],
) -> Counter:
    counts: Counter = Counter()
    for c in singles:
        counts[_parse_rank(c)] += 1
    for pr in pairs:
        r = _parse_rank(pr[0])
        counts[r] += len(pr)
    for tr in trips:
        r = _parse_rank(tr[0])
        counts[r] += len(tr)
    return counts


def _pair_reserved_for_twt(
    pair: List[str],
    bomb_core_ranks: Set[str],
    rank_counts: Counter,
) -> bool:
    """GUA-084 R-G084-1：≥4 同点 / 炸核 rank 的对子不配三带二。
    GUA-097 follow-up：大小王对子不配三带二（王太贵，保留为天王炸/炸弹材料）。"""
    r = _parse_rank(pair[0])
    if r in JOKERS:
        return True  # 大小王不做三带二 kick
    if r in bomb_core_ranks:
        return True
    return rank_counts.get(r, 0) >= 4


def _large_bomb_peel_options(bombs: List[List[str]]) -> List[int]:
    """Phase A：大炸 peel 只枚举 0 与 max_peel 两个端点。"""
    max_peel = 0
    for b in bombs:
        if len(b) > BOMB_CORE_MIN:
            max_peel = max(max_peel, len(b) - BOMB_CORE_MIN)
    if max_peel <= 0:
        return [0]
    return [0, max_peel]


# ── GUA-084/108：手牌级同花顺候选（花色 multiset，支持 n≥5 炸定向 peel）──

SfPlanEntry = Tuple[
    List[List[str]], List[List[str]], List[str], List[List[str]],
    List[List[str]], List[str], List[List[str]],
]


def _sf_rank_windows() -> List[List[str]]:
    windows: List[List[str]] = []
    for start in range(len(RANKS)):
        if start + 5 > len(RANKS):
            break
        windows.append([RANKS[start + k] for k in range(5)])
    windows.append(["A", "2", "3", "4", "5"])
    return windows


def _bombs_after_peel_one(bombs: List[List[str]], card: str) -> Optional[List[List[str]]]:
    """从 len>n≥5 的炸中剥下 card 一张；炸弹个数不变，张数 n→n-1。"""
    for idx, bomb in enumerate(bombs):
        if len(bomb) <= BOMB_CORE_MIN or card not in bomb:
            continue
        new_bombs = [b[:] for b in bombs]
        peeled_bomb = new_bombs[idx][:]
        peeled_bomb.remove(card)
        new_bombs[idx] = peeled_bomb
        return new_bombs
    return None


def _sf_card_sources(
    suit: str,
    rank: str,
    hand_ct: Counter,
    bombs: List[List[str]],
    used: Counter,
) -> List[Tuple[str, Optional[int]]]:
    """可填入同花顺某一 rank 的来源：(card, peel_bomb_idx|None)；四炸内牌不可用。"""
    options: List[Tuple[str, Optional[int]]] = []
    bomb_ct: Counter = Counter()
    peel_bomb_idx: Optional[int] = None
    for bi, bomb in enumerate(bombs):
        for card in bomb:
            if _parse_suit(card) == suit and _parse_rank(card) == rank:
                bomb_ct[card] += 1
                if len(bomb) > BOMB_CORE_MIN:
                    peel_bomb_idx = bi
    for card, total in hand_ct.items():
        if total <= 0 or card in JOKERS:
            continue
        if _parse_suit(card) != suit or _parse_rank(card) != rank:
            continue
        bound = bomb_ct.get(card, 0)
        free = total - bound - used.get(card, 0)
        if free > 0:
            options.append((card, None))
        if peel_bomb_idx is not None and card in bombs[peel_bomb_idx]:
            if used.get(card, 0) < total:
                options.append((card, peel_bomb_idx))
    return list(dict.fromkeys(options))


def _assign_sf_in_suit_window(
    suit: str,
    target_ranks: List[str],
    hand_ct: Counter,
    wilds: List[str],
    bombs: List[List[str]],
) -> List[Tuple[List[str], List[str], List[List[str]]]]:
    """DFS：枚举该花色窗口下所有可行 StraightFlush（含 wild / 大炸 peel）。"""
    results: List[Tuple[List[str], List[str], List[List[str]]]] = []
    seen_sf: Set[Tuple[str, ...]] = set()
    used_cards: Counter = Counter()

    def dfs(
        idx: int,
        chosen: List[str],
        wilds_used: List[str],
        bombs_state: List[List[str]],
        peeled_bomb_idxs: Set[int],
    ) -> None:
        if idx == len(target_ranks):
            key = tuple(sorted(chosen))
            if key not in seen_sf:
                seen_sf.add(key)
                results.append((chosen[:], wilds_used[:], [b[:] for b in bombs_state]))
            return

        rank = target_ranks[idx]
        for card, peel_idx in _sf_card_sources(
            suit, rank, hand_ct, bombs_state, used_cards,
        ):
            if peel_idx is not None:
                if peel_idx in peeled_bomb_idxs:
                    continue
                next_bombs = _bombs_after_peel_one(bombs_state, card)
                if next_bombs is None:
                    continue
                peeled_bomb_idxs.add(peel_idx)
                chosen.append(card)
                used_cards[card] += 1
                dfs(idx + 1, chosen, wilds_used, next_bombs, peeled_bomb_idxs)
                used_cards[card] -= 1
                chosen.pop()
                peeled_bomb_idxs.discard(peel_idx)
            else:
                chosen.append(card)
                used_cards[card] += 1
                dfs(idx + 1, chosen, wilds_used, bombs_state, peeled_bomb_idxs)
                used_cards[card] -= 1
                chosen.pop()

        if wilds:
            for wi, wild in enumerate(wilds):
                if wild in wilds_used:
                    continue
                chosen.append(wild)
                wilds_used.append(wild)
                used_cards[wild] += 1
                dfs(idx + 1, chosen, wilds_used, bombs_state, peeled_bomb_idxs)
                used_cards[wild] -= 1
                wilds_used.pop()
                chosen.pop()

    dfs(0, [], [], [b[:] for b in bombs], set())
    return results


def _remainder_pools_after_sf(
    hand_cards: List[str],
    sf_cards: List[str],
    wilds_used: List[str],
    bombs: List[List[str]],
    cur_rank: str,
) -> Tuple[List[str], List[List[str]], List[List[str]], List[str]]:
    """SF 与保留炸弹之外的剩余牌 → singles/pairs/trips + 未用 wild。"""
    rem_ct: Counter = Counter(hand_cards)
    wild_ct = Counter(wilds_used)
    for card in sf_cards:
        # GUA-076 fix: wild 用于 SF 时必须从 rem_ct 扣减（此前仅扣 wild_ct，
        # 导致 rem_ct 仍含已消耗的 wild → leftover 多算 → plan 双计）
        rem_ct[card] -= 1
        if wild_ct.get(card, 0) > 0:
            wild_ct[card] -= 1

    bomb_ct: Counter = Counter()
    for bomb in bombs:
        for card in bomb:
            bomb_ct[card] += 1

    leftover: List[str] = []
    for card, count in rem_ct.items():
        bound = bomb_ct.get(card, 0)
        free = count - bound
        if free > 0:
            leftover.extend([card] * free)

    rg = _rank_groups(leftover, cur_rank)
    rem_wilds = list(rg.pop("__wild__", []))
    rem_s, rem_p, rem_t, extra_bombs = _basic_classify(rg)
    if extra_bombs:
        rem_s.extend(c for b in extra_bombs for c in b)
    return rem_s, rem_p, rem_t, rem_wilds


def _sf_plan_entry_key(entry: SfPlanEntry) -> Tuple:
    nat, wild, _, _, _, _, bombs = entry
    sf_key = tuple(sorted(tuple(sorted(sf)) for sf in (nat + wild)))
    bomb_key = tuple(tuple(sorted(b)) for b in bombs)
    return (sf_key, bomb_key)


def _enumerate_sf_hand_candidates(
    hand_cards: List[str],
    cur_rank: str,
    wilds_all: List[str],
    bombs: List[List[str]],
) -> List[SfPlanEntry]:
    """
    从整手牌按花色 multiset 枚举 StraightFlush 候选（GUA-084 peel + GUA-108 竞争方案）。

    不依赖 _basic_classify 的混花对/四炸划分，避免 Step1 误检 []。
    """
    hand_ct: Counter = Counter(
        c for c in hand_cards if not _is_wild(c, cur_rank)
    )
    wilds_for_sf = wilds_all[:] if wilds_all else [
        c for c in hand_cards if _is_wild(c, cur_rank)
    ]
    entries: List[SfPlanEntry] = []
    seen: Set[Tuple] = set()

    for suit in SUITS:
        for window in _sf_rank_windows():
            for sf_cards, wilds_used, bombs_after in _assign_sf_in_suit_window(
                suit, window, hand_ct, wilds_for_sf[:], bombs
            ):
                rem_s, rem_p, rem_t, rem_w = _remainder_pools_after_sf(
                    hand_cards, sf_cards, wilds_used, bombs_after, cur_rank
                )
                if wilds_used:
                    nat_sf: List[List[str]] = []
                    wild_sf = [sf_cards]
                else:
                    nat_sf = [sf_cards]
                    wild_sf = []
                # GUA-076 fix: rem_w 已含未用于 SF 的 wild（_remainder_pools_after_sf 正确扣减），
                # 不再重复添加 wilds_all（此前 L591 把 wild 加了两遍 → plan 双计）
                rem_w_full = rem_w
                entry: SfPlanEntry = (
                    nat_sf, wild_sf, rem_s, rem_p, rem_t, rem_w_full, bombs_after
                )
                key = _sf_plan_entry_key(entry)
                if key not in seen:
                    seen.add(key)
                    entries.append(entry)
    return entries


def _merge_sf_plan_entries(*entry_lists: List[SfPlanEntry]) -> List[SfPlanEntry]:
    merged: List[SfPlanEntry] = []
    seen: Set[Tuple] = set()
    for entries in entry_lists:
        for entry in entries:
            key = _sf_plan_entry_key(entry)
            if key not in seen:
                seen.add(key)
                merged.append(entry)
    return merged


def _append_unique_sf(all_sf: List[List[str]], candidate: List[str]) -> None:
    norm = sorted(candidate)
    for existing in all_sf:
        if sorted(existing) == norm:
            return
    all_sf.append(list(candidate))


def _classify_dissolved_bomb_cards(
    bomb_cards: List[str],
    cur_rank: str,
) -> Tuple[List[str], List[List[str]], List[List[str]], List[str]]:
    """将被定向拆解的炸弹牌回收到 singles/pairs/trips/wilds 池。

    GUA-108: 这里不把 4 张同点牌重新识别回炸弹，而是以「非炸牌池」形式回注，
    允许顺子检测先消费其中一部分，再由后续剩余牌重分类决定是否回收为 trips/pairs。
    """
    rank_groups = _rank_groups(list(bomb_cards), cur_rank)
    wilds = rank_groups.get("__wild__", [])
    if "__wild__" in rank_groups:
        del rank_groups["__wild__"]
    singles, pairs, trips = _classify_no_bombs(rank_groups)
    return singles, pairs, trips, list(wilds)


def _count_detectable_straights(
    singles: List[str],
    pairs: List[List[str]],
    trips: List[List[str]],
    wilds: List[str],
    cur_rank: str,
) -> int:
    """轻量预估当前牌池可直接检测出的顺子数量。"""
    straights, _, _, _, _ = _detect_straights(
        list(singles),
        [p[:] for p in pairs],
        [t[:] for t in trips],
        cur_rank,
        list(wilds),
    )
    return len(straights)


def _eligible_straight_bridge_bombs(
    rem_s: List[str],
    rem_p: List[List[str]],
    rem_t: List[List[str]],
    rem_w: List[str],
    reserved_bombs: List[List[str]],
    cur_rank: str,
) -> List[int]:
    """GUA-108: 找出“拆 4 炸后能新增顺子候选”的炸弹下标。

    约束：
      - 仅考虑 4 张炸弹，避免把 5 炸及以上直接拉入“为成顺而拆炸”分支
      - 必须确实让可检测顺子数增加，避免无收益地枚举噪声候选
    """
    base_straight_count = _count_detectable_straights(rem_s, rem_p, rem_t, rem_w, cur_rank)
    eligible: List[int] = []
    for idx, bomb in enumerate(reserved_bombs):
        if len(bomb) != BOMB_CORE_MIN:
            continue
        add_s, add_p, add_t, add_w = _classify_dissolved_bomb_cards(bomb, cur_rank)
        trial_count = _count_detectable_straights(
            rem_s + add_s,
            rem_p + add_p,
            rem_t + add_t,
            rem_w + add_w,
            cur_rank,
        )
        if trial_count > base_straight_count:
            eligible.append(idx)
    return eligible


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
    singles: Optional[List[str]] = None,
    bomb_core_ranks: Optional[Set[str]] = None,
    wilds: Optional[List[str]] = None,
) -> Tuple[List[Tuple[List[str], List[str]]], List[List[str]], List[List[str]]]:
    """
    从三张和对子中检测三带二。
    返回 (three_with_twos, remaining_trips, remaining_pairs)。
    贪心匹配：每个 trip 搭配一个 pair，消耗 5 张牌 → 1 轮（相比 trip+pair 单独出省 1 轮）。
    GUA-084：跳过炸核 rank / pool 内 ≥4 张同点的对子。
    GUA-236：可选 wilds（就地消费）——对子+逢人配升三头再带另一对，避免
    「先顺剥 trip 剩两对+配子」无法组 TWT、被迫升炸拆顺。
    """
    rem_w = wilds if wilds is not None else []
    if (not trips and not (rem_w and len(pairs) >= 2)) or not pairs:
        return [], trips[:], pairs[:]

    pool_s = list(singles or [])
    reserved_ranks = bomb_core_ranks or set()
    remaining_trips = [t[:] for t in trips]
    remaining_pairs = [p[:] for p in pairs]
    three_with_twos: List[Tuple[List[str], List[str]]] = []

    # 贪心：按 rank 排序三张（从小到大优先让小 trip 吃小对，保留大对作独立跟牌）
    sorted_trips = sorted(remaining_trips, key=lambda t: _card_rank_value(t[0], cur_rank))
    # GUA-156: pairs 也按 rank 排序，保证小 trip 吃小对（原按发牌序，大对被误消耗）
    remaining_pairs.sort(key=lambda p: _card_rank_value(p[0], cur_rank))
    for trip in sorted_trips:
        rank_counts = _pool_rank_counts(pool_s, remaining_pairs, remaining_trips)
        pair_idx = None
        for i, pr in enumerate(remaining_pairs):
            if not _pair_reserved_for_twt(pr, reserved_ranks, rank_counts):
                pair_idx = i
                break
        if pair_idx is None:
            break
        pair = remaining_pairs.pop(pair_idx)
        three_with_twos.append((trip, pair))
        remaining_trips.remove(trip)

    # GUA-236: 配子 + 对子 → 三头，再带另一对
    while rem_w and len(remaining_pairs) >= 2:
        rank_counts = _pool_rank_counts(pool_s, remaining_pairs, remaining_trips)
        trip_base = remaining_pairs.pop(0)
        wing_idx = None
        for i, pr in enumerate(remaining_pairs):
            if not _pair_reserved_for_twt(pr, reserved_ranks, rank_counts):
                wing_idx = i
                break
        if wing_idx is None:
            remaining_pairs.insert(0, trip_base)
            break
        wing = remaining_pairs.pop(wing_idx)
        three_with_twos.append((trip_base + [rem_w.pop(0)], wing))

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


def _cards_high_rank_value(cards: List[str]) -> int:
    """一组牌的高端普通 rank 值（不含级牌特殊 15）。

    用于 _score_power 小顺子/小三连对减分判断：A 在 wrap 顺子（含 2）中当 1，
    避免级牌算 15、A 算 14 绕过「≤6 小牌型减分」（A2345 → 5，TJQKA → 14）。
    """
    ranks = [_parse_rank(c) for c in cards]
    if "A" in ranks and "2" in ranks:
        vals = [1 if r == "A" else _rank_to_value(r) for r in ranks]
    else:
        vals = [_rank_to_value(r) for r in ranks]
    return max(vals)


# ── 顺子检测 ──────────────────────────────────────────────

def _detect_straights(
    singles: List[str], pairs: List[List[str]], trips: List[List[str]],
    cur_rank: str, wilds: List[str], start_pos: int = 0,
) -> Tuple[List[List[str]], List[str], List[List[str]], List[List[str]], List[str]]:
    """
    从剩余牌中检测顺子（支持百搭（含百搭）填补缺口）。
    返回 (straights, remaining_singles, remaining_pairs, remaining_trips, remaining_wilds)。
    贪心策略：找最长连续 rank 段 → 5 张窗口扫描 → 缺口用 wilds 填补。

    GUA-187（2026-08-05）：start_pos 多窗口竞争。
    同一连续段允许从不同窗口起点扫描（如 2-6 / 3-7 / 4-8 并存），由上层枚举
    多个 start_pos 变体、评分择优，避免单窗口贪心漏枚举更优组法（如 Botzone
    27 张手牌：3-7 顺 + 对8 优于 4-8 顺 + 散单 3/8）。

    GUA-063 去小单化策略（2026-06-18）：
    - 窗口扫描从低→高（而非高→低）。原因：
      ① 掼蛋核心原则：去小单化——越小的单越难顺掉，组顺子首要目标就是吸收小单。
        如手牌 2-7 六连张，优先组 2-6 而非 3-7，把大单 7 留给其他组合（对子/三带二）。
      ② 大顺子的压制力在动态出牌中体现（逼炸/盖牌），初始组牌不应为此牺牲去小单化。
      ③ 单牌有灵活性——大单（8-K-A）比小单（2-3-4）更容易找到搭档形成对子或三条。

    GUA-164（2026-07-23）：A→2 wrap 包接段允许 1 个 RANKS-gap 用 1 张百搭填充。
    原版只数 strict RANKS-consecutive；现在允许 gap=1 时插入 `__WILD_<rank>_SLOT__` 标记，
    后续窗扫描遇到标记位直接消费 1 张百搭。这让 A-2-3(百搭)-4-5 这种含 wild 槽的
    包接顺子能被枚举出来。
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

    # 找最长连续 rank 段（strict consecutive，no wild slot in seg_ranks）
    best_start = 0
    best_len = 0
    best_is_wrap = False
    best_wrap_seg_ranks = None  # 含 __WILD_*_SLOT__ 标记
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
    # GUA-164：允许「gap=1 + 1 wild 填洞」，把 wild 槽插入 seg_ranks。
    wrap_seg_backward = None
    wrap_seg_forward = None

    # (a) Backward wrap：A → K → Q → ...（A 在末尾，A=14）— 需要自然 A 在高位 + 2 在低位
    if (len(rank_indices) > 1 and rank_indices[-1] == 'A' and rank_indices[0] == '2'
            and 'A' in card_by_rank and '2' in card_by_rank):
        # GUA-187（2026-08-05）：修正 wrap 段长度劫持 bug。
        # 原实现把 tail(A→K→…→2) 与 head(2→…→A) 首尾拼接成 25 长度往返段，
        # 段长 > 自然段长，导致 chosen_seg 被劫持、窗口从 A(高位) 反向扫描，
        # 违背 GUA-063「低→高窗口扫描、去小单化」原则（如 27 张 Botzone 手牌
        # 漏枚举 3-7 顺、H3/H4 落单）。
        # 修正：A 当 1 起头连接低位连续段（与 forward wrap 同义），长度 ≤ 6。
        wrap_seg_backward = ['A']
        wrap_bwd_wilds = 0
        for r2 in ('2', '3', '4', '5', '6'):
            if r2 in rank_indices:
                wrap_seg_backward.append(r2)
            elif wrap_bwd_wilds < available_wilds:
                wrap_seg_backward.append(f'__WILD_{r2}_SLOT__')
                wrap_bwd_wilds += 1
            else:
                break
            if len(wrap_seg_backward) >= 6:
                break
        if len(wrap_seg_backward) < 5:
            wrap_seg_backward = None

    # (b) Forward wrap：A 当 1 起头 → 2 → 3(wild) → 4 → 5 → ...（GUA-164 新增）
    # 不要求 A 是自然牌（A 可以是级牌/百搭），只要有自然牌可续接即可。
    # 例：curRank=A 时 HA 是百搭，仍可组 A(=1)-2-C2-3(SB百搭)-4-C4-5-H5。
    if len(rank_indices) > 0:
        wrap_seg_forward = ['A']
        wrap_fwd_wilds = 0
        cur_pos = RANKS.index('2')
        while len(wrap_seg_forward) < 6 and cur_pos < len(RANKS):
            next_rank = RANKS[cur_pos]
            if next_rank == 'A':
                break
            if next_rank in rank_indices:
                wrap_seg_forward.append(next_rank)
            elif wrap_fwd_wilds < available_wilds:
                wrap_seg_forward.append(f'__WILD_{next_rank}_SLOT__')
                wrap_fwd_wilds += 1
            else:
                break
            cur_pos += 1
        if len(wrap_seg_forward) < 5:
            wrap_seg_forward = None

    # GUA-164：选 wrap 段 — 同长度时优先 forward（A 当 1 起头）。
    # forward 适配用户特定诉求（A-2-3(百搭)-4-5），且通常使用松散单张而非拆组对；
    # 若用户希望枚举两个方向，需在更上层评分函数上做（_score_decompose 自然会给多 straights 加分）。
    # 顺序先 forward 后 backward 同长度时先用 forward。
    candidate_segs = [seg for seg in (wrap_seg_forward, wrap_seg_backward) if seg]
    chosen_seg = None
    for seg in candidate_segs:
        if len(seg) > best_len:
            chosen_seg = seg
            best_len = len(seg)
    if chosen_seg is None and candidate_segs:
        # 同长度：取 forward（已在列表首位）
        chosen_seg = candidate_segs[0]
        if len(chosen_seg) > best_len or best_is_wrap is False:
            # 严格大于才换 best；== 不再覆盖 best_len，但要换 seg
            if len(chosen_seg) >= best_len:
                best_len = len(chosen_seg)
                best_is_wrap = True
                best_wrap_seg_ranks = chosen_seg
    elif chosen_seg is not None:
        best_is_wrap = True
        best_wrap_seg_ranks = chosen_seg

    # 若最长段 < 5，无顺子（wrap 的 wild 槽已纳入长度统计）
    if best_len < 5:
        return [], singles[:], pairs[:], trips[:], list(wilds)

    # 统计每种牌面出现次数
    total_available = Counter()
    for r in rank_indices:
        for c in card_by_rank[r]:
            total_available[c] += 1

    straights = []
    used_cards = Counter()
    wilds_consumed = 0

    # 从最长段取顺子
    if best_is_wrap:
        seg_ranks = best_wrap_seg_ranks  # 可能含 __WILD_*_SLOT__ 标记
    else:
        seg_ranks = rank_indices[best_start:best_start + best_len]
    # GUA-187：多窗口竞争 —— 允许从非 0 起点扫描（如 3-7 而非 2-6），
    # 由上层枚举多个 start_pos 变体后评分择优。
    pos = min(start_pos, max(len(seg_ranks) - 5, 0))
    pos_max = len(seg_ranks) - 5
    while pos <= pos_max:
        window_ranks = seg_ranks[pos:pos + 5]
        # A→2 包接段：A 只能当 1 用（窗口第一位），跳过 A 在中间/末尾的无效窗口
        if best_is_wrap and 'A' in window_ranks and window_ranks[0] != 'A':
            pos += 1
            continue
        straight_cards = []
        tentative = Counter()
        tent_wilds_used = 0
        success = True

        for r in window_ranks:
            # GUA-164：显式 wild 槽位 —— 必须消费 1 张百搭
            if isinstance(r, str) and r.startswith('__WILD_') and r.endswith('_SLOT__'):
                if wilds_consumed + tent_wilds_used < available_wilds:
                    straight_cards.append(wilds[wilds_consumed + tent_wilds_used])
                    tent_wilds_used += 1
                else:
                    success = False
                    break
                continue
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
      - 同花顺 +3（牌面最大）
      - 五星炸 +2
      - 四头炸 +2
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

    # 登基牌炸弹 +3：同花顺（牌面最大）
    score += len(plan.straight_flushes) * 3

    # 炸弹计分：五星炸+2，四头炸+2（级牌四头不再额外加分）
    for b in plan.bombs:
        n = len(b)
        if n >= 6:
            score += 3          # 6张及以上炸弹
        elif n == 5:
            score += 2          # 五星炸
        elif n == 4:
            score += 2          # 四头炸

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

    # 整牌型结构加分：每个顺子 +1，每个三带二 +1
    # 抵消小牌罚分对结构强度手牌的误杀（如 SF+炸+2顺+TWT 不应因散5被打到助攻）
    score += len(plan.straights)
    score += len(plan.three_with_twos)
    score += len(plan.steel_plates)

    # 多炸加分：双炸及更多时额外 +2，反映多炸防守深度优势
    # 双炸 4+4 > 单炸 5+TWT 的结构强度，弥补小对子罚分对手数的误杀
    if len(plan.bombs) >= 2:
        score += 2

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
        # 用普通 rank 高端值判小顺子：A2345 wrap 顺子 A 当 1（高端=5），
        # 级牌在顺子中不享受 15 特殊值，避免小顺子减分被绕过
        if _cards_high_rank_value(s) <= rank6_limit:
            score -= 1

    for tp in plan.three_pairs:
        # tp = [[pair1], [pair2], [pair3]] — 每个对子 2 张，共 6 张
        all_cards = [c for pair in tp for c in pair]
        if _cards_high_rank_value(all_cards) <= rank6_limit:
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


def determine_score_tier(score: float) -> str:
    """
    GUA-062 总分角色分级（2026-06-20）：
      根据 4 维加权总分划分牌力档次，独立于 power_score 的角色定位。
      让 NN 同时看到「火力角色」+「结构档次」两个信号。

      阈值基于 11 副真实手牌样本：
        - ≥0.50 → 天胡
        - 0.40-0.50 → 好牌
        - 0.30-0.40 → 尚可
        - 0.20-0.30 → 偏弱
        - <0.20 → 烂牌
    """
    if score >= 0.50:
        return "天胡"
    elif score >= 0.40:
        return "好牌"
    elif score >= 0.30:
        return "尚可"
    elif score >= 0.20:
        return "偏弱"
    else:
        return "烂牌"


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

    权重调优 2026-06-20：
      - 牌力分 0.5（含炸弹+同花顺+登基牌+稀有牌型-减分，归一化到 NORM_MAX_POWER）
      - 手数 0.3
      - 静态回收评估 0.1
      - 灵活性 0.1
      - 去单化已移除（牌力分权重从0.3→0.5，去单化0.2砍掉）
    """
    n_rounds = plan.num_rounds()

    # 牌力计分 + 角色定位（先算，因为总分用它）
    plan.power_score = _score_power(plan, plan.cur_rank)
    plan.role = determine_role(plan.power_score)

    # 牌力分 0.5（替代原炸弹数，同花顺/登基炸/普通炸统一纳入牌力）
    plan.bomb_score = min(plan.power_score / NORM_MAX_POWER, 1.0)

    # 手数 0.3（轮次越少越好）
    plan.rounds_score = max(0.0, 1.0 - n_rounds / NORM_MAX_ROUNDS)

    # 静态回收评估 0.1
    plan.recovery_score = _score_recovery_static(plan, plan.cur_rank)

    # 灵活性 0.1
    plan.flexibility_score = _score_flexibility(plan, all_plans)

    # 4 维加权总分
    plan.score = (
        0.5 * plan.bomb_score +
        0.3 * plan.rounds_score +
        0.1 * plan.recovery_score +
        0.1 * plan.flexibility_score
    )
    plan.score_tier = determine_score_tier(plan.score)


# ── 方案枚举 ──────────────────────────────────────────────

def _upgrade_bombs_with_wilds(
    trips: List[List[str]], wilds: List[str], cur_rank: str = "",
) -> Tuple[List[List[str]], List[List[str]], List[str]]:
    """用逢人配将三张升级为四头炸（三张+1 wild=4头炸）。
    返回 (new_bombs, remaining_trips, remaining_wilds)。

    GUA-XXX: 钢板兼容 — 红桃配优先给非钢板 Trips。
    Part A: 有其他 Trips 时红桃配不给钢板 Trips
    Part B: 全部 Trips 仅能组成钢板时，不组钢板，红桃配+一个 Trip=炸弹
    """
    if not wilds or not trips:
        return [], trips[:], list(wilds)

    # GUA-XXX: 检测钢板潜力（连续 rank 的 trip 对）
    sp_indices: Set[int] = set()
    if len(trips) >= 2 and cur_rank:
        indexed = sorted(
            enumerate(trips),
            key=lambda x: _card_rank_value(x[1][0], cur_rank),
        )
        for i in range(len(indexed) - 1):
            idx1, t1 = indexed[i]
            idx2, t2 = indexed[i + 1]
            r1, r2 = _parse_rank(t1[0]), _parse_rank(t2[0])
            if r1 in RANKS and r2 in RANKS:
                v1, v2 = RANKS.index(r1), RANKS.index(r2)
                if v2 == v1 + 1 or (v1 == RANKS.index("A") and v2 == RANKS.index("2")):
                    sp_indices.add(idx1)
                    sp_indices.add(idx2)

    new_bombs: List[List[str]] = []
    wilds_consumed = 0

    if sp_indices:
        non_sp = [(i, t) for i, t in enumerate(trips) if i not in sp_indices]
        sp_items = [(i, t) for i, t in enumerate(trips) if i in sp_indices]

        if non_sp:
            # Part A: 有其他 Trips → wild 先给非钢板 trips
            for _i, trip in non_sp:
                if wilds_consumed < len(wilds):
                    new_bombs.append(trip + [wilds[wilds_consumed]])
                    wilds_consumed += 1
            # 仍有剩余 wild → 给钢板 trips
            for _i, trip in sp_items:
                if wilds_consumed < len(wilds):
                    new_bombs.append(trip + [wilds[wilds_consumed]])
                    wilds_consumed += 1
        else:
            # Part B: 全部 trips 仅能组成钢板 → 不组钢板，wild 升炸
            for _i, trip in sp_items:
                if wilds_consumed < len(wilds):
                    new_bombs.append(trip + [wilds[wilds_consumed]])
                    wilds_consumed += 1
    else:
        # 无钢板潜力：正常升炸
        for trip in trips:
            if wilds_consumed < len(wilds):
                new_bombs.append(trip + [wilds[wilds_consumed]])
                wilds_consumed += 1
            else:
                break

    remaining_trips = trips[wilds_consumed:]
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


def _run_multi_pass_loop(
    singles: List[str], pairs: List[List[str]], trips: List[List[str]],
    wilds: List[str], cur_rank: str, double_straights: bool,
    bomb_core_ranks: Optional[Set[str]] = None,
    three_pair_first: bool = False,
    straight_before_twt: bool = False,
    straight_start_offset: int = 0,
) -> Tuple[
    List[str], List[List[str]], List[List[str]], List[str],
    List[List[str]], List[List[List[str]]], List[List[List[str]]],
    List[Tuple[List[str], List[str]]],
]:
    """
    新流水线 Step 4：{} 多 pass 循环（2026-06-20 重构）。

    每轮依次（默认）：三带二 → 顺子1 → 顺子2(可选) → 三连对 → 钢板
            → trip降级+三连对扩展+trip恢复 → 单张合并对子
    GUA-109：`three_pair_first=True` 时每轮先三连对再三带二，使 334455 等与双三带二竞争方案并存。
    GUA-109：`straight_before_twt=True` 时每轮先顺子再三带二，使 6-10 顺子与 JJJ+66 等竞争方案并存。
    GUA-187：`straight_start_offset` 透传给 _detect_straights 实现多窗口竞争
    （同一连续段尝试不同窗口起点，评分择优）。
    循环直到无变化（退化为不变）。

    返回 (singles, pairs, trips, wilds, straights, three_pairs, steel_plates, three_with_twos)
    """
    s = list(singles)
    p = [pp[:] for pp in pairs]
    t = [tt[:] for tt in trips]
    w = list(wilds)

    straights: List[List[str]] = []
    three_pairs: List[List[List[str]]] = []
    steel_plates: List[List[List[str]]] = []
    three_with_twos: List[Tuple[List[str], List[str]]] = []

    MAX_PASS = 20
    for _pass_idx in range(MAX_PASS):
        prev_total = len(s) + sum(len(pp) for pp in p) * 2 + sum(len(tt) for tt in t) * 3

        # 1/5. 三带二 ↔ 三连对 ↔ 顺子（GUA-109 竞争分支：换序但不删另一检测）
        if straight_before_twt:
            new_st, s, p, t, w = _detect_straights(
                s, p, t, cur_rank, w, start_pos=straight_start_offset)
            straights.extend(new_st)

        if three_pair_first:
            new_tp, p = _detect_three_pairs(p, cur_rank)
            three_pairs.extend(new_tp)
            new_twt, t, p = _detect_three_with_two(
                t, p, cur_rank, singles=s, bomb_core_ranks=bomb_core_ranks,
                wilds=w)
            three_with_twos.extend(new_twt)
        else:
            new_twt, t, p = _detect_three_with_two(
                t, p, cur_rank, singles=s, bomb_core_ranks=bomb_core_ranks,
                wilds=w)
            three_with_twos.extend(new_twt)

        # 2. 三张 — 保留 trip 结构（不做额外检测，trip 在步骤 7 降级前保持原样）

        # 3. 顺子（第 1 轮；straight_before_twt 已在步骤 1 处理）
        if not straight_before_twt:
            new_st, s, p, t, w = _detect_straights(
                s, p, t, cur_rank, w, start_pos=straight_start_offset)
            straights.extend(new_st)

        # 4. 顺子（第 2 轮 / 双重）
        if double_straights:
            new_st2, s, p, t, w = _detect_straights(
                s, p, t, cur_rank, w, start_pos=straight_start_offset)
            straights.extend(new_st2)

        # 5. 三连对（默认序：三带二之后；three_pair_first 已在步骤 1 处理）
        if not three_pair_first:
            new_tp, p = _detect_three_pairs(p, cur_rank)
            three_pairs.extend(new_tp)

        # 6. 钢板
        new_sp, t = _detect_steel_plate(t, cur_rank)
        steel_plates.extend(new_sp)

        # 7. trip 降级 → 三连对扩展 → trip 恢复
        if t:
            # 7a: 每个 trip 拆为 pair + single
            tp_idx_to_leftover: Dict[int, str] = {}
            tp_pair_set: set = set()
            ext_pairs = list(p)
            for i, tt_ in enumerate(t):
                pair = sorted(tt_, key=lambda c: _card_rank_value(c, cur_rank))[:2]
                leftover_counts = Counter(tt_) - Counter(pair)
                leftover = list(leftover_counts.elements())[0]
                ext_pairs.append(pair)
                tp_idx_to_leftover[i] = leftover
                tp_pair_set.add(frozenset(pair))

            # 7b: 三连对检测（含降级产生的扩展对子）
            ext_tp, ext_rem_pairs = _detect_three_pairs(ext_pairs, cur_rank)
            if ext_tp:
                # 有新增三连对
                new_from_ext = ext_tp[len(three_pairs):] if len(ext_tp) > len(three_pairs) else ext_tp
                three_pairs.extend(new_from_ext if new_from_ext else [])

                # 7c: trip 恢复 — 未被三连对消耗的 trip-pair 恢复为完整 trip
                restored_trips: List[List[str]] = []
                extra_singles: List[str] = []
                real_pairs: List[List[str]] = []
                for rp in ext_rem_pairs:
                    key = frozenset(rp)
                    if key in tp_pair_set:
                        # 此 pair 来自 trip → 恢复为完整 trip
                        leftover_card = next(
                            tp_idx_to_leftover[i] for i, tt_ in enumerate(t)
                            if frozenset(sorted(tt_, key=lambda c: _card_rank_value(c, cur_rank))[:2]) == key
                        )
                        restored_trips.append(rp + [leftover_card])
                    else:
                        real_pairs.append(rp)

                # 7d: 被三连对消耗的 trip-pair，其 leftover 加入 singles
                consumed_tp = set()
                for new_tp_group in (new_from_ext if new_from_ext else ext_tp):
                    for pr in new_tp_group:
                        consumed_tp.add(frozenset(pr))
                for key in consumed_tp:
                    if key in tp_pair_set:
                        for tt_ in t:
                            tp_key = frozenset(sorted(tt_, key=lambda c: _card_rank_value(c, cur_rank))[:2])
                            if tp_key == key:
                                for i, orig_tt in enumerate(t):
                                    if orig_tt is tt_:
                                        extra_singles.append(tp_idx_to_leftover[i])
                                        break
                                break

                t = restored_trips
                p = real_pairs
                s.extend(extra_singles)

        # 8. 单张合并对子
        rank_map: Dict[str, List[str]] = {}
        for c in s:
            r = _parse_rank(c)
            if r not in rank_map:
                rank_map[r] = []
            rank_map[r].append(c)
        s = []
        for r, cards in rank_map.items():
            while len(cards) >= 2:
                p.append([cards.pop(0), cards.pop(0)])
            s.extend(cards)

        curr_total = len(s) + sum(len(pp) for pp in p) * 2 + sum(len(tt) for tt in t) * 3
        if curr_total >= prev_total:
            break

    return s, p, t, w, straights, three_pairs, steel_plates, three_with_twos


def _enumerate_plans(
    hand_cards: List[str], cur_rank: str, *, dedup: bool = True,
) -> List[GroupingPlan]:
    """
    GUA-062 P2 + 2026-06-20 重构：统一新流水线枚举组牌方案。

    新流水线（所有策略统一）：
      1. 同花顺检测（天然 → wild辅助 → 拆弹辅助，枚举所有SF候选）
      2. 拆弹 → singles 池（GUA-072：≤10 可拆；**仅 break_bombs=True 时在 Step2 执行**）
      3. wild → 升炸（逢人配固化炸弹，避免被后续顺子/三带二消耗）
      4. {} 多 pass 循环（三带二/三张/顺子1/顺子2/三连对/钢板/trip降级+trip恢复/单张合并对子）
      5. 剩余牌重分类

    生成方案：
      - SF_FIRST:     每个同花顺候选生成一个方案
      - ROUND_OPTIMAL: 拆弹 + 单顺子（基准）
      - ALL_COMBOS:    拆弹 + 双重顺子（最大组牌）
      - BOMB_FIRST:    不拆弹 + 单顺子（保炸弹）
      - BALANCED:      不拆弹 + 单顺子（同BOMB_FIRST，评分时依赖跨方案比较）
    """
    groups = _rank_groups(hand_cards, cur_rank)
    wilds_all = groups.get("__wild__", [])
    del groups["__wild__"]

    singles, pairs, trips, bombs = _basic_classify(groups)
    plans: List[GroupingPlan] = []

    # ═══════════════════════════════════
    # 拆弹阈值：仅 ≤10 的小炸弹可拆（GUA-072），保护 J/Q/K/A 炸弹
    # ═══════════════════════════════════
    def _safe_to_break_bomb(bomb: List[str]) -> bool:
        if not bomb:
            return True
        return _card_rank_value(bomb[0], cur_rank) <= 10

    # ═══════════════════════════════════
    # Step 1: 同花顺检测（枚举所有候选）
    # GUA-080/GUA-072 时序：SF 池仅用非炸牌；全部炸弹保留至 Step2，由 break_bombs 控制是否拆
    # ═══════════════════════════════════
    sf_singles = singles[:]
    sf_pairs = [p[:] for p in pairs]
    sf_trips = [t[:] for t in trips]
    all_bombs = [b[:] for b in bombs]

    sf_all_cards = (
        sf_singles
        + [x for px in sf_pairs for x in px]
        + [x for tx in sf_trips for x in tx]
    )
    sf_rg = _rank_groups(sf_all_cards, cur_rank)
    del sf_rg["__wild__"]
    sf_cs, sf_cp, sf_ct, sf_cb = _basic_classify(sf_rg)
    for bb in sf_cb:
        sf_cs.extend(bb)  # flatten any accidental bombs

    # 1a: 天然 SF（不用 wild）
    sf_nat, sf_n1, sf_p1, sf_t1, _ = _detect_straight_flushes(
        sf_cs, sf_cp, sf_ct, cur_rank, [])

    # 1b: 收集所有 SF 候选（天然 + wild 辅助）
    all_sf_results: List[Tuple[List[List[str]], List[List[str]], List[str], List[List[str]], List[List[str]], List[str], List[List[str]]]] = []
    if sf_nat:
        # 天然同花顺 → 第一个候选
        all_sf_results.append((sf_nat, [], sf_n1, sf_p1, sf_t1, wilds_all[:], all_bombs))

    # Wild-assisted SF — 枚举所有候选（不同花色/不同 rank）
    base_s = list(sf_n1) if sf_nat else sf_cs
    base_p = [p[:] for p in (sf_p1 if sf_nat else sf_cp)]
    base_t = [t[:] for t in (sf_t1 if sf_nat else sf_ct)]
    for sf_idx in range(10):
        sf_w, sf_n, sf_p, sf_t, sf_rw = _detect_straight_flushes(
            base_s, base_p, base_t, cur_rank, wilds_all, return_idx=sf_idx)
        if not sf_w:
            break
        all_sf_results.append((sf_nat, sf_w, sf_n, sf_p, sf_t, sf_rw, all_bombs))

    # 1c: 手牌 multiset 枚举（GUA-084 peel / GUA-108），补 Step1a/1b 漏检
    hand_sf_entries = _enumerate_sf_hand_candidates(
        hand_cards, cur_rank, wilds_all[:], all_bombs,
    )
    all_sf_results = _merge_sf_plan_entries(all_sf_results, hand_sf_entries)

    # ── SF candidate → 完整方案生成器 ──
    def _make_plan_from_sf(
        nat_sf: List[List[str]], wild_sf: List[List[str]],
        rem_s: List[str], rem_p: List[List[str]], rem_t: List[List[str]],
        rem_w: List[str], reserved_bombs: List[List[str]],
        strategy: str, break_bombs: bool, double_st: bool,
        large_bomb_peel: int = 0,
        bridge_bomb_idx: Optional[int] = None,
        three_pair_first: bool = False,
        straight_before_twt: bool = False,
        straight_start_offset: int = 0,
        upgrade_wild_bombs: bool = True,
    ) -> GroupingPlan:
        all_sf = nat_sf + wild_sf

        # Step 2: 拆弹 → singles 池（GUA-084：n≥5 保核限量 peel）
        pool_s = list(rem_s)
        pool_p = [p_[:] for p_ in rem_p]
        pool_t = [t_[:] for t_ in rem_t]
        pool_w = list(rem_w)

        remaining_bombs, peeled = _break_bombs_into_pool(
            reserved_bombs,
            break_bombs=break_bombs,
            cur_rank=cur_rank,
            large_bomb_peel=large_bomb_peel,
            safe_to_break_fn=_safe_to_break_bomb,
        )
        pool_s.extend(peeled)

        # Step 2b: 大炸 peel / 拆弹入池后重检同花顺（GUA-084/108）
        if peeled or large_bomb_peel > 0:
            redetect_nat, pool_s, pool_p, pool_t, pool_w = _detect_straight_flushes(
                pool_s, pool_p, pool_t, cur_rank, pool_w,
            )
            for sf in redetect_nat:
                _append_unique_sf(all_sf, sf)
            for sf_idx in range(10):
                sf_w, pool_s, pool_p, pool_t, pool_w = _detect_straight_flushes(
                    pool_s, pool_p, pool_t, cur_rank, pool_w, return_idx=sf_idx,
                )
                if not sf_w:
                    break
                _append_unique_sf(all_sf, sf_w[0])

        # GUA-108: 为成顺而定向拆 4 炸，候选只进枚举层，由评分决定是否值得。
        if bridge_bomb_idx is not None and 0 <= bridge_bomb_idx < len(remaining_bombs):
            bridge_bomb = remaining_bombs.pop(bridge_bomb_idx)
            add_s, add_p, add_t, add_w = _classify_dissolved_bomb_cards(
                bridge_bomb, cur_rank
            )
            pool_s.extend(add_s)
            pool_p.extend(add_p)
            pool_t.extend(add_t)
            pool_w.extend(add_w)

        bomb_core_ranks = _bomb_core_ranks(remaining_bombs)

        # Step 3: wild → 升炸（逢人配先固化，避免被顺子/三带二消耗）
        # GUA-236: upgrade_wild_bombs=False 保留配子给顺/TWT，禁止「为炸拆顺材料」
        if upgrade_wild_bombs:
            up_bombs, pool_t, pool_w = _upgrade_bombs_with_wilds(
                pool_t, pool_w, cur_rank)
            remaining_bombs = remaining_bombs + up_bombs
            bomb_core_ranks = _bomb_core_ranks(remaining_bombs)

        # Step 4: {} 多 pass 循环
        pool_s, pool_p, pool_t, pool_w, straights, three_pairs, steel_plates, twt_list = _run_multi_pass_loop(
            pool_s, pool_p, pool_t, pool_w, cur_rank, double_st, bomb_core_ranks,
            three_pair_first=three_pair_first,
            straight_before_twt=straight_before_twt,
            straight_start_offset=straight_start_offset)

        # Step 5: 剩余牌重分类
        rem_all = pool_s + [x for px in pool_p for x in px] + [x for tx in pool_t for x in tx]
        rem_rg = _rank_groups(rem_all, cur_rank)
        del rem_rg["__wild__"]
        rem_rs, rem_rp, rem_rt, new_bombs = _basic_classify(rem_rg)
        # _basic_classify 可能从剩余牌重新识别炸弹（4+ 同 rank）
        remaining_bombs = remaining_bombs + new_bombs

        return _build_plan(rem_rs, rem_rp, rem_rt, remaining_bombs,
                           straights, all_sf, three_pairs, pool_w, cur_rank, strategy,
                           three_with_twos=twt_list, steel_plates=steel_plates)

    # ═══════════════════════════════════
    # 生成各策略方案
    # ═══════════════════════════════════

    # GUA-187：顺子多窗口竞争 —— 顺子相关策略为每个 straight_start_offset 生成变体方案。
    # offset>0 时策略名加 `_OFF<n>` 后缀：dedup 键含 strategy，结构计数相同也会被去重，
    # 只有换策略名才能让 2-6 / 3-7 / 4-8 等窗口变体并存参与评分。
    STRAIGHT_OFFSETS = (0, 1, 2)

    def _add_plan_variants(
        nat: List[List[str]], wild: List[List[str]],
        rem_s: List[str], rem_p: List[List[str]], rem_t: List[List[str]],
        rem_w: List[str], res_b: List[List[str]],
        strategy: str, break_bombs: bool, double_st: bool,
        large_bomb_peel: int = 0,
        bridge_bomb_idx: Optional[int] = None,
        three_pair_first: bool = False,
        straight_before_twt: bool = False,
        offset_variants: bool = False,
        upgrade_wild_bombs: bool = True,
    ) -> None:
        offsets = STRAIGHT_OFFSETS if offset_variants else (0,)
        for off in offsets:
            plans.append(_make_plan_from_sf(
                nat, wild, rem_s, rem_p, rem_t, rem_w, res_b,
                f"{strategy}_OFF{off}" if off else strategy,
                break_bombs, double_st,
                large_bomb_peel=large_bomb_peel,
                bridge_bomb_idx=bridge_bomb_idx,
                three_pair_first=three_pair_first,
                straight_before_twt=straight_before_twt,
                straight_start_offset=off,
                upgrade_wild_bombs=upgrade_wild_bombs))

    if all_sf_results:
        # 有同花顺候选：SF 三策略 + GUA-084 BOMB_FIRST 保炸候选
        for nat, wild, rem_s, rem_p, rem_t, rem_w, res_b in all_sf_results:
            peel_opts = _large_bomb_peel_options(res_b)
            for peel in peel_opts:
                _add_plan_variants(
                    nat, wild, rem_s, rem_p, rem_t, rem_w, res_b,
                    "SF_FIRST", break_bombs=True, double_st=True,
                    large_bomb_peel=peel, offset_variants=True)
                _add_plan_variants(
                    nat, wild, rem_s, rem_p, rem_t, rem_w, res_b,
                    "ROUND_OPTIMAL", break_bombs=True, double_st=False,
                    large_bomb_peel=peel, offset_variants=True)
                _add_plan_variants(
                    nat, wild, rem_s, rem_p, rem_t, rem_w, res_b,
                    "ALL_COMBOS", break_bombs=True, double_st=True,
                    large_bomb_peel=peel, offset_variants=True)
            _add_plan_variants(
                nat, wild, rem_s, rem_p, rem_t, rem_w, res_b,
                "BOMB_FIRST", break_bombs=False, double_st=False,
                large_bomb_peel=0)
            _add_plan_variants(
                nat, wild, rem_s, rem_p, rem_t, rem_w, res_b,
                "THREE_PAIR_FIRST", break_bombs=True, double_st=False,
                large_bomb_peel=0, three_pair_first=True, offset_variants=True)
            _add_plan_variants(
                nat, wild, rem_s, rem_p, rem_t, rem_w, res_b,
                "STRAIGHT_BEFORE_TWT", break_bombs=True, double_st=False,
                large_bomb_peel=0, straight_before_twt=True, offset_variants=True)
            # GUA-236: 保留配子给顺+TWT，禁止为炸拆顺材料
            _add_plan_variants(
                nat, wild, rem_s, rem_p, rem_t, rem_w, res_b,
                "KEEP_WILD_ST_TWT", break_bombs=True, double_st=False,
                large_bomb_peel=0, straight_before_twt=True,
                upgrade_wild_bombs=False, offset_variants=True)
            for bridge_idx in _eligible_straight_bridge_bombs(
                rem_s, rem_p, rem_t, rem_w, res_b, cur_rank
            ):
                _add_plan_variants(
                    nat, wild, rem_s, rem_p, rem_t, rem_w, res_b,
                    "STRAIGHT_BRIDGE", break_bombs=False, double_st=False,
                    large_bomb_peel=0, bridge_bomb_idx=bridge_idx)
    else:
        # 无同花顺：生成 BOMB_FIRST + ROUND_OPTIMAL + ALL_COMBOS 基准方案
        peel_opts = _large_bomb_peel_options(all_bombs)
        for peel in peel_opts:
            _add_plan_variants(
                [], [], sf_n1, sf_p1, sf_t1, wilds_all[:], all_bombs,
                "ROUND_OPTIMAL", break_bombs=True, double_st=False,
                large_bomb_peel=peel, offset_variants=True)
            _add_plan_variants(
                [], [], sf_n1, sf_p1, sf_t1, wilds_all[:], all_bombs,
                "ALL_COMBOS", break_bombs=True, double_st=True,
                large_bomb_peel=peel, offset_variants=True)
            _add_plan_variants(
                [], [], sf_n1, sf_p1, sf_t1, wilds_all[:], all_bombs,
                "THREE_PAIR_FIRST", break_bombs=True, double_st=False,
                large_bomb_peel=peel, three_pair_first=True, offset_variants=True)
            _add_plan_variants(
                [], [], sf_n1, sf_p1, sf_t1, wilds_all[:], all_bombs,
                "STRAIGHT_BEFORE_TWT", break_bombs=True, double_st=False,
                large_bomb_peel=peel, straight_before_twt=True, offset_variants=True)
        _add_plan_variants(
            [], [], sf_n1, sf_p1, sf_t1, wilds_all[:], all_bombs,
            "BOMB_FIRST", break_bombs=False, double_st=False,
            large_bomb_peel=0)
        _add_plan_variants(
            [], [], sf_n1, sf_p1, sf_t1, wilds_all[:], all_bombs,
            "THREE_PAIR_FIRST", break_bombs=True, double_st=False,
            large_bomb_peel=0, three_pair_first=True, offset_variants=True)
        _add_plan_variants(
            [], [], sf_n1, sf_p1, sf_t1, wilds_all[:], all_bombs,
            "STRAIGHT_BEFORE_TWT", break_bombs=True, double_st=False,
            large_bomb_peel=0, straight_before_twt=True, offset_variants=True)
        # GUA-236: 保留配子给顺+TWT，禁止为炸拆顺材料
        _add_plan_variants(
            [], [], sf_n1, sf_p1, sf_t1, wilds_all[:], all_bombs,
            "KEEP_WILD_ST_TWT", break_bombs=True, double_st=False,
            large_bomb_peel=0, straight_before_twt=True,
            upgrade_wild_bombs=False, offset_variants=True)
        for bridge_idx in _eligible_straight_bridge_bombs(
            sf_n1, sf_p1, sf_t1, wilds_all[:], all_bombs, cur_rank
        ):
            _add_plan_variants(
                [], [], sf_n1, sf_p1, sf_t1, wilds_all[:], all_bombs,
                "STRAIGHT_BRIDGE", break_bombs=False, double_st=False,
                large_bomb_peel=0, bridge_bomb_idx=bridge_idx)

    # ═══════════════════════════════════
    # 去重：相同得分相同结构的方案只保留一个
    # ═══════════════════════════════════
    if dedup:
        seen_keys: set = set()
        deduped: List[GroupingPlan] = []
        for p in plans:
            key = (
                p.strategy,
                len(p.singles), len(p.pairs), len(p.trips), len(p.bombs),
                len(p.straights), len(p.straight_flushes), len(p.three_pairs),
                len(p.three_with_twos), len(p.steel_plates),
            )
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(p)
        plans = deduped

    # ── v2 评分：生成全部方案后统一评分（灵活性需要跨方案比较） ──
    for p in plans:
        _score_plan_v2(p, plans)

    return plans


@lru_cache(maxsize=128)
def _enumerate_plans_cached(
    hand_cards: Tuple[str, ...], cur_rank: str,
) -> Tuple[GroupingPlan, ...]:
    """Cache the pure default plan enumeration for repeated decision features."""
    return tuple(_enumerate_plans(list(hand_cards), cur_rank))


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
      9:  n_plans                  — 方案数 / 3（最多 3 方案，GUA-074）
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
                    "ROUND_OPTIMAL": 3, "NO_STRAIGHTS": 4, "ALL_COMBOS": 5,
                    "THREE_PAIR_FIRST": 6, "STRAIGHT_BEFORE_TWT": 7,
                    "KEEP_WILD_ST_TWT": 8, "STRAIGHT_BRIDGE": 9}
    base_strategy = best.strategy.split("_OFF")[0]
    f[7] = strategy_ids.get(base_strategy, 0) / 10.0

    # 方案多样性
    scores = [p.score for p in plans_sorted]
    f[8] = min(max(0.0, (max(scores) - min(scores)) if len(scores) > 1 else 0.0) * 5, 1.0)
    f[9] = min(len(plans) / 3.0, 1.0)

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

    # 牌利用率（GUA-076 修复：计入 three_with_twos 和 steel_plates）
    used = (len(best.singles) + sum(len(p) for p in best.pairs) +
            sum(len(t) for t in best.trips) + sum(len(b) for b in best.bombs) +
            sum(len(s) for s in best.straights) + sum(len(sf) for sf in best.straight_flushes) +
            sum(sum(len(pr) for pr in tp) for tp in best.three_pairs) +
            sum(len(twt[0]) + len(twt[1]) for twt in best.three_with_twos) +
            sum(sum(len(t) for t in sp) for sp in best.steel_plates))
    f[23] = min(used / max(n, 1), 1.0)

    return f


# ── 主入口 ────────────────────────────────────────────────

def _count_all_cards_in_plan(plan: GroupingPlan) -> int:
    """GUA-076：统计方案中所有牌张数（用于完整性校验）。"""
    count = (
        len(plan.singles)
        + sum(len(pr) for pr in plan.pairs)
        + sum(len(t) for t in plan.trips)
        + sum(len(b) for b in plan.bombs)
        + sum(len(s) for s in plan.straights)
        + sum(len(sf) for sf in plan.straight_flushes)
        + sum(sum(len(pr) for pr in tp) for tp in plan.three_pairs)
        + sum(len(twt[0]) + len(twt[1]) for twt in plan.three_with_twos)
        + sum(sum(len(t) for t in sp) for sp in plan.steel_plates)
    )
    return count


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
          - all_plans:  Top 3 方案（按评分降序，GUA-074）
    """
    if not hand_cards:
        empty = GroupingPlan(cur_rank=cur_rank, strategy="empty")
        return empty, [empty]

    plans = copy.deepcopy(_enumerate_plans_cached(tuple(hand_cards), cur_rank))

    # GUA-076：方案完整性校验 — 每个方案必须覆盖全部手牌
    # 2026-06-21 修复：不完整方案用 warning 记录并剔除，不崩溃
    expected = len(hand_cards)
    complete_plans: List[GroupingPlan] = []
    for i, p in enumerate(plans):
        actual = _count_all_cards_in_plan(p)
        if actual != expected:
            # GUA-076 fix: 用 Counter 替代 set 检测重复牌数量差异
            from collections import Counter
            plan_counter = Counter()
            for s in p.singles:
                plan_counter[s] += 1
            for pr in p.pairs:
                for c in pr:
                    plan_counter[c] += 1
            for t in p.trips:
                for c in t:
                    plan_counter[c] += 1
            for b in p.bombs:
                for c in b:
                    plan_counter[c] += 1
            for s in p.straights:
                for c in s:
                    plan_counter[c] += 1
            for sf in p.straight_flushes:
                for c in sf:
                    plan_counter[c] += 1
            for tp in p.three_pairs:
                for pr in tp:
                    for c in pr:
                        plan_counter[c] += 1
            for twt in p.three_with_twos:
                for c in twt[0]:
                    plan_counter[c] += 1
                for c in twt[1]:
                    plan_counter[c] += 1
            for sp in p.steel_plates:
                for t in sp:
                    for c in t:
                        plan_counter[c] += 1
            hand_counter = Counter(hand_cards)
            missing = sorted((hand_counter - plan_counter).elements())
            extra = sorted((plan_counter - hand_counter).elements())
            warnings.warn(
                f"GUA-076: Plan {i} ({p.strategy}) card count mismatch: "
                f"expected={expected} actual={actual} "
                f"missing={missing} extra={extra} — 剔除不完整方案",
                RuntimeWarning,
            )
        else:
            complete_plans.append(p)

    if not complete_plans:
        # 所有方案都不完整 — 保留原 plans 防止下游空列表崩溃
        warnings.warn(
            f"GUA-076: 全部 {len(plans)} 个方案均不完整 (expected={expected}), "
            f"保留原始方案避免空列表",
            RuntimeWarning,
        )
        complete_plans = plans

    complete_plans.sort(key=lambda p: p.score, reverse=True)
    return complete_plans[0], complete_plans[:3]  # GUA-074: 只保留 Top 3 方案，节约算力


def extract_grouping_features(
    hand_cards: List[str],
    cur_rank: str = "2",
) -> List[float]:
    """
    提取 24 维组牌特征向量（GUA-062 v2 增强版）。

    先枚举多方案（6 策略含回溯变体）→ 4 维加权评分 → 取 Top 3 → 提取方案级+多样性特征。
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

