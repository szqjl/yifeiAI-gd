# -*- coding: utf-8 -*-
"""
EndgameDecider — 残局 Q0→Q3 决策引擎
======================================
读取 _endgame_context，按优先序执行四级决策：

  Q0: 自己冲刺（self.should_sprint）→ 出最大整炸抢头游
  Q1: 封锁敌方（有敌人 ≤10）→ banned 硬排 + recommended 优先
  Q2: 助攻队友（teammate.is_close ≤5）→ assist_prefer 喂牌
  Q3: 炸弹兜底（非冲刺/封锁/助攻）→ should_bomb 判决

任一 Q 命中 → 返回 action；全未命中 → 返回 None，交由上游管线处理。
"""

from collections import Counter
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger("endgame_decider")

# ── 从 v7_guards 导入工具 ──
try:
    from ..guards.v7_guards import (
        get_action_type, get_card_value, get_card_rank, get_action_rank,
        CARD_RANK_ORDER, JOKER_VALUE_SB, JOKER_VALUE_HR,
        ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR, ACTION_TYPE_TRIPS,
        ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH, ACTION_TYPE_THREE_PAIR,
        ACTION_TYPE_TWO_TRIPS, ACTION_TYPE_THREE_WITH_TWO, ACTION_TYPE_STRAIGHT,
        ACTION_TYPE_PASS, ACTION_TYPE_FREE,
        is_bomb, _extract_action_cards,
    )
    GUARD_TOOLS_OK = True
except ImportError:
    try:
        from src.v.nn.guards.v7_guards import (
            get_action_type, get_card_value, get_card_rank, get_action_rank,
            CARD_RANK_ORDER, JOKER_VALUE_SB, JOKER_VALUE_HR,
            ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR, ACTION_TYPE_TRIPS,
            ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH, ACTION_TYPE_THREE_PAIR,
            ACTION_TYPE_TWO_TRIPS, ACTION_TYPE_THREE_WITH_TWO, ACTION_TYPE_STRAIGHT,
            ACTION_TYPE_PASS, ACTION_TYPE_FREE,
            is_bomb, _extract_action_cards,
        )
        GUARD_TOOLS_OK = True
    except ImportError:
        GUARD_TOOLS_OK = False
    CARD_RANK_ORDER = {"2":0,"3":1,"4":2,"5":3,"6":4,"7":5,"8":6,"9":7,"T":8,"J":9,"Q":10,"K":11,"A":12}
    JOKER_VALUE_SB, JOKER_VALUE_HR = 13, 14
    (
        ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR, ACTION_TYPE_TRIPS,
        ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH, ACTION_TYPE_THREE_PAIR,
        ACTION_TYPE_TWO_TRIPS, ACTION_TYPE_THREE_WITH_TWO, ACTION_TYPE_STRAIGHT,
        ACTION_TYPE_PASS, ACTION_TYPE_FREE,
    ) = (
        "Single", "Pair", "Trips", "Bomb", "StraightFlush",
        "ThreePair", "TwoTrips", "ThreeWithTwo", "Straight",
        "PASS", "Free",
    )


# ═══════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════

def _get_cards(action: List) -> List[str]:
    """从 action 中提取实际牌列表。"""
    if isinstance(action, list) and action and action[0] == "PASS":
        return []
    if isinstance(action, list) and len(action) >= 3 and isinstance(action[2], list):
        return action[2]
    return action


def _max_card_value(action: List, cur_rank: str = "2") -> int:
    """一手牌的最大单张值。"""
    cards = _get_cards(action)
    if not cards:
        return 0
    vals = [get_card_value(c, cur_rank) for c in cards] if GUARD_TOOLS_OK else \
           [CARD_RANK_ORDER.get(c[1] if len(c) >= 2 else c, 0) for c in cards]
    return max(vals)


def _declared_bomb_rank_value(action: List, cur_rank: str = "2") -> int:
    """炸弹比点用声明 rank / 自然三张，排除逢人配（级牌配子会把小炸虚高）。"""
    declared = ""
    if isinstance(action, list) and len(action) >= 2:
        declared = str(action[1] or "")
    if declared and declared not in ("PASS", "Bomb", "StraightFlush"):
        fake = declared if declared in ("SB", "HR", "B", "R") else f"S{declared}"
        if GUARD_TOOLS_OK:
            try:
                return get_card_value(fake, cur_rank)
            except Exception:
                pass
        return CARD_RANK_ORDER.get(declared, 0)
    cards = _get_cards(action)
    naturals = [
        c for c in cards
        if isinstance(c, str) and c != f"H{cur_rank}"
    ]
    use = naturals or cards
    if not use:
        return 0
    if GUARD_TOOLS_OK:
        return max(get_card_value(c, cur_rank) for c in use)
    return max(CARD_RANK_ORDER.get(c[1:] if len(c) > 1 else c, 0) for c in use)


def _is_two_trips_plus_wild_hand(hand_cards: List[str], cur_rank: str) -> bool:
    """GUA-281：恰好两趟三张 + 1 张逢人配（可升任一趟成四星炸）。"""
    wild = f"H{cur_rank}"
    cards = [str(c) for c in (hand_cards or [])]
    if len(cards) != 7 or cards.count(wild) != 1:
        return False
    others = [c for c in cards if c != wild]
    if GUARD_TOOLS_OK:
        ranks = [get_card_rank(c) for c in others]
    else:
        ranks = [c[1:] if len(c) > 1 else c for c in others]
    return sorted(Counter(ranks).values()) == [3, 3]


# GUA-288：与 _action_breaks_core_structure 共用的核心整牌类型集合。集中定义防漂移
# （组牌引擎产出小写 straight/trips 与子组；炸弹/同花顺为大写，见 grouping_engine.py:167）。
_BOMB_BREAK_CORE_TYPES = frozenset({
    "StraightFlush", "Bomb", "straight", "trips",
    "trip_in_three_with_two", "pair_in_three_with_two",
    "pair_in_three_pair", "trip_in_steel_plate",
})


def _bomb_disrupts_core_group(game_state: Dict[str, Any], action: List) -> bool:
    """GUA-288：炸弹动作是否借用了其他核心组（SF/straight/trips/Bomb）的牌而未整组消耗
    → 视为「拆核凑炸」。锚点 match=6a92e4aa 21:55:16：Bomb/T=[CT,ST,ST,H2] 把 H2（红桃
    配子）从唯一核心 StraightFlush[H5,H6,H7,H2,H9] 抽出凑 4 头炸，H2 出手后同花顺只剩
    5/6/7/9 四张散单 → V8 队负（scores=[0,3,0,3]）。

    与 _action_breaks_core_structure 不同：后者对 bomb-like 一律豁免（GUA-206：完整炸弹
    =用核心整牌压制，绝不拆核心打弱牌）；本函数专供 Q1 炸弹排序惩罚——有「整核炸弹」可选
    时，应优先于「借核凑炸」。不绝对禁用：GUA-278 危急截断等只剩借配炸时可继续使用。
    整组消耗某核心组视为核心整牌压制（GUA-206 语义），不计拆核。
    """
    if not _is_bomb_like_action(action):
        return False
    group_members = game_state.get("_group_members")
    gid_type_map = game_state.get("_group_gid_type_map", {})
    if not group_members:
        return False
    action_counts = Counter(str(c) for c in _get_cards(action))
    if not action_counts:
        return False
    for gid, members in group_members.items():
        gtype = gid_type_map.get(gid) or gid_type_map.get(str(gid), "")
        if gtype not in _BOMB_BREAK_CORE_TYPES:
            continue
        members_counts = Counter(str(c) for c in members)
        overlap = action_counts & members_counts
        if not overlap:
            continue
        if overlap != members_counts:
            return True
    return False


def _min_card_value(action: List, cur_rank: str = "2") -> int:
    """一手牌的最小单张值（领出小点优先用）。"""
    cards = _get_cards(action)
    if not cards:
        return 99
    vals = [get_card_value(c, cur_rank) for c in cards] if GUARD_TOOLS_OK else \
           [CARD_RANK_ORDER.get(c[1] if len(c) >= 2 else c, 0) for c in cards]
    return min(vals)


def _has_recapture(
    action: List, hand_cards: List[str], cur_rank: str = "2",
) -> bool:
    """
    同牌型是否有更高段回收（保留出牌权）。

    例：出单 Q，手中有 K/A → 有回收（K/A 可以压制对手并回收出牌权）。
    """
    atype = get_action_type(action) if GUARD_TOOLS_OK else ACTION_TYPE_FREE
    cards = _get_cards(action)
    if not cards:
        return False

    # GUA-215：bomb family（同花顺/炸弹/王炸）的回收 = 剩余手牌还能构成更强的炸弹，
    # 而非单张牌力跨牌型比较（同花顺最大单张 C6=6 < SB=16，会误判 SF 有回收，
    # 使 `_sort_by_recapture_first` 把 StraightFlush 排到 Single/SB 前面，浪费炸弹）。
    # 总序（guandan-knowledge L205）：王炸 > 8星 > 7星 > 6星 > 同花顺 > 5星 > 4星。
    if _is_bomb_family(action):
        return _hand_has_stronger_bomb(action, hand_cards, cur_rank)

    max_val = _max_card_value(action, cur_rank)

    # 在剩余手牌中找同牌型更高值
    for card in hand_cards:
        if GUARD_TOOLS_OK:
            cv = get_card_value(card, cur_rank)
        else:
            rk = card[1] if len(card) >= 2 else card
            cv = CARD_RANK_ORDER.get(rk, 0)
        if cv > max_val:
            return True
    return False


def _bomb_family_strength(action: List, cur_rank: str = "2") -> Optional[Tuple[int, int]]:
    """bomb family 强度键 (level, rank_value)，越大越强；非 bomb family 返回 None。

    层级（guandan-knowledge L205）：
      王炸(100) > 8星(80) > 7星(70) > 6星(60) > 同花顺(55) > 5星(50) > 4星(40)。
    rank_value 用于同层比较（同花顺比最大点，同点炸比点数）。
    """
    if _is_joker_bomb(action):
        return (100, 0)
    cards = _get_cards(action)
    if not cards:
        return None
    if GUARD_TOOLS_OK:
        atype = get_action_type(action)
    else:
        atype = action[0] if isinstance(action, list) and action else ""
    n = len(cards)
    if atype in (ACTION_TYPE_STRAIGHT_FLUSH, "StraightFlush"):
        return (55, _max_card_value(action, cur_rank))
    if atype in (ACTION_TYPE_BOMB, "Bomb"):
        return (n * 10, _max_card_value(action, cur_rank))
    return None


def _bomb_weakest_first_key(action: List, cur_rank: str = "2") -> int:
    """bomb family 排序键（弱→强优先）：键越小越弱越优先 →「炸够用就好」。

    与牌力序一致（guandan-knowledge L205）：同花顺(55) > 5星炸(50) > 4星炸(40)。
    对一组「均能压过对手」的候选，优先用**最弱一档**即可（够用就好，不浪费更
    强火力、不乱动同花顺）；仅当更弱档都不够压时才落到同花顺。
    按**平台声明类型** + 张数算 level（比 `_bomb_family_strength` 更稳，后者经
    `get_action_type` 对含配子的 5 星炸/同花顺可能重导为其它类型返回 None）：
    同花顺=55，N 星炸=N*10（4星=40<5星=50<同花顺=55）。被 `min` 取最小时选中最弱可用档。
    """
    cards = _get_cards(action)
    n = len(cards)
    atype = _get_declared_action_type(action)
    if atype in (ACTION_TYPE_STRAIGHT_FLUSH, "StraightFlush", "STRAIGHT_FLUSH"):
        return 55
    if atype in (ACTION_TYPE_BOMB, "Bomb", "BOMB"):
        return n * 10
    return 0


def _hand_has_natural_joker_bomb(hand_cards: List[str]) -> bool:
    """手牌能否构成王炸（2 大王 + 2 小王）。"""
    sb = hr = 0
    for card in hand_cards:
        c = str(card)
        if c in ("SB", "BJ"):
            sb += 1
        elif c in ("HR", "RJ"):
            hr += 1
    return sb >= 2 and hr >= 2


def _hand_has_stronger_bomb(
    action: List, hand_cards: List[str], cur_rank: str = "2",
) -> bool:
    """剩余手牌能否构成比 action 更强的炸弹（bomb family 内部比较）。

    对 StraightFlush：更强 = 王炸 / 6+ 星炸（6/7/8 星；同花顺 > 5 星及以下）。
    对 Bomb N 张：更强 = 王炸 / 更高星 / 同星更高点数 / （N<=5 时）同花顺。
    王炸无更强，返回 False。
    """
    act_key = _bomb_family_strength(action, cur_rank)
    if act_key is None:
        return False
    act_level = act_key[0]

    # 剩余手牌 = 手牌总量扣除 action 已用牌（防止 action 的牌被计入候选计数，
    # 例如 5×S6 + C2-C6 SF：出 SF 后 C6 已用，S6 只剩 5 张 = 五星炸，不构成更强）。
    hand_ct = Counter(str(c) for c in hand_cards)
    used_ct = Counter(str(c) for c in _get_cards(action))
    remaining_ct = hand_ct - used_ct

    if _hand_has_natural_joker_bomb(
        [c for c, cnt in remaining_ct.items() for _ in range(cnt)]
    ) and act_level < 100:
        return True

    counts: Counter = Counter()
    for card, cnt in remaining_ct.items():
        rk = get_card_rank(str(card)) if GUARD_TOOLS_OK else (
            str(card)[1] if len(str(card)) >= 2 else str(card))
        if rk in ("SB", "HR", "BJ", "RJ"):
            continue
        counts[rk] += cnt

    for rank, cnt in counts.items():
        if cnt < 4:
            continue
        if GUARD_TOOLS_OK:
            rank_val = get_card_value("S" + rank, cur_rank)
        else:
            rank_val = CARD_RANK_ORDER.get(rank, 0)
        cand_key = (cnt * 10, rank_val)
        if cand_key > act_key:
            return True

    return False


def _uniform_bomb_rank(cards: List[str]) -> Optional[str]:
    """炸弹候选的统一点数 rank；含王或混点则返回 None。"""
    if not cards or not GUARD_TOOLS_OK:
        return None
    ranks = {get_card_rank(str(c)) for c in cards}
    if any(r in ("HR", "SB") for r in ranks):
        return None
    if len(ranks) != 1:
        return None
    return next(iter(ranks))


def _bomb_splits_pure_rank_leaving_orphan(
    item: Any,
    bomb_items: List,
    hand_cards: List[str],
) -> bool:
    """
    GUA-103 收窄：更小纯点数炸若会留下同点孤张，则不应优先于整炸。

    例：五星 5 压 Pair/9 时，四炸留 C5 孤张 → 应出完整五星炸。
    不含「四炸 + 逢人配升五炸」场景（额外牌非同点）。
    """
    act = item[1] if isinstance(item, tuple) and len(item) == 2 else item
    cards = [str(c) for c in _get_cards(act)]
    bomb_rank = _uniform_bomb_rank(cards)
    if not bomb_rank or len(cards) < 4:
        return False

    hand_ct = Counter(str(c) for c in hand_cards)
    used_ct = Counter(cards)

    for other in bomb_items:
        other_act = other[1] if isinstance(other, tuple) and len(other) == 2 else other
        other_cards = [str(c) for c in _get_cards(other_act)]
        if len(other_cards) <= len(cards):
            continue
        if _uniform_bomb_rank(other_cards) != bomb_rank:
            continue
        other_ct = Counter(other_cards)
        if any(used_ct[r] > other_ct[r] for r in used_ct):
            continue
        extra_ct = other_ct - used_ct
        leftover = hand_ct - used_ct
        for orphan, need in extra_ct.items():
            if get_card_rank(orphan) != bomb_rank:
                continue
            if leftover.get(orphan, 0) == need:
                return True
    return False


def _has_non_single_lead_candidates(candidates: List[Tuple[int, List]]) -> bool:
    """领出候选中是否存在非单张（不含 PASS/炸弹）。"""
    if not GUARD_TOOLS_OK:
        return False
    for _, act in candidates:
        if _get_declared_action_type(act) in (ACTION_TYPE_PASS, "PASS"):
            continue
        if _is_bomb_like_action(act):
            continue
        try:
            if get_action_type(act) != ACTION_TYPE_SINGLE:
                return True
        except Exception:
            continue
    return False


def _pick_second_smallest_single(
    singles: List[Tuple[int, List]], cur_rank: str,
) -> Optional[Tuple[int, List]]:
    """散单中出倒数第二小（至少 2 张时）；仅 1 张则出该张。"""
    if not singles:
        return None
    ordered = sorted(
        singles,
        key=lambda item: get_card_value(_get_cards(item[1])[0], cur_rank),
    )
    return ordered[1] if len(ordered) >= 2 else ordered[0]


def _is_wild_level_card(card: str, cur_rank: str) -> bool:
    """红桃级牌 H{curRank} 为逢人配。"""
    if not card or not cur_rank:
        return False
    if len(card) >= 2 and card[0] == "H":
        return card[1:] == cur_rank
    return False


def _single_action_uses_wild_level_card(action: List, cur_rank: str) -> bool:
    if not GUARD_TOOLS_OK or not cur_rank:
        return False
    if get_action_type(action) != ACTION_TYPE_SINGLE:
        return False
    rank = get_action_rank(action) or ""
    if rank != cur_rank:
        return False
    cards = _get_cards(action)
    if len(cards) != 1:
        return False
    return _is_wild_level_card(str(cards[0]), cur_rank)


def _has_non_wild_level_single_option(items: List, cur_rank: str) -> bool:
    for item in items:
        act = item[1] if isinstance(item, tuple) and len(item) == 2 else item
        if not GUARD_TOOLS_OK:
            continue
        if get_action_type(act) != ACTION_TYPE_SINGLE:
            continue
        if (get_action_rank(act) or "") != cur_rank:
            continue
        cards = _get_cards(act)
        if len(cards) != 1:
            continue
        if not _is_wild_level_card(str(cards[0]), cur_rank):
            return True
    return False


def _is_non_wild_level_single(action: List, cur_rank: str) -> bool:
    """非逢人配的级牌单张（GUA-122 优选目标）。"""
    if not GUARD_TOOLS_OK or not cur_rank:
        return False
    if get_action_type(action) != ACTION_TYPE_SINGLE:
        return False
    if (get_action_rank(action) or "") != cur_rank:
        return False
    cards = _get_cards(action)
    if len(cards) != 1:
        return False
    return not _is_wild_level_card(str(cards[0]), cur_rank)


def _sort_q1_prefer_non_wild_level_singles(items: List, cur_rank: str) -> List:
    """
    GUA-122：压单时若同级存在非逢人配级牌，优先该级牌，且不得裸出 H{curRank}。

    在「回收优先 → 牌力大优先」之后调用：级牌单张可能因「出 A 仍有级牌回收」
    排到级牌本身前面，故此处把非 wild 级牌单张提到最前。
    """
    if not items or not cur_rank or not _has_non_wild_level_single_option(items, cur_rank):
        return items

    def _key(item):
        act = item[1] if isinstance(item, tuple) and len(item) == 2 else item
        if _single_action_uses_wild_level_card(act, cur_rank):
            return 2  # 逢人配级牌垫后
        if _is_non_wild_level_single(act, cur_rank):
            return 0  # 非 wild 级牌最前
        return 1

    return sorted(items, key=_key)


def _hand_counter_from_state(game_state: Dict[str, Any]) -> Counter:
    return Counter(game_state.get("handCards", []) or [])


def _is_finish_now_action(act: List, hand_counter: Counter) -> bool:
    """GUA-112：候选牌张 multiset 与当前手牌一致 → 一手清牌。"""
    if not isinstance(act, list) or not hand_counter:
        return False
    if _get_declared_action_type(act) in (ACTION_TYPE_PASS, "PASS"):
        return False
    cards = _get_cards(act)
    return bool(cards) and Counter(cards) == hand_counter


def find_finish_now_candidate(
    game_state: Dict[str, Any], action_list: List,
) -> Optional[Tuple[int, List]]:
    """
    在 action_list 中查找一手清牌候选。
    
    优先级：
      1. 非炸方案（ThreePair / ThreeWithTwo 等）优先于炸
      2. 炸中选最小张数（4星 < 5星 < 6星）
      3. 若唯一 finish_now 是含百搭的炸，且在 actionList 中存在更小炸 → 跳过 Q0.5
    """
    hand_counter = _hand_counter_from_state(game_state)
    if not hand_counter:
        return None

    candidates: List[Tuple[int, List]] = []
    for i, act in enumerate(action_list):
        if _is_finish_now_action(act, hand_counter):
            candidates.append((i, act))

    if not candidates:
        return None

    cur_rank = str(game_state.get("curRank", "2"))
    wild = "H" + cur_rank

    def _sort_key(item):
        act = item[1]
        atype = _get_declared_action_type(act)
        is_bomb = atype in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH) if GUARD_TOOLS_OK else False
        cards = _get_cards(act)
        bomb_size = len(cards) if is_bomb and isinstance(cards, list) else 0
        uses_wild = wild in cards if isinstance(cards, list) else False
        return (bomb_size, 1 if uses_wild else 0, item[0])

    candidates.sort(key=_sort_key)
    best_idx, best_act = candidates[0]

    # 跳过含百搭的 finish_now 大炸：若唯一候选是含百搭的炸，且存在更小非 finish_now 炸
    if not GUARD_TOOLS_OK:
        return best_idx, best_act

    best_atype = _get_declared_action_type(best_act)
    is_best_bomb = best_atype in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH)
    best_cards = _get_cards(best_act)

    if is_best_bomb and len(candidates) == 1 and isinstance(best_cards, list):
        if wild in best_cards:
            for i, act in enumerate(action_list):
                if i == best_idx:
                    continue
                atype = _get_declared_action_type(act)
                if atype in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
                    act_cards = _get_cards(act)
                    if isinstance(act_cards, list) and len(act_cards) < len(best_cards):
                        return None  # 跳过 Q0.5，让 Q1 选更小炸

    return best_idx, best_act


def finish_now_protected_action_types(
    game_state: Dict[str, Any], action_list: List,
) -> set:
    """GUA-112：所有一手清候选的 ACTION_TYPE，供 Q1 banned 保护集使用。"""
    hand_counter = _hand_counter_from_state(game_state)
    if not hand_counter or not GUARD_TOOLS_OK:
        return set()
    protected: set = set()
    for act in action_list:
        if not _is_finish_now_action(act, hand_counter):
            continue
        try:
            atype = get_action_type(act)
            if atype not in (ACTION_TYPE_PASS, ACTION_TYPE_FREE):
                protected.add(atype)
        except Exception:
            continue
    return protected


def _sort_by_recapture_first(
    actions: List, hand_cards: List[str], cur_rank: str = "2",
) -> List:
    """回收优先 → 牌力大优先（Q1/Q2 通用排序）。

    actions 可以是 (idx, act) 元组列表或纯 act 列表。
    第二键用最大单张牌力，避免跟压单张时「张数多优先」把 4 炸排到大王/小王前面。
    """
    def _sort_key(item):
        act = item[1] if isinstance(item, tuple) and len(item) == 2 else item
        return (
            not _has_recapture(act, hand_cards, cur_rank),  # 有回收排前面
            -_max_card_value(act, cur_rank),                 # 牌力大优先
        )
    return sorted(actions, key=_sort_key)


def pick_assist_feed_by_prefer(
    game_state: Dict[str, Any],
    action_list: List,
    assist_prefer: List[str],
    hand_cards: Optional[List[str]] = None,
) -> Optional[Tuple[int, List]]:
    """
    GUA-117 / Q2 共用：按 assist_prefer 过滤合法动作 → 回收排序 → 取最优。
    GUA-189：队友报单(1张)时单张排序规则——下家也报单则出大单防截胡，
            否则出小单让队友接。

    Returns:
        (action_list 下标, action) 或 None
    """
    if not assist_prefer or not action_list or not GUARD_TOOLS_OK:
        return None

    if hand_cards is None:
        hand_cards = game_state.get("handCards", []) or []

    prefer_set = set(assist_prefer)
    assist_actions: List[Tuple[int, List]] = []
    for i, action in enumerate(action_list):
        try:
            atype = get_action_type(action)
            if atype in prefer_set:
                assist_actions.append((i, action))
        except Exception:
            continue

    if not assist_actions:
        return None

    cur_rank = str(game_state.get("curRank", "2"))

    # GUA-189：队友报单(1张)时单张排序
    if "Single" in prefer_set and len(prefer_set) == 1:
        ec = game_state.get("_endgame_context", {})
        teammate = ec.get("teammate", {})
        if teammate.get("remaining") == 1:
            my_pos = int(game_state.get("myPos", 0))
            teammate_pos = (my_pos + 2) % 4
            numofplayers = game_state.get("numofplayers") or []
            # 顺时针找第一个非队友的活跃玩家(剩余>0)
            down_seat_rem = 99
            for offset in range(1, 4):
                seat = (my_pos + offset) % 4
                if seat == teammate_pos:
                    continue
                if isinstance(numofplayers, list) and seat < len(numofplayers):
                    rem = numofplayers[seat]
                    if isinstance(rem, (int, float)) and rem > 0:
                        down_seat_rem = int(rem)
                        break
            if down_seat_rem == 1:
                # GUA-271 定音：下家也报单时，手牌仅有散单→倒数第二小；
                # 另有对子/三带等整牌型→本路径不送单，交由其他领出逻辑。
                all_candidates = [
                    (i, a) for i, a in enumerate(game_state.get("actionList") or [])
                ]
                if _has_non_single_lead_candidates(all_candidates):
                    return None
                assist_actions.sort(key=lambda item: _max_card_value(item[1], cur_rank))
                return _pick_second_smallest_single(assist_actions, cur_rank)
            # 下家不报单: 出小单让队友接
            assist_actions.sort(key=lambda item: _max_card_value(item[1], cur_rank))
            return assist_actions[0]

    assist_actions = _sort_by_recapture_first(assist_actions, hand_cards, cur_rank)
    return assist_actions[0]


def action_list_item_to_feed_recommendation(
    action: List,
    intent: str,
    *,
    rank_map: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """将 actionList 条目转为 _recommend_play 推荐 dict。"""
    if not action:
        return None
    declared = _get_declared_action_type(action)
    if declared in (ACTION_TYPE_PASS, "PASS"):
        return {"type": "PASS", "rank": "", "cards": [], "intent": intent}
    if declared in ("Bomb", "StraightFlush"):
        cards = _get_cards(action)
        rank = action[1] if len(action) > 1 else ""
        if rank_map and rank in rank_map:
            rank = rank_map[rank]
        elif rank_map:
            rank = rank_map.get(rank, rank)
        return {
            "type": declared,
            "rank": rank,
            "cards": [str(c) for c in cards],
            "intent": intent,
        }
    if not GUARD_TOOLS_OK:
        return None
    atype = get_action_type(action)
    if atype in (ACTION_TYPE_PASS, ACTION_TYPE_FREE, "PASS", "Free"):
        return {"type": "PASS", "rank": "", "cards": [], "intent": intent}
    cards = _get_cards(action)
    rank = get_action_rank(action) or ""
    if rank_map and rank in rank_map:
        rank = rank_map[rank]
    elif rank_map:
        rank = rank_map.get(rank, rank)
    return {
        "type": atype,
        "rank": rank,
        "cards": [str(c) for c in cards],
        "intent": intent,
    }


def _is_bomb_like_action(action: List) -> bool:
    """是否为炸弹类动作（含同花顺）。"""
    if isinstance(action, list) and action:
        declared = action[0]
        if declared in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH, "Bomb", "StraightFlush"):
            return True
    if not GUARD_TOOLS_OK:
        return False
    try:
        atype = get_action_type(action)
    except Exception:
        return False
    return atype in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH)



def _is_joker_bomb(action: List) -> bool:
    """是否为王炸（两个王，bomb family 最大成员）。"""
    cards = _get_cards(action)
    if len(cards) != 2:
        return False
    norm = {str(c).upper() for c in cards}
    return norm == {"SJ", "BJ"} or norm == {"BJ", "SJ"}


def _is_bomb_family(action: List) -> bool:
    """
    GUA-131：判别一手牌型是否属于 bomb family（4+ 张同点炸 + 同花顺 + 王炸）。

    见 GUA-125 §0.0 / §4.1：bomb family 可跨型压杂牌（TWT / 顺子 / 三带二 / ...）。
    """
    if not action or not isinstance(action, list):
        return False
    if _is_bomb_like_action(action):
        return True
    if _is_joker_bomb(action):
        return True
    return False


def _get_declared_action_type(action: List) -> str:
    """优先取平台声明牌型；无声明时退回空串。"""
    if isinstance(action, list) and action and isinstance(action[0], str):
        return action[0]
    return ""


def _is_joker_pair_action(action: List) -> bool:
    """GUA-269：是否为对小王 / 对大王（平台 Pair/B 或 Pair/R）。"""
    if not action or not isinstance(action, list):
        return False
    if _get_declared_action_type(action) != ACTION_TYPE_PAIR:
        return False
    cards = _get_cards(action)
    if len(cards) != 2:
        return False
    ranks = {get_card_rank(str(c)) for c in cards} if GUARD_TOOLS_OK else set()
    if not ranks:
        rank = action[1] if len(action) > 1 else ""
        return rank in ("B", "R")
    return ranks <= {"SB", "HR"} and len(ranks) == 1


def _effective_structure_type(action: List) -> str:
    """结构类型：平台 StraightFlush / Bomb 声明优先于实牌推断。"""
    declared = _get_declared_action_type(action)
    if declared == "StraightFlush":
        return ACTION_TYPE_STRAIGHT_FLUSH
    if declared == "Bomb":
        return ACTION_TYPE_BOMB
    if not GUARD_TOOLS_OK:
        return declared
    try:
        return get_action_type(action)
    except Exception:
        return declared


def _action_beats_greater(
    challenger: List, defender: List, cur_rank: str,
) -> bool:
    """challenger 是否压过 greaterAction（平台 StraightFlush / Bomb 声明优先）。"""
    if not challenger or not defender:
        return False
    if _get_declared_action_type(challenger) in (ACTION_TYPE_PASS, "PASS"):
        return False
    if _get_declared_action_type(defender) in (ACTION_TYPE_PASS, "PASS"):
        return False

    ch_bomb = _is_bomb_like_action(challenger)
    df_bomb = _is_bomb_like_action(defender)
    if ch_bomb and not df_bomb:
        return True
    if df_bomb and not ch_bomb:
        return False
    if not ch_bomb:
        try:
            from src.game_logic.trick_state import action_beats
            return action_beats(challenger, defender, cur_rank) is True
        except Exception:
            return False

    ch_decl = _get_declared_action_type(challenger)
    df_decl = _get_declared_action_type(defender)
    ch_cards = _get_cards(challenger)
    df_cards = _get_cards(defender)
    ch_sf = ch_decl == "StraightFlush"
    df_sf = df_decl == "StraightFlush"

    # 同花顺 > 5星及以下炸；6星炸+ > 同花顺
    if ch_sf and not df_sf:
        return len(df_cards) <= 5
    if df_sf and not ch_sf:
        return len(ch_cards) >= 6
    if ch_sf and df_sf:
        ch_rank = challenger[1] if len(challenger) > 1 else ""
        df_rank = defender[1] if len(defender) > 1 else ""
        try:
            from src.game_logic.trick_state import rank_value
            return rank_value(ch_rank, cur_rank) > rank_value(df_rank, cur_rank)
        except Exception:
            return False

    ch_n, df_n = len(ch_cards), len(df_cards)
    if ch_n != df_n:
        return ch_n > df_n
    ch_rank = challenger[1] if len(challenger) > 1 else ""
    df_rank = defender[1] if len(defender) > 1 else ""
    try:
        from src.game_logic.trick_state import rank_value
        return rank_value(ch_rank, cur_rank) > rank_value(df_rank, cur_rank)
    except Exception:
        return False


def _is_following_enemy_bomb_control(
    game_state: Dict[str, Any], my_pos: Optional[int] = None,
) -> bool:
    """跟压敌方 bomb-like 控牌（非队友、非 PASS）。"""
    my_pos = my_pos if my_pos is not None else game_state.get("myPos", 0)
    greater_pos = game_state.get("greaterPos", -1)
    greater_action = game_state.get("greaterAction")
    enemy_positions = {(my_pos + 1) % 4, (my_pos + 3) % 4}
    if greater_pos not in enemy_positions:
        return False
    if not greater_action or _get_declared_action_type(greater_action) in (
        ACTION_TYPE_PASS, "PASS",
    ):
        return False
    return _is_bomb_like_action(greater_action)


def _enemy_bomb_sprint_remaining(game_state: Dict[str, Any]) -> Optional[int]:
    """控牌敌席剩张（用于反炸 sprint 阈值）。"""
    greater_pos = game_state.get("greaterPos", -1)
    nums = game_state.get("numofplayers") or []
    if greater_pos < 0 or greater_pos >= len(nums):
        return None
    try:
        return int(nums[greater_pos])
    except (TypeError, ValueError):
        return None


def collect_counter_bomb_like_candidates(
    action_list: List,
    greater_action: List,
    cur_rank: str,
) -> List[Tuple[int, List]]:
    """从 actionList 收集可压过 greater 的 bomb-like 候选。"""
    result: List[Tuple[int, List]] = []
    for i, act in enumerate(action_list):
        if not _is_bomb_like_action(act):
            continue
        if _action_beats_greater(act, greater_action, cur_rank):
            result.append((i, act))
    return result


def select_counter_bomb_like(
    action_list: List,
    greater_action: List,
    game_state: Dict[str, Any],
) -> Optional[Tuple[int, List]]:
    """GUA-103 最小足够成本选反炸候选。"""
    cur_rank = str(game_state.get("curRank", "2"))
    hand_cards = game_state.get("handCards", []) or []
    candidates = collect_counter_bomb_like_candidates(
        action_list, greater_action, cur_rank,
    )
    if not candidates:
        return None
    sorted_cands = _sort_q1_block_candidates(candidates, hand_cards, game_state)
    return sorted_cands[0] if sorted_cands else None


def should_allow_counter_bomb_core_exempt(
    action: List,
    game_state: Dict[str, Any],
    cur_rank: Optional[str] = None,
) -> bool:
    """GUA-123：跟压敌炸 sprint 时允许拆 Bomb/SF core 反炸。"""
    if not _is_following_enemy_bomb_control(game_state):
        return False
    if not _is_bomb_like_action(action):
        return False
    greater_action = game_state.get("greaterAction")
    if not greater_action:
        return False
    cur_rank = cur_rank or str(game_state.get("curRank", "2"))
    if not _action_beats_greater(action, greater_action, cur_rank):
        return False
    enemy_rem = _enemy_bomb_sprint_remaining(game_state)
    if enemy_rem is None or enemy_rem < 1:
        return False
    return True


def should_allow_gua239_single_probe(game_state: Dict[str, Any]) -> bool:
    """GUA-239：自由领出多手「先单试探」标记 → 豁免拆核心拦截。

    GUA-239 决策路径（`_q1_multi_hand_lead_single_first`）有意拆 SF/顺子核心组
    出最小天然单（如 SF(H7,H2,H2,HT,HJ) 中出 H7），选前在 game_state 设
    `_gua239_single_probe=True`；decide 层 `_action_breaks_core_structure`（L1432）
    与引擎 `_group_consistency_filter` 据此放行，否则被转 PASS / 回退 GUA-075，
    修复失效（实测 match 6a7dd97c 22:49:44）。game_state 每回合由 adapter 重建，
    标记不会跨回合泄漏。
    """
    return bool(game_state and game_state.get("_gua239_single_probe"))


def find_latent_bomb_like_beaters_not_in_action_list(
    hand_cards: List[str],
    cur_rank: str,
    greater_action: List,
    action_list: List,
) -> List[List[str]]:
    """组牌可见、可压敌炸，但平台 actionList 未枚举的 bomb-like 牌组（诊断用）。"""
    if not hand_cards or not greater_action:
        return []
    try:
        from src.v.nn.features.grouping_engine import enumerate_groupings
    except ImportError:
        return []

    def _cards_key(cards: List[str]) -> Tuple[str, ...]:
        return tuple(sorted(str(c) for c in cards))

    listed_keys = set()
    for act in action_list or []:
        if not _is_bomb_like_action(act):
            continue
        listed_keys.add(_cards_key(_get_cards(act)))

    latent: List[List[str]] = []
    try:
        best_plan, _ = enumerate_groupings(hand_cards, cur_rank)
    except Exception:
        return []

    for sf in getattr(best_plan, "straight_flushes", []) or []:
        sf_cards = [str(c) for c in sf]
        if _cards_key(sf_cards) in listed_keys:
            continue
        pseudo = ["StraightFlush", sf_cards[0][1] if sf_cards else "", sf_cards]
        if _action_beats_greater(pseudo, greater_action, cur_rank):
            latent.append(sf_cards)

    for bomb in getattr(best_plan, "bombs", []) or []:
        bomb_cards = [str(c) for c in bomb]
        if _cards_key(bomb_cards) in listed_keys:
            continue
        rank = bomb_cards[0][1] if bomb_cards else ""
        pseudo = ["Bomb", rank, bomb_cards]
        if _action_beats_greater(pseudo, greater_action, cur_rank):
            latent.append(bomb_cards)

    return latent


def _is_control_action(action: List) -> bool:
    """是否为真实控牌动作；平台声明优先，PASS/FREE 视为非控牌。"""
    declared = _get_declared_action_type(action)
    if declared and declared not in (ACTION_TYPE_PASS, ACTION_TYPE_FREE, "PASS", "Free"):
        return True

    if not GUARD_TOOLS_OK:
        return False
    try:
        atype = get_action_type(action)
    except Exception:
        return False
    return atype not in (ACTION_TYPE_PASS, ACTION_TYPE_FREE)


def _q1_structure_priority(action_type: str) -> int:
    """Q1 整牌候选优先级。数值越小优先级越高。"""
    type_priority = {
        ACTION_TYPE_STRAIGHT: 0,
        ACTION_TYPE_THREE_WITH_TWO: 1,
        ACTION_TYPE_TWO_TRIPS: 2,
        ACTION_TYPE_THREE_PAIR: 3,
        ACTION_TYPE_TRIPS: 4,
        ACTION_TYPE_PAIR: 5,
        ACTION_TYPE_BOMB: 6,
        ACTION_TYPE_STRAIGHT_FLUSH: 7,
    }
    return type_priority.get(action_type, 99)


def _breaks_core_subgroup(
    act: List, group_members: Dict[int, List[str]], group_gid_type: Dict[int, str],
) -> bool:
    """GUA-202 抽取：判断 action 是否拆解了 core 复合牌型子组的部分成员。

    复用 `_sort_q1_prefer_structure_preserving` 的逐张计数判据（正确处理重复牌）：
    consumed ∈ (0, len(members)) 即视为拆核。用 Counter 精确匹配避免重复牌误判。
    """
    from collections import Counter as _C
    if not group_members or not group_gid_type:
        return False
    cards = _get_cards(act)
    if not cards:
        return False
    act_cnt = _C(cards)
    for gid, members in group_members.items():
        gtype = group_gid_type.get(gid) or group_gid_type.get(str(gid), "")
        if gtype not in ("trip_in_three_with_two", "pair_in_three_with_two",
                         "pair_in_three_pair", "trip_in_steel_plate",
                         "trips", "straight", "Bomb", "StraightFlush"):
            continue
        mem_cnt = _C(members)
        consumed = sum(min(act_cnt[c], mem_cnt[c]) for c in act_cnt if c in mem_cnt)
        total = sum(mem_cnt.values())
        if 0 < consumed < total:
            return True
    return False


def _sort_q1_prefer_structure_preserving(
    actions: List, group_members: Dict[int, List[str]], group_gid_type: Dict[int, str],
) -> List:
    """
    GUA-175: Q1 候选排序，结构保持优先。
    检查候选是否从核心复合牌型的子组取部分牌 → 破坏牌型结构。
    不拆结构的排前面。GUA-181: 从 trip_in_three_with_two 扩展到所有子组类型。
    """
    _SUB_GROUP_TYPES = frozenset({
        "trip_in_three_with_two",
        "pair_in_three_with_two",
        "pair_in_three_pair",
        "trip_in_steel_plate",
    })
    if not group_members or not group_gid_type:
        return actions

    def _breaks_structure(item):
        act = item[1] if isinstance(item, tuple) and len(item) == 2 else item
        if len(act) < 3:
            return False
        cards = act[2]
        if not cards:
            return False
        for gid, members in group_members.items():
            gtype = group_gid_type.get(gid, "")
            if gtype not in _SUB_GROUP_TYPES:
                continue
            consumed = sum(1 for c in cards if c in members)
            if 0 < consumed < len(members):
                return True
        return False

    return sorted(actions, key=lambda item: _breaks_structure(item))


def _sort_q1_block_candidates(
    actions: List, hand_cards: List[str], game_state: Dict[str, Any],
) -> List:
    """Q1 候选排序：回收优先 → 牌力大优先 → 级牌单张少耗逢人配 → bomb-like 最小足够成本。
    GUA-175: 结构保持优先（不拆三带二的 Pair 排前面）。"""
    # GUA-175: 结构保持优先
    group_members = game_state.get("_group_members")
    group_gid_type = game_state.get("_group_gid_type_map")
    if group_members and group_gid_type:
        actions = _sort_q1_prefer_structure_preserving(actions, group_members, group_gid_type)

    cur_rank = str(game_state.get("curRank", "2"))
    ordered = _sort_by_recapture_first(actions, hand_cards, cur_rank)
    if not ordered or not GUARD_TOOLS_OK:
        return ordered

    ordered = _sort_q1_prefer_non_wild_level_singles(ordered, cur_rank)

    greater_action = game_state.get("greaterAction")
    if not greater_action:
        return ordered

    declared_greater_type = _get_declared_action_type(greater_action)
    if declared_greater_type in (ACTION_TYPE_PASS, ACTION_TYPE_FREE, "PASS", "Free"):
        return ordered
    if not declared_greater_type:
        try:
            greater_type = get_action_type(greater_action)
        except Exception:
            return ordered
        if greater_type in (ACTION_TYPE_PASS, ACTION_TYPE_FREE):
            return ordered

    bomb_items = [
        item for item in ordered
        if _is_bomb_like_action(item[1] if isinstance(item, tuple) and len(item) == 2 else item)
    ]
    if len(bomb_items) <= 1:
        return ordered

    # GUA-188: 检测是否存在非 SF 的普通炸弹（用于 SF 延后键）。
    # GUA-296：若所有非 SF 候选都是「拆核心组凑的炸」（借用同花顺/顺子/三条的牌，
    # 见 GUA-288 _bomb_disrupts_core_group），则它们并不比同花顺更「够用/保结构」，
    # 此时不应把同花顺延后——否则会拆掉原组牌引擎已组好的 StraightFlush 去凑 5 星炸
    # （锚点 match=6a95841d turn12：对手 4头炸 QQQQ，4星 3、4 压不过；5个3含黑桃3、
    #  5个4含黑桃4+黑桃5/6/7，应用 3-7 同花顺压，保留 3炸+4炸）。
    has_preserving_non_sf_bomb = any(
        (
            _get_declared_action_type(
                item[1] if isinstance(item, tuple) and len(item) == 2 else item
            ) not in ("StraightFlush", "STRAIGHT_FLUSH")
        ) and not _bomb_disrupts_core_group(
            game_state,
            item[1] if isinstance(item, tuple) and len(item) == 2 else item,
        )
        for item in bomb_items
    )

    def _bomb_min_sufficient_key(item):
        act = item[1] if isinstance(item, tuple) and len(item) == 2 else item
        cards = _get_cards(act)
        wild_count = sum(1 for c in cards if isinstance(c, str) and c.startswith("H") and c[1:] == cur_rank)
        split_orphan = _bomb_splits_pure_rank_leaving_orphan(item, bomb_items, hand_cards)
        act_type = _get_declared_action_type(act)
        is_sf = act_type in ("StraightFlush", "STRAIGHT_FLUSH")
        # GUA-281：两趟三张+配子冲刺 → 配子搭大点（非 GUA-103 最小足够炸）
        rank_key = _declared_bomb_rank_value(act, cur_rank)
        if _is_two_trips_plus_wild_hand(hand_cards, cur_rank):
            rank_key = -rank_key
        # GUA-288：借核心组牌凑炸（wildcard 从唯一 SF/straight/trips/Bomb 抽借）→ 整核炸优先。
        # 惩罚键位于张数之前：宁可多用 2 张出整核炸，也不拆唯一核心同花顺打成 4 张散单
        # （match=6a92e4aa 21:55:16）。GUA-281 两手冲刺时配子本就用于拼炸，不惩罚。
        borrow = 0
        if not _is_two_trips_plus_wild_hand(hand_cards, cur_rank):
            borrow = 1 if _bomb_disrupts_core_group(game_state, act) else 0
        return (
            # 仅当存在「保结构的非同花顺炸弹」时才把同花顺延后（GUA-296：拆核凑炸不算）
            1 if (is_sf and has_preserving_non_sf_bomb) else 0,
            1 if split_orphan else 0,
            borrow,
            len(cards),
            wild_count,
            rank_key,
        )

    bomb_items = sorted(bomb_items, key=_bomb_min_sufficient_key)
    bomb_iter = iter(bomb_items)
    result = []
    for item in ordered:
        act = item[1] if isinstance(item, tuple) and len(item) == 2 else item
        if _is_bomb_like_action(act):
            result.append(next(bomb_iter))
        else:
            result.append(item)
    return result


def _seat_holding_states(seat: int, my_pos: int, partner_pos: int) -> Tuple[int, ...]:
    """返回某席在 MemoryTracker.card_state 中的“可能持有”状态集合。"""
    if seat == my_pos:
        return (1,)  # MY_HAND
    if seat == partner_pos:
        return (-1, 2)  # UNKNOWN / PARTNER_HAND
    return (-1, 3)  # UNKNOWN / OPPONENT_HAND


def _rank_beats_same_type(played_rank: str, suppressor_rank: str, cur_rank: str) -> bool:
    """同型比较：suppressor_rank 是否能压制 played_rank。"""
    if not played_rank or not suppressor_rank:
        return False
    if suppressor_rank == "HR":
        return played_rank != "HR"
    if suppressor_rank == "SB":
        return played_rank not in ("HR", "SB")
    if suppressor_rank == cur_rank:
        return played_rank not in ("HR", "SB", cur_rank)
    if played_rank == cur_rank:
        return False
    if played_rank in ("HR", "SB"):
        return False
    return CARD_RANK_ORDER.get(suppressor_rank, -1) > CARD_RANK_ORDER.get(played_rank, -1)


# ── GUA-244：剩余池推理（对子/单被接风险）阈值 ──
GUA244_SINGLE_RISK = 0.7          # 单被主敌接走的池风险 ≥ 0.7 → 触发护栏
GUA244_PAIR_RISK = 0.3            # 对子被主敌接走的池风险 < 0.3 → 允许对子优先
GUA244_ENUM_POOL_MAX = 18         # 精确枚举上限：池 ≤18 张
GUA244_ENUM_SEAT_MAX = 6          # 且该席剩 ≤6 张（C(18,6)=18564，单次毫秒级）


def _pool_card_rank(card: str) -> str:
    """从牌名取 rank（S2→'2'；SB/HR 原样返回）。"""
    if card in ("SB", "HR"):
        return card
    return card[1:] if len(card) >= 2 else card


def _pool_card_beats_single(card: str, target_rank: str, cur_rank: str) -> bool:
    """GUA-244：池中单张 card 能否压 target_rank 单张（含级牌）。"""
    if not card or not target_rank:
        return False
    if card in ("SB", "HR"):
        return True
    return _rank_beats_same_type(target_rank, _pool_card_rank(card), cur_rank)


# ═══════════════════════════════════════════════════════
#  EndgameDecider
# ═══════════════════════════════════════════════════════

class EndgameDecider:
    """
    残局决策引擎。

    用法：
        decider = EndgameDecider()
        action, idx = decider.decide(game_state, action_list)
        if idx >= 0:
            return idx  # 残局命中了
        # 否则继续上游管线（GUA-075 / Guard / NN / heuristic）
    """

    # ── banned_types 硬排除 ──

    def apply_banned_filter(
        self, action_list: List, game_state: Dict[str, Any],
    ) -> Tuple[List, bool]:
        """
        对 action_list 执行 banned_types 硬排除。

        Returns:
            (filtered_action_list, is_empty)
        """
        ec = game_state.get("_endgame_context", {})
        if not ec.get("is_active"):
            return action_list, False

        enemies = ec.get("enemies", {})
        if not enemies:
            return action_list, False

        main_pos, main_enemy = self._select_main_enemy(enemies, ec.get("my_pos", game_state.get("myPos", 0)))
        banned_set = self._collect_q1_banned_set(game_state, ec, enemies, main_pos, main_enemy, action_list)

        # 敌方剩 5 张且当前控牌是 Single 时，Q1 需要先判断“4+1 vs 整牌型”。
        # 若此时把 Single 全硬删，会丢掉“最大合法单张先压”的机会。
        if self._should_relax_single_ban_for_enemy_five(game_state, ec, action_list):
            banned_set.discard(ACTION_TYPE_SINGLE)

        # GUA-235：baoshu never_play 的 Bomb/SF（报四「火不打四」）只约束跟压，
        # 不约束自由领出 / Q0 两手冲刺。否则敌剩 4 时硬删 Bomb → 冲刺看不到
        # 「Straight/A 剩五星炸」residue，退化出 Single/A（match=6a7c7876）。
        # GUA-240：Trips 同理——下家报三（三同张）never_play Trips，自由领出
        # 若硬删 Trips/AAA，Q0 冲刺只剩 Single+Pair 被 GUA-182 误判两对拆 AAA
        # （match=6a7f1a17，手牌 AAA+9 拆 Pair/A）。自由领出是进攻非跟压，豁免。
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        # GUA-267：火+一手整牌跟压报四 → 仍保留 Bomb/SF 供开炸冲刺
        # （match=6a8c3452 拆 Q 炸：禁炸后只剩 Trips/Q）。
        if self._q1_allow_bomb_vs_four_card_enemy_exception(game_state, ec):
            banned_set.discard(ACTION_TYPE_BOMB)
            banned_set.discard(ACTION_TYPE_STRAIGHT_FLUSH)
        if self._is_my_q1_lead_turn(game_state, my_pos):
            banned_set.discard(ACTION_TYPE_BOMB)
            banned_set.discard(ACTION_TYPE_STRAIGHT_FLUSH)
            banned_set.discard(ACTION_TYPE_TRIPS)
            # GUA-243：本方仅剩「炸弹 + 对子」两手整牌且队友已头游（remaining=0）时，
            # 自由领出豁免 Pair。报四/报双 never_play 的 Pair 只约束跟压，不得删掉
            # 我方整手冲刺对子（match=6a7ff9f50fbd680d7c7549bc L444-455：手牌
            # 4星8炸+对A 被 banned Pair 后 Q0 错拆 8 炸出 Single/8，broken=['Bomb']）。
            _hand = game_state.get("handCards", []) or []
            _team_rem = (ec.get("teammate") or {}).get("remaining")
            if _team_rem == 0 and self._is_bomb_plus_pair_two_hands(_hand):
                banned_set.discard(ACTION_TYPE_PAIR)

        if not banned_set:
            return action_list, False

        if not GUARD_TOOLS_OK:
            return action_list, False

        hand_counter = _hand_counter_from_state(game_state)

        # 硬排除（GUA-112：一手清候选永不被 banned 删掉）
        filtered = []
        for a in action_list:
            if hand_counter and _is_finish_now_action(a, hand_counter):
                filtered.append(a)
                continue
            try:
                atype = get_action_type(a)
                if atype not in banned_set:
                    filtered.append(a)
            except Exception:
                filtered.append(a)  # 未知类型放行

        is_empty = len(filtered) == 0
        if is_empty:
            logger.debug("banned 硬排后 actionList 为空，banned_set=%s", banned_set)

        return filtered, is_empty

    def _select_main_enemy(
        self, enemies: Dict[int, Dict[str, Any]], my_pos: int,
    ) -> Tuple[int, Dict[str, Any]]:
        """按危险度挑主目标敌人。"""
        sorted_enemies = sorted(
            enemies.items(),
            key=lambda kv: self._enemy_danger_score(kv[0], kv[1], my_pos),
        )
        return sorted_enemies[0]

    def _get_q1_protected_types(
        self,
        game_state: Dict[str, Any],
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
        action_list: Optional[List] = None,
    ) -> set:
        """
        Q1 中不应被 secondary ban 删掉的“保护型”。

        规则：
          1. 主目标 enemy 的 recommended / block_with 对应类型受保护
          2. 当前 greaterPos 若是敌人且已进残局，则 greaterAction 同型受保护
          3. GUA-112：存在一手清候选时，其 ACTION_TYPE 受保护
        """
        protected: set = set()
        try:
            from .endgame_preprocessor import EndgamePreprocessor as EP
        except ImportError:
            from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor as EP

        protected.update(EP()._map_types(main_enemy.get("recommended_types", [])))
        baoshu = main_enemy.get("baoshu", {}) or {}
        protected.update(EP()._map_types(baoshu.get("block_with", [])))

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction")
        enemy_positions = {(my_pos + 1) % 4, (my_pos + 3) % 4}
        if greater_pos in enemy_positions and greater_action and GUARD_TOOLS_OK:
            try:
                greater_type = get_action_type(greater_action)
                if greater_type not in (ACTION_TYPE_PASS, ACTION_TYPE_FREE):
                    protected.add(greater_type)
            except Exception:
                pass

        if action_list:
            protected.update(finish_now_protected_action_types(game_state, action_list))

        return protected

    def _collect_q1_banned_set(
        self,
        game_state: Dict[str, Any],
        ec: Dict[str, Any],
        enemies: Dict[int, Dict[str, Any]],
        main_pos: int,
        main_enemy: Dict[str, Any],
        action_list: List,
    ) -> set:
        """
        收集 Q1 banned 集合。

        旧逻辑对所有敌人直接取并集，容易出现：
          - 次要敌人的 ban 删掉主目标 recommended 类型
          - 当前敌人已用 Pair/Trips 控牌，但同型被规则表 ban 掉
        """
        protected_types = self._get_q1_protected_types(
            game_state, ec, main_pos, main_enemy, action_list,
        )
        banned_set: set = set()
        try:
            from .endgame_preprocessor import _ACTION_TYPE_CARD_COUNT as _card_count
        except ImportError:
            from src.v.nn.endgame.endgame_preprocessor import _ACTION_TYPE_CARD_COUNT as _card_count

        for opp_pos, ectx in enemies.items():
            remaining = ectx.get("remaining", 27)
            for banned_type in ectx.get("banned_types", []):
                if banned_type not in protected_types:
                    banned_set.add(banned_type)

            baoshu = ectx.get("baoshu", {})
            if not baoshu:
                continue
            for banned_type in baoshu.get("never_play", []):
                if _card_count.get(banned_type, 99) > remaining:
                    continue
                if banned_type not in protected_types:
                    banned_set.add(banned_type)
        # GUA-244：自由领出 + 主敌剩 ≤3 + 池存在 + 单被接风险高且对子风险低
        # → 豁免报双/报三的 Pair 禁封。否则对子被删 → 决策层兜底出低单送敌人
        # （match 6a8003e6 #17：手 D5 C6 66 77，p1 报双 Pair 被删 →
        # 兜底出 Single/C6 被级牌 D2 接走丢头游）。
        if self._gua244_pair_lead_safe(game_state, ec):
            banned_set.discard(ACTION_TYPE_PAIR)
        return banned_set

    def _should_relax_single_ban_for_enemy_five(
        self, game_state: Dict[str, Any], ec: Dict[str, Any], action_list: List,
    ) -> bool:
        """剩 5 张残局特例：保留 Single 候选给 Q1 做细分判断。"""
        if not GUARD_TOOLS_OK:
            return False
        greater_action = game_state.get("greaterAction")
        greater_pos = game_state.get("greaterPos", -1)
        if not greater_action or get_action_type(greater_action) != ACTION_TYPE_SINGLE:
            return False
        enemy_ctx = ec.get("enemies", {}).get(greater_pos, {})
        if enemy_ctx.get("remaining") != 5:
            return False
        special = self._q1_enemy_five_single_special(
            game_state, action_list, ec, greater_pos, enemy_ctx
        )
        return special is not None and get_action_type(special[1]) == ACTION_TYPE_SINGLE

    def pick_teammate_sprint_small_single(
        self, game_state: Dict[str, Any], action_list: List,
    ) -> Tuple[Optional[int], Optional[List]]:
        """GUA-160：队友恰剩 6 张时，主攻自由领最小自然小散单。"""
        if not GUARD_TOOLS_OK:
            return None, None
        if game_state.get("_role") not in ("主攻", "超强主攻"):
            return None, None

        my_pos = int(game_state.get("myPos", 0))
        greater_pos = int(game_state.get("greaterPos", -1) or -1)
        greater_action = game_state.get("greaterAction")
        if greater_pos not in (-1, my_pos):
            return None, None
        if greater_action and get_action_type(greater_action) not in (
            ACTION_TYPE_PASS, ACTION_TYPE_FREE,
        ):
            return None, None

        ec = game_state.get("_endgame_context", {}) or {}
        teammate_pos = (my_pos + 2) % 4
        teammate_remaining = self._estimate_player_remaining(
            teammate_pos, ec, game_state,
        )
        if teammate_remaining != 6:
            return None, None

        # GUA-229 下家报单禁止送单：下家（my_pos+1）剩 1 张时，送单=直接把牌权送对手跑
        next_pos = (my_pos + 1) % 4
        next_remaining = self._estimate_player_remaining(
            next_pos, ec, game_state,
        )
        if next_remaining == 1:
            logger.info(
                "GUA-229 下家报单禁止送单: next=%d remaining=%d 放弃 GUA-160 送单",
                next_pos, next_remaining,
            )
            return None, None

        cur_rank = str(game_state.get("curRank", "2"))
        card_mask = game_state.get("_card_mask") or {}
        scatter_cards = {
            str(card)
            for card, info in card_mask.items()
            if info and int(info[0]) == -1
        }
        candidates = []
        for index, action in enumerate(action_list):
            if get_action_type(action) != ACTION_TYPE_SINGLE:
                continue
            cards = _get_cards(action)
            if len(cards) != 1 or str(cards[0]) not in scatter_cards:
                continue
            rank = get_card_rank(str(cards[0]))
            pip = CARD_RANK_ORDER.get(rank, 99)
            if rank == cur_rank or not CARD_RANK_ORDER["3"] <= pip <= CARD_RANK_ORDER["9"]:
                continue
            candidates.append((pip, str(cards[0]), index, action))

        if not candidates:
            return None, None
        _, _, index, action = min(candidates)
        logger.info(
            "GUA-160 队友冲刺送单: teammate=%d remaining=%d idx=%d card=%s",
            teammate_pos, teammate_remaining, index, _get_cards(action),
        )
        return index, action

    @staticmethod
    def _teammate_is_head_finisher(
        game_state: Dict[str, Any], teammate_pos: int,
    ) -> bool:
        """GUA-272：平台 done 按完牌顺序；仅 done[0]==队友 才是真头游（非二游/三游）。"""
        done = game_state.get("done")
        if not isinstance(done, (list, tuple)) or not done:
            return False
        try:
            return int(done[0]) == int(teammate_pos)
        except (TypeError, ValueError):
            return False

    def pick_double_second_small_single(
        self, game_state: Dict[str, Any], action_list: List,
    ) -> Tuple[Optional[int], Optional[List]]:
        """GUA-161：队友已头游时，主攻自由领最小自然小散单争双上。

        GUA-272：须 done[0]==队友（真头游）；队友二游/三游（如 done=[3,0]）不触发。
        """
        if not GUARD_TOOLS_OK:
            return None, None
        if game_state.get("_role") not in ("主攻", "超强主攻"):
            return None, None

        my_pos = int(game_state.get("myPos", 0))
        greater_pos = int(game_state.get("greaterPos", -1) or -1)
        greater_action = game_state.get("greaterAction")
        if greater_pos not in (-1, my_pos):
            return None, None
        if greater_action and get_action_type(greater_action) not in (
            ACTION_TYPE_PASS, ACTION_TYPE_FREE,
        ):
            return None, None

        ec = game_state.get("_endgame_context", {}) or {}
        teammate_pos = (my_pos + 2) % 4
        teammate_remaining = self._estimate_player_remaining(
            teammate_pos, ec, game_state,
        )
        if teammate_remaining != 0:
            return None, None

        if not self._teammate_is_head_finisher(game_state, teammate_pos):
            logger.info(
                "GUA-272: teammate=%d remaining=0 但非头游 done=%s → 跳过 GUA-161",
                teammate_pos, game_state.get("done"),
            )
            return None, None

        # GUA-229 下家报单禁止送单：队友已头游但下家（my_pos+1）剩 1 张时，
        # 送单=把牌权直接送对手跑，争双上的前提崩塌
        next_pos = (my_pos + 1) % 4
        next_remaining = self._estimate_player_remaining(
            next_pos, ec, game_state,
        )
        if next_remaining == 1:
            logger.info(
                "GUA-229 下家报单禁止送单: next=%d remaining=%d 放弃 GUA-161 送单",
                next_pos, next_remaining,
            )
            return None, None

        cur_rank = str(game_state.get("curRank", "2"))
        card_mask = game_state.get("_card_mask") or {}
        scatter_cards = {
            str(card)
            for card, info in card_mask.items()
            if info and int(info[0]) == -1
        }
        candidates = []
        for index, action in enumerate(action_list):
            if get_action_type(action) != ACTION_TYPE_SINGLE:
                continue
            cards = _get_cards(action)
            if len(cards) != 1 or str(cards[0]) not in scatter_cards:
                continue
            rank = get_card_rank(str(cards[0]))
            pip = CARD_RANK_ORDER.get(rank, 99)
            if rank == cur_rank or not CARD_RANK_ORDER["3"] <= pip <= CARD_RANK_ORDER["9"]:
                continue
            candidates.append((pip, str(cards[0]), index, action))

        if not candidates:
            return None, None
        _, _, index, action = min(candidates)
        logger.info(
            "GUA-161 双上清散单: teammate=%d idx=%d card=%s",
            teammate_pos, index, _get_cards(action),
        )
        return index, action

    # ── 主决策入口 ──

    def decide(
        self, game_state: Dict[str, Any], action_list: List,
    ) -> Tuple[Optional[int], Optional[List]]:
        """
        Q0→Q3 残局决策。

        Returns:
            (action_index, action) or (None, None) if no endgame decision.
            action_index 是 action_list 中的下标。
        """
        ec = game_state.get("_endgame_context", {})
        if not ec.get("is_active"):
            return None, None

        if not action_list:
            return None, None

        self_context = ec.get("self", {})
        enemies = ec.get("enemies", {})

        # ── GUA-214: 队友出炸弹/同花顺（greater 炸弹类）→ 无论队友剩几张一律 PASS 让道
        # 与 GUA-205 支线1 同语义：队友已持 great 且出炸弹（含 StraightFlush）时，
        # 用任何牌压队友都是损己利敌（炸队友炸弹/同花顺 = 帮敌方拆控制权）。
        # 不依赖队友 is_close（剩牌多也强制让道），无敌人 imminent 例外
        # （队友出炸即掌控权在队友，接管无意义）。
        # 实测：6a76847d 09:21:26 队友剩 12 张出 Bomb/J，V8 Q0 冲刺用 SF/6 反压
        # → 本分支拦截为 PASS。
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction")
        teammate_pos = (my_pos + 2) % 4
        if greater_pos not in (-1, None) and greater_pos == teammate_pos:
            if greater_action and _get_declared_action_type(greater_action) not in ("PASS", "pass"):
                greater_declared = _get_declared_action_type(greater_action)
                if greater_declared in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
                    pidx = next(
                        (i for i, a in enumerate(action_list)
                         if _get_declared_action_type(a) in ("PASS", "pass")),
                        None,
                    )
                    if pidx is not None:
                        logger.info(
                            "GUA-214: greaterPos=teammate(%d) 出%s → PASS 让道（队友炸弹不压，剩牌无关）",
                            greater_pos, greater_declared,
                        )
                        return pidx, action_list[pidx]
                    return None, None

        # ── GUA-212: 不压队友 — greaterPos 为 teammate 且 teammate 已出牌 → PASS 让道
        # 覆盖队友出的任意牌型（炸/同花顺/顺/对子/单张等），非特殊控局一律让道，
        # 防止残局 Q0 冲刺 / Q1 封锁把队友当敌方反压（实测 V8 炸10 压队友 TJQKA 顺，
        # 出完剩 C2 D3 D4 D5 S5 烂尾；队友 close 已控牌时正确应对是让队友拿圈）。
        # 条件：队友 close（控牌）才强制让道——队友剩牌多不 close 时保留
        # GUA-113「主攻帮挡」（敌人可能压制队友，主攻拿回控制权）语义。
        # 例外：有敌人 ≤2 张（imminent）时允许接管拦截。
        if greater_pos not in (-1, None) and greater_pos == teammate_pos:
            if greater_action and _get_declared_action_type(greater_action) not in ("PASS", "pass"):
                teammate_close = ec.get("teammate", {}).get("is_close", False)
                enemy_imminent = any(
                    e.get("remaining", 99) <= 2 for e in enemies.values()
                ) if enemies else False
                if teammate_close and not enemy_imminent:
                    for i, a in enumerate(action_list):
                        if _get_declared_action_type(a) in ("PASS", "pass"):
                            logger.info(
                                "GUA-212: greaterPos=teammate(%d) 出%s → PASS 让道",
                                greater_pos, _get_declared_action_type(greater_action),
                            )
                            return i, a
                    return None, None

        # GUA-269：未冲刺不得用对王压队友对子。
        # match=6a8c3e2c t35 3号级牌对 22 压过 2 号对 T 后，1 号 9 张（QQQ+33+KK+对 SB）
        # 尚未两手冲刺，却打 Pair/B 抢权 → 4 号 Bomb/6 接管清头游。
        # 队友 close 时 GUA-212 已让道；此处覆盖队友剩牌多、主攻「帮挡」误用对王的洞。
        # 例外：自己 should_sprint（冲刺拿权）或敌人 ≤2 张 imminent（接管拦截）。
        gua269 = self._gua269_joker_pair_vs_teammate_pass(
            game_state, action_list, ec, greater_pos, greater_action, teammate_pos,
        )
        if gua269 is not None:
            return gua269

        # ── Q0.5: 一手清（finish_now）────  [GUA-097 fix: 提升至 Q0 之前]
        # GUA-112: 无论敌人/队友状态，只要 actionList 含一手清候选 → 立即出完
        # 原嵌套在 Q1 内，敌人不进残局区时 finish_now 被跳过
        # GUA-097: Q0 self sprint 在无炸弹时会 _select_best_index 取首个动作，
        # 可能选 Single 而非 Pair（2张同 rank），跳过 finish_now。
        # 修复：Q0.5 提升至最高优先级，一手清永远优先于冲刺规划。
        finish_now = self._q1_finish_now_candidate(game_state, action_list)
        if finish_now is not None:
            idx, action = finish_now
            logger.info("Q0.5 一手清: idx=%d type=%s", idx, get_action_type(action) if GUARD_TOOLS_OK else "?")
            return idx, action

        # ── Q0: 自己冲刺（次高优先级）────
        if self_context.get("should_sprint"):
            result = self._q0_self_sprint(game_state, action_list, ec)
            if result is not None:
                idx, action = result
                logger.info("Q0 自己冲刺: idx=%d type=%s", idx, get_action_type(action) if GUARD_TOOLS_OK else "?")
                return idx, action

        # ── Q1: 封锁敌方 ──
        if enemies:
            result = self._q1_block_enemy(game_state, action_list, ec)
            if result is not None:
                idx, action = result
                rewritten = self._gua269_rewrite_joker_pair_vs_teammate(
                    game_state, action_list, ec, idx, action,
                )
                if rewritten is not None:
                    return rewritten
                if _get_declared_action_type(action) not in ("PASS",):
                    # GUA-239：多手自由领出先单试探有意拆 SF/顺子核心 → 豁免拆核心转 PASS
                    if not should_allow_gua239_single_probe(game_state):
                        # GUA-252：敌方 ≤5 张且出单时，拆 TWT/整牌出最大单压牌是残局正确打法，
                        # 豁免「拆核心转 PASS」拦截（match=6a86823d 残局 777+KK 对手打 S8，
                        # Q1 已找到 K 要压，却被 _action_breaks_core_structure 误杀成 PASS）。
                        if not self._should_exempt_break_core_for_enemy_five_single(
                            game_state, ec, action,
                        ):
                            if self._action_breaks_core_structure(action, game_state):
                                # GUA-278：下家敌≤2 且有炸 → 最廉炸截断，勿拆核转 PASS
                                # （match=6a8d4603：GUA-135 min TWT → 拆核 PASS，放走下家头游）
                                bomb_alt = self._gua278_critical_lower_enemy_bomb(
                                    game_state, action_list, ec,
                                )
                                if bomb_alt is not None:
                                    return bomb_alt
                                pidx = next(
                                    (i for i, a in enumerate(action_list)
                                     if _get_declared_action_type(a) in ("PASS",)),
                                    None,
                                )
                                if pidx is not None:
                                    logger.info("Q1 封锁拆整牌(%s) → PASS",
                                                _get_declared_action_type(action))
                                    return (pidx, action_list[pidx])
                logger.info("Q1 封锁敌方: idx=%d type=%s", idx, get_action_type(action) if GUARD_TOOLS_OK else "?")
                return idx, action

        # ── Q2: 助攻队友 ──
        teammate = ec.get("teammate", {})
        if teammate.get("is_close"):
            result = self._q2_assist_teammate(game_state, action_list, ec)
            if result is not None:
                idx, action = result
                logger.info("Q2 助攻队友: idx=%d type=%s", idx, get_action_type(action) if GUARD_TOOLS_OK else "?")
                return idx, action

        # ── Q3: 炸弹兜底 ──
        result = self._q3_bomb_fallback(game_state, action_list, ec)
        if result is not None:
            idx, action = result
            logger.info("Q3 炸弹兜底: idx=%d type=%s", idx, get_action_type(action) if GUARD_TOOLS_OK else "?")
            return idx, action

        # 残局未命中 → 上游管线兜底
        return None, None

    # ═══════════════════════════════════════════════════
    #  Q0: 自己冲刺
    # ═══════════════════════════════════════════════════

    def _is_bomb_plus_pair_two_hands(self, hand_cards: List[str]) -> bool:
        """GUA-243: 本方是否恰好两手整牌 = 炸弹 + 对子（如 4星8炸 + 对A）。"""
        if not hand_cards:
            return False
        counts = sorted(
            Counter(get_card_rank(str(c)) for c in hand_cards).values()
        )
        return len(counts) == 2 and counts[0] == 2 and counts[1] >= 4

    @classmethod
    def _is_bomb_plus_one_structure_hand(cls, hand_cards: List[str]) -> bool:
        """GUA-267：恰好「火 + 一手整牌」。

        火 = ≥4 同点炸或同花顺。第二手仅限：单 / 对 / 顺 / TWT / 三张 /
        三连对 / 钢板。炸+两张散单等不算。
        """
        cards = [str(c) for c in (hand_cards or [])]
        if not cards or not GUARD_TOOLS_OK:
            return False
        fire = cls._find_bomb_family_cards(cards) or cls._find_straight_flush_cards(cards)
        if not fire:
            return False
        left = list(cards)
        for card in fire:
            try:
                left.remove(card)
            except ValueError:
                return False
        return cls._remainder_is_named_second_hand(left)

    @classmethod
    def _remainder_is_named_second_hand(cls, cards: List[str]) -> bool:
        """第二手是否为单/对/顺/TWT/三张/三连对/钢板。"""
        left = [str(c) for c in (cards or [])]
        n = len(left)
        if n == 0 or not GUARD_TOOLS_OK:
            return False
        ranks = [get_card_rank(c) for c in left]
        counts = sorted(Counter(ranks).values())
        if n == 1:
            return True
        if n == 2:
            if counts == [2]:
                return True
            jokers = {"HR", "SB", "R", "B"}
            return all(r in jokers for r in ranks)
        if n == 3:
            return counts == [3]
        if n == 5:
            if counts == [2, 3]:
                return True
            return cls._is_five_card_straight(left)
        if n == 6:
            two_trips = cls._find_two_trips_cards(left)
            if two_trips and len(two_trips) == 6:
                return True
            three_pair = cls._find_three_pair_cards(left)
            return bool(three_pair and len(three_pair) == 6)
        return False

    @staticmethod
    def _is_five_card_straight(cards: List[str]) -> bool:
        """5 张是否官方顺子窗口（A2345…TJQKA），级牌当自然点。"""
        if len(cards) != 5 or not GUARD_TOOLS_OK:
            return False
        ranks = [get_card_rank(str(c)) for c in cards]
        if len(set(ranks)) != 5:
            return False
        natural = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K"]
        windows = [natural[i:i + 5] for i in range(len(natural) - 4)]
        windows.append(["T", "J", "Q", "K", "A"])
        rank_set = set(ranks)
        return any(rank_set == set(w) for w in windows)

    @staticmethod
    def _outside_jokers_remain(game_state: Dict[str, Any]) -> Optional[bool]:
        """GUA-261：外面（非我手）是否仍有未出大小王。

        优先 `_belief.joker_signal`；否则 MemoryTracker.get_joker_tracking。
        无记牌证据时返回 None（不强制冲刺对）。
        """
        joker = (game_state.get("_belief") or {}).get("joker_signal") or {}
        if joker:
            out = (
                int(joker.get("hr_remain") or 0)
                - int(joker.get("hr_in_my_hand") or 0)
                + int(joker.get("sb_remain") or 0)
                - int(joker.get("sb_in_my_hand") or 0)
            )
            return out > 0
        tracker = game_state.get("_memory_tracker")
        if tracker is not None and hasattr(tracker, "get_joker_tracking"):
            try:
                tr = tracker.get_joker_tracking()
                out = int(
                    (tr.get("HR") or {}).get("outside_my_hand", 0)
                ) + int(
                    (tr.get("SB") or {}).get("outside_my_hand", 0)
                )
                return out > 0
            except Exception:
                return None
        return None

    @staticmethod
    def _hand_pair_plus_singles_no_joker(
        hand_cards: List[str],
    ) -> Optional[str]:
        """手牌恰为「一对 + 若干单」且无大小王 → 返回对子 rank；否则 None。"""
        if not hand_cards:
            return None
        ranks: List[str] = []
        for c in hand_cards:
            s = str(c)
            if s in ("SB", "HR", "BJ", "RJ"):
                return None
            rk = get_card_rank(s)
            if rk in ("SB", "HR", "BJ", "RJ"):
                return None
            ranks.append(rk)
        cnt = Counter(ranks)
        if any(v >= 3 for v in cnt.values()):
            return None
        pairs = [r for r, v in cnt.items() if v == 2]
        singles = [r for r, v in cnt.items() if v == 1]
        if len(pairs) != 1 or not singles:
            return None
        return pairs[0]

    def _q0_pair_plus_singles_sprint_lead(
        self,
        game_state: Dict[str, Any],
        non_bombs: List[Tuple[int, List]],
        action_list: List,
    ) -> Optional[Tuple[int, List]]:
        """GUA-261：无王在手 + 外面有王 + 对>K → 领出冲刺出对。

        用户定音（match=6a87fb05）：手牌级牌对2+单T、下家亦剩3，出单T被压致败；
        合理打法出级牌对冲刺。外面无大小王时可出单、拆级牌对回收（本分支不命中）。
        """
        hand_cards = list(game_state.get("handCards") or [])
        pair_rank = self._hand_pair_plus_singles_no_joker(hand_cards)
        if pair_rank is None:
            return None
        outside = self._outside_jokers_remain(game_state)
        if outside is not True:
            return None
        cur_rank = str(game_state.get("curRank", "2"))
        # 对子牌力：用同点任一牌面 + get_card_value（级牌=15 > K=11）
        sample = next(
            (c for c in hand_cards if get_card_rank(str(c)) == pair_rank),
            None,
        )
        if sample is None:
            return None
        pair_val = get_card_value(str(sample), cur_rank) if GUARD_TOOLS_OK else 0
        k_val = CARD_RANK_ORDER.get("K", 11)
        if pair_val <= k_val:
            return None
        pair_acts = [
            (i, a) for i, a in non_bombs
            if (
                _get_declared_action_type(a) == ACTION_TYPE_PAIR
                and len(_get_cards(a)) == 2
                and get_card_rank(str(_get_cards(a)[0])) == pair_rank
            )
        ]
        if not pair_acts:
            return None
        logger.info(
            "Q0 GUA-261 高对冲刺: pair=%s val=%d outside_jokers=1 idx=%d",
            pair_rank, pair_val, pair_acts[0][0],
        )
        return self._select_best_index(pair_acts, action_list, game_state)

    @staticmethod
    def _hand_is_trips_wild_single_five(
        hand_cards: List[str], cur_rank: str,
    ) -> bool:
        """GUA-273：5 张 = 三自然张同点 + 逢人配 + 单张（非三带二对子半幅）。"""
        wild = f"H{cur_rank}"
        if len(hand_cards) != 5 or hand_cards.count(wild) != 1:
            return False
        others = [c for c in hand_cards if c != wild]
        if len(others) != 4:
            return False
        rank_counts = Counter(get_card_rank(str(c)) for c in others)
        return sorted(rank_counts.values()) == [1, 3]

    def _q0_trips_wild_single_sprint_lead(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
        non_bombs: List[Tuple[int, List]],
    ) -> Optional[Tuple[int, List]]:
        """GUA-273：三带二+配子+单 两手结构冲刺。

        - 任一敌 remaining==1 → 直接 ThreeWithTwo 一手清头游；
        - 敌均 >1 → 先出最小天然单，配子+三头留炸/TWT 下轮冲头游。
        match 6a8d2762：误走 Q0 配子炸只剩 DT 单张末游。
        """
        if not self._is_my_q1_lead_turn(game_state, ec.get("my_pos", 0)):
            return None
        hand_cards = list(game_state.get("handCards") or [])
        cur_rank = str(game_state.get("curRank", "2"))
        if not self._hand_is_trips_wild_single_five(hand_cards, cur_rank):
            return None

        enemies = ec.get("enemies", {}) or {}
        enemy_one = any(
            int(e.get("remaining", 99) or 99) == 1 for e in enemies.values()
        )
        hand_set = set(hand_cards)

        if enemy_one:
            twt_acts = [
                (i, a) for i, a in non_bombs
                if _get_declared_action_type(a) == ACTION_TYPE_THREE_WITH_TWO
                and set(_get_cards(a)) == hand_set
            ]
            if twt_acts:
                logger.info(
                    "GUA-273: 敌报单 + 三带二配子单 → TWT 一手清 idx=%d",
                    twt_acts[0][0],
                )
                return twt_acts[0]

        # 敌均 >1 张：先出最小天然散单（非三头点数、不用配子），炸/TWT 留回手
        wild = f"H{cur_rank}"
        rank_counts = Counter(get_card_rank(str(c)) for c in hand_cards if c != wild)
        trip_rank = next(
            (r for r, cnt in rank_counts.items() if cnt == 3),
            None,
        )
        singles = [
            (i, a) for i, a in non_bombs
            if (
                _get_declared_action_type(a) == ACTION_TYPE_SINGLE
                and len(_get_cards(a)) == 1
                and str(_get_cards(a)[0]) != wild
                and (
                    trip_rank is None
                    or get_card_rank(str(_get_cards(a)[0])) != trip_rank
                )
            )
        ]
        if singles:
            singles.sort(key=lambda item: _min_card_value(item[1], cur_rank))
            logger.info(
                "GUA-273: 敌>1 张 → 先探单 idx=%d card=%s",
                singles[0][0], _get_cards(singles[0][1]),
            )
            return singles[0]
        return None

    def _q0_self_sprint(
        self, game_state: Dict[str, Any], action_list: List, ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        两手整牌 + 有 bomb-like 资源 → 按出牌权动态选冲刺顺序。

        被动跟压敌控时优先两手冲刺先手（如 StraightFlush→对子），
        非 GUA-103 最小足够炸节炸逻辑。
        """
        my_pos = ec.get("my_pos", 0)
        cur_pos = game_state.get("curPos", my_pos)
        # 自由领出兼容 curPos=-1 / greaterPos=-1（与 GUA-110 `_is_my_q1_lead_turn` 一致）
        is_my_turn = self._is_my_q1_lead_turn(game_state, my_pos)
        enemies = ec.get("enemies", {})

        if is_my_turn and self._q0_lead_bomb_guard_active(game_state):
            logger.info(
                "GUA-287 领出手多非两手清(%d 张) → 禁 Q0 冲刺甩炸，落回 Q1",
                len(game_state.get("handCards") or []),
            )
            return None

        # 分离 bomb-like（含平台 StraightFlush）与非 bomb-like
        bombs = []
        non_bombs = []
        for i, a in enumerate(action_list):
            if _get_declared_action_type(a) in (ACTION_TYPE_PASS, "PASS"):
                non_bombs.append((i, a))
            elif _is_bomb_like_action(a):
                bombs.append((i, a))
            else:
                non_bombs.append((i, a))

        if is_my_turn:
            tws_lead = self._q0_trips_wild_single_sprint_lead(
                game_state, action_list, ec, non_bombs,
            )
            if tws_lead is not None:
                return tws_lead

            play_seq = game_state.get("_active_play_sequence") or []
            if play_seq:
                try:
                    from .sprint_step_picker import SprintStepPicker

                    picker_hit = SprintStepPicker().pick_lead_step(
                        game_state,
                        play_seq,
                        game_state.get("_sprint_belief"),
                        action_list,
                        is_my_turn=True,
                    )
                    if picker_hit is not None:
                        logger.info(
                            "GUA-077 SprintStepPicker lead idx=%s type=%s",
                            picker_hit[0],
                            picker_hit[1][0] if picker_hit[1] else "?",
                        )
                        return picker_hit
                except Exception as exc:
                    logger.debug("GUA-077 SprintStepPicker skip: %s", exc)

        if not bombs:
            if not is_my_turn:
                return None
            if non_bombs:
                hand_cards = game_state.get("handCards", [])
                # GUA-182: 4 张两手整对 → 对子优先（不拆 Pair 打 Single）
                if len(hand_cards) == 4:
                    plays = [
                        (i, a) for i, a in non_bombs
                        if _get_declared_action_type(a) not in (ACTION_TYPE_PASS, "PASS")
                    ]
                    types = {_get_declared_action_type(a) for _, a in plays}
                    # GUA-240: 必须真是两手整对（rank 分布 2+2）才对子优先。
                    # AAA+9（A×3+9×1）被 banned 删 Trips 后 types 失真成
                    # {Pair,Single}，不得把「一手三张+一单」误判为两对拆 AAA
                    # （match=6a7f1a17，21:37:58 拆 Pair/A）。
                    is_two_pairs = sorted(
                        Counter(get_card_rank(c) for c in hand_cards).values()
                    ) == [2, 2]
                    if is_two_pairs and types == {ACTION_TYPE_PAIR, ACTION_TYPE_SINGLE}:
                        pair_acts = [
                            (i, a) for i, a in plays
                            if _get_declared_action_type(a) == ACTION_TYPE_PAIR
                        ]
                        if pair_acts:
                            # GUA-203: 两对子间按小牌优先（先出小对留大对回收），
                            # 避免 actionList 顺序（手牌顺序）导致先出大对。
                            cur_rank = str(game_state.get("curRank", "2"))
                            pair_acts.sort(
                                key=lambda item: _min_card_value(item[1], cur_rank),
                            )
                            return self._select_best_index(pair_acts, action_list, game_state)
                # GUA-183: 敌人报单（≤1 张）领出时，对子/顺子/三带二/三张/三连对/钢板优先于单张
                enemies = ec.get("enemies", {})
                if enemies and is_my_turn:
                    enemy_close = any(
                        e.get("remaining", 27) <= 1 for e in enemies.values()
                    )
                    if enemy_close:
                        non_pass = [
                            (i, a) for i, a in non_bombs
                            if _get_declared_action_type(a) not in (ACTION_TYPE_PASS, "PASS")
                        ]
                        paired_types = {
                            ACTION_TYPE_PAIR,
                            ACTION_TYPE_STRAIGHT,
                            ACTION_TYPE_THREE_WITH_TWO,
                            ACTION_TYPE_TRIPS,
                            ACTION_TYPE_THREE_PAIR,
                            ACTION_TYPE_TWO_TRIPS,
                        }
                        structured_acts = [
                            (i, a) for i, a in non_pass
                            if _get_declared_action_type(a) in paired_types
                        ]
                        if structured_acts:
                            structured_acts.sort(
                                key=lambda x: len(_get_cards(x[1])),
                                reverse=True,
                            )
                            return self._select_best_index(structured_acts, action_list, game_state)
                # GUA-261: 无王在手 + 外面有大小王 + 手牌=对+单(们) + 对>K
                # → 领出冲刺出对（禁先出单被王压后级牌对烂手）。
                # 外面无王时不命中，落回两手冲刺（可先单、拆级牌对回收）。
                pair_sprint = self._q0_pair_plus_singles_sprint_lead(
                    game_state, non_bombs, action_list,
                )
                if pair_sprint is not None:
                    return pair_sprint
                # GUA-236: 仅剩顺+TWT（或任意两手整牌）→ 两手冲刺择优，顺优先于 TWT
                all_cands = [(i, a) for i, a in enumerate(action_list)]
                sprint_lead = self._select_two_turn_sprint_structure(
                    non_bombs, all_cands, game_state, ec,
                    prefer_structure_first=True,
                )
                if sprint_lead is not None:
                    return sprint_lead
                # 自由领出：完整组合（TWT/ThreePair/TwoTrips）优先于散拆；
                # 若同时有 Straight，用结构优先级保证顺 > TWT
                structure_acts = [
                    (i, a) for i, a in non_bombs
                    if _get_declared_action_type(a) in (
                        ACTION_TYPE_STRAIGHT,
                        ACTION_TYPE_THREE_WITH_TWO,
                        ACTION_TYPE_THREE_PAIR,
                        ACTION_TYPE_TWO_TRIPS,
                    )
                ]
                if structure_acts and is_my_turn:
                    structure_acts.sort(
                        key=lambda item: (
                            _q1_structure_priority(
                                _effective_structure_type(item[1])
                            ),
                            -len(_get_cards(item[1])),
                        ),
                    )
                    return structure_acts[0]
                return self._select_best_index(non_bombs, action_list, game_state)
            return None

        # 判断出牌顺序
        enemy_in_endgame = any(
            e.get("remaining", 27) <= 10 for e in enemies.values()
        )

        if is_my_turn:
            bomb_first = False
            if enemy_in_endgame:
                # 检查是否有致命同张数牌型
                cur_rank = str(game_state.get("curRank", "2"))
                for e in enemies.values():
                    e_rem = e.get("remaining", 27)
                    if e_rem <= 10:
                        for idx, act in non_bombs:
                            cards = _get_cards(act)
                            if len(cards) == e_rem and _max_card_value(act, cur_rank) <= CARD_RANK_ORDER.get("K", 11):
                                bomb_first = True
                                break
                    if bomb_first:
                        break

            if bomb_first:
                # 先炸后整：出最大炸弹
                # GUA-221: 炸后剩余牌必须 ≤1 或构成一手整牌，否则（炸弹拆自同张数牌型）
                # 先炸=空扔拆结构，炸完只剩散牌，落回先整后炸（保炸出单等）。
                bomb_idx, bomb_action = self._select_best_bomb(bombs, action_list)
                bomb_cards = _get_cards(bomb_action)
                hand_cards = game_state.get("handCards", []) or []
                remain = list((Counter(hand_cards) - Counter(bomb_cards)).elements())
                remain_type = get_action_type(remain) if GUARD_TOOLS_OK else None
                if len(remain) <= 1 or remain_type not in (None, ACTION_TYPE_FREE):
                    return (bomb_idx, bomb_action)
                logger.info(
                    "Q0 跳过 bomb_first(GUA-221): 炸后剩 %d 张非整手 %s，先整后炸",
                    len(remain), remain,
                )
                bomb_first = False

            # GUA-151: 领出时炸后剩牌 ≤1（一次清场或仅剩单张）→ 直接出炸抢头游
            # 避免 prefer_structure_first 把炸排在整牌后面，
            # 导致"全同点手牌可一次清场"被拆成 Trips+Pair 等错误选择。
            # GUA-168 修正：若结构刚好是 [bomb + 单张] 且对手两家均非 1 张，
            # 优先出单试探、炸留作回手，跳过 GUA-151 直出炸。
            if bombs:
                hand_cards = game_state.get("handCards", []) or []
                total = len(hand_cards)
                enemies = ec.get("enemies", {})
                opp_not_one = all(
                    e.get("remaining", 27) != 1 for e in enemies.values()
                )
                has_single = any(
                    _get_declared_action_type(a) == "Single"
                    for _, a in non_bombs
                )
                skip_gua151 = False
                for _idx, _act in bombs:
                    bomb_cards = _get_cards(_act)
                    bomb_size = len(bomb_cards)
                    if bomb_size >= total - 1:
                        if bomb_size == total - 1 and opp_not_one and has_single:
                            # GUA-168: bomb+单张、对手非1张、有可出单 → 落回两手冲刺逻辑
                            skip_gua151 = True
                            break
                        logger.info(
                            "Q0 领出炸清场抢头游: total=%d bomb_size=%d",
                            total, bomb_size,
                        )
                        return self._select_best_bomb(bombs, action_list)
                if skip_gua151:
                    pass  # 落回下方先整后炸逻辑

            # GUA-179：3 手冲刺保护（1 炸 + 2 非炸结构）→ 先出弱结构存炸防反
            if len(bombs) == 1 and len(non_bombs) == 2:
                _nb0_type = _effective_structure_type(non_bombs[0][1])
                _nb1_type = _effective_structure_type(non_bombs[1][1])
                _nb0_pass = _get_declared_action_type(non_bombs[0][1]) == "PASS"
                _nb1_pass = _get_declared_action_type(non_bombs[1][1]) == "PASS"
                if not _nb0_pass and not _nb1_pass:
                    _type0 = _get_declared_action_type(non_bombs[0][1])
                    _type1 = _get_declared_action_type(non_bombs[1][1])
                    _p0 = _q1_structure_priority(_nb0_type) if _nb0_type != "PASS" else 99
                    _p1 = _q1_structure_priority(_nb1_type) if _nb1_type != "PASS" else 99
                    # 选 priority 低（更弱/更安全）的结构先出
                    weaker_idx = 0 if _p0 >= _p1 else 1
                    weaker_item = non_bombs[weaker_idx]
                    logger.info(
                        "Q0 3手冲刺: 先出弱结构 %s (pri=%d) 存炸防反",
                        _get_declared_action_type(weaker_item[1]),
                        _p0 if weaker_idx == 0 else _p1,
                    )
                    return weaker_item

            # GUA-243：本方仅剩「炸弹 + 对子」两手整牌且队友未头游时，
            # 若下家剩两张（报双）→ 拆对子打单（炸留作回手），不拆炸弹打单。
            # 队友未头游时对子冲刺主动权不如炸稳，拆对单试探、炸控回手。
            hand_cards = game_state.get("handCards", []) or []
            if bombs and self._is_bomb_plus_pair_two_hands(hand_cards):
                _team_rem = (ec.get("teammate") or {}).get("remaining")
                if _team_rem not in (None, 0):
                    _next_pos = (my_pos + 1) % 4
                    _next_rem = (enemies.get(_next_pos) or {}).get("remaining")
                    if _next_rem == 2:
                        _pair_rank = None
                        for _rank, _cnt in Counter(
                            get_card_rank(str(c)) for c in hand_cards
                        ).items():
                            if _cnt == 2:
                                _pair_rank = _rank
                                break
                        if _pair_rank is not None:
                            for _i, _a in non_bombs:
                                if (
                                    _get_declared_action_type(_a) == ACTION_TYPE_SINGLE
                                    and len(_get_cards(_a)) == 1
                                    and get_card_rank(str(_get_cards(_a)[0])) == _pair_rank
                                ):
                                    logger.info(
                                        "Q0 GUA-243 拆对打单: 队友未头游下家剩2 idx=%d card=%s",
                                        _i, _get_cards(_a),
                                    )
                                    return _i, _a

            # 先整后炸：两手冲刺优先整组（TwoTrips/ThreePair/TWT…），禁半组 Trips
            all_cands = [(i, a) for i, a in enumerate(action_list)]
            sprint_lead = self._select_two_turn_sprint_structure(
                non_bombs, all_cands, game_state, ec,
                prefer_structure_first=True,
            )
            if sprint_lead is not None:
                return sprint_lead
            # 两手冲刺失败 + 有炸 → 让管线落回 Q1（GUA-142 整结构保 SF/炸冲刺路径）
            if bombs:
                return None
            whole = self._select_q0_whole_structure_lead(non_bombs, game_state)
            if whole is not None:
                return whole
            if non_bombs:
                return self._select_best_index(non_bombs, action_list, game_state)
            # 整牌没有 → 炸
            return self._select_best_bomb(bombs, action_list)
        else:
            # 出牌权不在我手
            if enemy_in_endgame:
                # 两手冲刺：被动跟压时优先出能压敌且保留完整第二手的先手（如 SF→对子）
                sprint_first = self._q0_passive_sprint_vs_enemy_control(
                    game_state, action_list, ec,
                )
                if sprint_first is not None:
                    return sprint_first
                # GUA-207: 被动跟压 + 敌控散牌型 + 手牌 = 炸 + 少量散牌（非两手冲刺）
                # → 先用最小可压散牌（含级牌）压制、保留炸弹作回手，避免盲目炸后
                #   被敌方更大炸反压而散牌失去控制权。
                keep_bomb = self._q0_passive_keep_bomb_play_scatter(
                    game_state, action_list, ec,
                )
                if keep_bomb is not None:
                    return keep_bomb
                # GUA-248: greater 来自队友（不 close 场景）→ 不兜底炸队友
                # 队友剩牌多不 close 时 GUA-212 不强制让道，但队友出牌（含顶大单 A）
                # 属队友节奏；Q0 兜底 _select_best_bomb 会把队友当敌方反压，浪费炸弹
                # 且坑队友拿圈。实测 match 6a85a735 20:53:40 V8 Bomb/T 压队友 DA。
                # 例外：敌人 ≤2 张（imminent）接管拦截除外（与 GUA-212 语义一致）。
                greater_pos = game_state.get("greaterPos", -1)
                if greater_pos not in (-1, None) and greater_pos == (my_pos + 2) % 4:
                    enemy_imminent = any(
                        e.get("remaining", 99) <= 2 for e in enemies.values()
                    ) if enemies else False
                    if not enemy_imminent:
                        logger.info(
                            "GUA-248: greaterPos=teammate(%d) → Q0 被动不兜底炸队友",
                            greater_pos,
                        )
                        return None
                if bombs:
                    return self._select_best_bomb(bombs, action_list)
                return None
            else:
                # 不急于炸，让对手出 → 残局管线不越权，fall through 到 GUA-075
                return None

    def _q0_lead_bomb_guard_active(self, game_state: Dict[str, Any]) -> bool:
        """
        GUA-287：手牌>5 且语义手数>2（非两手整牌清）→ Q0 自由领出禁冲刺甩炸。

        用户口径（2026-08-29）：有炸 + 手多（非两手清）→ 炸不出领出轮；
        先整牌锁窗（GUA-107）/ 单诱拆（GUA-220 Tier2），炸弹留作回手/截断。
        两手整牌（语义≤2，含两手冲刺 GUA-236/257/221 等）不受影响。
        无 `_group_type_map`（单元测试等构造）保持旧行为（真实对局恒有组牌注入）。
        """
        hand_cards = game_state.get("handCards") or []
        if len(hand_cards) <= 5:
            return False
        grouptype_map = game_state.get("_group_type_map")
        if not grouptype_map:
            return False
        try:
            from .endgame_preprocessor import EndgamePreprocessor as EP
        except ImportError:  # pragma: no cover
            from src.v.nn.endgame.endgame_preprocessor import (  # type: ignore
                EndgamePreprocessor as EP,
            )
        return EP.count_semantic_hands(grouptype_map) > 2

    def _select_q0_whole_structure_lead(
        self,
        non_bombs: List[Tuple[int, List]],
        game_state: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        Q0 自由领出：优先整牌型（小点在前），跳过可被整组覆盖的半组。

        整牌型：Straight / ThreeWithTwo / TwoTrips / ThreePair / Trips / Pair / Single。
        若候选里已有 TwoTrips，则跳过同牌点钢板半组 Trips；同理 ThreePair vs Pair。
        """
        if not non_bombs:
            return None
        cur_rank = str(game_state.get("curRank", "2"))

        has_two_trips = False
        has_three_pair = False
        has_twt = False
        for _, act in non_bombs:
            declared = _get_declared_action_type(act)
            if declared == ACTION_TYPE_TWO_TRIPS:
                has_two_trips = True
            elif declared == ACTION_TYPE_THREE_PAIR:
                has_three_pair = True
            elif declared == ACTION_TYPE_THREE_WITH_TWO:
                has_twt = True

        scored: List[Tuple[Tuple[int, int, int], Tuple[int, List]]] = []
        for item in non_bombs:
            _, act = item
            declared = _get_declared_action_type(act)
            if declared in (ACTION_TYPE_PASS, "PASS"):
                continue
            # 有整组钢板时，禁止半组 Trips 领出
            if has_two_trips and declared == ACTION_TYPE_TRIPS:
                continue
            if has_three_pair and declared == ACTION_TYPE_PAIR:
                continue
            if has_twt and declared in (ACTION_TYPE_TRIPS, ACTION_TYPE_PAIR):
                # 有完整三带二时，不拆成 Trips/Pair 领出
                continue
            atype = _effective_structure_type(act)
            cards = _get_cards(act)
            scored.append((
                (
                    _q1_structure_priority(atype),
                    _min_card_value(act, cur_rank) if cards else 99,
                    -len(cards),
                ),
                item,
            ))
        if not scored:
            return None
        scored.sort(key=lambda entry: entry[0])
        return scored[0][1]

    def _q0_passive_sprint_vs_enemy_control(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        Q0 被动跟压：两手冲刺时出能压敌控且保留完整第二手的先手整牌。

        非 GUA-103「最小足够炸」逻辑（节炸仅在 Q1 多档 bomb-like 间比较）。
        """
        if not self._is_q1_following_enemy_control(game_state, ec):
            return None

        greater_action = game_state.get("greaterAction")
        if not greater_action or not _is_control_action(greater_action):
            return None

        cur_rank = str(game_state.get("curRank", "2"))
        all_candidates = [(i, a) for i, a in enumerate(action_list)]
        playable = []
        for idx, act in all_candidates:
            if _get_declared_action_type(act) in (ACTION_TYPE_PASS, "PASS"):
                continue
            if _action_beats_greater(act, greater_action, cur_rank):
                playable.append((idx, act))

        if not playable:
            return None

        return self._select_two_turn_sprint_structure(
            playable, all_candidates, game_state, ec,
        )

    def _q0_passive_keep_bomb_play_scatter(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-207: 被动跟压时保留炸弹，先用最小可压散牌（含级牌）压制。

        适用场景（镜像 GUA-168 领出侧「先出单试探、炸留作回手」）：
          跟压敌方控牌 + greater 为散牌型（Single/Pair）+ 手牌 = 炸弹 + 少量散牌
          （非两手冲刺结构）+ 敌未报单 → 用最小能压 greater 的散牌（级牌优先）
          先压，炸弹保留作回手冲刺。

        原缺陷：`_q0_passive_sprint_vs_enemy_control` 两手冲刺规划失败后直接
        `_select_best_bomb` 盲目炸，被敌方更大炸反压后散牌彻底失去控制权。
        例（match=6a74236927e7bf01db12f002 L493-500）：手牌 Bomb/5 + D2 + SJ，
        敌 Single/Q → 应出 D2 压并留 Bomb/5 回手，而非直接 Bomb/5 被 Bomb/J 反压。
        """
        if not self._is_q1_following_enemy_control(game_state, ec):
            return None

        greater_action = game_state.get("greaterAction")
        if not greater_action or not _is_control_action(greater_action):
            return None

        cur_rank = str(game_state.get("curRank", "2"))
        greater_type = _get_declared_action_type(greater_action)
        if greater_type not in (ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR):
            return None

        # GUA-281：两趟三张+配子是两手冲刺（配子升炸），不是「炸+散牌」
        if _is_two_trips_plus_wild_hand(game_state.get("handCards") or [], cur_rank):
            return None

        # 敌报单时不适用：单张可被敌直接接走，且无回手意义 → 落回出炸逻辑
        enemies = ec.get("enemies", {})
        if enemies and any(e.get("remaining", 27) == 1 for e in enemies.values()):
            return None

        scatter_plays = []
        for idx, act in enumerate(action_list):
            declared = _get_declared_action_type(act)
            if declared in (ACTION_TYPE_PASS, "PASS"):
                continue
            if _is_bomb_like_action(act):
                continue
            if declared not in (ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR):
                continue
            if not _action_beats_greater(act, greater_action, cur_rank):
                continue
            # GUA-254: 不拆核心整牌当散牌压——手牌 = 炸 + 散牌时，散牌候选里若含
            # 炸弹/顺子/trips 等核心组成员（如 9999 拆出 C9、AAAA 拆出 SA），单出会
            # 拆掉回手炸弹，后续只剩 trips+散牌被 Q1「拆整牌」拦截只能全 PASS
            # （match=6a86911a 残局拆 9999/AAAA 双炸后连 PASS 负）。此处一律跳过
            # 拆核心动作（不做 GUA-252 豁免——敌≤5 出单拆最大单压牌由 Q1
            # `_q1_enemy_five_single_special` 处理，其选最大单而非 Q0 的最小可压单）。
            if self._action_breaks_core_structure(act, game_state):
                continue
            scatter_plays.append((idx, act))

        if not scatter_plays:
            return None

        # 级牌优先（大牌留作冲刺），同值取小
        scatter_plays.sort(key=lambda item: (
            _min_card_value(item[1], cur_rank), item[0],
        ))
        idx, act = scatter_plays[0]
        logger.info(
            "Q0 被动保留炸: greater=%s/%s → 先出散牌 %s/%s 保留炸弹回手",
            greater_type,
            greater_action[1] if len(greater_action) > 1 else "",
            _get_declared_action_type(act),
            act[1] if len(act) > 1 else "",
        )
        return idx, act

    # ═══════════════════════════════════════════════════
    #  Q1: 封锁敌方
    # ═══════════════════════════════════════════════════

    def _q1_block_enemy(
        self, game_state: Dict[str, Any], action_list: List, ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        敌人进入残局区 → 按 recommended_types 出牌封锁。

        多敌人时：
          - banned 取并集
          - 主目标（最危险敌人）recommended 优先
          - 动作须过 banned_set 滤
        """
        my_pos = ec.get("my_pos", 0)
        enemies = ec.get("enemies", {})
        if not enemies:
            return None

        teammate_hold = self._q1_hold_teammate_max_control(game_state, action_list, ec)
        if teammate_hold is not None:
            return teammate_hold

        upper_yield = self._q1_yield_upper_endgame_to_teammate(
            game_state, action_list, ec,
        )
        if upper_yield is not None:
            return upper_yield

        finish_now = self._q1_finish_now_candidate(game_state, action_list)
        if finish_now is not None:
            return finish_now

        # GUA-282：队友领出圈禁止对敌方普通覆盖开炸/SF；有同型则跟，仅炸可压则 PASS。
        if self._q1_teammate_led_hold_bombs(game_state, ec):
            stripped = [
                a for a in action_list
                if isinstance(a, list) and not _is_bomb_like_action(a)
            ]
            has_follow = any(
                _get_declared_action_type(a) not in (ACTION_TYPE_PASS, "PASS")
                for a in stripped
            )
            if not has_follow:
                gua282_pass = self._q1_hold_teammate_led_trick_bomb(
                    game_state, action_list, ec,
                )
                if gua282_pass is not None:
                    return gua282_pass
            else:
                # 炸位改 PASS 占位，保留原下标，避免 actIndex 错位
                action_list = [
                    (["PASS", "PASS", "PASS"]
                     if isinstance(a, list) and _is_bomb_like_action(a)
                     else a)
                    for a in action_list
                ]

        # GUA-142：自由领出整组 ThreePair/TwoTrips，出完后剩 SF/炸冲刺路径
        structure_sprint = self._q1_free_lead_structure_sprint(
            game_state, action_list, ec,
        )
        if structure_sprint is not None:
            return structure_sprint

        # ① 找最危险敌人（主目标）
        main_pos, main_enemy = self._select_main_enemy(enemies, my_pos)

        gua115_pass = self._q1_gua115_fire_no_bomb_four_pass(
            game_state, action_list, ec, main_pos, main_enemy,
        )
        if gua115_pass is not None:
            return gua115_pass

        gua267_bomb = self._q1_bomb_plus_one_sprint_vs_four(
            game_state, action_list, ec, main_enemy,
        )
        if gua267_bomb is not None:
            return gua267_bomb

        counter_bomb = self._q1_counter_enemy_bomb(
            game_state, action_list, ec, main_pos, main_enemy,
        )
        if counter_bomb is not None:
            return counter_bomb

        # ④.5 GUA-131/132/133 C1/C2/C4 决策（C1 队友协作冲刺 / C2 SF finish / C4 5星炸 finish）
        c124 = self._q1_c1_c2_c4_dispatch(
            game_state, action_list, ec, main_pos, main_enemy,
        )
        if c124 is not None:
            return c124

        # ④.5b GUA-134 C3/C5/C6 决策（高闭合率 yf2 自闭合三手清空）
        c356 = self._q1_c3_c5_c6_dispatch(
            game_state, action_list, ec, main_pos, main_enemy,
        )
        if c356 is not None:
            return c356

        # 敌方剩 5 张 + 当前控牌为 Single 的残局特判：
        # 先判断上/下家、4+1/整牌型、队友牌力和“敌方是否仍可能有更大单张”，
        # 再决定是直接用我方最大合法单张压，还是保留炸弹。

        # ④.5c GUA-135 双进优先级判定（C2/C4 接受 @1 头游 + C3/C5/C6 yf2 自闭合后队整体策略）
        dsp = self._q1_double_second_priority_dispatch(
            game_state, action_list, ec, main_pos, main_enemy,
        )
        if dsp is not None:
            return dsp

        # GUA-264: 跟压单散单 vs 拆对平衡（牌力差≤2 不拆）。
        # 须在 enemy_five_single（敌剩5→最大单）与 recommended 大单张之前，
        # 否则下家剩5会直接拆 A，已散的 Q 被浪费（match 6a880831）。
        structure_bal = self._q1_structure_balanced_single_press(
            game_state,
            [(i, a) for i, a in enumerate(action_list)],
            ec, main_pos, main_enemy,
        )
        if structure_bal is not None:
            return structure_bal

        special = self._q1_enemy_five_single_special(game_state, action_list, ec, main_pos, main_enemy)
        if special is not None:
            return special

        # ② 收集 banned_set（所有敌人 banned + baoshu.never_play 并集）
        banned_set = self._collect_q1_banned_set(game_state, ec, enemies, main_pos, main_enemy, action_list)

        # ③ 构建 banned 过滤后的候选列表
        hand_cards = game_state.get("handCards", [])
        banned_candidates = []
        non_banned_candidates = []
        if GUARD_TOOLS_OK:
            for i, a in enumerate(action_list):
                try:
                    atype = get_action_type(a)
                    if atype in banned_set:
                        banned_candidates.append((i, a))
                    else:
                        non_banned_candidates.append((i, a))
                except Exception:
                    non_banned_candidates.append((i, a))
        else:
            non_banned_candidates = [(i, a) for i, a in enumerate(action_list)]

        teammate_single_cover = self._q1_teammate_single_cover_special(
            game_state, non_banned_candidates, ec, main_pos, main_enemy,
        )
        if teammate_single_cover is not None:
            return teammate_single_cover

        # ③.5 GUA-190：敌方剩 1 张 + 跟牌压单 + 我方手牌结构恰好「2 炸 + 1 孤立大单(>K) + 其余 2 手整牌」
        # → 直接炸弹封死，不给敌方残余牌接牌机会（无法可靠判断残余牌，以手牌结构替代判据）。
        enemy_one_bomb_lock = self._q1_enemy_one_bomb_lock_special(
            game_state, non_banned_candidates, ec, main_pos, main_enemy,
        )
        if enemy_one_bomb_lock is not None:
            return enemy_one_bomb_lock

        # ④.5e GUA-220 Tier 1：下家剩 2 张 + 队友剩 5 张且前序打过 TWT →
        # 优先不组炸弹送队友 TWT（豁免隐式配子炸过滤；下家 2 张压不了 TWT，队友可一手走完）
        twt_feed = self._q1_feed_teammate_twt_when_downseat_two(
            game_state, non_banned_candidates, ec,
        )
        if twt_feed is not None:
            return twt_feed

        # ④.5d GUA-271：领出 + 队友剩 1 → 天然单送队友（级牌留回收；下家 2 张防守）
        teammate_one_natural = self._q1_teammate_one_natural_single_lead(
            game_state, non_banned_candidates, ec,
        )
        if teammate_one_natural is not None:
            return teammate_one_natural

        # ④.5e GUA-202：我方领出 + 队友 close → 优先送牌（防整牌锁敌抢跑）
        lead_feed = self._q1_lead_feed_teammate_special(
            game_state, non_banned_candidates, ec,
        )
        if lead_feed is not None:
            return lead_feed

        # GUA-244：领出 + 主敌剩 ≤3 + 池存在 + 本方多对低单 → 池风险
        # 「单被接 ≥0.7 且对子被接 <0.3」时对子先于单/整牌锁。
        # 须在 _q1_enemy_critical_lead_special 之前：match 6a8003e6 #16/#17
        # 原 TWT 锁敌后兜底出 Single/C6 被级牌 D2 接走丢头游，应 77→66→TWT。
        pool_pair_first = self._q1_pool_pair_first_special(
            game_state, non_banned_candidates, ec, main_pos, main_enemy,
        )
        if pool_pair_first is not None:
            return pool_pair_first

        enemy_one_lead = self._q1_enemy_critical_lead_special(
            game_state, non_banned_candidates, ec, main_pos, main_enemy,
        )
        if enemy_one_lead is not None:
            return enemy_one_lead

        # GUA-239: 自由领出 + 本方多手（≥4 手且含对子 ≥2）+ 下家剩 6 张 + 有天然单
        # → 先出最小天然单试探（保留大王 HR / 对子 ≥2 作回手），而非匹配 recommended
        # 甩整牌 SF/Straight。实测 match 6a7dd97c 22:49:44：V8 手 SF(H7,H2,H2,HT,HJ)+HR
        # +4 对、下家 P3 剩 6 张，Q1 把 SF（GUA-232 降级成 Straight）当 5 张整牌打出，
        # 被 P1 Straight/8 压死失权、对子烂手；正确应先出最小单张 7（下家 6→5），
        # 大王回手后出对子（对子克 5 张）。
        # 出 H7 有意拆 SF 核心组 → 设 _gua239_single_probe 标记，决定层/引擎据此豁免
        # 拆核心拦截（否则被转 PASS / 回退 GUA-075）。须在 _filter_q1_core_break_candidates
        # 之前执行（该过滤会把拆核心的 Single H7 提前滤除）。
        gua239 = self._q1_multi_hand_lead_single_first(
            game_state, non_banned_candidates, ec,
        )
        if gua239 is not None:
            game_state["_gua239_single_probe"] = True
            return gua239

        # GUA-249: 自由领出 + 下家敌方剩 6/7 张 + 本方仅单/对（候选只含 Single/Pair/PASS）
        # + 对子 ≥1 → 先探后克：有天然单出最小天然单试探（保留对子回手）；
        # 无天然单（全对）直接出最小对子（对子克 5 张起点）。实测敌7 领出全对四手
        # （33 44 88 99）原兜底拆对 Single/8 拆散对子结构，应出最小对子。
        gua249 = self._q1_only_single_pair_lead_probe(
            game_state, non_banned_candidates, ec,
        )
        if gua249 is not None:
            return gua249

        # GUA-265: 无炸 + TWT/三张 + 多对 + 下家剩 6/7 → 按记牌先 TWT 或第二小对，
        # 禁止机械拆级牌打最大单（最大单仅当自己还有炸弹）。
        gua265 = self._q1_no_bomb_twt_pairs_lead(
            game_state, non_banned_candidates, ec,
        )
        if gua265 is not None:
            return gua265

        # GUA-210: 封锁候选过滤「拆核心」动作——级牌单张若在 StraightFlush /
        # straight / 炸弹核心组内（如 SF S2-S6 的 S2），Q1 通用路径会优先选级牌
        # 压牌，被 decide 层 _action_breaks_core_structure 拦截后直接 PASS，
        # 浪费可压且不拆核心的次优候选（实测对局 6a7476fe req15：手牌
        # DA,SQ,S2-S6 压敌方 Single/K，Q1 选级牌 S2 拆 SF → PASS 让出头游，
        # 正确应出 scatter 的 DA）。
        non_banned_candidates = self._filter_q1_core_break_candidates(
            non_banned_candidates, game_state)

        non_banned_candidates = self._prune_q1_risky_same_type_lane_candidates(
            game_state, non_banned_candidates, ec, main_pos, main_enemy,
        )

        # GUA-222: 敌方报单剩 1 张 + 跟牌压单 → 用最大单张压（忽略回收优先）。
        # 回收优先排序会把「拆对出的单」排到散单前（出 9 后 J 可回收、出 J 无可回收），
        # 实测 match 6a782bde：手 SJ+H7S7+D9D9 压 Single/5 选拆对 D9，被下家最后一张
        # 压过 done；报单敌方残余 1 张接走即丢头游，应取最大牌力单张。
        enemy_one_press = self._q1_enemy_one_single_press_max(
            game_state, non_banned_candidates, ec, main_pos, main_enemy,
        )
        if enemy_one_press is not None:
            return enemy_one_press

        # GUA-256: 压单时手牌有 ≥2 个可压普通散单（非级牌）且无炸弹 →
        # 出「倒数第二小」的散单，不用级牌大单拦。实测 match 6a869e90
        # （logs/v8_vs_botzone_20260820_142630.log L108-115）：手牌散单 D8/CJ/DQ
        # + 级牌 C2 + 对子 SA/HA，压 Single/7 被 GUA-122 排序把 C2 提到最前 → 出
        # 级牌 C2 拦小单浪费大牌；应出倒数第二小散单 CJ（保留最小 D8 / 级牌 C2）。
        scatter_second = self._q1_scatter_single_second_smallest_press(
            game_state, non_banned_candidates, ec, main_pos, main_enemy,
        )
        if scatter_second is not None:
            return scatter_second

        # GUA-266: 敌方处在 6/7/8 张结构区时，拦截要看「可能牌型 + 拦完能否再拦」，
        # 禁止机械打最大单（大王/级牌/A）。领出优先整牌锁；跟压单若只剩贵单且
        # 打出后没有干净回手 → PASS。
        gua266 = self._q1_structured_zone_lookahead(
            game_state, non_banned_candidates, ec, main_pos, main_enemy,
        )
        if gua266 is not None:
            return gua266

        # GUA-245: 残局 Q1 级牌压单策略缺失。
        # 对手剩 ≤5 张出单 + 本方持有级牌单张 + 本方有冲刺路径 →
        # 主动压单夺回领出权（而非 PASS 让对手跑完）。
        # 须在 ④ recommended 之前：match 6a83177a V8 含 D2×2+S2 连续 8 次 PASS。
        level_card_press = self._q1_level_card_press_single(
            game_state, non_banned_candidates, ec, main_pos, main_enemy,
        )
        if level_card_press is not None:
            return level_card_press

        # ④ 走 recommended 优先（主目标）
        rec_types = main_enemy.get("recommended_types", [])
        if rec_types:
            recom_actions = self._filter_by_recommended_types(
                non_banned_candidates, rec_types, game_state,
            )
            if recom_actions:
                # recommended 排序（回收优先）
                recom_actions = _sort_q1_block_candidates(recom_actions, hand_cards, game_state)
                return self._select_best_index(recom_actions, action_list, game_state)

        # ⑤ recommended 走不通 → 看 baoshu.block_with
        baoshu = main_enemy.get("baoshu", {})
        block_with = baoshu.get("block_with", []) if baoshu else []
        if block_with:
            block_actions = self._filter_by_recommended_types(
                non_banned_candidates, block_with, game_state,
            )
            if block_actions:
                block_actions = _sort_q1_block_candidates(block_actions, hand_cards, game_state)
                return self._select_best_index(block_actions, action_list, game_state)

        # ⑥ 仍无 → 任意 non_banned
        if non_banned_candidates:
            non_banned_candidates = _sort_q1_block_candidates(
                non_banned_candidates, hand_cards, game_state,
            )
            return self._select_best_index(non_banned_candidates, action_list, game_state)

        # ⑦ 全被 banned → 走降级路径
        my_pos_val = game_state.get("myPos", 0)
        cur_pos = game_state.get("curPos", my_pos_val)
        is_passive = (cur_pos != my_pos_val)

        # L3 降级：放宽 banned，仅保留 baoshu.never_play 硬禁
        baoshu_never: set = set()
        for opp_pos, ectx in enemies.items():
            bs = ectx.get("baoshu", {})
            if bs:
                baoshu_never.update(bs.get("never_play", []))

        return self._l3_fallback(
            action_list, baoshu_never, str(game_state.get("curRank", "2")),
            is_passive,
        )

    def _filter_q1_core_break_candidates(
        self, candidates: List, game_state: Dict[str, Any],
    ) -> List:
        """GUA-210: 过滤会破坏核心整牌结构的 Q1 封锁候选（保留 PASS 与不拆核心者）。

        仅当过滤后仍有非 PASS 候选才替换；否则返回原列表，全部拆核心时
        交由 decide 层 _action_breaks_core_structure / GUA-199 拦截裁决 PASS。
        """
        if not GUARD_TOOLS_OK:
            return candidates
        kept: List = []
        for item in candidates:
            act = item[1]
            try:
                if _get_declared_action_type(act) in ("PASS", "pass"):
                    kept.append(item)
                    continue
                if self._action_breaks_core_structure(act, game_state):
                    continue
            except Exception:
                pass
            kept.append(item)
        if any(_get_declared_action_type(i[1]) not in ("PASS", "pass")
               for i in kept):
            return kept
        return candidates

    # ── GUA-142：自由领出整结构保 SF/炸冲刺路径 ──

    @staticmethod
    def _remainder_after_action(
        hand_cards: List[str], action: List,
    ) -> Optional[List[str]]:
        """从手牌 multiset 扣除 action 牌张；扣不齐返回 None。"""
        left = list(hand_cards or [])
        for card in _get_cards(action):
            key = str(card)
            try:
                left.remove(key)
            except ValueError:
                return None
        return left

    @staticmethod
    def _find_bomb_family_cards(hand_cards: List[str]) -> Optional[List[str]]:
        """取一手 ≥4 同点炸（张数最多者）。"""
        if not hand_cards or not GUARD_TOOLS_OK:
            return None
        by_rank: Dict[str, List[str]] = {}
        for card in hand_cards:
            rk = get_card_rank(str(card))
            if rk in ("HR", "SB"):
                continue
            by_rank.setdefault(rk, []).append(str(card))
        best: Optional[List[str]] = None
        for cards in by_rank.values():
            if len(cards) >= 4 and (best is None or len(cards) > len(best)):
                best = list(cards)
        return best

    @staticmethod
    def _find_straight_flush_cards(hand_cards: List[str]) -> Optional[List[str]]:
        """
        取一手 5 张同花顺（不含逢人配配牌；A-2-3-4-5 与 10-J-Q-K-A 包接）。
        """
        if not hand_cards or not GUARD_TOOLS_OK:
            return None
        # 自然序（A 既可作高也可作低，用双端）
        natural = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K"]
        by_suit: Dict[str, Dict[str, str]] = {}
        for card in hand_cards:
            c = str(card)
            if len(c) < 2:
                continue
            suit, rank = c[0], c[1:]
            if rank in ("HR", "SB", "R", "B") or c in ("HR", "SB"):
                continue
            by_suit.setdefault(suit, {})[rank] = c

        windows = []
        for i in range(len(natural) - 4):
            windows.append(natural[i:i + 5])
        # A 高顺：T J Q K A
        windows.append(["T", "J", "Q", "K", "A"])

        for suit, rank_map in by_suit.items():
            for window in windows:
                if all(r in rank_map for r in window):
                    return [rank_map[r] for r in window]
        return None

    @staticmethod
    def _find_two_trips_cards(hand_cards: List[str]) -> Optional[List[str]]:
        """
        取一手 6 张钢板（平台 TwoTrips）：两个连续 rank 各 3 张。
        group 内部名 two_trips ↔ 平台 TwoTrips（钢板）。
        """
        if not hand_cards or not GUARD_TOOLS_OK:
            return None
        from collections import Counter
        by_rank: Counter = Counter()
        for card in hand_cards:
            rk = get_card_rank(str(card))
            if rk in ("HR", "SB"):
                continue
            by_rank[rk] += 1
        trip_ranks = sorted(
            (rk for rk, n in by_rank.items() if n >= 3),
            key=lambda r: CARD_RANK_ORDER[r],
        )
        for rk in trip_ranks:
            nxt = next(
                (r for r, v in CARD_RANK_ORDER.items() if v == CARD_RANK_ORDER[rk] + 1),
                None,
            )
            if nxt in by_rank and by_rank[nxt] >= 3:
                out, used = [], {rk: 0, nxt: 0}
                for card in hand_cards:
                    r = get_card_rank(str(card))
                    if r in used and used[r] < 3:
                        used[r] += 1
                        out.append(str(card))
                return out
        return None

    @staticmethod
    def _find_three_pair_cards(hand_cards: List[str]) -> Optional[List[str]]:
        """
        取一手 6 张三连对（平台 ThreePair）：三个连续 rank 各 2 张。
        group 内部名 three_pair ↔ 平台 ThreePair。
        """
        if not hand_cards or not GUARD_TOOLS_OK:
            return None
        from collections import Counter
        by_rank: Counter = Counter()
        for card in hand_cards:
            rk = get_card_rank(str(card))
            if rk in ("HR", "SB"):
                continue
            by_rank[rk] += 1
        pair_ranks = sorted(
            (rk for rk, n in by_rank.items() if n >= 2),
            key=lambda r: CARD_RANK_ORDER[r],
        )
        for rk in pair_ranks:
            nxt = next(
                (r for r, v in CARD_RANK_ORDER.items() if v == CARD_RANK_ORDER[rk] + 1),
                None,
            )
            nxt2 = next(
                (r for r, v in CARD_RANK_ORDER.items() if v == CARD_RANK_ORDER[rk] + 2),
                None,
            )
            if (
                nxt in by_rank and by_rank[nxt] >= 2
                and nxt2 in by_rank and by_rank[nxt2] >= 2
            ):
                out, used = [], {rk: 0, nxt: 0, nxt2: 0}
                for card in hand_cards:
                    r = get_card_rank(str(card))
                    if r in used and used[r] < 2:
                        used[r] += 1
                        out.append(str(card))
                return out
        return None

    @staticmethod
    def _find_high_straight_cards(hand_cards: List[str]) -> Optional[List[str]]:
        """
        取一手 5 连顺（平台 Straight），起点 rank ≥ 8（用户口径）：
        8-9-T-J-Q / 9-T-J-Q-K / T-J-Q-K-A（不含王）。
        """
        if not hand_cards or not GUARD_TOOLS_OK:
            return None
        rank_set = set()
        for card in hand_cards:
            rk = get_card_rank(str(card))
            if rk in ("HR", "SB"):
                continue
            rank_set.add(rk)
        for window in (
            ["8", "9", "T", "J", "Q"],
            ["9", "T", "J", "Q", "K"],
            ["T", "J", "Q", "K", "A"],
        ):
            if all(r in rank_set for r in window):
                return [
                    next(str(c) for c in hand_cards if get_card_rank(str(c)) == r)
                    for r in window
                ]
        return None

    @staticmethod
    def _find_high_recovery_structure_cards(hand_cards: List[str]) -> Optional[List[str]]:
        """取一手「难被压」的冲刺尾牌结构：钢板 / 三连对 / 8+ 顺子。"""
        return (
            EndgameDecider._find_two_trips_cards(hand_cards)
            or EndgameDecider._find_three_pair_cards(hand_cards)
            or EndgameDecider._find_high_straight_cards(hand_cards)
        )

    @staticmethod
    def _action_breaks_bomb_family(
        action: List, hand_cards: List[str],
    ) -> bool:
        """检查出牌是否拆了 ≥4 同点炸弹（部分取走但非全部）。

        GUA-258：GUA-142 自由领出 ThreePair/TwoTrips 冲刺时，若候选动作从炸弹
        （≥4 同点）中取走部分张数，视为拆炸——出完后无炸弹回手，冲刺路径为假，
        应过滤。GUA-154 只在 adapter 层事后标记 broken，拦不住。
        例：手牌 6666+8888+77+顺9-K，ThreePair 667788 从 6666 取 2、8888 取 2
        → 拆双炸（match 6a87081b）。
        不误伤：GUA-142 正常用例从 SF（5 个不同点）或 trips（3 张）取牌凑 ThreePair。
        """
        if not hand_cards or not GUARD_TOOLS_OK:
            return False
        from collections import Counter
        hand_rank: Counter = Counter()
        for c in hand_cards:
            rk = get_card_rank(str(c))
            if rk in ("HR", "SB"):
                continue
            hand_rank[rk] += 1
        action_used: Counter = Counter()
        for c in _get_cards(action):
            rk = get_card_rank(str(c))
            if rk in ("HR", "SB"):
                continue
            action_used[rk] += 1
        for rk, n_used in action_used.items():
            n_hand = hand_rank.get(rk, 0)
            if n_hand >= 4 and 0 < n_used < n_hand:
                return True
        return False

    @classmethod
    def _has_structure_sprint_path(cls, hand_cards: List[str]) -> bool:
        """
        GUA-142 局部：剩牌含 SF / ≥4 炸 / 难被压尾牌（钢板、三连对、8+ 顺子），
        且剥掉该手后剩余点数组 ≤3（对/单/王等，对应「冲刺牌型回手 + 至多约两手尾/王」）。

        GUA-241：纳入钢板/三连对/8+ 顺子为冲刺牌型（用户口径 2026-08-14）。
        不修改 GUA-135 `_has_sprint_capability`（后者只认同点炸 + 一手难压尾牌）。
        """
        cards = list(hand_cards or [])
        if len(cards) < 5:
            return False
        bomb_like = (
            cls._find_straight_flush_cards(cards)
            or cls._find_bomb_family_cards(cards)
            or cls._find_high_recovery_structure_cards(cards)
        )
        if not bomb_like:
            return False
        left = list(cards)
        for c in bomb_like:
            try:
                left.remove(c)
            except ValueError:
                return False
        if not left:
            return True
        if not GUARD_TOOLS_OK:
            return len(left) <= 5
        ranks = {get_card_rank(str(c)) for c in left}
        return len(ranks) <= 3

    def _q1_free_lead_structure_sprint(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-142：自由领出时，优先 ThreePair/TwoTrips，若出完后仍具备 SF/炸冲刺路径。
        """
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction")
        # 自由领出：无有效敌控
        if greater_pos is not None and int(greater_pos) >= 0 and _is_control_action(greater_action):
            return None

        hand_cards = list(game_state.get("handCards", []) or [])
        if not hand_cards or not GUARD_TOOLS_OK:
            return None

        structure_types = {ACTION_TYPE_THREE_PAIR, ACTION_TYPE_TWO_TRIPS, "ThreePair", "TwoTrips"}
        candidates: List[Tuple[int, List]] = []
        for i, act in enumerate(action_list):
            try:
                atype = get_action_type(act)
            except Exception:
                continue
            if atype not in structure_types:
                continue
            # GUA-258：排除拆 ≥4 同点炸弹的动作（拆炸后无炸弹回手=假冲刺路径）
            if self._action_breaks_bomb_family(act, hand_cards):
                continue
            remainder = self._remainder_after_action(hand_cards, act)
            if remainder is None:
                continue
            if self._has_structure_sprint_path(remainder):
                candidates.append((i, act))

        if not candidates:
            return None

        cur_rank = str(game_state.get("curRank", "2"))
        candidates = _sort_by_recapture_first(candidates, hand_cards, cur_rank)
        # 同回收下偏小点整组（冲刺前先出结构）
        candidates.sort(
            key=lambda item: (
                not _has_recapture(item[1], hand_cards, cur_rank),
                _min_card_value(item[1], cur_rank),
                -len(_get_cards(item[1])),
            ),
        )
        picked = candidates[0]
        logger.info(
            "GUA-142 free_lead structure_sprint: idx=%s type=%s",
            picked[0],
            get_action_type(picked[1]) if GUARD_TOOLS_OK else "?",
        )
        return picked

    def _is_q1_following_enemy_control(
        self, game_state: Dict[str, Any], ec: Dict[str, Any],
    ) -> bool:
        """当前是否在跟压敌方控牌（非自由领出）。"""
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction")
        enemy_positions = {(my_pos + 1) % 4, (my_pos + 3) % 4}
        if greater_pos not in enemy_positions:
            return False
        return _is_control_action(greater_action)

    def _q1_allow_bomb_vs_four_card_enemy_exception(
        self, game_state: Dict[str, Any], ec: Dict[str, Any],
    ) -> bool:
        """火不打四例外：允许用炸。

        GUA-267：自己恰好「火 + 一手整牌」（单/对/顺/TWT/三张/三连对/钢板）
        → 即使敌剩 4 张也开炸冲刺（match=6a8c3452）。
        GUA-115：不炸必输且 `has_two_clean_hands`（rest∈{1,2,3,5}）。
        """
        if self._is_bomb_plus_one_structure_hand(game_state.get("handCards") or []):
            return True
        try:
            from .endgame_preprocessor import EndgamePreprocessor as EP
        except ImportError:
            from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor as EP

        if not EP._will_lose(game_state):
            return False
        return bool(ec.get("self", {}).get("has_two_clean_hands"))

    def _q1_bomb_plus_one_sprint_vs_four(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-267：火+一手 vs 报四跟压 → 能压的完整炸抢先冲刺。"""
        if main_enemy.get("remaining") != 4:
            return None
        if not self._is_q1_following_enemy_control(game_state, ec):
            return None
        if not self._is_bomb_plus_one_structure_hand(game_state.get("handCards") or []):
            return None
        greater_action = game_state.get("greaterAction")
        if not greater_action:
            return None
        cur_rank = str(game_state.get("curRank", "2"))
        bombs: List[Tuple[int, List]] = []
        for i, act in enumerate(action_list):
            if not isinstance(act, list):
                continue
            if not _is_bomb_like_action(act):
                continue
            if _action_beats_greater(act, greater_action, cur_rank):
                bombs.append((i, act))
        if not bombs:
            return None
        picked = self._select_best_bomb(bombs, action_list)
        if picked is not None:
            logger.info(
                "GUA-267 火+一手 vs 报四: 开炸冲刺 idx=%d type=%s",
                picked[0], _get_declared_action_type(picked[1]),
            )
        return picked

    def _q1_counter_enemy_bomb(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-188：敌出炸时从 actionList 选最小足够反炸（不再硬跳过 >5 张）。"""
        if not self._is_q1_following_enemy_control(game_state, ec):
            return None
        greater_action = game_state.get("greaterAction")
        if not _is_bomb_like_action(greater_action):
            return None
        picked = select_counter_bomb_like(action_list, greater_action, game_state)
        if picked:
            return picked
        # 敌 sprint 出炸但压不过 → 明确 PASS，避免后续 Q1 误选弱炸
        for i, act in enumerate(action_list):
            if _get_declared_action_type(act) in (ACTION_TYPE_PASS, "PASS"):
                return (i, act)
        return None

    def _q1_gua115_fire_no_bomb_four_pass(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-115：主敌剩 4 张且跟压时火不打四；仅 bomb-like 可压则 PASS。"""
        if main_enemy.get("remaining") != 4:
            return None
        if not self._is_q1_following_enemy_control(game_state, ec):
            return None

        # GUA-286：变手炸弹资源 ≥3 把时豁免 GUA-115，开最廉炸截断。
        # 主敌剩 4 张 + 我方三炸在手，开一把还有两把续控；即便敌藏四炸，
        # 开一把被反压后仍有炸续控（match=6a927cbd：三炸被 PASS 放走下家 TWT 连牌）。
        gua286 = self._q1_gua286_three_bombs_vs_four(
            game_state, action_list,
        )
        if gua286 is not None:
            return gua286

        if self._q1_allow_bomb_vs_four_card_enemy_exception(game_state, ec):
            return None

        pass_candidate: Optional[Tuple[int, List]] = None
        has_non_bomb_candidate = False
        for i, act in enumerate(action_list):
            if not isinstance(act, list):
                continue
            declared = _get_declared_action_type(act)
            if declared in (ACTION_TYPE_PASS, "PASS"):
                pass_candidate = (i, act)
                continue
            if _is_bomb_like_action(act):
                continue
            has_non_bomb_candidate = True

        if has_non_bomb_candidate:
            return None
        return pass_candidate

    def _q1_gua286_three_bombs_vs_four(
        self,
        game_state: Dict[str, Any],
        action_list: List,
    ) -> Optional[Tuple[int, List]]:
        """GUA-286：主敌剩 4 张（调用方已判）时，变手炸弹资源 ≥3 开最廉炸截断。

        统计范围：变手 bomb-like 资源（普通炸 ≥4 同点 / 同花顺）≥3，
        且在 actionList 中存在能压 greaterAction 的炸弹（`_action_beats_greater` 真）。
        炸弹资源数按 actionList 中 bomb-like 候选的**种类**计：同一手牌的四张点
        与同花顺分解出的多条路径可能对应多个候选，去重避免重复计数。

        返回最廉 Bomb/SF（`_select_cheapest_bomb_or_sf`：Bomb≻SF，张少≻点小），
        保留大炸回手续控。
        """
        greater_action = game_state.get("greaterAction")
        if not greater_action:
            return None
        if not action_list:
            return None

        cur_rank = str(game_state.get("curRank", "2"))
        usable_bombs: List[Tuple[int, List]] = []
        seen_groups: List[set] = []
        for i, act in enumerate(action_list):
            if not isinstance(act, list):
                continue
            if not _is_bomb_like_action(act):
                continue
            try:
                atype = get_action_type(act)
            except Exception:
                atype = _get_declared_action_type(act)
            cards = _get_cards(act)
            if atype == ACTION_TYPE_STRAIGHT_FLUSH:
                group_key = frozenset(str(c) for c in cards)
            else:
                ranks = sorted({get_card_rank(str(c)) for c in cards})
                group_key = frozenset(ranks)
            if group_key in seen_groups:
                continue
            seen_groups.append(group_key)
            if _action_beats_greater(act, greater_action, cur_rank):
                usable_bombs.append((i, act))

        if len(usable_bombs) < 3:
            return None

        # 最廉 Bomb/SF（先保结构、再按牌力弱→强，够用就好），与 GUA-278 同语义。
        # GUA-296：① 首键「拆核心组」惩罚——不拆原组牌引擎已组好的 StraightFlush 去凑
        # 5 星炸（5个3含黑桃3、5个4含黑桃4+黑桃5/6/7 → 应保留 3炸+4炸+同花顺 而非
        # 用 5个3 拆 SF）。锚点 match=6a95841d turn12：4 头炸 3、4 压不过对手 4头炸 QQQQ，
        # 原逻辑 Bomb≻SF 直接选 33333 拆 SF（GUA-154 self broken=['StraightFlush']）。
        # ② 次键用牌力序 _bomb_weakest_first_key（SF≻Bomb，4星<5星<同花顺）：候选均够压时
        # 优先最弱一档（4星炸够用就用，不动同花顺）；仅当更弱档不够压才落到同花顺。
        picked = min(
            usable_bombs,
            key=lambda item: (
                _bomb_disrupts_core_group(game_state, item[1]),
                _bomb_weakest_first_key(item[1], cur_rank),
                len(_get_cards(item[1])),
                _max_card_value(item[1], cur_rank),
            ),
        )
        if picked is not None:
            logger.info(
                "GUA-286: 变手炸弹资源=%d ≥3 vs 主敌报四 → 最廉炸截断 idx=%d type=%s",
                len(usable_bombs), picked[0],
                _get_declared_action_type(picked[1]),
            )
        return picked

    def _q1_finish_now_candidate(
        self, game_state: Dict[str, Any], action_list: List,
    ) -> Optional[Tuple[int, List]]:
        """GUA-112：若平台给出一手清牌候选，Q1 不得拆完整手牌。"""
        return find_finish_now_candidate(game_state, action_list)

    def _gua269_joker_pair_vs_teammate_pass(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
        greater_pos: Any,
        greater_action: List,
        teammate_pos: int,
    ) -> Optional[Tuple[int, List]]:
        """GUA-269：未冲刺且压队友对子的同型只有对王 → PASS。"""
        if greater_pos not in (teammate_pos,) or not greater_action:
            return None
        if _get_declared_action_type(greater_action) != ACTION_TYPE_PAIR:
            return None
        self_ctx = ec.get("self") or {}
        if self_ctx.get("should_sprint"):
            return None
        enemies = ec.get("enemies") or {}
        if any(e.get("remaining", 99) <= 2 for e in enemies.values()):
            return None
        pair_follows = [
            a for a in action_list
            if _get_declared_action_type(a) == ACTION_TYPE_PAIR
        ]
        if not pair_follows:
            return None
        if not all(_is_joker_pair_action(a) for a in pair_follows):
            return None
        pidx = next(
            (i for i, a in enumerate(action_list)
             if _get_declared_action_type(a) in ("PASS", "pass")),
            None,
        )
        if pidx is None:
            return None
        logger.info(
            "GUA-269: greaterPos=teammate(%d) Pair 唯一同型是对王且未冲刺 → PASS",
            teammate_pos,
        )
        return pidx, action_list[pidx]

    def _gua269_rewrite_joker_pair_vs_teammate(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
        idx: int,
        action: List,
    ) -> Optional[Tuple[int, List]]:
        """GUA-269：Q1 已选对王压队友且未冲刺 → 改 PASS。"""
        if not _is_joker_pair_action(action):
            return None
        self_ctx = ec.get("self") or {}
        if self_ctx.get("should_sprint"):
            return None
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        teammate_pos = (my_pos + 2) % 4
        greater_pos = game_state.get("greaterPos", -1)
        if greater_pos != teammate_pos:
            return None
        enemies = ec.get("enemies") or {}
        if any(e.get("remaining", 99) <= 2 for e in enemies.values()):
            return None
        pidx = next(
            (i for i, a in enumerate(action_list)
             if _get_declared_action_type(a) in ("PASS", "pass")),
            None,
        )
        if pidx is None:
            return None
        logger.info(
            "GUA-269: Q1 对王压队友(idx=%d) 未冲刺 → PASS",
            idx,
        )
        return pidx, action_list[pidx]

    def _q1_teammate_led_hold_bombs(
        self,
        game_state: Dict[str, Any],
        ec: Dict[str, Any],
    ) -> bool:
        """GUA-282：本圈队友领出且非接管例外 → Q1 不得开炸。"""
        tracker = game_state.get("_memory_tracker")
        led = getattr(tracker, "teammate_led_current_trick", None)
        if tracker is None or not callable(led) or not led():
            return False
        greater_action = game_state.get("greaterAction") or []
        gt = _get_declared_action_type(greater_action)
        if gt in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH, "Bomb", "StraightFlush"):
            return False
        enemies = ec.get("enemies") or {}
        if any(int(e.get("remaining", 99) or 99) <= 2 for e in enemies.values()):
            return False
        if (ec.get("self") or {}).get("should_sprint"):
            return False
        return True

    def _q1_hold_teammate_led_trick_bomb(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """队友领出圈仅剩炸/SF 可压 → PASS。"""
        if not self._q1_teammate_led_hold_bombs(game_state, ec):
            return None
        for i, act in enumerate(action_list):
            if _get_declared_action_type(act) in (ACTION_TYPE_PASS, "PASS"):
                logger.info("GUA-282: 队友领出圈仅炸可压 → PASS 不抢回手")
                return (i, act)
        return None

    def _q1_yield_upper_endgame_to_teammate(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-270：上家敌进残局 + 队友剩牌>5 → 仅「只有炸能压」时 PASS，交由队友。

        match=6a8d09c3 约第 30 回合：队友 3 号出对 → 上家 4 号 JJ 压过 →
        1 号（9 张）残局 Q1 直接 88888 开炸抢权，队友仍持多牌应继续配合线。

        定音：须 greaterPos=上家敌且上家 remaining∈残局区；队友>5 张时不抢炸。
        **例外**：actionList 仍有非炸同型可压（如 Single/Pair）→ 不 PASS，正常跟压
        （match 6a8d1ca9 上家 Single/5 有散单可压不得 PASS）。
        """
        if not self._is_q1_following_enemy_control(game_state, ec):
            return None

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        up_pos = (my_pos - 1) % 4
        greater_pos = game_state.get("greaterPos", -1)
        if greater_pos != up_pos:
            return None

        numofplayers = ec.get("numofplayers") or game_state.get("numofplayers", [27] * 4)
        upper_remaining = int(numofplayers[up_pos] if up_pos < len(numofplayers) else 27)
        try:
            from .endgame_preprocessor import max_end_card
        except ImportError:
            from src.v.nn.endgame.endgame_preprocessor import max_end_card
        if not (1 <= upper_remaining <= max_end_card):
            return None

        # GUA-289：上家本手之前已用过炸弹（historical）→ GUA-270 让道失效，开炸截断。
        # match=6a92e4aa 21:55:13（第 52 回合）：上家连出 Bomb/4→Bomb/3 剩 3 张，V8 手
        # 6 星 J 炸仍 GUA-270 PASS → 放走上家冲刺（scores=[0,3,0,3] V8 队负）。
        # 用户定音（2026-08-29）：上家已用炸说明炸已落底、冲刺在即，不应再按「普通残局
        # 交队友」让道。口径=historical：不算本手刚出的那把炸（21:55:09 上家第一把
        # Bomb/4 刚落地仍保持让道）。
        # GUA-293：优先用 adapter 跨对局累计的 bombs_played（在线 MemoryTracker 恒空，
        # 见 botzone_adapter._count_bombs_played 注释）；无则回退 _memory_tracker。
        cumulative_bombs = game_state.get("_bombs_played_by_seat")
        if isinstance(cumulative_bombs, dict):
            tracked_bombs = int(cumulative_bombs.get(up_pos, 0))
        else:
            tracker = game_state.get("_memory_tracker")
            tracked_bombs = (
                int(tracker.bombs_played.get(up_pos, 0))
                if tracker is not None and hasattr(tracker, "bombs_played")
                else 0
            )
        greater_action = game_state.get("greaterAction")
        greater_is_upper_bomb = (
            tracked_bombs >= 1
            and isinstance(greater_action, list)
            and _is_bomb_like_action(greater_action)
        )
        if tracked_bombs - (1 if greater_is_upper_bomb else 0) >= 1:
            return None

        teammate_pos = (my_pos + 2) % 4
        teammate_remaining = int(
            ec.get("teammate", {}).get("remaining")
            or (numofplayers[teammate_pos] if teammate_pos < len(numofplayers) else 27)
            or 27
        )
        if teammate_remaining <= 5:
            return None

        enemies = ec.get("enemies", {})
        if any(int(e.get("remaining", 99) or 99) <= 2 for e in enemies.values()):
            return None

        has_non_bomb_beater = any(
            _get_declared_action_type(act) not in (ACTION_TYPE_PASS, "PASS")
            and not _is_bomb_like_action(act)
            for act in action_list
            if isinstance(act, list)
        )
        if has_non_bomb_beater:
            return None

        for i, act in enumerate(action_list):
            if _get_declared_action_type(act) in (ACTION_TYPE_PASS, "PASS"):
                logger.info(
                    "GUA-270: 上家敌残局(remaining=%d) 队友剩%d>5 → PASS 交由队友",
                    upper_remaining, teammate_remaining,
                )
                return (i, act)
        return None

    def _q1_hold_teammate_max_control(
        self, game_state: Dict[str, Any], action_list: List, ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """队友已用当前牌型的最大控牌时，Q1 不应再反压队友。"""
        if not GUARD_TOOLS_OK:
            return None

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        teammate_pos = (my_pos + 2) % 4
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction")
        if greater_pos != teammate_pos or not greater_action:
            return None

        if not _is_control_action(greater_action):
            return None

        pass_candidates = []
        for i, act in enumerate(action_list):
            try:
                if get_action_type(act) == ACTION_TYPE_PASS:
                    pass_candidates.append((i, act))
            except Exception:
                continue
        if not pass_candidates:
            return None

        # 队友已经控牌时，Q1 不得再用同花顺/更大炸反压队友。
        if self._should_hold_teammate_bomb_lane(action_list, greater_action):
            return pass_candidates[0]

        # GUA-113：超弱/助攻不得抢队友控牌（含三带二等非 bomb-like 结构反压）。
        if self._is_assist_role_no_win_path(game_state):
            return pass_candidates[0]

        if self._is_teammate_control_effectively_max(game_state, greater_action, ec):
            return pass_candidates[0]
        return None

    def _is_assist_role_no_win_path(self, game_state: Dict[str, Any]) -> bool:
        """GUA-113：组牌 role 为超弱/助攻时，Q1 队友控牌场景一律让道。"""
        role = str(game_state.get("_role") or game_state.get("role") or "")
        return role in ("超弱", "助攻")

    def _should_hold_teammate_bomb_lane(self, action_list: List, greater_action: List) -> bool:
        """队友已控牌时，禁止我方再用 bomb-like 动作反压队友。"""
        if not _is_control_action(greater_action):
            return False

        return any(
            _is_bomb_like_action(act)
            for act in action_list
            if isinstance(act, list) and _get_declared_action_type(act) != ACTION_TYPE_PASS
        )

    def _is_teammate_control_effectively_max(
        self, game_state: Dict[str, Any], greater_action: List, ec: Dict[str, Any],
    ) -> bool:
        """队友当前控牌是否已足够稳，Q1 应让道。"""
        if _is_bomb_like_action(greater_action):
            return True

        ga_type = get_action_type(greater_action)

        tracker = game_state.get("_memory_tracker")
        if tracker is None:
            return self._is_high_teammate_control_static(greater_action, str(game_state.get("curRank", "2")))

        enemies = ec.get("enemies", {})
        enemy_positions = list(enemies.keys())
        if not enemy_positions:
            my_pos = ec.get("my_pos", game_state.get("myPos", 0))
            enemy_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]

        for seat in enemy_positions:
            if self._seat_may_suppress_teammate_control(game_state, seat, greater_action):
                return False
        return True

    def _is_high_teammate_control_static(self, greater_action: List, cur_rank: str) -> bool:
        """无 tracker 时，退回到静态高牌阈值。"""
        ga_type = get_action_type(greater_action)
        if ga_type in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            return True

        cur_val = 0
        if ga_type == ACTION_TYPE_SINGLE:
            cur_val = _max_card_value(greater_action, cur_rank)
        elif ga_type in (ACTION_TYPE_PAIR, ACTION_TYPE_TRIPS, ACTION_TYPE_THREE_WITH_TWO):
            ga_rank = get_action_rank(greater_action)
            if ga_rank in ("B", "R"):
                cur_val = 16 if ga_rank == "B" else 17
            else:
                cur_val = get_card_value(f"H{ga_rank}", cur_rank)
        elif ga_type == ACTION_TYPE_STRAIGHT:
            top_rank = self._get_straight_top_rank(greater_action, cur_rank)
            cur_val = CARD_RANK_ORDER.get(top_rank, 99)
        else:
            return False

        thresholds = {
            ACTION_TYPE_SINGLE: 15,
            ACTION_TYPE_PAIR: 12,
            ACTION_TYPE_TRIPS: 11,
            ACTION_TYPE_THREE_WITH_TWO: 12,
            ACTION_TYPE_STRAIGHT: 10,
        }
        return cur_val >= thresholds.get(ga_type, 99)

    def _seat_may_suppress_teammate_control(
        self, game_state: Dict[str, Any], seat: int, greater_action: List,
    ) -> bool:
        """某敌席是否仍可能用同型更大牌压住队友当前控牌。"""
        cur_rank = str(game_state.get("curRank", "2"))
        ga_type = get_action_type(greater_action)
        target_rank = get_action_rank(greater_action)

        if ga_type == ACTION_TYPE_SINGLE:
            return self._seat_may_hold_single_above(game_state, seat, target_rank, cur_rank)
        if ga_type == ACTION_TYPE_PAIR:
            return self._seat_may_hold_same_rank_combo_above(game_state, seat, target_rank, cur_rank, 2)
        if ga_type == ACTION_TYPE_TRIPS:
            return self._seat_may_hold_same_rank_combo_above(game_state, seat, target_rank, cur_rank, 3)
        if ga_type == ACTION_TYPE_THREE_WITH_TWO:
            return self._seat_may_hold_three_with_two_above(game_state, seat, target_rank, cur_rank)
        if ga_type == ACTION_TYPE_STRAIGHT:
            return self._seat_may_hold_straight_above(game_state, seat, greater_action, cur_rank)
        return True

    def _q1_enemy_five_single_special(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """敌方剩 5 张且当前是单张控牌时的细化判定。"""
        if not GUARD_TOOLS_OK:
            return None

        greater_action = game_state.get("greaterAction")
        if not greater_action or get_action_type(greater_action) != ACTION_TYPE_SINGLE:
            return None
        if main_enemy.get("remaining") != 5:
            return None

        my_pos = ec.get("my_pos", 0)
        cur_rank = str(game_state.get("curRank", "2"))
        best_single = self._find_highest_single_beater(action_list, greater_action, cur_rank)
        if best_single is None:
            return None

        teammate_pos = (my_pos + 2) % 4
        up_pos = (my_pos - 1) % 4
        down_pos = (my_pos + 1) % 4
        side = "upper" if main_pos == up_pos else "lower" if main_pos == down_pos else "other"

        shape = self._infer_enemy_five_shape(game_state, ec, main_pos)
        teammate_strong = self._is_teammate_strong(game_state, teammate_pos)
        teammate_can_cover = self._seat_may_hold_single_above(
            game_state, teammate_pos, get_action_rank(greater_action), cur_rank
        )
        enemy_has_bigger_than_my_single = self._seat_may_hold_single_above(
            game_state, main_pos, get_action_rank(best_single[1]), cur_rank
        )
        bombs = []
        for idx, act in enumerate(action_list):
            try:
                if is_bomb(act):
                    bombs.append((idx, act))
            except Exception:
                continue
        best_bomb = self._select_best_bomb(bombs, action_list) if bombs else None

        # 上家：若是整牌型，直接用我方最大合法单张压；
        # 若像 4+1，则只有在队友兜不住且敌方剩余单张不可能大过我方最大单时才单压。
        if side == "upper":
            if shape == "structured":
                return best_single
            if shape == "bomb_plus_single":
                if (not teammate_can_cover) and (not enemy_has_bigger_than_my_single):
                    return best_single
                if best_bomb is not None and teammate_strong:
                    return best_bomb
                return None
            if not teammate_strong:
                return best_single
            if best_bomb is not None:
                return best_bomb
            return None

        # 下家：整牌型直接单压；4+1 仅在剩余单张不可能大过我方最大单时单压。
        if side == "lower":
            if shape == "structured":
                return best_single
            if shape == "bomb_plus_single":
                if not enemy_has_bigger_than_my_single:
                    return best_single
                if best_bomb is not None:
                    return best_bomb
                return None
            if not teammate_strong:
                return best_single
            if best_bomb is not None:
                return best_bomb
            return None

        return None

    def _find_highest_single_beater(
        self, action_list: List, greater_action: List, cur_rank: str,
    ) -> Optional[Tuple[int, List]]:
        """返回能压当前 single 的最大合法单张。"""
        if not GUARD_TOOLS_OK:
            return None
        greater_cards = _get_cards(greater_action)
        if not greater_cards:
            return None
        greater_value = get_card_value(greater_cards[0], cur_rank)
        best: Optional[Tuple[int, List]] = None
        best_value = -1
        for idx, act in enumerate(action_list):
            if get_action_type(act) != ACTION_TYPE_SINGLE:
                continue
            cards = _get_cards(act)
            if not cards:
                continue
            value = get_card_value(cards[0], cur_rank)
            if value > greater_value and value > best_value:
                best = (idx, act)
                best_value = value
        return best

    def _filter_natural_single_feed_candidates(
        self,
        singles: List[Tuple[int, List]],
        hand_cards: List[str],
        cur_rank: str,
    ) -> List[Tuple[int, List]]:
        """天然单：手牌中该 rank 仅 1 张；排除大小王与逢人配级牌。"""
        if not singles or not hand_cards:
            return []
        cnt = Counter(get_card_rank(str(c)) for c in hand_cards)
        naturals: List[Tuple[int, List]] = []
        for idx, act in singles:
            cards = _get_cards(act)
            if len(cards) != 1:
                continue
            card = str(cards[0])
            rk = get_card_rank(card)
            if rk in ("SB", "HR"):
                continue
            if _is_wild_level_card(card, cur_rank):
                continue
            if cnt.get(rk, 0) != 1:
                continue
            naturals.append((idx, act))
        return naturals

    def _select_min_natural_single_feed(
        self,
        candidates: List[Tuple[int, List]],
        hand_cards: List[str],
        game_state: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """从候选中挑最小天然单（送队友；级牌留作回收）。"""
        if not GUARD_TOOLS_OK:
            return None
        singles = [
            (i, a) for i, a in candidates
            if get_action_type(a) == ACTION_TYPE_SINGLE
        ]
        cur_rank = str(game_state.get("curRank", "2"))
        naturals = self._filter_natural_single_feed_candidates(
            singles, hand_cards, cur_rank,
        )
        if not naturals:
            return None
        return min(
            naturals,
            key=lambda item: get_card_value(_get_cards(item[1])[0], cur_rank),
        )

    def _q1_teammate_one_natural_single_lead(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-271：领出 + 队友剩 1 → 天然单送队友（级牌留回收）。

        match=6a8d0d7f：上家 Q 被级牌 2 压后接风领出，原 GUA-202 出 D2（级牌）
        → GUA-244 出 KK → TWT 烂尾。定音：下家剩 2 张时最小天然单最优防守
        （下家每圈只能出 1 张）；级牌 2 留回收。下家也报单：仅散单时出倒数第二小；
        另有对子/三带等→不送单，交由其他领出逻辑。
        """
        if not GUARD_TOOLS_OK:
            return None

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if not self._is_my_q1_lead_turn(game_state, my_pos):
            return None

        teammate = ec.get("teammate", {})
        if int(teammate.get("remaining", 0) or 0) != 1:
            return None

        hand_cards = list(game_state.get("handCards", []) or [])
        cur_rank = str(game_state.get("curRank", "2"))
        singles = []
        for idx, act in candidates:
            try:
                if get_action_type(act) != ACTION_TYPE_SINGLE:
                    continue
            except Exception:
                continue
            if self._is_bomb_destroying_action(act, hand_cards, game_state):
                continue
            singles.append((idx, act))

        naturals = self._filter_natural_single_feed_candidates(
            singles, hand_cards, cur_rank,
        )
        if not naturals:
            return None

        numofplayers = ec.get("numofplayers") or game_state.get("numofplayers", [27] * 4)
        down_pos = (my_pos + 1) % 4
        down_rem = int(numofplayers[down_pos] if down_pos < len(numofplayers) else 99)

        if down_rem == 1:
            if _has_non_single_lead_candidates(candidates):
                return None
            picked = _pick_second_smallest_single(naturals, cur_rank)
            if picked is None:
                return None
        else:
            picked = min(
                naturals,
                key=lambda item: get_card_value(_get_cards(item[1])[0], cur_rank),
            )

        logger.info(
            "GUA-271: 队友剩1领出天然单 idx=%d card=%s down_rem=%d",
            picked[0], _get_cards(picked[1]), down_rem,
        )
        return picked

    def _q1_lead_feed_teammate_special(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-202：我方领出轮 + 队友 is_close → 优先按 assist_prefer 送牌。

        解决「敌方报单领出时 Q1 整牌锁敌抢跑，队友剩 2 张却不出对子」：
        残局管线 Q1 先于 Q2，Q1 内 `_q1_enemy_critical_lead_special` 整牌锁敌
        （ThreeWithTwo 优先）直接 return，Q2 送牌永远到不了。本特判插在
        `_q1_enemy_critical_lead_special` 之前，领出轮且队友 close 时优先喂牌。

        安全约束（全部满足才送，否则回退整牌锁敌）：
          1. 本回合是自由领出（_is_my_q1_lead_turn）
          2. 队友 is_close（1-5 张）
          3. 送牌候选不拆炸弹核心结构（_is_bomb_destroying_action）
          4. 不送 Bomb/SF/JokerBomb（炸是回手/锁敌资源）
          5. 队友报单(1张)时仅送安全单（_select_enemy_one_safe_single，防敌方截胡）
        """
        if not GUARD_TOOLS_OK:
            return None

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if not self._is_my_q1_lead_turn(game_state, my_pos):
            return None

        teammate = ec.get("teammate", {})
        if not teammate.get("is_close"):
            return None

        assist_prefer = teammate.get("assist_prefer", [])
        if not assist_prefer:
            return None

        # GUA-202 护栏①：V8 自己有 2 手冲刺线 → 自己冲刺优先，不送牌。
        # 队友剩 1 张时送天然单拿头游优先于两手冲刺规划（GUA-271）。
        teammate_rem_guard = int(teammate.get("remaining", 0) or 0)
        if teammate_rem_guard != 1:
            structured_all = [
                (i, a) for i, a in candidates
                if _get_declared_action_type(a) not in (ACTION_TYPE_PASS, "PASS")
                and not _is_bomb_like_action(a)
            ]
            if self._select_two_turn_sprint_structure(
                structured_all, candidates, game_state, ec,
                prefer_structure_first=True,
            ) is not None:
                return None

        hand_cards = list(game_state.get("handCards", []) or [])
        feed_candidates: List[Tuple[int, List]] = []
        for idx, act in candidates:
            try:
                atype = get_action_type(act)
            except Exception:
                continue
            if atype == ACTION_TYPE_PASS:
                continue
            if atype not in assist_prefer:
                continue
            if atype in ("Bomb", "StraightFlush", "JokerBomb"):
                continue
            if self._is_bomb_destroying_action(act, hand_cards, game_state):
                continue
            # 不拆 core 整牌结构（TTT/TWT/Trips 等，见 GUA-202 细案 §2.2）
            if _breaks_core_subgroup(
                act,
                game_state.get("_group_members") or {},
                game_state.get("_group_gid_type_map") or {},
            ):
                continue
            feed_candidates.append((idx, act))

        if not feed_candidates:
            return None

        # GUA-202 护栏②：送牌通道同样要过风险剪枝（GUA-111）。
        # 若送牌类型（如 Pair）该通道最终更可能被敌方持有，则送牌会被截胡，
        # 不成立 → 回退整牌锁敌/推荐路径。
        main_pos2, main_enemy2 = self._select_main_enemy(ec.get("enemies", {}), my_pos)
        pruned_feed = self._prune_q1_risky_same_type_lane_candidates(
            game_state, feed_candidates, ec, main_pos2, main_enemy2,
        )
        if pruned_feed:
            feed_candidates = pruned_feed
        if not feed_candidates:
            return None

        # 队友报单(1张)：优先天然单（级牌留回收）；无天然单再走安全单
        remaining = int(teammate.get("remaining", 0) or 0)
        if remaining == 1:
            numofplayers = ec.get("numofplayers") or game_state.get("numofplayers", [27] * 4)
            down_pos = (my_pos + 1) % 4
            down_rem = int(numofplayers[down_pos] if down_pos < len(numofplayers) else 99)
            if down_rem == 1 and _has_non_single_lead_candidates(candidates):
                return None
            natural_feed = self._select_min_natural_single_feed(
                feed_candidates, hand_cards, game_state,
            )
            if natural_feed is not None:
                logger.info(
                    "Q1 领出送队友(GUA-202/271): idx=%d type=%s",
                    natural_feed[0], get_action_type(natural_feed[1]),
                )
                return natural_feed
            safe = self._select_enemy_one_safe_single(feed_candidates, game_state, ec)
            if safe is None:
                return None
            logger.info("Q1 领出送队友(GUA-202): idx=%d type=%s",
                        safe[0], get_action_type(safe[1]))
            return safe

        # 送牌排序：牌力小优先（队友更好接）→ 回收优先（留回手）
        # 与 GUA-189 送小单让队友接的意图一致，不沿用 _sort_by_recapture_first
        # （其牌力大优先会让队友接不住）。
        cur_rank = str(game_state.get("curRank", "2"))
        ordered = sorted(
            feed_candidates,
            key=lambda item: (_max_card_value(item[1], cur_rank), not _has_recapture(item[1], hand_cards, cur_rank)),
        )
        logger.info("Q1 领出送队友(GUA-202): idx=%d type=%s",
                    ordered[0][0], get_action_type(ordered[0][1]))
        return ordered[0]

    def _q1_feed_teammate_twt_when_downseat_two(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-220 Tier 1：下家剩 2 张 + 队友剩 5 张且前序打过 TWT → 优先不组炸弹送队友 TWT。

        下家剩 2 张时盲出对子可能被下家对子直接压赢（头游）。若队友剩 5 张且本局前序
        出过 ThreeWithTwo（MemoryTracker.play_history 证据，队友可能正是 5 张 TWT 一手牌），
        优先放弃隐式配子炸（如 3K+H2），改送 TWT——下家 2 张压不了 TWT，队友可一手走完。
        因此本特判**豁免** `_is_bomb_destroying_action` 过滤（这正是「不组炸弹」之意）。
        """
        if not GUARD_TOOLS_OK:
            return None

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if not self._is_my_q1_lead_turn(game_state, my_pos):
            return None
        down_pos = (my_pos + 1) % 4
        down = (ec.get("enemies") or {}).get(down_pos)
        if down is None or int(down.get("remaining", 0) or 0) != 2:
            return None

        teammate = ec.get("teammate", {})
        if not teammate.get("is_close") or int(teammate.get("remaining", 0) or 0) != 5:
            return None

        # 队友前序打过 TWT（MemoryTracker.play_history 证据）
        tracker = game_state.get("_memory_tracker")
        mate_pos = (my_pos + 2) % 4
        played_twt = False
        if tracker is not None:
            for entry in getattr(tracker, "play_history", []) or []:
                if entry.get("seat") != mate_pos:
                    continue
                atype = str(entry.get("action_type", "") or "").upper()
                if "THREEWITHTWO" in atype or "THREE_WITH_TWO" in atype:
                    played_twt = True
                    break
        if not played_twt:
            return None

        hand_cards = list(game_state.get("handCards", []) or [])
        cur_rank = str(game_state.get("curRank", "2"))
        twt_candidates: List[Tuple[int, List]] = []
        for idx, act in candidates:
            try:
                atype = get_action_type(act)
            except Exception:
                continue
            if atype != ACTION_TYPE_THREE_WITH_TWO:
                continue
            if _is_bomb_like_action(act):
                continue
            twt_candidates.append((idx, act))
        if not twt_candidates:
            return None

        ordered = sorted(
            twt_candidates,
            key=lambda item: (_max_card_value(item[1], cur_rank), not _has_recapture(item[1], hand_cards, cur_rank)),
        )
        logger.info("Q1 下家2张送队友TWT(GUA-220): idx=%d type=%s",
                    ordered[0][0], get_action_type(ordered[0][1]))
        return ordered[0]

    def _q1_downseat_two_single_first(
        self,
        singles: List[Tuple[int, List]],
        game_state: Dict[str, Any],
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-220 Tier 2：下家剩 2 张时优先出单（单先于对），逼下家拆对。

        下家剩 2 张且我方领出：若直接出对子，下家一旦持更大对（如 QQ）即可压赢头游。
        改先出**能逼下家拆对的最小单张**——下家拆对后只剩 1 张，我方后续继续领出时
        再出对子，下家单张无法应对。安全约束：
          1. 不拆我方炸弹（_is_bomb_destroying_action，含 GUA-219 隐式配子炸）
          2. 出该单后我方仍持有更大的非炸单张可回收（保证能继续领出，不把牌权白送）
        """
        if not singles:
            return None
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if not self._is_my_q1_lead_turn(game_state, my_pos):
            return None
        down_pos = (my_pos + 1) % 4
        down = (ec.get("enemies") or {}).get(down_pos)
        if down is None or int(down.get("remaining", 0) or 0) != 2:
            return None

        hand_cards = list(game_state.get("handCards", []) or [])
        cur_rank = str(game_state.get("curRank", "2"))
        feasible = []
        for idx, act in singles:
            if self._is_bomb_destroying_action(act, hand_cards, game_state):
                continue
            cards = _get_cards(act)
            if not cards:
                continue
            lead_value = get_card_value(cards[0], cur_rank)
            if not self._hand_has_recapture_single(
                hand_cards, cards, lead_value, cur_rank, game_state,
            ):
                continue
            feasible.append((lead_value, idx, act))
        if not feasible:
            return None

        feasible.sort(key=lambda item: item[0])
        logger.info("Q1 下家2张优先出单(GUA-220): idx=%d type=%s",
                    feasible[0][1], get_action_type(feasible[0][2]))
        return (feasible[0][1], feasible[0][2])

    def _hand_has_recapture_single(
        self,
        hand_cards: List[str],
        played_cards: List[str],
        lead_value: int,
        cur_rank: str,
        game_state: Dict[str, Any],
    ) -> bool:
        """出 lead 单后，剩余手牌仍持有更大的非炸单张可回收（保证继续领出）。"""
        remaining = list((Counter(hand_cards) - Counter(played_cards)).elements())
        for card in remaining:
            if get_card_value(card, cur_rank) <= lead_value:
                continue
            rec_act = ["Single", "", [card]]
            if self._is_bomb_destroying_action(rec_act, hand_cards, game_state):
                continue
            return True
        return False

    def _q1_teammate_single_cover_special(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """队友领单且关键敌方在后手时，只有安全单才允许反超队友；否则 PASS。"""
        if not GUARD_TOOLS_OK:
            return None
        if main_enemy.get("remaining") not in (1, 2):
            return None

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        teammate_pos = (my_pos + 2) % 4
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction")
        if greater_pos != teammate_pos or not greater_action:
            return None
        if get_action_type(greater_action) != ACTION_TYPE_SINGLE:
            return None

        singles = []
        pass_candidate: Optional[Tuple[int, List]] = None
        has_bomb_like = False
        for idx, act in candidates:
            try:
                atype = get_action_type(act)
            except Exception:
                continue
            if atype == ACTION_TYPE_PASS and pass_candidate is None:
                pass_candidate = (idx, act)
                continue
            if atype == ACTION_TYPE_SINGLE:
                singles.append((idx, act))
                continue
            if _is_bomb_like_action(act):
                has_bomb_like = True

        if not singles:
            return None

        safe_single = self._select_enemy_one_safe_single(singles, game_state, ec)
        if safe_single is not None:
            return safe_single

        if pass_candidate is not None and not has_bomb_like:
            return pass_candidate
        return None

    def _q1_enemy_critical_lead_special(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """敌方剩 1/2 张且我方领牌时：先整牌锁敌，再看安全单。"""
        if not GUARD_TOOLS_OK:
            return None
        remaining = int(main_enemy.get("remaining", 27) or 27)
        if remaining not in (1, 2):
            return None

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if not self._is_my_q1_lead_turn(game_state, my_pos):
            return None

        structured = []
        singles = []
        for idx, act in candidates:
            try:
                atype = get_action_type(act)
            except Exception:
                continue
            if atype == ACTION_TYPE_PASS:
                continue
            if atype == ACTION_TYPE_SINGLE:
                singles.append((idx, act))
            else:
                structured.append((idx, act))

        if structured:
            sprint_structure = self._select_two_turn_sprint_structure(
                structured, candidates, game_state, ec,
            )
            if sprint_structure is not None:
                return sprint_structure
            # 筛选出非炸弹自身且不拆弹的安全结构候选
            hand_cards = list(game_state.get("handCards", []) or [])
            safe_structured = [
                (i, a) for i, a in structured
                if not self._is_bomb_destroying_action(a, hand_cards, game_state)
                and get_action_type(a) not in ("Bomb", "StraightFlush", "JokerBomb")
            ]
            if safe_structured:
                best_lock = self._select_enemy_one_locking_structure(safe_structured, game_state)
                if best_lock is not None:
                    # GUA-220：下家剩 2 张时，若整牌锁首选是对子（2 张，下家 2 张可压），
                    # 改单先于对（逼下家拆对；出后继续领出再出对锁死）；
                    # 顺子/TWT/Trips 等 3+ 张下家 2 张压不了，仍直接锁死（GUA-078 语义）。
                    if get_action_type(best_lock[1]) == ACTION_TYPE_PAIR:
                        downseat_single = self._q1_downseat_two_single_first(
                            singles, game_state, ec,
                        )
                        if downseat_single is not None:
                            return downseat_single
                    return best_lock

        safe_single = self._select_enemy_one_safe_single(singles, game_state, ec)
        if safe_single is not None:
            return safe_single

        if remaining == 1:
            return self._select_enemy_one_strongest_single(singles, game_state)
        return None

    def _q1_enemy_one_bomb_lock_special(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-190：敌方剩 1 张 + 跟牌压单时，若我方手牌结构为
        「≥2 手炸 + 恰好 1 个孤立大单(>K) + 其余恰好 2 手整牌」→ 直接炸弹封死。

        判据用我方手牌结构替代"敌方残余牌判断"（下家是否大王不可靠）：
        开炸 → 领出整牌 → 若被压再炸 → 领出另一整牌 → 留大单头游。
        """
        if not GUARD_TOOLS_OK:
            return None
        if int(main_enemy.get("remaining", 27) or 27) != 1:
            return None
        # 跟牌压单：greater 为 Single 且我方非领出（greaterAction 存在即跟牌回合）
        greater_action = game_state.get("greaterAction")
        if not greater_action:
            return None
        try:
            gtype = get_action_type(greater_action)
        except Exception:
            return None
        if gtype != ACTION_TYPE_SINGLE:
            return None
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))

        hand_cards = list(game_state.get("handCards", []) or [])
        if not hand_cards:
            return None
        cur_rank = str(game_state.get("curRank", "2"))

        from collections import Counter
        cnt: Counter = Counter()
        for c in hand_cards:
            try:
                cnt[get_card_rank(str(c))] += 1
            except Exception:
                return None

        # ① 孤立单张恰好 1 个，且 > K
        single_ranks = [r for r, n in cnt.items() if n == 1]
        if len(single_ranks) != 1:
            return None
        solo_rank = single_ranks[0]
        k_value = get_card_value("SK", cur_rank)
        solo_value = get_card_value(
            next((c for c in hand_cards if get_card_rank(str(c)) == solo_rank), "SB"),
            cur_rank,
        )
        if solo_value <= k_value:
            return None

        # ② ≥2 手炸
        bomb_ranks = [r for r, n in cnt.items() if n >= 4]
        if len(bomb_ranks) < 2:
            return None

        # ③ 其余（count 2/3）恰好 2 手整牌
        rest_ranks = [r for r, n in cnt.items() if 2 <= n <= 3]
        if not self._rest_forms_two_hands(rest_ranks, cnt):
            return None

        # 从候选里选炸弹（最小足够封死当前 Single）
        bomb_cands = [
            (i, a) for i, a in candidates if _is_bomb_like_action(a)
        ]
        if not bomb_cands:
            return None
        bomb_cands = _sort_q1_block_candidates(bomb_cands, hand_cards, game_state)
        picked = bomb_cands[0]
        logger.info(
            "GUA-190 enemy-one bomb lock: idx=%s type=%s",
            picked[0],
            _get_declared_action_type(picked[1]) if GUARD_TOOLS_OK else "?",
        )
        return picked

    def _q1_multi_hand_lead_single_first(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-239：自由领出 + 本方多手（≥4 手且含对子 ≥2）+ 下家剩 6 张
        + 有天然单可拆 → 出最小天然单试探，而非匹配 recommended 甩整牌。

        实测 match 6a7dd97c 22:49:44：V8=player2 手 SF(H7,H2,H2,HT,HJ)+HR+4 对，
        下家 P3 剩 6 张，Q1 把 SF（GUA-232 降级成 Straight）当 5 张整牌打出，
        被 P1 Straight/8 压死失权，后续拆对单走、对子烂手。正确应先出最小单张
        （H7/7）试探，大王 HR 回手，再用对子（≥2 对可回手）克下家 5 张。
        返回 (idx, action)；调用方须据此设 `_gua239_single_probe` 标记豁免拆核心拦截。
        """
        if not GUARD_TOOLS_OK:
            return None

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if not self._is_my_q1_lead_turn(game_state, my_pos):
            return None

        # 下家（(my_pos+1)%4）必须是敌方且恰剩 6 张（对子克 5 张的起点）
        enemies = ec.get("enemies", {}) or {}
        down_pos = (my_pos + 1) % 4
        down_enemy = enemies.get(down_pos)
        if not isinstance(down_enemy, dict):
            return None
        if int(down_enemy.get("remaining", 0) or 0) != 6:
            return None

        hand_cards = list(game_state.get("handCards", []) or [])
        if not hand_cards:
            return None

        # 本方多手：≥4 手且含对子 ≥2（组牌引擎 _group_members 多集真源）
        hands, pair_groups = self._count_hand_structure(hand_cards, game_state)
        if hands < 4 or pair_groups < 2:
            return None

        # 找最小天然单（rank 在手牌中仅 1 张；大小王排除留作回手；
        # 逢人配 H{curRank} 排除——它是炸弹/整牌配子，裸出等于拆结构
        # 浪费万能牌，应保留配炸/配 TWT）
        cur_rank = str(game_state.get("curRank", "2"))
        cnt = Counter(get_card_rank(c) for c in hand_cards)
        natural_singles: List[Tuple[int, List]] = []
        for i, a in candidates:
            try:
                if get_action_type(a) != ACTION_TYPE_SINGLE:
                    continue
            except Exception:
                continue
            cards = _get_cards(a)
            if len(cards) != 1:
                continue
            card = cards[0]
            rk = get_card_rank(card)
            if rk in ("SB", "HR"):
                continue
            if _is_wild_level_card(str(card), cur_rank):
                continue
            if cnt.get(rk, 0) != 1:
                continue
            natural_singles.append((i, a))
        if not natural_singles:
            return None

        picked = min(
            natural_singles,
            key=lambda item: get_card_value(_get_cards(item[1])[0], cur_rank),
        )
        logger.info(
            "GUA-239 multi_hand lead single_first: idx=%d type=%s",
            picked[0], ACTION_TYPE_SINGLE,
        )
        return picked

    def _q1_only_single_pair_lead_probe(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-249：自由领出 + 下家敌方剩 6/7 张 + 本方仅单/对（候选只含 Single/Pair/PASS）
        + 对子 ≥1 → 先探后克：有天然单出最小天然单试探（保留对子回手）；
        无天然单（全对）直接出最小对子（对子克 5 张起点）。

        背景（用户 2026-08-19 定音，本地 demo 实测）：敌剩 6/7 张时 endgame_rule
        推荐全是整牌型（6 → [ThreePair,TwoTrips,Straight,Trips]；7 →
        [Straight,TwoTrips,ThreePair]），本方仅单/对时 ④ recommended 过滤空 →
        ⑤ baoshu 无 → ⑥ 任意 non_banned 回收优先兜底。实测敌7 领出全对四手
        （33 44 88 99）拆对 Single/8（留 8 回收）——拆散对子结构、非对子克 5 张
        起点。正确：有天然单先出最小天然单（先探后克，保留对子回手）；全对直接
        出最小对子（对子克 5 张）。插 GUA-239 之后、_filter_q1_core_break_candidates
        之前（全对场景不会拆核心，无拆核心拦截豁免需求）。
        """
        if not GUARD_TOOLS_OK:
            return None

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if not self._is_my_q1_lead_turn(game_state, my_pos):
            return None

        # 下家（(my_pos+1)%4）敌方剩 6 或 7 张（对子克 5 张的窗口）
        enemies = ec.get("enemies", {}) or {}
        down_pos = (my_pos + 1) % 4
        down_enemy = enemies.get(down_pos)
        if not isinstance(down_enemy, dict):
            return None
        if int(down_enemy.get("remaining", 0) or 0) not in (6, 7):
            return None

        # 本方候选仅 Single/Pair/PASS（无炸/无整牌结构）
        non_pass_types = set()
        pair_items: List[Tuple[int, List]] = []
        single_items: List[Tuple[int, List]] = []
        for i, a in candidates:
            try:
                atype = _get_declared_action_type(a)
            except Exception:
                return None
            if atype in (ACTION_TYPE_PASS, "PASS"):
                continue
            if atype not in (ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR):
                return None
            non_pass_types.add(atype)
            if atype == ACTION_TYPE_PAIR:
                pair_items.append((i, a))
            else:
                single_items.append((i, a))
        if not pair_items:
            return None

        hand_cards = list(game_state.get("handCards", []) or [])
        cur_rank = str(game_state.get("curRank", "2"))

        # 有天然单（rank 在手牌仅 1 张；大小王排除，留作回手）→ 先探后克
        cnt = Counter(get_card_rank(c) for c in hand_cards)
        natural_singles: List[Tuple[int, List]] = []
        for i, a in single_items:
            cards = _get_cards(a)
            if len(cards) != 1:
                continue
            card = cards[0]
            rk = get_card_rank(card)
            if rk in ("SB", "HR"):
                continue
            if cnt.get(rk, 0) != 1:
                continue
            natural_singles.append((i, a))
        if natural_singles:
            picked = min(
                natural_singles,
                key=lambda item: get_card_value(_get_cards(item[1])[0], cur_rank),
            )
            logger.info(
                "GUA-249 only_single_pair lead probe: idx=%d type=%s",
                picked[0], ACTION_TYPE_SINGLE,
            )
            return picked

        # 无天然单（全对）→ 直接出最小对子（对子克 5 张起点）
        picked = min(
            pair_items,
            key=lambda item: _max_card_value(item[1], cur_rank),
        )
        logger.info(
            "GUA-249 only_single_pair lead probe: idx=%d type=%s",
            picked[0], ACTION_TYPE_PAIR,
        )
        return picked

    def _q1_no_bomb_twt_pairs_lead(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-265：无炸领出 + TWT/三张 + 多对 + 下家剩 6/7。

        用户定音（match ``6a884eac``，手牌 88+TT+KKK+22）：
          ① 记牌能判断三张/TWT 最大 → 先出 TWT，剩 4 张让对手误以为炸弹；
          ② 不确定是否最大 → 打第二小对子，级牌对回收；
          ③ 打最大单仅当自己还有炸弹——本手无炸不得机械拆级牌出最大单。

        插在 GUA-249 之后：249 只覆盖「仅单/对」；本手有 TWT 时 249 不触发，
        endgame_rule[7] 推荐 Straight/钢板对不上 → ⑥ 回收排序拆级牌出 Single/2。
        """
        if not GUARD_TOOLS_OK:
            return None

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if not self._is_my_q1_lead_turn(game_state, my_pos):
            return None
        if self._self_has_bomb_family(game_state, candidates, ec):
            return None

        enemies = ec.get("enemies", {}) or {}
        down_pos = (my_pos + 1) % 4
        down_enemy = enemies.get(down_pos)
        if not isinstance(down_enemy, dict):
            return None
        if int(down_enemy.get("remaining", 0) or 0) not in (6, 7):
            return None

        twt_items: List[Tuple[int, List]] = []
        trips_items: List[Tuple[int, List]] = []
        pair_items: List[Tuple[int, List]] = []
        for i, a in candidates:
            try:
                atype = get_action_type(a)
            except Exception:
                continue
            if atype == ACTION_TYPE_THREE_WITH_TWO:
                twt_items.append((i, a))
            elif atype == ACTION_TYPE_TRIPS:
                trips_items.append((i, a))
            elif atype == ACTION_TYPE_PAIR:
                pair_items.append((i, a))
        if not twt_items and not trips_items:
            return None

        hand_cards = list(game_state.get("handCards", []) or [])
        cur_rank = str(game_state.get("curRank", "2"))
        cnt = Counter(get_card_rank(c) for c in hand_cards)
        complete_pairs = []
        for i, a in pair_items:
            cards = _get_cards(a)
            if len(cards) != 2:
                continue
            rk = get_card_rank(cards[0])
            if cnt.get(rk, 0) != 2:
                continue
            complete_pairs.append((i, a, rk, get_card_value(cards[0], cur_rank)))
        if len(complete_pairs) < 2:
            return None

        trip_rank = self._core_trip_rank_for_gua265(game_state, trips_items, twt_items)
        if not trip_rank:
            return None

        if self._twt_or_trips_likely_max(game_state, trip_rank, cur_rank):
            picked = self._pick_twt_or_trips_for_gua265(
                twt_items, trips_items, trip_rank, cur_rank,
            )
            if picked is not None:
                logger.info(
                    "GUA-265 twt_max lead: idx=%d type=%s rank=%s",
                    picked[0], get_action_type(picked[1]), trip_rank,
                )
                return picked

        complete_pairs.sort(key=lambda x: x[3])
        # 第二小对子；若正好是级牌对则改取最小非级牌对（级牌对回收）
        chosen = complete_pairs[1]
        if chosen[2] == cur_rank:
            non_level = [p for p in complete_pairs if p[2] != cur_rank]
            if not non_level:
                return None
            chosen = non_level[0] if len(non_level) == 1 else non_level[min(1, len(non_level) - 1)]
        logger.info(
            "GUA-265 second_pair lead: idx=%d type=Pair rank=%s",
            chosen[0], chosen[2],
        )
        return (chosen[0], chosen[1])

    @staticmethod
    def _self_has_bomb_family(
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
    ) -> bool:
        if (ec.get("self") or {}).get("has_bomb"):
            return True
        for gtype in (game_state.get("_group_gid_type_map") or {}).values():
            gt = str(gtype).lower()
            if gt in ("bomb", "straightflush", "jokerbomb") or "bomb" in gt:
                return True
        for _, a in candidates:
            try:
                atype = get_action_type(a)
            except Exception:
                continue
            if atype in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH, "JokerBomb"):
                return True
        return False

    @staticmethod
    def _core_trip_rank_for_gua265(
        game_state: Dict[str, Any],
        trips_items: List[Tuple[int, List]],
        twt_items: List[Tuple[int, List]],
    ) -> Optional[str]:
        cur_rank = str(game_state.get("curRank", "2"))
        members = game_state.get("_group_members") or {}
        types = game_state.get("_group_gid_type_map") or {}
        ranks: List[str] = []
        for gid, mems in members.items():
            gt = str(types.get(gid, "")).lower()
            if "trip" in gt and mems:
                ranks.append(get_card_rank(mems[0]))
        if not ranks:
            for _, a in list(trips_items) + list(twt_items):
                rk = str(a[1]) if len(a) > 1 else ""
                if rk and rk not in ("PASS", "Free"):
                    ranks.append(rk)
        if not ranks:
            return None
        return max(ranks, key=lambda r: get_card_value(f"S{r}", cur_rank))

    @staticmethod
    def _tracker_outside_rank(tracker: Any, rank: str) -> int:
        if tracker is None:
            return 99
        played = getattr(tracker, "PLAYED", 4)
        mine = getattr(tracker, "MY_HAND", 1)
        if rank in ("SB", "HR"):
            copies = (tracker.card_state or {}).get(rank, [-1, -1])
            return sum(1 for c in copies if c not in (played, mine))
        n = 0
        for suit in ("S", "H", "D", "C"):
            copies = (tracker.card_state or {}).get(f"{suit}{rank}", [-1, -1])
            n += sum(1 for c in copies if c not in (played, mine))
        return n

    def _twt_or_trips_likely_max(
        self,
        game_state: Dict[str, Any],
        trip_rank: str,
        cur_rank: str,
    ) -> bool:
        """外面没有任何更高点能凑出三张（≥3 张未知）→ 本手 TWT/三张可视为最大。"""
        tracker = game_state.get("_memory_tracker")
        if tracker is None:
            return False
        trip_val = get_card_value(f"S{trip_rank}", cur_rank)
        for rk in CARD_RANK_ORDER:
            if get_card_value(f"S{rk}", cur_rank) <= trip_val:
                continue
            if self._tracker_outside_rank(tracker, rk) >= 3:
                return False
        return True

    @staticmethod
    def _pick_twt_or_trips_for_gua265(
        twt_items: List[Tuple[int, List]],
        trips_items: List[Tuple[int, List]],
        trip_rank: str,
        cur_rank: str,
    ) -> Optional[Tuple[int, List]]:
        matched_twt = []
        for i, a in twt_items:
            if str(a[1]) != trip_rank:
                continue
            cards = _get_cards(a)
            kickers = [c for c in cards if get_card_rank(c) != trip_rank]
            kicker_val = get_card_value(kickers[0], cur_rank) if kickers else 99
            matched_twt.append((kicker_val, i, a))
        if matched_twt:
            matched_twt.sort(key=lambda x: x[0])
            _, i, a = matched_twt[0]
            return (i, a)
        for i, a in trips_items:
            if str(a[1]) == trip_rank:
                return (i, a)
        return None

    _STRUCTURED_ZONE_REMAINING = frozenset({6, 7, 8})
    _STRUCTURE_LOCK_TYPES = frozenset({
        ACTION_TYPE_STRAIGHT,
        ACTION_TYPE_THREE_WITH_TWO,
        ACTION_TYPE_TWO_TRIPS,
        ACTION_TYPE_THREE_PAIR,
    })

    def _q1_structured_zone_lookahead(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-266：6/7/8 张结构区不机械打最大单。

        用户定音（match ``6a890699`` / ``6a890546``）：下家剩 7 张时要先判断
        对手可能牌型（顺/钢板/连对），以及拦截后自己后续还能不能拦住。
        机械出大王/级牌单拦小单，拦完没有回手 = 白送控牌。

        - 领出：有 Straight/TWT/钢板/连对 → 出整牌，不出级牌/王/A 单。
        - 跟压 Single：有非贵散单 → 最小够压；只剩贵单且打出后无干净回手 → PASS。
        报单剩 1 / 敌剩 ≤5 不介入（GUA-222 / GUA-252 / GUA-245）。
        """
        if not GUARD_TOOLS_OK:
            return None
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        down_pos = (my_pos + 1) % 4
        enemies = ec.get("enemies", {}) or {}
        down_rem = int((enemies.get(down_pos) or {}).get("remaining", 0) or 0)
        main_rem = int((main_enemy or {}).get("remaining", 0) or 0)
        in_zone = (
            down_rem in self._STRUCTURED_ZONE_REMAINING
            or main_rem in self._STRUCTURED_ZONE_REMAINING
        )
        if not in_zone:
            return None
        if main_rem == 1 or down_rem == 1:
            return None

        if self._is_my_q1_lead_turn(game_state, my_pos):
            if down_rem and down_rem <= 5:
                return None
            return self._q1_lead_structure_not_precious_single(candidates, game_state)

        greater = game_state.get("greaterAction")
        try:
            if not greater or get_action_type(greater) != ACTION_TYPE_SINGLE:
                return None
        except Exception:
            return None
        greater_pos = game_state.get("greaterPos")
        try:
            g_rem = int((enemies.get(int(greater_pos)) or {}).get("remaining", 0) or 0)
        except (TypeError, ValueError):
            g_rem = 0
        if g_rem and g_rem <= 5:
            return None
        return self._q1_follow_no_dump_precious_single(
            game_state, candidates, greater,
        )

    def _q1_lead_structure_not_precious_single(
        self,
        candidates: List[Tuple[int, List]],
        game_state: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """领出：有整牌锁则出整牌，禁止级牌/王/A 单。"""
        structures: List[Tuple[int, List, int]] = []
        for i, a in candidates:
            try:
                atype = get_action_type(a)
            except Exception:
                continue
            if atype in self._STRUCTURE_LOCK_TYPES:
                if self._action_breaks_core_structure(a, game_state):
                    continue
                structures.append((i, a, _q1_structure_priority(atype)))
        if not structures:
            return None
        structures.sort(key=lambda x: (x[2], -len(_get_cards(x[1]))))
        picked = (structures[0][0], structures[0][1])
        logger.info(
            "GUA-266 lead structure lock: idx=%d type=%s",
            picked[0], get_action_type(picked[1]),
        )
        return picked

    def _q1_follow_no_dump_precious_single(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        greater: List,
    ) -> Optional[Tuple[int, List]]:
        """跟压单：非贵散单最小够压；只剩贵单且无干净回手 → PASS。"""
        cur_rank = str(game_state.get("curRank", "2"))
        hand_cards = list(game_state.get("handCards", []) or [])
        cnt = Counter(get_card_rank(c) for c in hand_cards)
        g_cards = _get_cards(greater)
        if not g_cards:
            return None
        g_val = get_card_value(g_cards[0], cur_rank)
        beaters: List[Tuple[int, List, int, bool]] = []
        pass_item = None
        for i, a in candidates:
            try:
                atype = get_action_type(a)
            except Exception:
                continue
            if atype in (ACTION_TYPE_PASS, "PASS"):
                pass_item = (i, a)
                continue
            if atype != ACTION_TYPE_SINGLE:
                continue
            cards = _get_cards(a)
            if len(cards) != 1:
                continue
            val = get_card_value(cards[0], cur_rank)
            if val <= g_val:
                continue
            # 只认天然散单（该点在手仅 1 张）；拆对/拆三头不算「便宜拦截」
            rk = get_card_rank(cards[0])
            if cnt.get(rk, 0) != 1:
                continue
            precious = self._is_precious_single_card(cards[0], cur_rank)
            beaters.append((i, a, val, precious))
        if not beaters:
            return None

        cheap = [b for b in beaters if not b[3]]
        if cheap:
            picked = min(cheap, key=lambda x: x[2])
            logger.info(
                "GUA-266 follow min non-precious: idx=%d card=%s",
                picked[0], _get_cards(picked[1])[0],
            )
            return (picked[0], picked[1])

        # 只剩贵单：打出后若还有不拆核心的贵单/炸可回手，则交给后续最大单路径
        if self._has_clean_followup_stopper(game_state, candidates, beaters[0][1]):
            return None
        # GUA-290: 打出贵单后剩余为「一手封顶冲刺」（对级牌/对A/王等一墩且
        # 全高牌，可直推跑完）→ 该出贵单抢回领出权冲刺，不应 PASS。
        # 锚点 match=6a942e2d1b27100f38da1595 21:21:03：手 SB+对2，上家敌出 Single/Q，
        # 原 GUA-266 判 dump-precious-no-stopper → PASS 放走敌冲刺（scores=[0,3,0,3]）。
        if self._precious_single_leaves_sprint_hand(game_state, beaters[0][1]):
            logger.info(
                "GUA-290 follow sprint-hand precious: idx=%d card=%s",
                beaters[0][0], _get_cards(beaters[0][1])[0],
            )
            return (beaters[0][0], beaters[0][1])
        if pass_item is None:
            return None
        logger.info("GUA-266 follow dump-precious-no-stopper → PASS")
        return pass_item

    @staticmethod
    def _is_precious_single_card(card: str, cur_rank: str) -> bool:
        rk = get_card_rank(card)
        if rk in ("SB", "HR"):
            return True
        if rk == str(cur_rank):
            return True
        if rk == "A":
            return True
        return get_card_value(card, cur_rank) >= 14

    def _has_clean_followup_stopper(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        played: List,
    ) -> bool:
        """打出 played 后，是否还剩不拆核心的炸弹或天然贵散单可再拦。"""
        played_list = _get_cards(played)
        left = list(game_state.get("handCards") or [])
        for c in played_list:
            try:
                left.remove(c)
            except ValueError:
                pass
        cnt_left = Counter(get_card_rank(c) for c in left)
        cur_rank = str(game_state.get("curRank", "2"))
        played_set = set(played_list)
        for _, a in candidates:
            try:
                atype = get_action_type(a)
            except Exception:
                continue
            cards = _get_cards(a)
            if not cards or any(c in played_set for c in cards):
                continue
            if atype in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH, "JokerBomb"):
                return True
            if atype != ACTION_TYPE_SINGLE or len(cards) != 1:
                continue
            rk = get_card_rank(cards[0])
            if cnt_left.get(rk, 0) != 1:
                continue
            if not self._is_precious_single_card(cards[0], cur_rank):
                continue
            return True
        return False

    def _precious_single_leaves_sprint_hand(
        self,
        game_state: Dict[str, Any],
        played: List,
    ) -> bool:
        """GUA-290：打出贵单后，剩余是否为一手封顶冲刺（同 rank 墩且高牌）。

        口子：GUA-266 原判「贵单无干净回手 → PASS」只从防线视角看「能否再拦」，
        没看进攻视角——打出小王后剩余对级牌/对A 是一手直推、拿回领出权即冲刺，
        根本不需要回手。此处判定剩余均为同一高 rank（级牌/王/A），即为一手封顶。
        """
        played_list = _get_cards(played)
        left = list(game_state.get("handCards") or [])
        for c in played_list:
            try:
                left.remove(c)
            except ValueError:
                pass
        if not left:
            return False
        cur_rank = str(game_state.get("curRank", "2"))
        ranks = {get_card_rank(c) for c in left}
        if len(ranks) != 1:
            return False
        rk = next(iter(ranks))
        if rk in ("SB", "HR"):
            return True
        if rk == str(cur_rank):
            return True
        if rk == "A":
            return True
        return False

    @staticmethod
    def _count_hand_structure(
        hand_cards: List[str], game_state: Dict[str, Any],
    ) -> Tuple[int, int]:
        """统计手数（一手=一个可出组合）与对子组数，返回 (hands, pair_groups)。

        优先用组牌引擎 `_group_members` + `_group_gid_type_map`（多集真源，
        gid=-1 为散单每张一手）；缺失时退化为按 rank 计数粗估。
        """
        group_members = game_state.get("_group_members") or {}
        group_types = game_state.get("_group_gid_type_map") or {}
        if group_members:
            hands = 0
            pair_groups = 0
            for gid, members in group_members.items():
                if gid == -1:
                    hands += len(members)  # 散单每张一手
                else:
                    hands += 1
                    gtype = group_types.get(gid)
                    if gtype in ("pair", "pair_in_three_pair", "pair_in_three_with_two"):
                        pair_groups += 1
            if hands > 0:
                return hands, pair_groups
        cnt = Counter(hand_cards)
        singles = sum(1 for r, c in cnt.items() if c == 1)
        pairs = sum(1 for r, c in cnt.items() if c == 2)
        trips = sum(1 for r, c in cnt.items() if c == 3)
        quads = sum(1 for r, c in cnt.items() if c == 4)
        return singles + pairs + trips + quads * 2, pairs

    def _q1_structure_balanced_single_press(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-264：跟压 Single 时，散单与拆对单做结构平衡。

        定音（match ``6a880831``）：
          ① 真散单（该 rank 手牌仅 1 张）与拆对单牌力差 ≤2 → 不拆，出散单
          ② 已拆留下的散单能压 → 优先于再拆新对（同上，差≤2）
          ③ 差 >2 仍可拆；敌方任一方报单剩 1 → 不介入（交给 GUA-222 / 最大单）

        从完整 non_banned 候选取散单（含低于「大单张」门槛的 CQ），
        避免 recommended 滤掉够压牌后再逼拆 AA。
        """
        if not GUARD_TOOLS_OK:
            return None

        enemies = ec.get("enemies", {}) or {}
        if any(
            int(e.get("remaining", 27) or 27) == 1
            for e in enemies.values()
            if isinstance(e, dict)
        ):
            return None

        greater_action = game_state.get("greaterAction")
        if not greater_action:
            return None
        try:
            gtype = get_action_type(greater_action)
        except Exception:
            gtype = None
        if gtype != ACTION_TYPE_SINGLE:
            return None

        # 领出轮不套用（只处理跟压）
        my_pos = int(ec.get("my_pos", game_state.get("myPos", 0)) or 0)
        if self._is_my_q1_lead_turn(game_state, my_pos):
            return None

        hand_cards = list(game_state.get("handCards", []) or [])
        if not hand_cards:
            return None
        rank_counts = Counter(
            get_card_rank(str(c)) for c in hand_cards if c
        )

        singles: List[Tuple[int, List]] = [
            (i, a) for i, a in candidates
            if _get_declared_action_type(a) == ACTION_TYPE_SINGLE
        ]
        if len(singles) < 2:
            return None

        cur_rank = str(game_state.get("curRank", "2"))

        def _act_rank(act: List) -> str:
            rk = get_action_rank(act) if GUARD_TOOLS_OK else ""
            if rk:
                return str(rk)
            cards = _get_cards(act)
            if cards:
                return str(get_card_rank(str(cards[0])))
            return ""

        scatters: List[Tuple[int, List]] = []
        pair_splits: List[Tuple[int, List]] = []
        for item in singles:
            rk = _act_rank(item[1])
            if not rk:
                continue
            if rank_counts.get(rk, 0) >= 2:
                pair_splits.append(item)
            elif rank_counts.get(rk, 0) == 1:
                scatters.append(item)

        if not scatters or not pair_splits:
            return None

        def _val(item: Tuple[int, List]) -> int:
            return _max_card_value(item[1], cur_rank)

        # 仅当「当前最大可压单」本身是拆对时才介入。
        # 若最大已是散单（含级牌 C2），交给 GUA-256 等后续逻辑，避免误伤。
        max_item = max(singles, key=_val)
        max_rk = _act_rank(max_item[1])
        if rank_counts.get(max_rk, 0) < 2:
            return None

        # 存在「某拆对单 − 某散单 ≤2」→ 该散单可替代拆对（不因 +1/+2 优势去拆）
        # 例：J 对 Q（差1）不拆；CQ 对 A（差2）不拆；J 对 A（差3）仍可拆 A
        eligible: List[Tuple[int, List]] = []
        seen_idx = set()
        for s in scatters:
            sv = _val(s)
            for p in pair_splits:
                if _val(p) - sv <= 2:
                    if s[0] not in seen_idx:
                        eligible.append(s)
                        seen_idx.add(s[0])
                    break

        if not eligible:
            return None

        # 多个可替代散单：取牌力最大（已拆剩 Q 优于更小散 J，兼顾防守）
        picked = max(eligible, key=_val)
        ref_split = max(pair_splits, key=_val)
        logger.info(
            "GUA-264 structure-balanced single: idx=%d scatter=%s "
            "vs split=%s (gap<=2)",
            picked[0],
            _act_rank(picked[1]),
            _act_rank(ref_split[1]),
        )
        return picked

    def _q1_enemy_one_single_press_max(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-222：敌方（任一阵营玩家）报单剩 1 张 + 我方跟牌压单时，
        取最大牌力单张压（忽略「回收优先」排序）。

        回收优先排序会把拆对出的单排到散单前（如手 SJ+H7S7+D9D9 压 Single/5 时，
        出 D9 后 J 可回收、出 SJ 无可回收 → 选拆对 D9）。但报单敌方残余最后一张
        随时可能接走，丢头游风险远大于保留大单回收的价值。
        """
        enemies = ec.get("enemies", {}) or {}
        if not any(
            int(e.get("remaining", 27) or 27) == 1
            for e in enemies.values()
            if isinstance(e, dict)
        ):
            return None
        greater_action = game_state.get("greaterAction")
        if not greater_action:
            return None
        try:
            gtype = get_action_type(greater_action)
        except Exception:
            gtype = None
        if gtype != ACTION_TYPE_SINGLE:
            return None
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if game_state.get("curPos", my_pos) == my_pos:
            return None
        singles = [
            (i, a) for i, a in candidates
            if _get_declared_action_type(a) == ACTION_TYPE_SINGLE
        ]
        if not singles:
            return None
        cur_rank = str(game_state.get("curRank", "2"))
        picked = max(singles, key=lambda item: _max_card_value(item[1], cur_rank))
        logger.info(
            "GUA-222 enemy-one single press: idx=%d type=%s",
            picked[0],
            _get_declared_action_type(picked[1]),
        )
        return picked

    def _q1_scatter_single_second_smallest_press(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-256：压单时手牌有 ≥2 个可压普通散单（非级牌）且无炸弹 →
        出「倒数第二小」的散单，不用级牌大单拦。

        Gate：
          1. greaterAction == Single（跟牌压单，非领出）
          2. 手牌无炸弹（Bomb/SF 不在候选）
          3. 可压 greater 的普通散单 ≥2 张（排除级牌单张与逢人配 H{curRank}）
          4. 取按牌力升序倒数第二小的散单

        不命中任一 gate 返回 None 让老逻辑继续（含 GUA-122 级牌提前排序）。

        实测 match 6a869e90（logs/v8_vs_botzone_20260820_142630.log L108-115，
        第46回合）：V8 手牌 6 = 散单 D8/CJ/DQ/C2 + 对子 SA/HA，greater=Single/7，
        无炸弹。修复前 GUA-122 把非逢人配级牌 C2 提到最前 → 出 Single/C2 拦小单，
        浪费级牌回手；应出倒数第二小散单 CJ。
        """
        if not GUARD_TOOLS_OK:
            return None

        greater_action = game_state.get("greaterAction")
        if not greater_action:
            return None
        try:
            gtype = get_action_type(greater_action)
        except Exception:
            return None
        if gtype != ACTION_TYPE_SINGLE:
            return None

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if game_state.get("curPos", my_pos) == my_pos:
            return None

        hand_cards = list(game_state.get("handCards", []) or [])
        if not hand_cards:
            return None
        cur_rank = str(game_state.get("curRank", "2"))

        # Gate 2: 手牌无炸弹（Bomb/SF 不在候选）
        if any(
            _is_bomb_like_action(item[1] if isinstance(item, tuple) and len(item) == 2 else item)
            for item in candidates
        ):
            return None

        # Gate 3+4: 可压 greater 的普通散单（排除级牌单张与逢人配）
        group_members = game_state.get("_group_members") or {}
        group_gid_type = game_state.get("_group_gid_type_map") or {}
        core_members: set = set()
        for gid, members in group_members.items():
            gtype = group_gid_type.get(gid) or group_gid_type.get(str(gid), "")
            if gtype in ("scatter", "Scatter"):
                continue  # 散单组本身
            if isinstance(members, (list, tuple)):
                core_members.update(str(c) for c in members)

        beaters: List[Tuple[int, List]] = []
        for idx, act in candidates:
            try:
                atype = get_action_type(act)
            except Exception:
                continue
            if atype != ACTION_TYPE_SINGLE:
                continue
            cards = _get_cards(act)
            if len(cards) != 1:
                continue
            card = str(cards[0])
            if _is_wild_level_card(card, cur_rank):
                continue  # 逢人配 H{curRank} 不拆
            try:
                if get_card_rank(card) == cur_rank:
                    continue  # 非逢人配级牌（如 C2）不参与散单
            except Exception:
                continue
            if core_members and card in core_members:
                continue  # 核心组（pair/trips/Bomb等）成员不算普通散单
            if not _action_beats_greater(act, greater_action, cur_rank):
                continue
            beaters.append((idx, act))

        if len(beaters) < 2:
            return None

        # 按牌力升序取倒数第二小（第二小）
        beaters.sort(key=lambda item: _max_card_value(item[1], cur_rank))
        picked = beaters[1]
        logger.info(
            "GUA-256 scatter single second-smallest press: idx=%d card=%s",
            picked[0],
            _get_cards(picked[1])[0] if _get_cards(picked[1]) else "?",
        )
        return picked

    def _q1_level_card_press_single(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-245：残局 Q1 级牌压单策略缺失。

        Gate：
          1. greaterAction == Single（对手出单）
          2. 任一敌人 remaining ≤ 5（残局冲刺阶段）
          3. 本方持有级牌单张（cur_rank rank 的单张，非逢人配 H{curRank}）
          4. 本方有冲刺路径（_has_structure_sprint_path 含顺子/整牌/炸弹）

        命中 → 取最小级牌压（保留大级牌回手）。
        不命中任一 gate 返回 None 让老逻辑继续。

        实测 match 6a83177a（logs/v8_vs_botzone_20260817_211528.log）：
        V8 含 D2×2 + S2（三张级牌 2，curRank=2），对手多次出 Single，
        Q1 连续 8 次 PASS on Single（22:15:59~22:16:41）。
        根因：_q1_block_enemy 通用路径在「非报单对手出单 + 非领出」场景下，
        候选排序优先「回收优先」/「拆核心保护」/「级牌保留」，
        未考虑「级牌压单 → 夺回领出权 → 顺子冲刺」路径。
        """
        if not GUARD_TOOLS_OK:
            return None

        # Gate 1: greaterAction == Single
        greater_action = game_state.get("greaterAction")
        if not greater_action:
            return None
        try:
            gtype = get_action_type(greater_action)
        except Exception:
            return None
        if gtype != ACTION_TYPE_SINGLE:
            return None

        # 我方非领出（对手出单我方跟牌）
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if game_state.get("curPos", my_pos) == my_pos:
            return None

        # Gate 2: 任一敌人 remaining ≤ 5
        enemies = ec.get("enemies", {}) or {}
        has_low_enemy = False
        for e in enemies.values():
            if isinstance(e, dict) and int(e.get("remaining", 27) or 27) <= 5:
                has_low_enemy = True
                break
        if not has_low_enemy:
            return None

        hand_cards = list(game_state.get("handCards", []) or [])
        if not hand_cards:
            return None
        cur_rank = str(game_state.get("curRank", "2"))

        # Gate 3: 本方持有级牌单张（cur_rank rank 的单张，非逢人配 H{curRank}）
        # 级牌单张 = rank == cur_rank 且 suit != H（H{curRank} 是逢人配）
        level_singles: List[Tuple[int, List]] = []
        for idx, act in candidates:
            try:
                atype = get_action_type(act)
            except Exception:
                continue
            if atype != ACTION_TYPE_SINGLE:
                continue
            cards = _get_cards(act)
            if len(cards) != 1:
                continue
            card = str(cards[0])
            # 排除逢人配 H{curRank}
            if _is_wild_level_card(card, cur_rank):
                continue
            # rank == cur_rank（级牌）
            try:
                if get_card_rank(card) != cur_rank:
                    continue
            except Exception:
                continue
            level_singles.append((idx, act))

        if not level_singles:
            return None

        # Gate 4: 本方有冲刺路径（顺子/整牌/炸弹）
        if not self._has_structure_sprint_path(hand_cards):
            return None

        # 取最小级牌压（保留大级牌回手）
        picked = min(level_singles, key=lambda item: _max_card_value(item[1], cur_rank))
        logger.info(
            "GUA-245 level-card press single: idx=%d card=%s sprint=True",
            picked[0],
            _get_cards(picked[1])[0] if _get_cards(picked[1]) else "?",
        )
        return picked

    @staticmethod
    def _is_one_hand_structure(ranks: List[str], cnt) -> bool:
        """这些 rank（count 均为 2 或 3）能否组成恰好一手整牌。"""
        if not ranks:
            return False
        counts = sorted(cnt[r] for r in ranks)
        total = sum(counts)
        if counts == [2] or counts == [3]:
            return total in (2, 3)
        if counts == [2, 3] or counts == [3, 3]:
            return total in (5, 6)
        if counts == [2, 2, 2]:
            return total == 6
        return False

    @classmethod
    def _rest_forms_two_hands(cls, rest_ranks: List[str], cnt) -> bool:
        """其余（非单非炸）牌能否恰好拆成 2 手整牌。"""
        n = len(rest_ranks)
        if n < 2:
            return False
        total = sum(cnt[r] for r in rest_ranks)
        if total < 6 or total > 12:
            return False
        for mask in range(1, (1 << n) - 1):
            g1 = [rest_ranks[i] for i in range(n) if mask & (1 << i)]
            g2 = [rest_ranks[i] for i in range(n) if not (mask & (1 << i))]
            if cls._is_one_hand_structure(g1, cnt) and cls._is_one_hand_structure(g2, cnt):
                return True
        return False

    def _is_bomb_destroying_action(
        self, act: List, hand_cards: List[str],
        game_state: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """检查非炸弹候选是否消耗了炸弹核心牌。

        GUA-219：优先回溯组牌引擎 `_group_members`——识别**隐式配子炸**
        （如 3K+H2 成 Bomb/K，K 天然仅 3 张，旧 rank≥4 计数识别不到）。
        对 Bomb/StraightFlush 组：action 用了组内**部分**成员（overlap 非空且
        != members_set）即判拆炸；组牌信息缺失时回退手牌某 rank≥4 张的显式炸计数。
        """
        act_cards = _get_cards(act)
        if not act_cards:
            return False
        try:
            atype = get_action_type(act)
        except Exception:
            return False
        if atype in ("Bomb", "StraightFlush", "JokerBomb"):
            return False

        # GUA-219：组牌引擎真源（识别隐式配子炸，同花顺/炸弹组保留配子成员）
        group_members = (game_state or {}).get("_group_members")
        gid_type_map = (game_state or {}).get("_group_gid_type_map", {})
        if group_members:
            act_set = set(act_cards)
            for gid, members in group_members.items():
                gtype = gid_type_map.get(gid) or gid_type_map.get(str(gid), "")
                if gtype not in ("Bomb", "StraightFlush"):
                    continue
                members_set = set(members)
                overlap = act_set & members_set
                if overlap and overlap != members_set:
                    return True

        # 回退：手牌某 rank≥4 张的显式炸计数
        from collections import Counter
        act_counter = Counter(act_cards)
        hand_counter = Counter(hand_cards)
        for rank in set(c[1] for c in hand_cards):
            in_hand = sum(1 for c in hand_cards if c[1] == rank)
            if in_hand >= 4:
                in_act = sum(1 for c in act_cards if c[1] == rank)
                if 1 <= in_act <= in_hand - 1 and in_hand - in_act < 4:
                    return True
        return False

    @staticmethod
    def _locking_residue_metrics(
        act: List, hand_cards: List[str],
    ) -> Tuple[int, int]:
        """GUA-260：估算出牌后残手「手数」与「是否仅散牌」。

        用点数计数粗估（不重跑组牌）：同点 2/3/≥4 各算一手整结构，
        同点 1 算一手散单。返回 ``(residue_hands, scatter_only)``，
        ``scatter_only=1`` 表示残手全是散单（无对/三/炸可回手）。
        """
        played = Counter(_get_cards(act))
        if not played:
            return 99, 1
        hand_cnt = Counter(hand_cards)
        if any(played[c] > hand_cnt[c] for c in played):
            return 99, 1
        residue = hand_cnt - played
        if not residue:
            return 0, 0
        rank_cnt: Counter = Counter()
        for card, n in residue.items():
            try:
                rank_cnt[get_card_rank(str(card))] += n
            except Exception:
                rank_cnt[str(card)] += n
        hands = 0
        structured = 0
        for n in rank_cnt.values():
            hands += 1
            if n >= 2:
                structured += 1
        scatter_only = 0 if structured > 0 else 1
        return hands, scatter_only

    def _straight_outside_safe_sort_key(
        self, act: List, game_state: Dict[str, Any],
    ) -> int:
        """GUA-263 §六：外面 5/10 打光 → 对应起点 Straight 优先（键越小越好）。

        0 = 安全顺（对手组不出同型窗）；1 = 其它动作/非安全顺。
        """
        if _get_declared_action_type(act) != ACTION_TYPE_STRAIGHT:
            return 1
        safe = set(
            (
                (game_state.get("_belief") or {}).get("straight_skeleton") or {}
            ).get("safe_straight_windows")
            or []
        )
        if not safe:
            return 1
        rank = ""
        if isinstance(act, list) and len(act) >= 2:
            rank = str(act[1] or "")
        return 0 if rank in safe else 1

    def _select_enemy_one_locking_structure(
        self, candidates: List[Tuple[int, List]], game_state: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """敌方报单/报双领出锁敌：按残手质量选整牌，而非牌型名硬排优先级。

        GUA-260（match `6a87e5a3`）：旧键 ``structure_priority`` 把 TWT(1)
        排在 Trips(4) 前 → 拆 777 打 55577，残手两张散单；应先出完整
        Trips/555 留下 Trips/777+单。统一评分（越小越好）：
        ① 不拆核心组（``_action_breaks_core_structure``）
        ② 不拆炸（``_is_bomb_destroying_action``）
        ②b GUA-263：外面 5/10 打光时优先安全顺（对手无法同型压制）
        ③ 残手手数少
        ④ 残手保留整结构（非全散单）
        ⑤ 牌型优先级仅作软并列打破
        """
        if not candidates:
            return None

        cur_rank = str(game_state.get("curRank", "2"))
        hand_cards = list(game_state.get("handCards", []) or [])

        def _key(item: Tuple[int, List]):
            _, act = item
            atype = get_action_type(act)
            breaks_core = self._action_breaks_core_structure(act, game_state)
            bomb_destroy = self._is_bomb_destroying_action(act, hand_cards, game_state)
            residue_hands, scatter_only = self._locking_residue_metrics(
                act, hand_cards,
            )
            return (
                1 if breaks_core else 0,
                1 if bomb_destroy else 0,
                self._straight_outside_safe_sort_key(act, game_state),
                residue_hands,
                scatter_only,
                _q1_structure_priority(atype),
                -len(_get_cards(act)),
                _max_card_value(act, cur_rank),
            )

        return min(candidates, key=_key)

    def _is_my_q1_lead_turn(self, game_state: Dict[str, Any], my_pos: int) -> bool:
        """Q1 自由领出兼容两种平台表示：curPos=myPos 或 curPos/greaterPos 都为 -1。

        Botzone 模式特判：adapter 只在轮到自己决策时调用 engine，恒设
        curPos=myPos；若存在真实待压的 greater（敌人出牌且非 PASS 占位），
        则是跟牌轮而非自由领出，避免 Q0 冲刺/封锁逻辑在跟牌轮误触发
        （实测 match=6a7172a327e7bf01db10319f 104 步：player3 出 Single/8，
        V8 手有 DJ 却因误判领出轮而 PASS）。
        """
        cur_pos = game_state.get("curPos", my_pos)
        greater_pos = game_state.get("greaterPos", -1)
        if cur_pos == my_pos:
            if not game_state.get("_botzone_mode"):
                return True
            # Botzone：跟牌轮特征 = 有真实待压 greater（敌人出牌且非 PASS 占位）
            if greater_pos in (-1, None, my_pos):
                return True
            if _is_control_action(game_state.get("greaterAction")):
                return False
            return True
        return cur_pos in (-1, None) and greater_pos in (-1, my_pos)

    def _find_exact_residue_candidate(
        self,
        residue_counter: Counter,
        candidates: List[Tuple[int, List]],
        *,
        exclude_idx: Optional[int] = None,
    ) -> Optional[Tuple[int, List]]:
        """在候选里找能恰好覆盖剩余手牌的那一手。"""
        residue_count = sum(residue_counter.values())
        if residue_count <= 0:
            return None

        for idx, act in candidates:
            if exclude_idx is not None and idx == exclude_idx:
                continue
            cards = _get_cards(act)
            if not cards or len(cards) != residue_count:
                continue
            if Counter(cards) != residue_counter:
                continue
            try:
                atype = get_action_type(act)
            except Exception:
                continue
            if atype == ACTION_TYPE_PASS:
                continue
            return idx, act
        return None

    def _select_two_turn_sprint_structure(
        self,
        structured: List[Tuple[int, List]],
        candidates: List[Tuple[int, List]],
        game_state: Dict[str, Any],
        ec: Dict[str, Any],
        *,
        prefer_structure_first: bool = False,
    ) -> Optional[Tuple[int, List]]:
        """仅剩两手时，优先选择能先手冲刺的整牌型。

        prefer_structure_first=True（Q0 自由领出）：整结构先于炸，炸作回手。
        """
        hand_cards = list(game_state.get("handCards", []) or [])
        hand_counter = Counter(hand_cards)
        if sum(hand_counter.values()) <= 1:
            return None

        cur_rank = str(game_state.get("curRank", "2"))
        # GUA-238: 残局两手 = 整牌 TWT(5) + 单张，且对手本局已对 ThreeWithTwo PASS
        # （memory_tracker 弱点证据，如 match=6a7dcf31 连打两个 TWT 对手全 PASS）→
        # 先出 TWT 冲刺，避免「保留 TWT 后出单」被对手压单后 TWT 卡死。
        opponent_twt_weakness = self._opponents_twt_weak(game_state, ec)
        sprint_candidates: List[Tuple[Tuple[int, int, int, int, int, int], Tuple[int, List]]] = []
        for item in structured:
            idx, act = item
            cards = _get_cards(act)
            if not cards:
                continue
            played_counter = Counter(cards)
            if any(played_counter[card] > hand_counter[card] for card in played_counter):
                continue

            residue_counter = hand_counter - played_counter
            residue_item = self._find_exact_residue_candidate(
                residue_counter, candidates, exclude_idx=idx,
            )
            if residue_item is None:
                continue

            residue_type = _effective_structure_type(residue_item[1])
            residue_bucket = 0
            if residue_type == ACTION_TYPE_SINGLE:
                safe_residue = self._select_enemy_one_safe_single([residue_item], game_state, ec)
                residue_bucket = 1 if safe_residue is not None else 2
            elif residue_type in (ACTION_TYPE_TRIPS, ACTION_TYPE_THREE_PAIR,
                                  ACTION_TYPE_TWO_TRIPS, ACTION_TYPE_STRAIGHT):
                # GUA-240: 残手 Trips 无法压 Single 回收——「先出散单留整牌」对 Trips
                # 不成立（出单后 Trips 只能等下圈同型，本圈单权回收不了），视为风险
                # 残手排后，让整牌 Trips 冲刺优先（match=6a7f1a17 21:37:58：
                # 手牌 AAA+9，先出 Single/9 即送单；出 Trips/AAA 顶大几乎必收权）。
                # 注：TWT 残手不在此列——TWT+单已由 GUA-238 twt_sprint_boost 处理
                # （有弱点先 TWT，无弱点维持先单）；Straight↔TWT 互拼走 GUA-236
                # 领出顺优先（Straight=0 < TWT=1，两候选均 bucket=0 时顺序不变）。
                # GUA-257（同源扩展，match=6a86e9540fbd680d7c7c6318 第58回合）：
                # 残手为 ThreePair/TwoTrips/Straight 整牌结构时同样视为风险——「先出
                # 单张留整牌」单被压后整牌烂手（本局 Single/T 被 Bomb/9 压死，445566
                # 整牌此后一直无法出手）。两手整牌语义下应「先出整牌特殊牌型、单留
                # 最后」。与 Trips 同 bucket=2，让「先出整牌」候选凭 structure_priority
                # 排前（ThreePair=3 < Single=99、TwoTrips=2、Straight=0）。
                residue_bucket = 2

            act_type = _effective_structure_type(act)
            declared = _get_declared_action_type(act)
            if prefer_structure_first:
                # 自由领出：整结构(0) > SF(1) > Bomb(2)；炸留作回手
                bomb_sprint_rank = (
                    0 if declared not in ("Bomb", "StraightFlush")
                    else 1 if declared == "StraightFlush"
                    else 2
                )
            else:
                # 被动跟压：若余手是炸（Bomb/StraightFlush），结构首发与炸首发同级，炸留作防御回手
                residue_bomb_like = False
                if residue_item is not None:
                    residue_declared = _get_declared_action_type(residue_item[1])
                    residue_bomb_like = residue_declared in ("Bomb", "StraightFlush")
                bomb_sprint_rank = (
                    0 if declared == "StraightFlush"
                    else 1 if declared == "Bomb" or residue_bomb_like
                    else 2
                )
            # GUA-238: 残手是单张 + 本候选为 TWT 整牌 + 对手对 TWT 有弱点 →
            # 该 TWT 候选最高优先级（先出 TWT 冲刺），否则维持原排序。
            twt_sprint_boost = 1
            if (
                act_type == ACTION_TYPE_THREE_WITH_TWO
                and residue_type == ACTION_TYPE_SINGLE
                and opponent_twt_weakness
            ):
                twt_sprint_boost = 0
            # GUA-263：外面 5/10 打光 → 对应起点 Straight 优先冲（对手难同型压）
            straight_safe_boost = self._straight_outside_safe_sort_key(
                act, game_state,
            )
            sprint_candidates.append((
                (
                    twt_sprint_boost,
                    straight_safe_boost,
                    residue_bucket,
                    bomb_sprint_rank,
                    _q1_structure_priority(act_type),
                    -len(cards),
                    (
                        -_declared_bomb_rank_value(act, cur_rank)
                        if declared == "Bomb"
                        else _max_card_value(act, cur_rank)
                    ),
                ),
                item,
            ))

        if not sprint_candidates:
            return None
        sprint_candidates.sort(key=lambda entry: entry[0])
        return sprint_candidates[0][1]

    def _opponents_twt_weak(
        self, game_state: Dict[str, Any], ec: Dict[str, Any],
    ) -> bool:
        """GUA-238: 任一对手对 ThreeWithTwo 有 PASS/被迫开炸弱点证据（接不住 TWT 圈）。"""
        tracker = game_state.get("_memory_tracker")
        if tracker is None:
            return False
        if not hasattr(tracker, "get_type_weakness"):
            return False
        enemies = (ec.get("enemies") or {}).keys()
        if not enemies:
            my_pos = ec.get("my_pos", game_state.get("myPos", 0))
            enemies = {(my_pos + 1) % 4, (my_pos + 3) % 4}
        for seat in enemies:
            weakness = tracker.get_type_weakness(int(seat))
            if weakness.get("ThreeWithTwo", 0) > 0:
                return True
        return False

    def _prune_q1_risky_same_type_lane_candidates(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> List[Tuple[int, List]]:
        """Q1 自由领出时，若同型通道最终更可能归敌方，则先剪掉风险同型候选。"""
        if not candidates or not GUARD_TOOLS_OK:
            return candidates
        if game_state.get("_memory_tracker") is None:
            return candidates

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if not self._is_my_q1_lead_turn(game_state, my_pos):
            return candidates

        remaining = int(main_enemy.get("remaining", 27) or 27)
        if remaining > 10:
            return candidates

        safe_candidates: List[Tuple[int, List]] = []
        risky_candidates: List[Tuple[int, List]] = []
        has_non_risky_non_pass = False
        for item in candidates:
            _, act = item
            try:
                atype = get_action_type(act)
            except Exception:
                safe_candidates.append(item)
                has_non_risky_non_pass = True
                continue

            if atype == ACTION_TYPE_PASS:
                safe_candidates.append(item)
                continue

            if self._is_risky_same_type_lane_action(game_state, ec, act):
                risky_candidates.append(item)
                continue

            safe_candidates.append(item)
            has_non_risky_non_pass = True

        if not risky_candidates or not has_non_risky_non_pass:
            return candidates
        return safe_candidates

    def _is_risky_same_type_lane_action(
        self, game_state: Dict[str, Any], ec: Dict[str, Any], action: List,
    ) -> bool:
        """同型通道风险：我方无接力、敌方外部仍可能有更大同型。"""
        atype = get_action_type(action)
        if atype not in (ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR, ACTION_TYPE_TRIPS):
            return False

        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        teammate_pos = (my_pos + 2) % 4
        enemies = list((ec.get("enemies") or {}).keys())
        if not enemies:
            enemies = [(my_pos + 1) % 4, (my_pos + 3) % 4]

        if not any(self._seat_may_hold_action_type_above(game_state, seat, action) for seat in enemies):
            return False
        if self._seat_may_relay_same_type_after_my_lead(game_state, teammate_pos, action):
            return False
        return True

    def _seat_may_hold_action_type_above(
        self, game_state: Dict[str, Any], seat: int, action: List,
    ) -> bool:
        """某席是否仍可能持有能压过该动作的同型。"""
        cur_rank = str(game_state.get("curRank", "2"))
        atype = get_action_type(action)
        target_rank = get_action_rank(action)
        if not target_rank:
            return False

        if atype == ACTION_TYPE_SINGLE:
            return self._seat_may_hold_single_above(game_state, seat, target_rank, cur_rank)
        if atype == ACTION_TYPE_PAIR:
            return self._seat_may_hold_same_rank_combo_above(game_state, seat, target_rank, cur_rank, 2)
        if atype == ACTION_TYPE_TRIPS:
            return self._seat_may_hold_same_rank_combo_above(game_state, seat, target_rank, cur_rank, 3)
        return False

    def _seat_may_relay_same_type_after_my_lead(
        self, game_state: Dict[str, Any], seat: int, action: List,
    ) -> bool:
        """队友是否大概率还有同型接力窗口。"""
        atype = get_action_type(action)
        required_cards = {
            ACTION_TYPE_SINGLE: 1,
            ACTION_TYPE_PAIR: 2,
            ACTION_TYPE_TRIPS: 3,
        }.get(atype, 0)
        if required_cards <= 0:
            return False

        belief = game_state.get("_belief") or {}
        hand_counts = belief.get("hand_counts") or game_state.get("numofplayers") or [27, 27, 27, 27]
        teammate_rest = hand_counts[seat] if len(hand_counts) > seat else 27
        if teammate_rest < required_cards:
            return False
        return self._seat_may_hold_action_type_above(game_state, seat, action)

    def _select_enemy_one_safe_single(
        self,
        singles: List[Tuple[int, List]],
        game_state: Dict[str, Any],
        ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """从单张中挑当前外部无压制的安全单；有多个时取最省的一张。"""
        if not singles:
            return None

        cur_rank = str(game_state.get("curRank", "2"))
        enemy_positions = list((ec.get("enemies") or {}).keys())
        if not enemy_positions:
            my_pos = ec.get("my_pos", game_state.get("myPos", 0))
            enemy_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]

        safe = []
        for item in singles:
            _, act = item
            rank = get_action_rank(act)
            if not rank:
                continue
            if any(
                self._seat_may_hold_single_above(game_state, seat, rank, cur_rank)
                for seat in enemy_positions
            ):
                continue
            safe.append(item)

        if not safe:
            return None

        def _key(item: Tuple[int, List]):
            _, act = item
            cards = _get_cards(act)
            value = get_card_value(cards[0], cur_rank) if cards else 99
            return value

        return min(safe, key=_key)

    def _pool_single_beat_risk(
        self, game_state: Dict[str, Any], seat: int, target_rank: str,
    ) -> Optional[float]:
        """GUA-244：P(该席剩余牌含 ≥1 张能压 target_rank 单张，含级牌)。

        池 ≤GUA244_ENUM_POOL_MAX 且该席剩 ≤GUA244_ENUM_SEAT_MAX → 精确 C(n,rem)；
        否则按池构成边际近似。无池返回 None，该席剩 0 返回 0.0。
        """
        pool = game_state.get("_remaining_pool_cards")
        if not pool:
            return None
        nop = game_state.get("numofplayers", [27, 27, 27, 27])
        rem = int(nop[seat]) if len(nop) > seat else 27
        if rem <= 0:
            return 0.0
        cur_rank = str(game_state.get("curRank", "2"))
        n_pool = len(pool)
        if rem > n_pool:
            return 1.0
        beaters = sum(1 for c in pool if _pool_card_beats_single(c, target_rank, cur_rank))
        if n_pool <= GUA244_ENUM_POOL_MAX and rem <= GUA244_ENUM_SEAT_MAX:
            from math import comb
            return 1.0 - comb(n_pool - beaters, rem) / comb(n_pool, rem)
        return 1.0 - ((n_pool - beaters) / n_pool) ** rem

    def _pool_pair_beat_risk(
        self, game_state: Dict[str, Any], seat: int, pair_rank: str,
    ) -> Optional[float]:
        """GUA-244：P(该席剩余牌含 >pair_rank 对子)。

        枚举精确：C(n_pool, rem) 组合中含「某 >pair_rank rank 的两张副本」；
        超限 → 边际（union bound 上界）近似。无池返回 None。
        """
        pool = game_state.get("_remaining_pool_cards")
        if not pool:
            return None
        nop = game_state.get("numofplayers", [27, 27, 27, 27])
        rem = int(nop[seat]) if len(nop) > seat else 27
        if rem <= 0:
            return 0.0
        cur_rank = str(game_state.get("curRank", "2"))
        n_pool = len(pool)
        if rem > n_pool:
            return 1.0
        if n_pool <= GUA244_ENUM_POOL_MAX and rem <= GUA244_ENUM_SEAT_MAX:
            from math import comb
            from itertools import combinations
            rank_counts: Counter = Counter()
            for c in pool:
                r = _pool_card_rank(c)
                if r not in ("SB", "HR"):
                    rank_counts[r] += 1
            qualifying = [
                r for r, n in rank_counts.items()
                if n >= 2 and _rank_beats_same_type(pair_rank, r, cur_rank)
            ]
            if not qualifying:
                return 0.0
            qual_set = set(qualifying)
            total = comb(n_pool, rem)
            cnt = 0
            for combo in combinations(range(n_pool), rem):
                drawn: Dict[str, int] = {}
                for i in combo:
                    r = _pool_card_rank(pool[i])
                    drawn[r] = drawn.get(r, 0) + 1
                if any(drawn.get(r, 0) >= 2 for r in qual_set):
                    cnt += 1
            return cnt / total
        # 边际上界（union bound）：P(抽到某 >pair_rank rank 两张副本) 之和
        rank_counts = Counter()
        for c in pool:
            r = _pool_card_rank(c)
            if r not in ("SB", "HR"):
                rank_counts[r] += 1
        risk = 0.0
        for r, n in rank_counts.items():
            if n < 2 or not _rank_beats_same_type(pair_rank, r, cur_rank):
                continue
            p = 1.0
            for k in range(2):
                p *= (n - k) / (n_pool - k)
            risk += p
        return min(1.0, risk)

    def _gua244_pair_lead_safe(self, game_state: Dict[str, Any], ec: Dict[str, Any]) -> bool:
        """GUA-244：自由领出 + 存在 ≤3 张主敌 + 池存在 + 本方 ≥2 对 + 低单 +
        池风险「单被接 ≥0.7 且对子被接 <0.3」→ 豁免报双/报三的 Pair 禁封。

        match 6a8003e6 #17：手 D5 C6 66 77，p1 报双，池 15 张含级牌 D2，
        单被接 104/105=0.99、对子被接 6/105=0.057 → Pair 解禁 → 决策层出对子。
        """
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if not self._is_my_q1_lead_turn(game_state, my_pos):
            return False
        pool = game_state.get("_remaining_pool_cards")
        if not pool:
            return False
        hand_cards = list(game_state.get("handCards", []) or [])
        if not hand_cards:
            return False
        cnt: Counter = Counter()
        for c in hand_cards:
            r = _pool_card_rank(c)
            if r not in ("SB", "HR"):
                cnt[r] += 1
        pair_count = sum(1 for n in cnt.values() if n >= 2)
        low_singles = [r for r, n in cnt.items() if n == 1]
        if pair_count < 2 or not low_singles:
            return False
        # 独立对子（计数==2；计数==3 是 TWT/Trips 核心，拆它会破坏整牌锁）
        independent_pairs = [r for r, n in cnt.items() if n == 2]
        if not independent_pairs:
            return False
        enemies = ec.get("enemies") or {}
        cur_rank = str(game_state.get("curRank", "2"))
        lowest_single = min(low_singles, key=lambda r: CARD_RANK_ORDER.get(r, 99))
        highest_pair = max(
            independent_pairs, key=lambda r: CARD_RANK_ORDER.get(r, -1),
        )
        for pos, e in enemies.items():
            rem = int(e.get("remaining", 27) or 27)
            if rem not in (1, 2, 3):
                continue
            sr = self._pool_single_beat_risk(game_state, pos, lowest_single)
            pr = self._pool_pair_beat_risk(game_state, pos, highest_pair)
            if (sr is not None and pr is not None
                    and sr >= GUA244_SINGLE_RISK and pr < GUA244_PAIR_RISK):
                return True
        return False

    def _q1_pool_pair_first_special(
        self,
        game_state: Dict[str, Any],
        candidates: List[Tuple[int, List]],
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-244：领出 + 主敌剩 ≤3 + 池存在 + 本方 ≥2 对 + 低单 +
        池风险「单被接 ≥0.7 且对子被接 <0.3」→ 出最高对子（对子先于单/整牌锁）。

        match 6a8003e6 #17：手 D5 C6 66 77，主敌 p1 剩 2，池 15 张含级牌 D2，
        单被接 104/105=0.99、对子被接 6/105=0.057 → 出 77 而非 Single/C6
        （原 C6 被级牌 D2 接走 → p1 S8 走完头游，V8 末游）。
        """
        if not GUARD_TOOLS_OK:
            return None
        if int(ec.get("teammate", {}).get("remaining", 0) or 0) == 1:
            return None
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        if not self._is_my_q1_lead_turn(game_state, my_pos):
            return None
        rem = int(main_enemy.get("remaining", 27) or 27)
        if rem not in (1, 2, 3):
            return None
        pool = game_state.get("_remaining_pool_cards")
        if not pool:
            return None
        hand_cards = list(game_state.get("handCards", []) or [])
        cur_rank = str(game_state.get("curRank", "2"))
        cnt: Counter = Counter()
        for c in hand_cards:
            r = _pool_card_rank(c)
            if r not in ("SB", "HR"):
                cnt[r] += 1
        pair_ranks = [r for r, n in cnt.items() if n >= 2]
        low_singles = [r for r, n in cnt.items() if n == 1]
        if len(pair_ranks) < 2 or not low_singles:
            return None
        lowest_single = min(low_singles, key=lambda r: CARD_RANK_ORDER.get(r, 99))
        sr = self._pool_single_beat_risk(game_state, main_pos, lowest_single)
        if sr is None or sr < GUA244_SINGLE_RISK:
            return None
        pairs = [
            (i, a) for i, a in candidates
            if _get_cards(a) and get_action_type(a) == ACTION_TYPE_PAIR
            and not self._is_bomb_destroying_action(a, hand_cards, game_state)
            # GUA-244：排除拆 TWT/Trips 三同张核心的对子（AAA+JJ 的 AAA）
            # ——组牌把 TWT 拆成 trip 子组 + 独立 pair 子组，GUA-219 只查
            # Bomb/SF 组；此处按 rank 计数==3 拦截拆 triple。
            and cnt.get(_pool_card_rank(_get_cards(a)[0]), 0) != 3
        ]
        if not pairs:
            return None
        cand_ranks = [_pool_card_rank(_get_cards(a)[0]) for _, a in pairs]
        highest_pair = max(cand_ranks, key=lambda r: CARD_RANK_ORDER.get(r, -1))
        pr = self._pool_pair_beat_risk(game_state, main_pos, highest_pair)
        if pr is None or pr >= GUA244_PAIR_RISK:
            return None
        best = max(pairs, key=lambda it: get_card_value(_get_cards(it[1])[0], cur_rank))
        logger.info(
            "Q1 池推理对子优先(GUA-244): idx=%d rank=%s single_risk=%.2f pair_risk=%.2f",
            best[0], get_action_rank(best[1]), sr, pr,
        )
        return best

    def _select_enemy_one_strongest_single(
        self, singles: List[Tuple[int, List]], game_state: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """无安全单时，至少不要退回去领 K 这类伪控牌单；改领当前最强单张。"""
        if not singles:
            return None

        cur_rank = str(game_state.get("curRank", "2"))

        def _key(item: Tuple[int, List]):
            _, act = item
            cards = _get_cards(act)
            value = get_card_value(cards[0], cur_rank) if cards else -1
            return value

        return max(singles, key=_key)

    def _infer_enemy_five_shape(
        self, game_state: Dict[str, Any], ec: Dict[str, Any], seat: int,
    ) -> str:
        """粗推 5 张残局更像 4+1 还是整牌型。返回 bomb_plus_single/structured/unknown。"""
        tracker = game_state.get("_memory_tracker")
        belief = game_state.get("_belief") or {}
        if tracker is None:
            return "unknown"

        possible_bomb = self._seat_may_hold_four_of_kind(game_state, seat)
        possible_structured = self._seat_may_hold_structured_five(game_state, seat)
        bomb_risk = (belief.get("opp_bomb_risks") or {}).get(seat, 0.0)

        if possible_bomb and not possible_structured and bomb_risk >= 0.5:
            return "bomb_plus_single"
        if possible_structured and not possible_bomb:
            return "structured"
        if possible_bomb and possible_structured:
            return "unknown"
        return "unknown"

    def _seat_may_hold_four_of_kind(self, game_state: Dict[str, Any], seat: int) -> bool:
        """某席是否仍可能持有四炸（4 头炸）。"""
        tracker = game_state.get("_memory_tracker")
        if tracker is None:
            return False
        my_pos = game_state.get("myPos", 0)
        partner_pos = (my_pos + 2) % 4
        holding_states = _seat_holding_states(seat, my_pos, partner_pos)
        for rank in CARD_RANK_ORDER.keys():
            if rank in ("SB", "HR"):
                continue
            possible = 0
            for suit in ("S", "H", "D", "C"):
                ct = f"{suit}{rank}"
                for state in tracker.card_state.get(ct, [-1, -1]):
                    if state in holding_states:
                        possible += 1
            if possible >= 4:
                return True
        return False

    def _seat_may_hold_structured_five(self, game_state: Dict[str, Any], seat: int) -> bool:
        """某席是否仍可能持有 5 张整牌型（三带二/顺子/同花顺）。"""
        tracker = game_state.get("_memory_tracker")
        if tracker is None:
            return False
        my_pos = game_state.get("myPos", 0)
        partner_pos = (my_pos + 2) % 4
        holding_states = _seat_holding_states(seat, my_pos, partner_pos)

        rank_possible: Dict[str, int] = {}
        for rank in CARD_RANK_ORDER.keys():
            if rank in ("SB", "HR"):
                continue
            cnt = 0
            for suit in ("S", "H", "D", "C"):
                ct = f"{suit}{rank}"
                for state in tracker.card_state.get(ct, [-1, -1]):
                    if state in holding_states:
                        cnt += 1
            rank_possible[rank] = cnt

        # 三带二
        has_trip = any(cnt >= 3 for cnt in rank_possible.values())
        has_pair = any(cnt >= 2 for cnt in rank_possible.values())
        if has_trip and has_pair:
            return True

        # 顺子
        ordered = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
        for i in range(len(ordered) - 4):
            window = ordered[i:i + 5]
            if all(rank_possible.get(r, 0) >= 1 for r in window):
                return True

        # 同花顺（粗判：同花色五连张都可能）
        for suit in ("S", "H", "D", "C"):
            suit_ranks = set()
            for rank in ordered:
                ct = f"{suit}{rank}"
                if any(state in holding_states for state in tracker.card_state.get(ct, [-1, -1])):
                    suit_ranks.add(rank)
            for i in range(len(ordered) - 4):
                window = ordered[i:i + 5]
                if all(r in suit_ranks for r in window):
                    return True
        return False

    def _seat_possible_rank_counts(self, game_state: Dict[str, Any], seat: int) -> Dict[str, int]:
        """某席仍可能持有的各 rank 张数上界。"""
        tracker = game_state.get("_memory_tracker")
        if tracker is None:
            return {}
        my_pos = game_state.get("myPos", 0)
        partner_pos = (my_pos + 2) % 4
        holding_states = _seat_holding_states(seat, my_pos, partner_pos)
        rank_counts: Dict[str, int] = {}
        for ct, copies in tracker.card_state.items():
            rank = ct if ct in ("HR", "SB") else (ct[1:] if len(ct) >= 2 else ct)
            cnt = sum(1 for state in copies if state in holding_states)
            if cnt > 0:
                rank_counts[rank] = rank_counts.get(rank, 0) + cnt
        return rank_counts

    def _seat_may_hold_same_rank_combo_above(
        self, game_state: Dict[str, Any], seat: int, target_rank: str, cur_rank: str, need: int,
    ) -> bool:
        """某席是否仍可能持有更大的对子/三张。"""
        rank_counts = self._seat_possible_rank_counts(game_state, seat)
        for rank, cnt in rank_counts.items():
            if cnt >= need and _rank_beats_same_type(target_rank, rank, cur_rank):
                return True
        return False

    def _seat_may_hold_three_with_two_above(
        self, game_state: Dict[str, Any], seat: int, target_rank: str, cur_rank: str,
    ) -> bool:
        """某席是否仍可能持有更大的三带二。"""
        rank_counts = self._seat_possible_rank_counts(game_state, seat)
        for trip_rank, trip_cnt in rank_counts.items():
            if trip_cnt < 3 or not _rank_beats_same_type(target_rank, trip_rank, cur_rank):
                continue
            for pair_rank, pair_cnt in rank_counts.items():
                if pair_rank != trip_rank and pair_cnt >= 2:
                    return True
        return False

    def _get_straight_top_rank(self, action: List, cur_rank: str) -> Optional[str]:
        """顺子的比较锚点：取当前可见牌中的最大 rank。"""
        cards = _get_cards(action)
        if not cards:
            return get_action_rank(action)
        best = max(cards, key=lambda c: get_card_value(c, cur_rank))
        return get_card_rank(best)

    def _seat_may_hold_straight_above(
        self, game_state: Dict[str, Any], seat: int, greater_action: List, cur_rank: str,
    ) -> bool:
        """某席是否仍可能持有更大的顺子。"""
        top_rank = self._get_straight_top_rank(greater_action, cur_rank)
        if not top_rank:
            return True

        ordered = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
        if top_rank not in ordered:
            return True

        rank_counts = self._seat_possible_rank_counts(game_state, seat)
        top_index = ordered.index(top_rank)
        for start in range(len(ordered) - 4):
            window = ordered[start:start + 5]
            if ordered.index(window[-1]) <= top_index:
                continue
            if all(rank_counts.get(rank, 0) >= 1 for rank in window):
                return True
        return False

    def _seat_may_hold_single_above(
        self, game_state: Dict[str, Any], seat: int, target_rank: str, cur_rank: str,
    ) -> bool:
        """某席是否仍可能持有高于 target_rank 的单张。"""
        # GUA-244：有剩余池时池优先（确定性残牌全集），无池回退 MemoryTracker
        pool = game_state.get("_remaining_pool_cards")
        if pool:
            nop = game_state.get("numofplayers", [27, 27, 27, 27])
            rem = int(nop[seat]) if len(nop) > seat else 27
            if rem <= 0:
                return False
            return any(_pool_card_beats_single(c, target_rank, cur_rank) for c in pool)
        tracker = game_state.get("_memory_tracker")
        if tracker is None or not target_rank:
            return True
        my_pos = game_state.get("myPos", 0)
        partner_pos = (my_pos + 2) % 4
        holding_states = _seat_holding_states(seat, my_pos, partner_pos)
        threshold = CARD_RANK_ORDER.get(target_rank, -1)
        # 级牌、大王、小王始终视为高牌
        for ct, copies in tracker.card_state.items():
            if ct == "HR":
                if any(state in holding_states for state in copies):
                    return True
                continue
            if ct == "SB":
                if any(state in holding_states for state in copies):
                    return True
                continue
            rank = ct[1:] if len(ct) >= 2 else ct
            if _rank_beats_same_type(target_rank, rank, cur_rank):
                if any(state in holding_states for state in copies):
                    return True
        return False

    def _is_teammate_strong(self, game_state: Dict[str, Any], teammate_pos: int) -> bool:
        """粗判队友牌力是否偏强：剩张不多或手里可能仍有炸。"""
        belief = game_state.get("_belief") or {}
        hand_counts = belief.get("hand_counts") or game_state.get("numofplayers") or [27, 27, 27, 27]
        teammate_rest = hand_counts[teammate_pos] if len(hand_counts) > teammate_pos else 27
        opp_bomb_risks = belief.get("opp_bomb_risks") or {}
        teammate_bomb_risk = opp_bomb_risks.get(teammate_pos, 0.0)
        return teammate_rest <= 8 or teammate_bomb_risk >= 0.5

    def _enemy_danger_score(self, enemy_pos: int, ectx: Dict[str, Any], my_pos: int) -> tuple:
        """危险度越低越危险。"""
        remaining = ectx.get("remaining", 27)
        pos_score = 0 if enemy_pos == (my_pos + 1) % 4 else 1
        has_baoshu = "baoshu" in ectx
        danger_map = {"极高": 0, "高": 1, "中高": 2, "中": 3, "低": 4}
        d_level = danger_map.get(ectx.get("danger_level", "低"), 5)
        return (remaining, pos_score, 0 if has_baoshu else 1, d_level)

    # ═══════════════════════════════════════════════════
    #  Q2: 助攻队友
    # ═══════════════════════════════════════════════════

    def _q2_assist_teammate(
        self, game_state: Dict[str, Any], action_list: List, ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        队友 ≤5 张 → 按 assist_prefer 喂牌送队友走（Q1 单一真源）。
        """
        teammate = ec.get("teammate", {})
        if not teammate or not teammate.get("is_close"):
            return None

        assist_prefer = teammate.get("assist_prefer", [])
        if not assist_prefer:
            return None

        return pick_assist_feed_by_prefer(
            game_state, action_list, assist_prefer,
        )

    # ═══════════════════════════════════════════════════
    #  Q3: 炸弹兜底
    # ═══════════════════════════════════════════════════

    def _q3_bomb_fallback(
        self, game_state: Dict[str, Any], action_list: List, ec: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        非冲刺/封锁/助攻场景，用 should_bomb 确认是否炸。
        """
        cur_rank = str(game_state.get("curRank", "2"))

        if not GUARD_TOOLS_OK:
            return None

        # 0. GUA-170-A: 优先非炸压牌（有同型合法压则不用炸）
        # GUA-284: 最省候选若拆核 → 继续试次省散牌，勿直接 PASS
        # （match=6a8e9548：最省 Q 拆 TWT 核对 J，散牌 HK 可用却被误 PASS）
        press_candidates = self._find_all_cheapest_press_candidates(
            game_state, action_list, cur_rank,
        )
        if press_candidates:
            all_break_core = True
            for cheaper_idx, cheaper_act in press_candidates:
                if _get_declared_action_type(cheaper_act) in ("PASS",):
                    continue
                if self._action_breaks_core_structure(cheaper_act, game_state):
                    if self._should_exempt_break_core_for_enemy_five_single(
                        game_state, ec, cheaper_act,
                    ):
                        logger.info("Q3 非炸压牌(省,GUA-252): idx=%d", cheaper_idx)
                        return (cheaper_idx, cheaper_act)
                    logger.info(
                        "Q3 最省压牌拆整牌(%s) 跳过",
                        _get_declared_action_type(cheaper_act),
                    )
                    continue
                all_break_core = False
                logger.info("Q3 非炸压牌(省): idx=%d", cheaper_idx)
                return (cheaper_idx, cheaper_act)
            if all_break_core:
                pass_idx = next(
                    (i for i, a in enumerate(action_list)
                     if _get_declared_action_type(a) in ("PASS",)),
                    None,
                )
                if pass_idx is not None:
                    logger.info("Q3 全部压牌均拆整牌 → PASS")
                    return (pass_idx, action_list[pass_idx])

        # 分离炸弹
        bombs = []
        for i, a in enumerate(action_list):
            try:
                if is_bomb(a):
                    bombs.append((i, a))
            except Exception:
                pass

        if not bombs:
            return None

        # 对每个炸弹执行 should_bomb 判断
        try:
            from .endgame_preprocessor import EndgamePreprocessor
        except ImportError:
            from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor

        for idx, bomb in bombs:
            bomb_cards = _get_cards(bomb)
            bomb_size = len(bomb_cards)
            result = EndgamePreprocessor._should_bomb(game_state, bomb_size)
            if result["should_bomb"]:
                # 出这个炸弹
                return (idx, bomb)

        # 都不该炸 → 走常规牌型
        return None

    # ── GUA-170-A: 最省同型压牌 ──

    @staticmethod
    def _find_all_cheapest_press_candidates(
        game_state: Dict[str, Any], action_list: List, cur_rank: str,
    ) -> List[Tuple[int, List]]:
        """找所有非炸同型压牌候选，按 rank 值升序（最省在前）。"""
        greater_action = game_state.get("greaterAction") or game_state.get("greater_action")
        if not greater_action or greater_action[0] in ("PASS", None, ""):
            return []

        candidates = []
        for i, a in enumerate(action_list):
            try:
                if _get_declared_action_type(a) in ("PASS",):
                    continue
                if _is_bomb_like_action(a):
                    continue
                if not _action_beats_greater(a, greater_action, cur_rank):
                    continue
                candidates.append((i, a))
            except Exception:
                pass

        if not candidates:
            return []

        candidates.sort(key=lambda x: _min_card_value(x[1], cur_rank))
        return candidates

    @staticmethod
    def _find_cheapest_press(
        game_state: Dict[str, Any], action_list: List, cur_rank: str,
    ) -> Optional[Tuple[int, List]]:
        """找最省的非炸同型压牌（压 greaterAction），若有则优先于炸弹。

        Returns (index, action) or None。
        """
        candidates = EndgameDecider._find_all_cheapest_press_candidates(
            game_state, action_list, cur_rank,
        )
        return candidates[0] if candidates else None

    @staticmethod
    def _should_exempt_break_core_for_enemy_five_single(
        game_state: Dict[str, Any], ec: Dict[str, Any],
        action: Optional[List] = None,
    ) -> bool:
        """GUA-252：敌方 ≤5 张且出单 → 豁免「拆核心转 PASS」拦截。

        残局敌剩 ≤5 张打单时，拆 TWT/整牌出最大合法单张压牌是正确的夺权打法
        （match=6a86823d 残局 777+KK 对手打 S8：Q1 已找到 K 要压，
        却被 _action_breaks_core_structure 误杀成 PASS，导致对手连续控牌）。
        仅当全部满足才豁免：
          1. greaterAction 是 Single
          2. 出牌者是敌人（非我方、非队友）
          3. 该敌人剩余 ≤5
          4. 待出的 action 是 Single 且能压过当前单（拆出压不过的单=送菜）
        """
        try:
            greater_action = game_state.get("greaterAction")
            if not greater_action or get_action_type(greater_action) != ACTION_TYPE_SINGLE:
                return False
            greater_pos = game_state.get("greaterPos", -1)
            if greater_pos in (-1, None):
                return False
            my_pos = ec.get("my_pos", game_state.get("myPos", 0))
            teammate_pos = (my_pos + 2) % 4
            if greater_pos == my_pos or greater_pos == teammate_pos:
                return False
            enemies = ec.get("enemies", {}) or {}
            if greater_pos not in enemies:
                # 未识别为敌人时，按 seat 判（非我、非队友即敌）
                if greater_pos not in ((my_pos + 1) % 4, (my_pos + 3) % 4):
                    return False
            enemy_ctx = enemies.get(greater_pos, {}) or {}
            remaining = enemy_ctx.get("remaining", -1)
            if not (isinstance(remaining, int) and remaining >= 0):
                # 敌人剩余未知时用 numofplayers 估算
                numofplayers = (
                    ec.get("numofplayers")
                    or game_state.get("numofplayers")
                    or []
                )
                if (
                    isinstance(numofplayers, (list, tuple))
                    and 0 <= greater_pos < len(numofplayers)
                    and isinstance(numofplayers[greater_pos], int)
                ):
                    remaining = numofplayers[greater_pos]
            if not (isinstance(remaining, int) and 0 <= remaining <= 5):
                return False
            # 4. 拆出的 Single 必须能压过当前单
            if action is not None:
                if get_action_type(action) != ACTION_TYPE_SINGLE:
                    return False
                greater_cards = _get_cards(greater_action)
                action_cards = _get_cards(action)
                if not greater_cards or not action_cards:
                    return False
                cur_rank = str(game_state.get("curRank", "2"))
                greater_value = get_card_value(greater_cards[0], cur_rank)
                action_value = get_card_value(action_cards[0], cur_rank)
                if action_value <= greater_value:
                    return False
            return True
        except Exception:
            return False

    @staticmethod
    def _action_breaks_core_structure(
        action: List, game_state: Dict[str, Any],
    ) -> bool:
        """检查出牌是否会破坏 core 整牌结构。

        用 _group_members 逐组扫描：若某 core 类型组的部分成员被 action 使用，
        但非全部成员，则视为破坏结构。成员比较用 Counter（同点重复牌不能
        用 set 塌缩，GUA-267）。兼容 GUA-154 跨组归属。
        """
        # GUA-206: 完整炸弹/同花顺本身就是最高等级核心整牌（同花顺 > 5星炸 > 4星炸，
        # 组牌引擎 _score_power 同花顺 +3、普通炸弹 +2 已体现该大小关系）。
        # 出完整炸弹类动作 = 用核心整牌压制敌人，绝非 GUA-199 要拦的「拆核心打弱牌」
        # （如 444+H2 拆 H2 打 22 对子，那类 action 是 Pair 等非炸弹型，不受豁免）。
        # 背景：组牌引擎优先组同花顺、用 H2 配子补 SF（[SA,S2,S3,S4,H2]），而平台
        # actionList 枚举真实牌 SF（[SA,S2,S3,S4,S5]）——两张同花顺牌面 set 不同，
        # 若不豁免会被误判「拆核心」→ 强压敌炸被 PASS（match=6a74198a step20/22）。
        if _is_bomb_like_action(action):
            return False
        group_members = game_state.get("_group_members")
        gid_type_map = game_state.get("_group_gid_type_map", {})
        if not group_members:
            return False
        # GUA-267：必须用 Counter。4 张 Q 含两张 SQ 时 set 会塌成 3 张，
        # 三条 Q 被误判为打完整个炸核（match=6a8c3452）。
        action_cards_counts = Counter(str(c) for c in _get_cards(action))
        if not action_cards_counts:
            return False

        # 核心整牌类型（不包含普通对子/单张）
        # 注意：组牌引擎产出为小写 straight / trips，复合牌型拆为子组；
        # 炸弹/同花顺为组牌引擎大写 "Bomb"/"StraightFlush"（grouping_engine.py:167）。
        # GUA-199: Bomb 纳入核心 → 拆炸弹 core 打弱牌（如 444+H2 拆 H2 打 22 对子）
        # 被拦截 PASS，防止把炸弹核心当弱牌打出（match=6a71ace3 回合11）。
        # GUA-288: 集合与模块级 _BOMB_BREAK_CORE_TYPES 保持一致（供 _bomb_disrupts_core_group 复用）。
        CORE_TYPES = _BOMB_BREAK_CORE_TYPES

        for gid, members in group_members.items():
            gtype = gid_type_map.get(gid) or gid_type_map.get(str(gid), "")
            if gtype not in CORE_TYPES:
                continue
            members_counts = Counter(str(c) for c in members)
            overlap = action_cards_counts & members_counts
            if not overlap:
                continue
            if overlap != members_counts:
                return True
        return False

    # ═══════════════════════════════════════════════════
    #  辅助过滤 & 选择
    # ═══════════════════════════════════════════════════

    def _filter_by_recommended_types(
        self, candidates: List[Tuple[int, List]],
        rec_types: List[str], game_state: Dict[str, Any],
    ) -> List:
        """
        从 candidates 中筛选匹配 recommended_types 的动作。

        rec_types 是中文名（如 "大单张", "三带二"）或 V7 枚举名。
        """
        if not rec_types or not GUARD_TOOLS_OK:
            return []

        try:
            from .endgame_preprocessor import EndgamePreprocessor as EP
        except ImportError:
            from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor as EP

        # 将中文名转换为 V7 枚举
        mapped_types: List[str] = []
        for name in rec_types:
            if name in EP.SHAPE_MAP:
                mapped_types.extend(EP.SHAPE_MAP[name])
            else:
                # 可能已经是 V7 枚举名
                mapped_types.append(name)
        mapped_types = list(set(mapped_types))

        if not mapped_types:
            return []

        result = []
        for idx, a in candidates:
            try:
                atype = get_action_type(a)
                if atype in mapped_types:
                    # 大单张需额外检查值 ≥ 动态阈值
                    if "大单张" in rec_types or "最大单张" in rec_types:
                        if atype == ACTION_TYPE_SINGLE:
                            threshold = EP()._resolve_big_single_threshold(game_state)
                            cards = _get_cards(a)
                            if cards:
                                cv = get_card_value(cards[0], str(game_state.get("curRank", "2")))
                                if cv < CARD_RANK_ORDER.get(threshold, 11):
                                    continue  # 不够大
                    result.append((idx, a))
            except Exception:
                pass

        return result

    def _select_best_index(
        self, candidates: List[Tuple[int, List]],
        action_list: List, game_state: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """从已排序候选中选最佳：第一个（已排序）或最大牌力。"""
        if not candidates:
            return None
        # candidates 已由调用方排序（回收优先），取第一个
        idx, act = candidates[0]
        return (idx, act)

    def _select_best_bomb(
        self, bombs: List[Tuple[int, List]], action_list: List,
        cur_rank: str = "2",
    ) -> Optional[Tuple[int, List]]:
        """选最大炸弹（张数多 > 声明点数大）。逢人配不参与比点（GUA-281）。"""
        if not bombs:
            return None

        def bomb_score(item: Tuple[int, List]) -> int:
            _, act = item
            cards = _get_cards(act)
            # 张数多优先，同张数按声明点数（排除配子虚高）
            return len(cards) * 100 + _declared_bomb_rank_value(act, cur_rank)

        best = max(bombs, key=bomb_score)
        return best

    def _select_cheapest_bomb_or_sf(
        self, action_list: List, cur_rank: str = "2",
    ) -> Optional[Tuple[int, List]]:
        """GUA-278：actionList 中最廉 Bomb/StraightFlush（牌力弱→强优先，够用就好）。"""
        cands: List[Tuple[int, int, int, int, List]] = []
        for i, a in enumerate(action_list or []):
            at = _get_declared_action_type(a)
            if at not in ("Bomb", "StraightFlush"):
                continue
            cards = _get_cards(a)
            # 牌力序（guandan-knowledge）：SF(55)≻5星(50)≻4星(40)。
            # 弱→强优先 = 够用就好；4星够压就用 4星，不浪费更强火力/不动同花顺。
            family = _bomb_weakest_first_key(a, cur_rank)
            cands.append(
                (family, len(cards), _max_card_value(a, cur_rank), i, a)
            )
        if not cands:
            return None
        best = min(cands)
        return (best[3], best[4])

    def _gua278_critical_lower_enemy_bomb(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[int, List]]:
        """GUA-278：下家敌 remaining≤2 且有炸 → 最廉 Bomb/SF 截断。

        锚点 match=6a8d4603：下家 TWT/K 后剩≈2，GUA-135 选 min TWT →
        Q1 拆核转 PASS，放走下家头游。定音：有炸则禁该 PASS / 禁优先拆核 TWT。
        """
        try:
            my_pos = int(game_state.get("myPos", 0) or 0)
            greater_pos = int(game_state.get("greaterPos", -1))
        except (TypeError, ValueError):
            return None
        if greater_pos < 0:
            return None
        lower_pos = (my_pos + 1) % 4
        if greater_pos != lower_pos:
            return None

        rem = 99
        if ec:
            enemies = ec.get("enemies") or {}
            einfo = enemies.get(lower_pos)
            if einfo is None:
                einfo = enemies.get(str(lower_pos))
            if isinstance(einfo, dict):
                try:
                    rem = int(einfo.get("remaining", 99) or 99)
                except (TypeError, ValueError):
                    rem = 99
        if rem > 2:
            nums = game_state.get("numofplayers") or []
            if isinstance(nums, (list, tuple)) and len(nums) > lower_pos:
                try:
                    rem = int(nums[lower_pos] or 99)
                except (TypeError, ValueError):
                    rem = 99
            if rem > 2:
                pub = game_state.get("publicInfo") or []
                if isinstance(pub, list) and len(pub) > lower_pos:
                    try:
                        rem = int((pub[lower_pos] or {}).get("rest", 99) or 99)
                    except (TypeError, ValueError):
                        rem = 99
        if rem < 1 or rem > 2:
            return None

        picked = self._select_cheapest_bomb_or_sf(
            action_list, str(game_state.get("curRank", "2")),
        )
        if picked is not None:
            logger.info(
                "GUA-278: 下家敌 remaining=%d ≤2 → 最廉炸/同花顺截断",
                rem,
            )
        return picked

    # ── L3 降级 ──

    def _l3_fallback(
        self, action_list: List,
        baoshu_never: set, cur_rank: str,
        is_passive: bool,
    ) -> Optional[Tuple[int, List]]:
        """
        极限降级：无炸 + 主动方 + 全被禁。

        L1: 有炸出炸（已由上游处理，这里是无炸场景）
        L2: 被动方 → PASS
        L3: 放宽 banned，仅保留 baoshu.never_play，打级牌以下最大牌
        """
        if not GUARD_TOOLS_OK:
            return None

        # L2: 被动 → PASS
        if is_passive:
            for i, a in enumerate(action_list):
                try:
                    if get_action_type(a) == ACTION_TYPE_PASS:
                        return (i, a)
                except Exception:
                    pass
            return None

        # L3: 主动方 → 放宽禁令
        rank_value = CARD_RANK_ORDER.get(cur_rank, 0)

        relaxed = []
        for i, a in enumerate(action_list):
            try:
                atype = get_action_type(a)
                if atype == ACTION_TYPE_PASS:
                    continue
                if atype in baoshu_never:
                    continue  # baoshu 硬禁仍然保留

                # 筛选级牌以下
                cards = _get_cards(a)
                if cards and all(get_card_value(c, cur_rank) < rank_value for c in cards):
                    relaxed.append((i, a))
            except Exception:
                pass

        if relaxed:
            # 级牌以下从大到小
            relaxed.sort(key=lambda x: _max_card_value(x[1], cur_rank), reverse=True)
            logger.debug("L3 降级出牌: 级牌以下 %d 候选", len(relaxed))
            return (relaxed[0][0], relaxed[0][1])

        # 没牌了 → 出最大能出的（忽略 ban）
        max_idx, max_act = 0, action_list[0]
        max_val = 0
        for i, a in enumerate(action_list):
            try:
                if get_action_type(a) == ACTION_TYPE_PASS:
                    continue
                val = _max_card_value(a, cur_rank)
                if val > max_val:
                    max_val, max_idx, max_act = val, i, a
            except Exception:
                pass
        return (max_idx, max_act)

    # ═══════════════════════════════════════════════════════
    #  GUA-131 / GUA-132 / GUA-133  C1/C2/C4 决策树
    #  关联：docs/guandan-brain/issues/GUA-131/132/133-completion.md
    #  决策真源：GUA-125 §0.5.1 / §0.5.2
    # ═══════════════════════════════════════════════════════

    def _detect_c1_c2_c4_context(
        self, game_state: Dict[str, Any], ec: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        C1/C2/C4 通用上下文探测。

        触发条件（与 GUA-131/132/133 §1 对齐）：
          - 当前 greaterAction 是 5 张 TWT（5 张三带二）
          - greaterPos 是 yf2 的上家或下家（@1 报 5 张）
          - 该敌 remaining ∈ {5, 6}（5 张 = @1 报 5 张 finish 含 5 张；6 张残局）
          - yf2 整手 ≥ 10 张
          - yf2 属于跟压（greaterPos != my_pos）

        返回 dict 或 None：{
          "kind": "C1" | "C2" | "C4" | None,
          "enemy_pos": int,
          "enemy_ctx": dict,
          "teammate_pos": int,
          "remaining_after_press": int,  # 5 张 TWT 出完 @1 余张
        }
        """
        greater_action = game_state.get("greaterAction")
        if not greater_action:
            return None
        if not GUARD_TOOLS_OK:
            return None
        try:
            if get_action_type(greater_action) != ACTION_TYPE_THREE_WITH_TWO:
                return None
        except Exception:
            return None
        cards = _get_cards(greater_action)
        if len(cards) != 5:
            return None
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        greater_pos = game_state.get("greaterPos", -1)
        if greater_pos not in ((my_pos - 1) % 4, (my_pos + 1) % 4):
            return None
        enemies = ec.get("enemies", {})
        enemy_ctx = enemies.get(greater_pos, {})
        if not enemy_ctx:
            return None
        remaining = int(enemy_ctx.get("remaining", 0))
        if remaining < 5 or remaining > 6:
            return None
        hand_cards = list(game_state.get("handCards", []) or [])
        if len(hand_cards) < 10:
            return None
        teammate_pos = (my_pos + 2) % 4
        return {
            "enemy_pos": greater_pos,
            "enemy_ctx": enemy_ctx,
            "teammate_pos": teammate_pos,
            "remaining_after_press": max(remaining - 5, 0),
            "my_pos": my_pos,
            "hand_cards": hand_cards,
        }

    def _classify_finish_type(
        self, enemy_ctx: Dict[str, Any], game_state: Dict[str, Any],
    ) -> str:
        """
        推断 @1 余手（finish）的可能牌型。

        返回 "bomb_family"（含 SF/4+ 炸/王炸）、"straight"（普通顺子）、"twt"（杂牌 TWT）、
        "scatter"（5 张散）的概率元组近似，但本实现只返回最可能的一类。
        """
        remaining = int(enemy_ctx.get("remaining", 0))
        if remaining < 1:
            return "scatter"
        belief = (game_state.get("_belief") or {}).get("opp_bomb_risks") or {}
        enemy_pos = enemy_ctx.get("pos", -1)
        bomb_risk = float(belief.get(enemy_pos, 0.0)) if enemy_pos >= 0 else 0.0
        if bomb_risk >= 0.5:
            return "bomb_family"
        return "twt"

    def _has_six_joker_bomb(
        self, hand_cards: List[str],
    ) -> bool:
        """yf2 整手中是否含 6+ 张同点炸（JJJJJJ 6J 形态）。"""
        if not hand_cards:
            return False
        from collections import Counter
        ranks = Counter(get_card_rank(c) for c in hand_cards)
        return any(cnt >= 6 for cnt in ranks.values())

    def _has_teammate_bomb_family(
        self, game_state: Dict[str, Any], teammate_pos: int,
    ) -> bool:
        """队友（yf1）是否仍可能持有 bomb family。"""
        tracker = game_state.get("_memory_tracker")
        if tracker is None:
            return False  # 无记忆模块 → 不能验证，留作 GUA-134 跟进
        my_pos = game_state.get("myPos", 0)
        partner_pos = (my_pos + 2) % 4
        if teammate_pos != partner_pos:
            return False
        try:
            if self._seat_may_hold_four_of_kind(game_state, teammate_pos):
                return True
            if self._seat_may_hold_structured_five(game_state, teammate_pos):
                return True
        except Exception:
            return False
        return False

    def _has_teammate_bigger_twt(
        self, game_state: Dict[str, Any], teammate_pos: int,
        greater_action: List,
    ) -> bool:
        """
        队友（yf1）是否仍可能持有 ≥ greaterAction 点 的杂牌 TWT。

        用于 C1 拦截能力评估：若 yf1 有 ≥@1 finish 点的 TWT，可同型压回。
        """
        if not GUARD_TOOLS_OK:
            return False
        try:
            greater_rank = get_action_rank(greater_action)
        except Exception:
            return False
        if not greater_rank:
            return False
        cur_rank = str(game_state.get("curRank", "2"))
        return self._seat_may_hold_three_with_two_above(
            game_state, teammate_pos, greater_rank, cur_rank,
        )

    def _find_twt_min_point(
        self, action_list: List, cur_rank: str,
        hand_cards: Optional[List[str]] = None,
    ) -> Optional[Tuple[int, List]]:
        """从 action_list 中找杂牌 TWT（min 牌力优先；同 rank 时优先选 pair 不产生孤张的）。"""
        if not GUARD_TOOLS_OK:
            return None
        best: Optional[Tuple[int, List]] = None
        best_value = 10**9
        best_orphan = 1
        for i, a in enumerate(action_list):
            try:
                if get_action_type(a) != ACTION_TYPE_THREE_WITH_TWO:
                    continue
            except Exception:
                continue
            cards = _get_cards(a)
            if not cards:
                continue
            if _is_bomb_like_action(a):
                continue
            try:
                v = max(get_card_value(c, cur_rank) for c in cards)
            except Exception:
                continue

            orphan = 0
            if hand_cards and len(cards) == 5:
                rank_counts = Counter(get_card_rank(c) for c in cards)
                pair_rank = next((r for r, cnt in rank_counts.items() if cnt == 2), None)
                if pair_rank:
                    hc_count = sum(1 for c in hand_cards if get_card_rank(c) == pair_rank)
                    if hc_count > 2:
                        orphan = 1

            key = (v, orphan)
            if best is None or key < (best_value, best_orphan):
                best_value = v
                best_orphan = orphan
                best = (i, a)
        return best

    def _find_min_non_bomb_lead_action(
        self, action_list: List, cur_rank: str,
    ) -> Optional[Tuple[int, List]]:
        """GUA-150：从 action_list 中找最小非炸非 PASS 动作（用于 self_sprint 出牌夺权）。

        优先级：Single > Pair > Trips > ThreeWithTwo > Straight > ThreePair > TwoTrips
        （留炸弹给冲刺尾手）。同型取牌力最小。

        返回：(idx, action) 或 None。
        """
        if not GUARD_TOOLS_OK:
            return None
        # 型优先级（值越小越优先）
        type_priority = {
            ACTION_TYPE_SINGLE: 0,
            ACTION_TYPE_PAIR: 1,
            ACTION_TYPE_TRIPS: 2,
            ACTION_TYPE_THREE_WITH_TWO: 3,
            ACTION_TYPE_STRAIGHT: 4,
            ACTION_TYPE_THREE_PAIR: 5,
            ACTION_TYPE_TWO_TRIPS: 6,
        }
        best: Optional[Tuple[int, List]] = None
        best_key: Tuple[int, int] = (10**9, 10**9)
        for i, a in enumerate(action_list):
            try:
                atype = get_action_type(a)
            except Exception:
                continue
            if atype == ACTION_TYPE_PASS or atype == ACTION_TYPE_FREE:
                continue
            if _is_bomb_like_action(a):
                continue
            cards = _get_cards(a)
            if not cards:
                continue
            prio = type_priority.get(atype, 8)
            try:
                v = max(get_card_value(c, cur_rank) for c in cards)
            except Exception:
                continue
            key = (prio, v)
            if key < best_key:
                best_key = key
                best = (i, a)
        return best

    def _find_six_joker_bomb_in_actions(
        self, action_list: List, hand_cards: List[str],
    ) -> Optional[Tuple[int, List]]:
        """从 action_list 中找 yf2 的 6+ 张同点炸。"""
        if not GUARD_TOOLS_OK:
            return None
        from collections import Counter
        ranks = Counter(get_card_rank(c) for c in hand_cards)
        big_ranks = [r for r, cnt in ranks.items() if cnt >= 6]
        if not big_ranks:
            return None
        for i, a in enumerate(action_list):
            try:
                if get_action_type(a) != ACTION_TYPE_BOMB:
                    continue
            except Exception:
                continue
            cards = _get_cards(a)
            if len(cards) >= 6:
                return (i, a)
        return None

    def _find_pass_action(
        self, action_list: List,
    ) -> Optional[Tuple[int, List]]:
        """找 PASS 动作。"""
        for i, a in enumerate(action_list):
            if _get_declared_action_type(a) in (ACTION_TYPE_PASS, "PASS"):
                return (i, a)
            if GUARD_TOOLS_OK:
                try:
                    if get_action_type(a) == ACTION_TYPE_PASS:
                        return (i, a)
                except Exception:
                    pass
        return None

    def _c1_decision(
        self, game_state: Dict[str, Any], action_list: List,
        ec: Dict[str, Any], ctx: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-131 C1 决策：@1 出 5 张 TWT + 余 finish 是更大 TWT。

        yf2 圈 1 策略（与 GUA-125 §0.5.1 终版对齐）：
          - PASS 蓄力 → @1 圈 2 必出 finish → @1 头游（必败）
          - 出 bomb family（6J）→ @3 / yf1 反应可能打断；闭合路径依赖圈 2 领出
          - 跟 min TWT（777+22 / 888+22）→ 剩 2 手 = 冲刺能力，等 yf1 接力闭合

        闭合依赖：yf1 需用 bomb family 或 ≥@1 finish 点的 TWT 拦截 @1 finish。
        """
        if not ctx:
            return None
        teammate_pos = ctx["teammate_pos"]
        greater_action = game_state.get("greaterAction")
        hand_cards = ctx["hand_cards"]

        # 1. 校验 yf1 是否有 bomb family（最稳的拦截手段）
        yf1_has_bomb = self._has_teammate_bomb_family(game_state, teammate_pos)
        # 2. 校验 yf1 是否有 ≥@1 finish 点的 TWT（同型压回）
        yf1_has_bigger_twt = self._has_teammate_bigger_twt(
            game_state, teammate_pos, greater_action,
        )

        if yf1_has_bomb or yf1_has_bigger_twt:
            # 路径 A：跟 min TWT 形成冲刺能力（剩 2 手 = 6J + 单手）
            cur_rank = str(game_state.get("curRank", "2"))
            twt = self._find_twt_min_point(action_list, cur_rank, hand_cards=ctx["hand_cards"])
            if twt is not None:
                logger.info(
                    "GUA-131 C1: 跟 min TWT 形成冲刺能力（yf1_has_bomb=%s, yf1_has_bigger_twt=%s）",
                    yf1_has_bomb, yf1_has_bigger_twt,
                )
                return twt

        # 3. 兜底：yf1 不能接力，尝试 yf2 圈 1 出 6J 自闭合
        six_j = self._find_six_joker_bomb_in_actions(action_list, hand_cards)
        if six_j is not None:
            logger.info("GUA-131 C1 兜底: 出 6J 自闭合（yf1 不能接力）")
            return six_j

        # 3.5 退路：yf1 不能接力且无 6J → 若有普通炸则回退常规 Q1 流程
        has_bomb = any(
            isinstance(a, list) and _is_bomb_like_action(a)
            for a in action_list
        )
        if has_bomb:
            logger.info("GUA-131 C1 退路: 有普通炸可反压 @1，回退到常规 Q1 封锁流程")
            return None

        # 4. 路径 C：PASS 蓄力（必败，仅在无可行动作时兜底）
        pass_act = self._find_pass_action(action_list)
        if pass_act is not None:
            return pass_act
        return None

    def _c2_decision(
        self, game_state: Dict[str, Any], action_list: List,
        ec: Dict[str, Any], ctx: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-132 C2 决策：@1 finish = 同花顺 SF（bomb family）。

        牌理：@1 SF 可跨型压所有杂牌 → @1 一手清必头游，不可阻挡。
        yf 队策略：接受 @1 头游，yf2 圈 1 跟 min TWT 形成冲刺能力，
        圈 2 反抢 @3 拿第二名。
        """
        if not ctx:
            return None
        cur_rank = str(game_state.get("curRank", "2"))
        twt = self._find_twt_min_point(action_list, cur_rank, hand_cards=ctx["hand_cards"])
        if twt is None:
            # 无 TWT 可跟 → 出 6J 圈 2 反抢 @3
            six_j = self._find_six_joker_bomb_in_actions(
                action_list, ctx["hand_cards"],
            )
            if six_j is not None:
                logger.info("GUA-132 C2: 无 TWT，出 6J 反抢 @3")
                return six_j
            return self._find_pass_action(action_list)
        logger.info("GUA-132 C2: 跟 min TWT 形成冲刺能力，圈 2 反抢 @3")
        return twt

    def _c4_decision(
        self, game_state: Dict[str, Any], action_list: List,
        ec: Dict[str, Any], ctx: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-133 C4 决策：@1 finish = 5 星炸（bomb family）。

        牌理：6 张炸压 5 张炸（§4.1 bomb family 张数优势），@1 5 炸不能压 6J。
        yf 队策略：接受 @1 头游，yf2 圈 1 必出 JJJJJJ（6 张炸）自闭合拿第二名。
        """
        if not ctx:
            return None
        hand_cards = ctx["hand_cards"]
        six_j = self._find_six_joker_bomb_in_actions(action_list, hand_cards)
        if six_j is not None:
            logger.info("GUA-133 C4: 出 6J 反抢 @1 5 炸，自闭合拿第二名")
            return six_j
        # 兜底：无 6+ 张炸 → 跟 min TWT 形成冲刺能力，圈 2 反抢 @3
        cur_rank = str(game_state.get("curRank", "2"))
        twt = self._find_twt_min_point(action_list, cur_rank, hand_cards=hand_cards)
        if twt is not None:
            logger.info("GUA-133 C4 兜底: 无 6J，跟 min TWT 形成冲刺能力")
            return twt
        return self._find_pass_action(action_list)

    def _q1_c1_c2_c4_dispatch(
        self, game_state: Dict[str, Any], action_list: List,
        ec: Dict[str, Any], main_pos: int, main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        C1/C2/C4 决策分发器，挂在 _q1_block_enemy ④ 与 ⑤ 之间。

        仅在 C1/C2/C4 上下文触发；其他情形返回 None 让 Q1 走原流程。
        """
        # GUA-134 互斥：如果 C3/C5/C6 命中，让 _q1_c3_c5_c6_dispatch 处理
        if self._is_c3_c5_c6_scenario(game_state, ec) is not None:
            return None
        ctx = self._detect_c1_c2_c4_context(game_state, ec)
        if ctx is None:
            return None

        finish_kind = self._classify_finish_type(ctx["enemy_ctx"], game_state)
        ctx["finish_kind"] = finish_kind

        if finish_kind == "bomb_family":
            # 简化：bomb family 暂统一走 C4（5+ 炸）。C2(SF) 与 C4 闭合路径一致（接受 @1 头游 + 闭合 @3），
            # 区别仅在 yf2 自闭合的难度，不影响圈 1 决策。C2 精确判定留 GUA-134 跟进。
            return self._c4_decision(game_state, action_list, ec, ctx)

        # 推断 C1（finish 是更大 TWT）：与 c1/c2/c4 中其他 finish 区分
        # 简化：finish_kind == "twt" 且 ctx.remaining_after_press ≤ 5 → C1
        return self._c1_decision(game_state, action_list, ec, ctx)


    # ═══════════════════════════════════════════════════════
    #  GUA-134  C3 / C5 / C6 决策（高闭合率自闭合三手清空）
    #  关联：docs/guandan-brain/issues/GUA-134-completion.md
    #  决策真源：GUA-125 §0.5.2 C3/C5/C6 行
    # ═══════════════════════════════════════════════════════

    def _classify_c356_kind(
        self, enemy_ctx, game_state, greater_action,
    ) -> str:
        """
        C3/C5/C6 finish 牌型细分。

        返回:
          "straight" - C3（@1 finish = 顺子）
          "smaller_twt" - C5（@1 finish = 更小 TWT）
          "scatter" - C6（@1 finish = 5 张散）
          "unknown" - 探测不到
        """
        if not GUARD_TOOLS_OK:
            return "unknown"
        finish_atype = enemy_ctx.get("finish_type")
        if not finish_atype:
            remaining = int(enemy_ctx.get("remaining", 0)) - 5
            if remaining == 5:
                finish_atype = "Straight"
            elif remaining == 3:
                finish_atype = "ThreeWithTwo"
            elif 0 < remaining < 5:
                finish_atype = "Scatter"
        if not finish_atype:
            return "unknown"
        if finish_atype in ("Straight", "STRAIGHT"):
            return "straight"
        if finish_atype in ("ThreeWithTwo", "THREE_WITH_TWO"):
            fv = enemy_ctx.get("finish_rank_value", 0)
            if fv and fv < 7:
                return "smaller_twt"
            return "unknown"
        if finish_atype in ("Scatter", "SCATTER"):
            return "scatter"
        return "unknown"

    def _is_c3_c5_c6_scenario(self, game_state, ec):
        """
        C3/C5/C6 通用上下文探测。

        复用 C1/C2/C4 上下文探测，叠加 finish 牌型判定。
        返回 ctx dict 或 None
        """
        ctx = self._detect_c1_c2_c4_context(game_state, ec)
        if ctx is None:
            return None
        greater_action = game_state.get("greaterAction")
        kind = self._classify_c356_kind(ctx["enemy_ctx"], game_state, greater_action)
        if kind in ("straight", "smaller_twt", "scatter"):
            ctx["c356_kind"] = kind
            return ctx
        return None

    def _c3_c5_c6_decision(self, game_state, action_list, ec, ctx):
        """
        GUA-134 C3/C5/C6 决策：yf2 圈 1 必跟 min TWT 夺权。

        闭合路径（高闭合率 yf2 自闭合三手清空）：
          圈 1: yf2 跟 TWT → @1 PASS → @3 PASS → yf1 PASS
          圈 2: yf2 领出 6J → 三家 PASS
          圈 3: yf2 领出 777+888 三连对 → 三家 PASS
          圈 4: yf2 领出 22 对 → 三家 PASS → yf2 头游

        GUA-235：无更大 TWT 可跟时，若仍有 Bomb/SF 可压，回退常规 Q1（与 C1
        「有普通炸则 return None」对齐）。旧逻辑直接 PASS，导致敌剩 6 出 TWT
        时有五星炸/同花顺却过牌（match=6a7c7876）。
        """
        if not ctx:
            return None
        cur_rank = str(game_state.get("curRank", "2"))
        twt = self._find_twt_min_point(action_list, cur_rank, hand_cards=ctx["hand_cards"])
        if twt is not None:
            kind = ctx.get("c356_kind", "unknown")
            logger.info(
                "GUA-134 C3/C5/C6(%s): 跟 min TWT 夺权，三手清空闭合",
                kind,
            )
            return twt
        has_bomb_like = any(
            isinstance(a, list) and _is_bomb_like_action(a)
            for a in action_list
        )
        if has_bomb_like:
            logger.info(
                "GUA-134 C3/C5/C6(%s): 无更大 TWT，有 Bomb/SF 可压 → 回退常规 Q1",
                ctx.get("c356_kind", "unknown"),
            )
            return None
        pass_act = self._find_pass_action(action_list)
        if pass_act is not None:
            return pass_act
        return None

    def _q1_c3_c5_c6_dispatch(
        self, game_state, action_list, ec, main_pos, main_enemy,
    ):
        """
        C3/C5/C6 决策分发器，挂在 _q1_block_enemy ④ 与 ⑤ 之间，
        与 GUA-131/132/133 并联（C1/C2/C4 优先）。
        """
        ctx = self._is_c3_c5_c6_scenario(game_state, ec)
        if ctx is None:
            return None
        return self._c3_c5_c6_decision(game_state, action_list, ec, ctx)

    # ═══════════════════════════════════════════════════════
    #  GUA-135  双进优先级判定（C2/C4 接受 @1 头游 + C3/C5/C6 闭合后队整体策略）
    #  关联：docs/guandan-brain/issues/GUA-135-completion.md
    #  决策真源：GUA-125 §0.5.2 + §0.6
    # ═══════════════════════════════════════════════════════

    def _has_sprint_capability(
        self, hand_cards: List[str],
    ) -> bool:
        """
        GUA-135：判定手牌是否具备冲刺能力（炸 + 单手结构，可多层炸剥）。

        冲刺能力 ≠ sprint 真闭环（真闭环需出完后无人反制）。
        这里只判定结构上具备冲刺条件：
          - 至少一手 bomb family（≥4 同点）
          - 剥掉炸后剩余恰好一手整牌（单/对/三/TWT/顺/钢板/三连对/再炸…）
          - 双炸+结构：剥第一炸后若仍有炸，递归判定剩余是否仍冲刺
        """
        return self._hand_has_sprint_capability(list(hand_cards or []))

    @staticmethod
    def _remainder_is_one_structure(cards: List[str]) -> bool:
        """剩余牌是否可视为一手整牌型（非 6 张散单）。"""
        n = len(cards)
        if n <= 0:
            return False
        if n <= 5:
            return True
        if n != 6:
            return False
        from collections import Counter
        ranks = Counter(get_card_rank(c) for c in cards)
        counts = sorted(ranks.values())
        # 6 星炸：6 张同 rank
        if counts == [6]:
            return True
        # GUA-287: 钢板(3+3)/三连对(2+2+2) 必须 rank 连续才是整手牌型。
        # 原实现仅比 counts，把「对6+对T+王对」等非连续 rank 组合误判为三连对一手，
        # 导致 botzone 6a927cbd 14:31:41 V8 手牌剥双炸后剩 6 张散对被判冲刺 → 领出甩炸。
        if GUARD_TOOLS_OK:
            if counts == [3, 3]:
                return EndgameDecider._find_two_trips_cards(cards) is not None
            if counts == [2, 2, 2]:
                return EndgameDecider._find_three_pair_cards(cards) is not None
        return False

    @staticmethod
    def _is_single_high_recovery_hand(cards: List[str]) -> bool:
        """
        GUA-241：整手是否恰好一手「难被压」的冲刺尾牌——
        5 张 8+ 顺子 / 6 张钢板(TwoTrips) / 6 张三连对(ThreePair)。
        """
        cards = list(cards or [])
        if not cards or not GUARD_TOOLS_OK:
            return False
        n = len(cards)
        if n == 5:
            return EndgameDecider._find_high_straight_cards(cards) is not None
        if n == 6:
            return (
                EndgameDecider._find_two_trips_cards(cards) is not None
                or EndgameDecider._find_three_pair_cards(cards) is not None
            )
        return False

    @staticmethod
    def _hand_has_sprint_capability(hand_cards: List[str], *, _depth: int = 0) -> bool:
        """纯函数：手牌是否 炸(+炸*)+单手结构，或整手一手难被压尾牌(GUA-241)。"""
        if not hand_cards or len(hand_cards) < 5 or _depth > 4:
            return False
        from collections import Counter
        ranks = Counter(get_card_rank(c) for c in hand_cards)
        bomb_rank, max_count = max(ranks.items(), key=lambda kv: kv[1])
        if max_count < 4:
            # GUA-241：无炸，但整手恰好一手难被压尾牌（5 张 8+顺 / 6 张钢板或三连对）
            return EndgameDecider._is_single_high_recovery_hand(hand_cards)

        left = []
        removed = 0
        for c in hand_cards:
            if get_card_rank(c) == bomb_rank and removed < max_count:
                removed += 1
                continue
            left.append(c)

        if not left:
            return False

        left_ranks = Counter(get_card_rank(c) for c in left)
        if any(c >= 4 for c in left_ranks.values()):
            return EndgameDecider._hand_has_sprint_capability(left, _depth=_depth + 1)
        return EndgameDecider._remainder_is_one_structure(left)

    def _estimate_player_remaining(
        self, position: int, ec: Dict[str, Any], game_state: Dict[str, Any],
    ) -> int:
        """
        GUA-135：估算某玩家当前剩牌数（用于双进优先级判定）。

        来源优先级：
          1. 记忆模块（_memory_tracker.get_hand_count）— 含 0（已出完）
          2. 敌方平台报牌（enemy_ctx.remaining）
          3. 队友上下文（ec["teammate"].remaining）
          4. numofplayers[position]
          5. 默认 -1（未知；禁止把未知当成「已头游=0」）

        返回：剩牌数；未知为 -1。
        """
        tracker = game_state.get("_memory_tracker")
        if tracker is not None:
            try:
                # 显式 hand_counts（含 0=已出完）优先；缺席不得把默认 0 当已头游
                hand_counts = getattr(tracker, "hand_counts", None)
                if isinstance(hand_counts, dict) and position in hand_counts:
                    return int(hand_counts[position])
                count = tracker.get_hand_count(position)
                if isinstance(count, int) and count > 0:
                    return count
            except Exception:
                pass
        enemies = ec.get("enemies", {}) or {}
        enemy_ctx = enemies.get(position, {}) or {}
        remaining = enemy_ctx.get("remaining")
        if isinstance(remaining, int) and remaining >= 0:
            return remaining
        mate = ec.get("teammate", {}) or {}
        if mate.get("remaining") is not None:
            my_pos = ec.get("my_pos", game_state.get("myPos", 0))
            if position == (my_pos + 2) % 4:
                mate_rem = mate.get("remaining")
                if isinstance(mate_rem, int) and mate_rem >= 0:
                    return mate_rem
        numofplayers = (
            ec.get("numofplayers")
            or game_state.get("numofplayers")
            or []
        )
        if (
            isinstance(numofplayers, (list, tuple))
            and 0 <= position < len(numofplayers)
        ):
            n = numofplayers[position]
            if isinstance(n, int) and n >= 0:
                return n
        return -1

    def _is_double_second_priority_scenario(
        self, game_state: Dict[str, Any], ec: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        GUA-135：探测当前席是否落在「双进优先级判定」场景。

        座位语义（相对 myPos，禁止写死 yf1/yf2）：
          - self = 本家
          - teammate = myPos+2
          - enemy = 当前控牌敌方（greaterPos）

        触发条件（任一）：
          - 敌 finish 是 bomb family（C2 SF / C4 5 炸）→ 敌必头游
          - self / teammate 整手 ≤ 6 张 → 双冲刺赛道
          - 队友已出完（remaining==0）且曾判冲刺/炸族 → teammate_sprint

        返回 ctx dict 或 None：{
          "trigger": "C2" | "C4" | "self_sprint" | "teammate_sprint" | "sprint_race",
          "self_remaining" / "teammate_remaining" / "enemy_remaining",
          "self_sprint" / "teammate_sprint" / "enemy_sprint",
          ...
        }
        """
        # GUA-135 独立探测（不依赖 _detect_c1_c2_c4_context 的 remaining ∈ {5,6} 限制）
        if not GUARD_TOOLS_OK:
            return None
        greater_action = game_state.get("greaterAction")
        if not greater_action:
            return None
        try:
            if get_action_type(greater_action) != ACTION_TYPE_THREE_WITH_TWO:
                return None
        except Exception:
            return None
        cards = _get_cards(greater_action)
        if len(cards) != 5:
            return None
        my_pos = ec.get("my_pos", game_state.get("myPos", 0))
        greater_pos = game_state.get("greaterPos", -1)
        if greater_pos not in ((my_pos - 1) % 4, (my_pos + 1) % 4):
            return None
        enemies = ec.get("enemies", {}) or {}
        enemy_ctx = enemies.get(greater_pos, {}) or {}
        if not enemy_ctx:
            return None
        hand_cards = list(game_state.get("handCards", []) or [])
        if len(hand_cards) < 5:
            return None
        teammate_pos = (my_pos + 2) % 4
        # 构造最小 ctx 供后续判定使用
        ctx = {
            "enemy_pos": greater_pos,
            "enemy_ctx": enemy_ctx,
            "teammate_pos": teammate_pos,
            "my_pos": my_pos,
            "hand_cards": hand_cards,
        }
        enemy_pos = greater_pos

        # 估算各方剩牌（self 用本家手牌长度）
        self_remaining = len(hand_cards)
        teammate_remaining = self._estimate_player_remaining(
            teammate_pos, ec, game_state,
        )
        enemy_remaining = self._estimate_player_remaining(
            enemy_pos, ec, game_state,
        )

        # 判定冲刺能力（剩 2 手 = 炸弹 + 单手）
        self_sprint = self._has_sprint_capability(hand_cards)

        # GUA-136：队友冲刺能力（推断手牌）
        teammate_sprint = self._estimate_player_sprint_capability(
            teammate_pos, game_state,
        )
        # 兜底：记牌认为队友可能有炸族（仅作冲刺信号，不得单独当「已头游」）
        if not teammate_sprint:
            try:
                teammate_sprint = self._has_teammate_bomb_family(
                    game_state, teammate_pos,
                )
            except Exception:
                pass

        # GUA-136：敌方冲刺能力
        enemy_sprint = self._estimate_player_sprint_capability(
            enemy_pos, game_state,
        )

        # 直接读 enemy_ctx.finish_type（不依赖 _classify_finish_type，因其看 belief.bomb_risk）
        _ft_raw = ctx["enemy_ctx"].get("finish_type")
        if _ft_raw in ("StraightFlush", "STRAIGHT_FLUSH", "Bomb", "BOMB", "JokerBomb"):
            finish_kind = "bomb_family"
        elif _ft_raw in ("Straight", "STRAIGHT"):
            finish_kind = "straight"
        elif _ft_raw in ("ThreeWithTwo", "THREE_WITH_TWO"):
            finish_kind = "twt"
        elif _ft_raw in ("Scatter", "SCATTER"):
            finish_kind = "scatter"
        else:
            finish_kind = self._classify_finish_type(ctx["enemy_ctx"], game_state)

        # 触发判定
        trigger = None
        if finish_kind == "bomb_family":
            # C2 / C4：敌 finish 是 bomb family → 敌必头游 → 我方抢第二
            finish_atype = ctx["enemy_ctx"].get("finish_type", "")
            if "StraightFlush" in str(finish_atype) or "SF" in str(finish_atype):
                trigger = "C2"
            else:
                trigger = "C4"
        elif teammate_sprint and teammate_remaining == 0:
            # 仅队友真出完（remaining==0）才走「已头游让道」
            trigger = "teammate_sprint"
        elif (
            self_remaining <= 6
            and 0 <= teammate_remaining <= 6
            and self_remaining >= 5
        ):
            # 双冲刺赛道（双方都 ≤ 6 张；teammate 未知 -1 不进）
            trigger = "sprint_race"
        elif (finish_kind in ("straight", "twt", "scatter")) and (
            self_remaining >= 10 or self_sprint
        ):
            # 本家自闭合头游路径 → 队友抢第二
            trigger = "self_sprint"

        if trigger is None:
            return None

        return {
            "trigger": trigger,
            "enemy_pos": enemy_pos,
            "teammate_pos": teammate_pos,
            "my_pos": my_pos,
            "hand_cards": hand_cards,
            "self_remaining": self_remaining,
            "teammate_remaining": teammate_remaining,
            "enemy_remaining": enemy_remaining,
            "self_sprint": self_sprint,
            "teammate_sprint": teammate_sprint,
            "enemy_sprint": enemy_sprint,
            # 兼容旧测试字段名（只读别名）
            "yf2_remaining": self_remaining,
            "yf1_remaining": teammate_remaining,
            "@3_remaining": enemy_remaining,
            "yf2_sprint": self_sprint,
            "yf1_sprint": teammate_sprint,
            "@3_sprint": enemy_sprint,
            "finish_kind": finish_kind,
            "ctx": ctx,
        }

    def _q1_double_second_priority(
        self, game_state: Dict[str, Any], action_list: List,
        ec: Dict[str, Any], main_pos: int, main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-135：双进优先级判定（相对 myPos：self / teammate / enemy）。

        判定逻辑：
          1. self 是否已有冲刺能力？
             - 是 → 本家自闭合拿第二（C2/C4/self_sprint）
          2. teammate 冲刺 / 炸族？
             - 仅 teammate_remaining==0（真已头游）→ 本家让道 PASS
          3. enemy 冲刺？
             - 是 → 本家拦截抢第二
             - 否 → PASS 等待更优时机

        返回：最优动作 (idx, action) 或 None
        """
        ctx = self._is_double_second_priority_scenario(game_state, ec)
        if ctx is None:
            return None

        trigger = ctx["trigger"]
        self_sprint = ctx["self_sprint"]
        teammate_sprint = ctx["teammate_sprint"]
        enemy_sprint = ctx["enemy_sprint"]
        teammate_remaining = ctx["teammate_remaining"]
        hand_cards = ctx["hand_cards"]
        cur_rank = str(game_state.get("curRank", "2"))

        # 情形 1：C2/C4（敌必头游）→ 队整体抢第二（§4.1 三步判定）
        if trigger in ("C2", "C4"):
            teammate_pos = ctx.get("teammate_pos", (ec.get("my_pos", 0) + 2) % 4)
            if self_sprint:
                # ① 本家已有冲刺能力 → 圈 1 PASS，圈 2/3 自闭合拿第二
                logger.info(
                    "GUA-135 %s: enemy 必头游，self 自闭合拿第二（冲刺能力成立）",
                    trigger,
                )
                pass_act = self._find_pass_action(action_list)
                if pass_act is not None:
                    return pass_act
            else:
                # ② 队友能否/应否抢第二
                teammate_bomb_intercept = False
                try:
                    teammate_bomb_intercept = self._has_teammate_bomb_family(
                        game_state, teammate_pos,
                    )
                except Exception:
                    pass
                if teammate_bomb_intercept:
                    logger.info(
                        "GUA-135 %s: teammate bomb family 拦截，self 必第三，PASS",
                        trigger,
                    )
                    pass_act = self._find_pass_action(action_list)
                    if pass_act is not None:
                        return pass_act
                if teammate_sprint:
                    logger.info(
                        "GUA-135 %s: teammate 有冲刺能力，self PASS 让 teammate 拿第二",
                        trigger,
                    )
                    pass_act = self._find_pass_action(action_list)
                    if pass_act is not None:
                        return pass_act
                # ③ 敌冲刺 → 拦截抢第二，否则 PASS 等闭合
                if enemy_sprint:
                    logger.info(
                        "GUA-135 %s: enemy 有冲刺能力，self 拦截抢第二",
                        trigger,
                    )
                    six_j = self._find_six_joker_bomb_in_actions(
                        action_list, hand_cards,
                    )
                    if six_j is not None:
                        return six_j
                    twt = self._find_twt_min_point(action_list, cur_rank, hand_cards=hand_cards)
                    if twt is not None:
                        return twt
                logger.info(
                    "GUA-135 %s: enemy 必头游且无冲刺信号，self PASS 等闭合",
                    trigger,
                )
                pass_act = self._find_pass_action(action_list)
                if pass_act is not None:
                    return pass_act

        # 情形 2：self_sprint（本家自闭合路径）→ 队友抢第二
        if trigger == "self_sprint":
            if teammate_sprint:
                # GUA-150：比较 self 与 teammate 的冲刺路径长度（num_rounds）
                # - self_hands ≤ teammate_hands → self 出牌夺权（不 PASS）
                # - self_hands > teammate_hands 或 teammate 未知 → PASS 让道（保持原行为）
                my_pos = ec.get("my_pos", 0)
                teammate_pos = ctx.get("teammate_pos", (my_pos + 2) % 4)
                self_hands = self._estimate_self_num_rounds(game_state)
                teammate_hands = self._estimate_player_num_rounds(teammate_pos, game_state)

                # GUA-150 可靠性检查：MemoryTracker 推断的牌数是否覆盖 teammate 大部分实际剩牌
                _reliable = self._check_teammate_estimate_reliable(teammate_pos, game_state)

                if _reliable and self_hands > 0 and teammate_hands > 0 and self_hands <= teammate_hands:
                    logger.info(
                        "GUA-150 self_sprint_priority: self_hands=%d ≤ teammate_hands=%d → self 出牌夺权",
                        self_hands, teammate_hands,
                    )
                    # GUA-278：下家敌危急时优先最廉炸，勿先拆核 TWT
                    bomb_alt = self._gua278_critical_lower_enemy_bomb(
                        game_state, action_list, ec,
                    )
                    if bomb_alt is not None:
                        return bomb_alt
                    # 优先 TWT（与原 else 分支一致），其次最小非炸非 PASS 动作
                    twt = self._find_twt_min_point(action_list, cur_rank, hand_cards=hand_cards)
                    if twt is not None:
                        logger.info("GUA-150 self_sprint_priority: 选 min TWT 夺权")
                        return twt
                    lead = self._find_min_non_bomb_lead_action(action_list, cur_rank)
                    if lead is not None:
                        logger.info(
                            "GUA-150 self_sprint_priority: 选 min 非炸非 PASS 动作夺权 idx=%d",
                            lead[0],
                        )
                        return lead
                    logger.info(
                        "GUA-150 self_sprint_priority: 无 TWT/非炸候选，仍 PASS 让道",
                    )
                    pass_act = self._find_pass_action(action_list)
                    if pass_act is not None:
                        return pass_act
                elif _reliable:
                    logger.info(
                        "GUA-150 self_sprint_priority: self_hands=%d > teammate_hands=%d（或可靠未知）→ self PASS 让 teammate 拿第二",
                        self_hands, teammate_hands,
                    )
                    pass_act = self._find_pass_action(action_list)
                    if pass_act is not None:
                        return pass_act
                else:
                    logger.info(
                        "GUA-150 self_sprint_priority: teammate_hands=%d 推断不可靠（inferred <%d）→ 降级为出牌夺权",
                        teammate_hands, self._min_reliable_inferred(teammate_pos, game_state),
                    )

            # GUA-278：下家敌≤2 + 有炸 → 最廉炸截断（禁先 min TWT 再拆核 PASS）
            bomb_alt = self._gua278_critical_lower_enemy_bomb(
                game_state, action_list, ec,
            )
            if bomb_alt is not None:
                return bomb_alt
            # 当 teammate_sprint=False 或 GUA-150 估计不可靠时：跟 min TWT 夺权
            twt = self._find_twt_min_point(action_list, cur_rank, hand_cards=hand_cards)
            if twt is not None:
                logger.info(
                    "GUA-135 self_sprint: 跟 min TWT 夺权",
                )
                return twt

        # 情形 3：teammate_sprint — 仅队友真已出完才让道 PASS
        if trigger == "teammate_sprint":
            if teammate_remaining != 0:
                logger.info(
                    "GUA-135 teammate_sprint: teammate remaining=%s ≠0，非已头游 → 不强制 PASS",
                    teammate_remaining,
                )
                return None
            logger.info(
                "GUA-135 teammate_sprint: teammate remaining=0（已头游），self 让道 PASS",
            )
            pass_act = self._find_pass_action(action_list)
            if pass_act is not None:
                return pass_act

        # 情形 4：sprint_race（双方都 ≤ 6 张）→ 判定谁拿第二
        if trigger == "sprint_race":
            if self_sprint and not teammate_sprint:
                logger.info(
                    "GUA-135 sprint_race: self 有冲刺能力，self 拿第二",
                )
                twt = self._find_twt_min_point(action_list, cur_rank, hand_cards=hand_cards)
                if twt is not None:
                    return twt
            elif teammate_sprint and not self_sprint:
                logger.info(
                    "GUA-135 sprint_race: teammate 有冲刺能力，self PASS 让 teammate 拿第二",
                )
                pass_act = self._find_pass_action(action_list)
                if pass_act is not None:
                    return pass_act

        return None

    def _q1_double_second_priority_dispatch(
        self, game_state: Dict[str, Any], action_list: List,
        ec: Dict[str, Any], main_pos: int, main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-135 双进优先级判定分发器。

        挂在 _q1_block_enemy ④.5b (GUA-134) 之后、⑤ _q1_enemy_five_single_special 之前。
        """
        return self._q1_double_second_priority(
            game_state, action_list, ec, main_pos, main_enemy,
        )

    # ═══════════════════════════════════════════════════════
    #  GUA-136  玩家剩牌估算增强（记忆模块 + 圈序出牌历史）
    #  关联：docs/guandan-brain/issues/GUA-136-completion.md
    #  决策真源：GUA-135 §4.1 数据源升级
    # ═══════════════════════════════════════════════════════

    def _estimate_player_hand_cards(
        self, position: int, game_state: Dict[str, Any],
    ) -> List[str]:
        """
        GUA-136：推断某玩家当前手牌（具体牌列表）。

        实现：遍历 MemoryTracker.card_state 找 position 标记的牌种，展开为实际牌列表。
        无记忆模块 → 返回 []。

        返回：手牌列表（具体牌），可能为空
        """
        tracker = game_state.get("_memory_tracker")
        if tracker is None or not hasattr(tracker, "card_state"):
            return []
        try:
            result: List[str] = []
            for ct, copies in tracker.card_state.items():
                own_count = sum(1 for c in copies if c == position)
                for _ in range(own_count):
                    result.append(ct)
            return result
        except Exception:
            return []

    def _check_teammate_estimate_reliable(
        self, teammate_pos: int, game_state: Dict[str, Any],
    ) -> bool:
        """
        GUA-150：队友手数估计是否可靠。

        MemoryTracker 禁用排除法时，对 teammate 的手牌几乎无知（只有王归属推断），
        此时 _estimate_player_num_rounds 结果不可靠，不应作为让道依据。

        可靠判定：MemoryTracker 推断的牌数 ≥ teammate 实际剩牌 × 50%。
        否则返回 False（不可靠 → 降级为出牌夺权）。
        """
        inferred = self._estimate_player_hand_cards(teammate_pos, game_state)
        if not inferred:
            return False
        numofplayers = game_state.get("numofplayers", [])
        if not isinstance(numofplayers, (list, tuple)) or not (0 <= teammate_pos < len(numofplayers)):
            return True
        actual_remaining = numofplayers[teammate_pos]
        if isinstance(actual_remaining, int) and actual_remaining > 0:
            if len(inferred) < actual_remaining * 0.5:
                return False
        return True

    def _min_reliable_inferred(
        self, teammate_pos: int, game_state: Dict[str, Any],
    ) -> int:
        """GUA-150：日志辅助——可靠性阈值下限."""
        numofplayers = game_state.get("numofplayers", [])
        if isinstance(numofplayers, (list, tuple)) and 0 <= teammate_pos < len(numofplayers):
            rem = numofplayers[teammate_pos]
            if isinstance(rem, int) and rem > 0:
                return int(rem * 0.5)
        return 0

    def _estimate_player_sprint_capability(
        self, position: int, game_state: Dict[str, Any],
    ) -> bool:
        """
        GUA-136：判定某玩家（yf1 或 @3）是否具备冲刺能力。

        冲刺能力 = 剩 2 手 = 炸弹 + 单手（参见 GUA-135 §0）

        实现：推断手牌 → 应用 _has_sprint_capability 判定。
        无推断 → 保守 False。

        返回：True / False
        """
        hand_cards = self._estimate_player_hand_cards(position, game_state)
        if not hand_cards:
            return False
        return self._has_sprint_capability(hand_cards)

    # ═══════════════════════════════════════════════════════
    #  GUA-137  玩家整手结构推断增强（grouping_engine）
    #  关联：docs/guandan-brain/issues/GUA-137-completion.md
    #  决策真源：GUA-136 sprint 判定升级
    # ═══════════════════════════════════════════════════════

    def _estimate_player_grouping_plan(
        self, position: int, game_state: Dict[str, Any],
    ) -> Optional[Any]:
        """
        GUA-137 推断 yf1/@3 整手结构（GroupingPlan） + GUA-138 LRU 缓存。

        实现：
          - Layer 1：MemoryTracker.card_state → 手牌列表 → enumerate_groupings（缓存）
          - Layer 2：enemy_ctx.hand_types 构造虚拟 plan（仅 singles）
          - Layer 3：返回 None

        GUA-138 性能优化：使用 _GroupingPlanCache LRU 缓存避免重复计算。
        缓存键：(tuple(sorted(hand)), cur_rank)；容量 64；深拷贝避免污染。

        返回：GroupingPlan 实例或 None
        """
        # GUA-138：lazy init LRU 缓存（每个 EndgameDecider 实例独立）
        if not hasattr(self, "_grouping_plan_cache"):
            self._grouping_plan_cache = _GroupingPlanCache(max_size=64)
        # GUA-138：cur_rank 变化 → 失效整缓存（GUA-138 §3.3）
        prev_cur_rank = getattr(self, "_last_cur_rank", None)
        cur_rank_now = str(game_state.get("curRank", "2"))
        if prev_cur_rank is not None and prev_cur_rank != cur_rank_now:
            self._grouping_plan_cache.invalidate(cur_rank=prev_cur_rank)
        self._last_cur_rank = cur_rank_now

        # Layer 1: MemoryTracker → 手牌 → 缓存命中/计算
        hand_cards = self._estimate_player_hand_cards(position, game_state)
        if hand_cards:
            try:
                from src.v.nn.features.grouping_engine import enumerate_groupings
                def _compute_fn(h, r):
                    best_plan, _ = enumerate_groupings(h, r)
                    return best_plan
                return self._grouping_plan_cache.get_or_compute(
                    hand_cards, cur_rank_now, _compute_fn,
                )
            except Exception:
                pass
        # Layer 2: enemy_ctx.hand_types 兜底
        ec = game_state.get("_endgame_context") or {}
        enemies = ec.get("enemies", {}) or {}
        enemy_ctx = enemies.get(position, {}) or {}
        hand_types = enemy_ctx.get("hand_types", [])
        if hand_types:
            try:
                from src.v.nn.features.grouping_engine import GroupingPlan
                return GroupingPlan(
                    singles=list(hand_types),
                    cur_rank=str(game_state.get("curRank", "2")),
                )
            except Exception:
                pass
        return None

    def _estimate_player_num_rounds(
        self, position: int, game_state: Dict[str, Any],
    ) -> int:
        """
        GUA-137：推断 yf1/@3 出完所有牌需要几圈（num_rounds）。

        返回：圈数（0 表示未知）
        """
        plan = self._estimate_player_grouping_plan(position, game_state)
        if plan is None:
            return 0
        try:
            return plan.num_rounds()
        except Exception:
            return 0

    def _estimate_self_num_rounds(
        self, game_state: Dict[str, Any],
    ) -> int:
        """
        GUA-150：计算 self 最少几手能清完（基于实际 hand_cards，不依赖 MemoryTracker）。

        用于 self_sprint_priority 比较：self_hands ≤ teammate_hands → self 出牌夺权。

        返回：手数（0 表示未知/计算失败）
        """
        hand_cards = list(game_state.get("handCards") or [])
        if not hand_cards:
            return 0
        cur_rank = str(game_state.get("curRank", "2"))
        try:
            from src.v.nn.features.grouping_engine import enumerate_groupings
            best_plan, _ = enumerate_groupings(hand_cards, cur_rank)
            if best_plan is None:
                return 0
            return best_plan.num_rounds()
        except Exception:
            return 0

    def _estimate_player_sprint_capability_v2(
        self, position: int, game_state: Dict[str, Any],
    ) -> bool:
        """
        GUA-137：冲刺能力精确判定（基于整手结构）。

        算法：
          - 推断整手 plan → num_rounds + has_bomb_family
          - 冲刺能力 = num_rounds ≤ 2 AND has_bomb_family

        返回：True / False
        """
        plan = self._estimate_player_grouping_plan(position, game_state)
        if plan is None:
            return False
        try:
            num_rounds = plan.num_rounds()
        except Exception:
            return False
        has_bomb_family = (
            len(getattr(plan, "bombs", [])) > 0
            or len(getattr(plan, "straight_flushes", [])) > 0
        )
        return num_rounds <= 2 and has_bomb_family

# ═══════════════════════════════════════════════════════
#  GUA-138  grouping_engine LRU 缓存（性能优化）
#  关联：docs/guandan-brain/issues/GUA-138-completion.md
#  决策真源：GUA-137 §1 性能瓶颈
# ═══════════════════════════════════════════════════════


class _GroupingPlanCache:
    """GUA-138：GroupingPlan LRU 缓存。

    键：tuple(sorted(hand_cards)) + (cur_rank,)
    值：GroupingPlan 深拷贝（避免下游修改污染）
    容量：默认 64（LRU 淘汰）
    """

    def __init__(self, max_size: int = 64):
        from collections import OrderedDict
        self._cache: "OrderedDict" = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(hand_cards, cur_rank):
        return (tuple(sorted(hand_cards)), cur_rank)

    def get_or_compute(self, hand_cards, cur_rank, compute_fn):
        """获取缓存或计算并缓存。

        Args:
            hand_cards: 手牌列表
            cur_rank: 当前级牌
            compute_fn: (hand_cards, cur_rank) -> GroupingPlan

        Returns:
            GroupingPlan 深拷贝（缓存命中时）或新计算结果（cache miss）
        """
        key = self._make_key(hand_cards, cur_rank)
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hits += 1
            return self._deepcopy_plan(self._cache[key])
        self._misses += 1
        plan = compute_fn(hand_cards, cur_rank)
        if plan is not None:
            self._cache[key] = plan
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
        return plan

    def invalidate(self, hand_cards=None, cur_rank=None):
        """失效缓存（全部或特定 hand/cur_rank）。

        Args:
            hand_cards: 失效特定手牌；None 时不按 hand 过滤
            cur_rank: 失效特定 cur_rank；None 时不按 cur_rank 过滤
        """
        if hand_cards is None and cur_rank is None:
            self._cache.clear()
            return
        keys_to_remove = []
        if hand_cards is not None:
            sorted_hand = tuple(sorted(hand_cards))
            keys_to_remove.extend(k for k in self._cache if k[0] == sorted_hand)
        if cur_rank is not None:
            keys_to_remove.extend(k for k in self._cache if k[1] == cur_rank)
        for k in set(keys_to_remove):
            self._cache.pop(k, None)

    def stats(self):
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
            "max_size": self._max_size,
        }

    def clear(self):
        self._cache.clear()

    @staticmethod
    def _deepcopy_plan(plan):
        """深拷贝 GroupingPlan（避免下游修改污染缓存）。"""
        import copy
        try:
            return copy.deepcopy(plan)
        except Exception:
            return plan

