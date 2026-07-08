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


def _has_recapture(action: List, hand_cards: List[str]) -> bool:
    """
    同牌型是否有更高段回收（保留出牌权）。

    例：出单 Q，手中有 K/A → 有回收（K/A 可以压制对手并回收出牌权）。
    """
    atype = get_action_type(action) if GUARD_TOOLS_OK else ACTION_TYPE_FREE
    cards = _get_cards(action)
    if not cards:
        return False

    cur_rank = "2"  # 调用方应提供
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


def _sort_q1_prefer_non_wild_level_singles(items: List, cur_rank: str) -> List:
    """
    GUA-122：压单时若同级存在非逢人配级牌，不得裸出 H{curRank}。
    """
    if not items or not cur_rank or not _has_non_wild_level_single_option(items, cur_rank):
        return items

    def _wild_penalty(item):
        act = item[1] if isinstance(item, tuple) and len(item) == 2 else item
        return 1 if _single_action_uses_wild_level_card(act, cur_rank) else 0

    return sorted(items, key=_wild_penalty)


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
    """在 action_list 中查找一手清牌候选（首个匹配）。"""
    hand_counter = _hand_counter_from_state(game_state)
    if not hand_counter:
        return None
    for i, act in enumerate(action_list):
        if _is_finish_now_action(act, hand_counter):
            return i, act
    return None


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
    actions: List, hand_cards: List[str],
) -> List:
    """回收优先 → 张数多优先（Q1/Q2 通用排序）
    
    actions 可以是 (idx, act) 元组列表或纯 act 列表。
    """
    def _sort_key(item):
        act = item[1] if isinstance(item, tuple) and len(item) == 2 else item
        return (
            not _has_recapture(act, hand_cards),  # 有回收排前面
            -len(_get_cards(act)),                  # 张数多优先
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

    assist_actions = _sort_by_recapture_first(assist_actions, hand_cards)
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
    if enemy_rem is None or enemy_rem > 5 or enemy_rem < 1:
        return False
    return True


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


def _sort_q1_block_candidates(
    actions: List, hand_cards: List[str], game_state: Dict[str, Any],
) -> List:
    """Q1 候选排序：回收优先 → 级牌单张少耗逢人配 → bomb-like 最小足够成本。"""
    ordered = _sort_by_recapture_first(actions, hand_cards)
    if not ordered or not GUARD_TOOLS_OK:
        return ordered

    cur_rank = str(game_state.get("curRank", "2"))
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

    def _bomb_min_sufficient_key(item):
        act = item[1] if isinstance(item, tuple) and len(item) == 2 else item
        cards = _get_cards(act)
        wild_count = sum(1 for c in cards if isinstance(c, str) and c.startswith("H") and c[1:] == cur_rank)
        split_orphan = _bomb_splits_pure_rank_leaving_orphan(item, bomb_items, hand_cards)
        return (
            1 if split_orphan else 0,
            len(cards),
            wild_count,
            _max_card_value(act, cur_rank),
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

        # ── Q0: 自己冲刺（最高优先级）────
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
        is_my_turn = (cur_pos == my_pos)
        enemies = ec.get("enemies", {})

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

        if not bombs:
            # 没有炸弹 → 按非炸弹最佳出牌
            if non_bombs:
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
                return self._select_best_bomb(bombs, action_list)
            else:
                # 先整后炸：出最大整牌
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
                if bombs:
                    return self._select_best_bomb(bombs, action_list)
                return None
            else:
                # 不急于炸，让对手出
                if non_bombs:
                    return self._select_best_index(non_bombs, action_list, game_state)
                return None  # 只有炸，但没有合适时机

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

        finish_now = self._q1_finish_now_candidate(game_state, action_list)
        if finish_now is not None:
            return finish_now

        # ① 找最危险敌人（主目标）
        main_pos, main_enemy = self._select_main_enemy(enemies, my_pos)

        gua115_pass = self._q1_gua115_fire_no_bomb_four_pass(
            game_state, action_list, ec, main_pos, main_enemy,
        )
        if gua115_pass is not None:
            return gua115_pass

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

        enemy_one_lead = self._q1_enemy_critical_lead_special(
            game_state, non_banned_candidates, ec, main_pos, main_enemy,
        )
        if enemy_one_lead is not None:
            return enemy_one_lead

        non_banned_candidates = self._prune_q1_risky_same_type_lane_candidates(
            game_state, non_banned_candidates, ec, main_pos, main_enemy,
        )

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
        """GUA-115 例外：不炸必输且自方两手整牌冲刺时仍允许用炸。"""
        try:
            from .endgame_preprocessor import EndgamePreprocessor as EP
        except ImportError:
            from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor as EP

        if not EP._will_lose(game_state):
            return False
        return bool(ec.get("self", {}).get("has_two_clean_hands"))

    def _q1_counter_enemy_bomb(
        self,
        game_state: Dict[str, Any],
        action_list: List,
        ec: Dict[str, Any],
        main_pos: int,
        main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """GUA-123：敌 sprint 出炸时，从 actionList 选最小足够反炸。"""
        if main_enemy.get("remaining", 99) > 5:
            return None
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

    def _q1_finish_now_candidate(
        self, game_state: Dict[str, Any], action_list: List,
    ) -> Optional[Tuple[int, List]]:
        """GUA-112：若平台给出一手清牌候选，Q1 不得拆完整手牌。"""
        return find_finish_now_candidate(game_state, action_list)

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
            cur_val = CARD_RANK_ORDER.get(get_action_rank(greater_action), 99)
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
            return self._select_enemy_one_locking_structure(structured, game_state)

        safe_single = self._select_enemy_one_safe_single(singles, game_state, ec)
        if safe_single is not None:
            return safe_single

        if remaining == 1:
            return self._select_enemy_one_strongest_single(singles, game_state)
        return None

    def _select_enemy_one_locking_structure(
        self, candidates: List[Tuple[int, List]], game_state: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """敌方报单时，优先选能直接锁死其 1 张跟牌窗口的整牌型。"""
        if not candidates:
            return None

        cur_rank = str(game_state.get("curRank", "2"))

        def _key(item: Tuple[int, List]):
            _, act = item
            atype = get_action_type(act)
            return (
                _q1_structure_priority(atype),
                -len(_get_cards(act)),
                _max_card_value(act, cur_rank),
            )

        return min(candidates, key=_key)

    def _is_my_q1_lead_turn(self, game_state: Dict[str, Any], my_pos: int) -> bool:
        """Q1 自由领出兼容两种平台表示：curPos=myPos 或 curPos/greaterPos 都为 -1。"""
        cur_pos = game_state.get("curPos", my_pos)
        greater_pos = game_state.get("greaterPos", -1)
        if cur_pos == my_pos:
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
    ) -> Optional[Tuple[int, List]]:
        """仅剩两手时，优先选择能先手冲刺的整牌型。"""
        hand_cards = list(game_state.get("handCards", []) or [])
        hand_counter = Counter(hand_cards)
        if sum(hand_counter.values()) <= 1:
            return None

        cur_rank = str(game_state.get("curRank", "2"))
        sprint_candidates: List[Tuple[Tuple[int, int, int, int], Tuple[int, List]]] = []
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

            act_type = _effective_structure_type(act)
            declared = _get_declared_action_type(act)
            # 两手冲刺先手：StraightFlush 优于临时星炸（保留第二手整牌结构）
            bomb_sprint_rank = (
                0 if declared == "StraightFlush"
                else 1 if declared == "Bomb"
                else 2
            )
            sprint_candidates.append((
                (
                    residue_bucket,
                    bomb_sprint_rank,
                    _q1_structure_priority(act_type),
                    -len(cards),
                    _max_card_value(act, cur_rank),
                ),
                item,
            ))

        if not sprint_candidates:
            return None
        sprint_candidates.sort(key=lambda entry: entry[0])
        return sprint_candidates[0][1]

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
    ) -> Optional[Tuple[int, List]]:
        """选最大炸弹（张数多 > 牌力大）。"""
        if not bombs:
            return None

        def bomb_score(item: Tuple[int, List]) -> int:
            _, act = item
            cards = _get_cards(act)
            # 张数多优先，同张数牌力大优先
            return len(cards) * 100 + _max_card_value(act)

        best = max(bombs, key=bomb_score)
        return best

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
    ) -> Optional[Tuple[int, List]]:
        """从 action_list 中找杂牌 TWT（min 牌力优先）。"""
        if not GUARD_TOOLS_OK:
            return None
        best: Optional[Tuple[int, List]] = None
        best_value = 10**9
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
            if v < best_value:
                best_value = v
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
            twt = self._find_twt_min_point(action_list, cur_rank)
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
        twt = self._find_twt_min_point(action_list, cur_rank)
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
        twt = self._find_twt_min_point(action_list, cur_rank)
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
        """
        if not ctx:
            return None
        cur_rank = str(game_state.get("curRank", "2"))
        twt = self._find_twt_min_point(action_list, cur_rank)
        if twt is not None:
            kind = ctx.get("c356_kind", "unknown")
            logger.info(
                "GUA-134 C3/C5/C6(%s): 跟 min TWT 夺权，三手清空闭合",
                kind,
            )
            return twt
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
        GUA-135：判定手牌是否具备冲刺能力（剩 2 手 = 炸弹 + 单手）。

        冲刺能力 ≠ sprint 真闭环（sprint 真闭环需出完 6J + 接力 X 两手清空）。
        这里只判定结构上具备冲刺条件。

        实现要点：
          - 至少有 4 张同点（bomb family 一员）
          - 剩余张数 ≤ 5 张且可组成单整牌型（单 / 对 / 三张 / 三连对 / 三带二 / 钢板 / 顺子 / 同花顺 / 炸弹）
        """
        if not hand_cards or len(hand_cards) < 5:
            return False
        from collections import Counter
        ranks = Counter(get_card_rank(c) for c in hand_cards)
        # 至少 4 张同点（炸弹家族）
        max_count = max(ranks.values()) if ranks else 0
        if max_count < 4:
            return False
        # 剩余张数 ≤ 5 张（出掉炸弹后单手 ≤ 5 张）
        remaining_after_bomb = len(hand_cards) - max_count
        if remaining_after_bomb > 5:
            return False
        if remaining_after_bomb == 0:
            # 整手就是一个炸弹，无冲刺能力（已是「一手清空」）
            return False
        return True

    def _estimate_player_remaining(
        self, position: int, ec: Dict[str, Any], game_state: Dict[str, Any],
    ) -> int:
        """
        GUA-135：估算某玩家当前剩牌数（用于双进优先级判定）。

        来源优先级：
          1. 平台报牌（enemy_ctx.remaining）— 最准
          2. 记忆模块（_memory_tracker）— 估
          3. 默认 = 0（未知）

        返回：估算的剩牌数（0 表示未知）
        """
        # GUA-136 增强：MemoryTracker 优先（仅当返回 > 0 时，否则回退 enemy_ctx）
        tracker = game_state.get("_memory_tracker")
        if tracker is not None:
            try:
                count = tracker.get_hand_count(position)
                if isinstance(count, int) and count > 0:
                    return count
            except Exception:
                pass
        # 兜底：平台报牌
        enemies = ec.get("enemies", {}) or {}
        enemy_ctx = enemies.get(position, {}) or {}
        remaining = enemy_ctx.get("remaining")
        if isinstance(remaining, int) and remaining >= 0:
            return remaining
        return 0

    def _is_double_second_priority_scenario(
        self, game_state: Dict[str, Any], ec: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        GUA-135：探测 yf2 当前是否落在「双进优先级判定」场景。

        触发条件（任一）：
          - @1 finish 是 bomb family（C2 SF / C4 5 炸）→ @1 必头游
          - yf2 / yf1 整手 ≤ 6 张 → 双冲刺赛道
          - yf1 已 bomb family 拦截（C1 路径 A）

        返回 ctx dict 或 None：{
          "trigger": "C2" | "C4" | "yf2_self_sprint" | "yf1_sprint" | "sprint_race",
          "enemy_pos": int,
          "teammate_pos": int,
          "yf2_remaining": int,
          "yf1_remaining": int,
          "@3_remaining": int,
          "yf2_sprint": bool,
          "yf1_sprint": bool,
          "@3_sprint": bool,
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

        # 估算各方剩牌
        yf2_remaining = len(hand_cards)
        yf1_remaining = self._estimate_player_remaining(teammate_pos, ec, game_state)
        at3_remaining = self._estimate_player_remaining(enemy_pos, ec, game_state)

        # 判定冲刺能力（剩 2 手 = 炸弹 + 单手）
        yf2_sprint = self._has_sprint_capability(hand_cards)

        # GUA-136 增强：yf1 冲刺能力精确评估（基于推断手牌）
        yf1_sprint = self._estimate_player_sprint_capability(teammate_pos, game_state)
        # 兜底：若 yf1 bomb family 已拦截（C1 路径 A），必头游
        if not yf1_sprint:
            try:
                yf1_sprint = self._has_teammate_bomb_family(game_state, teammate_pos)
            except Exception:
                pass

        # GUA-136 增强：@3 冲刺能力精确评估（基于推断手牌）
        at3_sprint = self._estimate_player_sprint_capability(enemy_pos, game_state)

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
        if finish_kind == "bomb_family":  # 不限 yf2_remaining（@1 必头游 → yf 队必抢第二）
            # C2 / C4：@1 finish 是 bomb family → @1 必头游
            # 进一步区分 C2 / C4（看 enemy_ctx.finish_type）
            finish_atype = ctx["enemy_ctx"].get("finish_type", "")
            if "StraightFlush" in str(finish_atype) or "SF" in str(finish_atype):
                trigger = "C2"
            else:
                trigger = "C4"
        elif yf1_sprint:
            # yf1 已 bomb family 拦截（C1 路径 A）→ yf1 头游，yf2 必第三
            trigger = "yf1_sprint"
        elif yf2_remaining <= 6 and yf1_remaining <= 6 and yf2_remaining >= 5:
            # 双冲刺赛道（双方都 ≤ 6 张）→ 判定谁抢第二
            trigger = "sprint_race"
        elif (finish_kind in ("straight", "twt", "scatter")) and (yf2_remaining >= 10 or yf2_sprint):
            # yf2 自闭合头游（C3/C5/C6 或 C1 路径 B）→ yf1 必抢第二
            # 条件：① yf2 整手 ≥ 10 张（残局大剩牌，跟 TWT 形成冲刺能力）
            #       ② yf2_sprint（yf2 已有冲刺能力，直接闭合）
            trigger = "yf2_self_sprint"

        if trigger is None:
            return None

        return {
            "trigger": trigger,
            "enemy_pos": enemy_pos,
            "teammate_pos": teammate_pos,
            "my_pos": my_pos,
            "hand_cards": hand_cards,
            "yf2_remaining": yf2_remaining,
            "yf1_remaining": yf1_remaining,
            "@3_remaining": at3_remaining,
            "yf2_sprint": yf2_sprint,
            "yf1_sprint": yf1_sprint,
            "@3_sprint": at3_sprint,
            "finish_kind": finish_kind,
            "ctx": ctx,
        }

    def _q1_double_second_priority(
        self, game_state: Dict[str, Any], action_list: List,
        ec: Dict[str, Any], main_pos: int, main_enemy: Dict[str, Any],
    ) -> Optional[Tuple[int, List]]:
        """
        GUA-135：双进优先级判定（C2/C4 接受 @1 头游 + C3/C5/C6 闭合后队整体策略）。

        判定逻辑：
          1. yf2 当前是否已有冲刺能力（剩 2 手 = 炸弹 + 单手）？
             - 是 → yf2 自己继续自闭合拿第二（C2/C4/yf2_self_sprint）
          2. yf1 当前冲刺能力（@1 finish = bomb family 且 yf1 bomb family 已拦截）？
             - 是 → yf1 必头游，yf2 必第三（让道）
          3. @3 冲刺能力？
             - 是 → yf2 必须用 bomb family 拦截 @3 抢第二
             - 否 → yf2 PASS 等待更优时机

        返回：最优动作 (idx, action) 或 None
        """
        ctx = self._is_double_second_priority_scenario(game_state, ec)
        if ctx is None:
            return None

        trigger = ctx["trigger"]
        yf2_sprint = ctx["yf2_sprint"]
        yf1_sprint = ctx["yf1_sprint"]
        at3_sprint = ctx["@3_sprint"]
        hand_cards = ctx["hand_cards"]
        cur_rank = str(game_state.get("curRank", "2"))

        # 情形 1：C2/C4（@1 必头游）→ yf2 自己拿第二
        if trigger in ("C2", "C4"):
            if yf2_sprint:
                # yf2 已有冲刺能力（剩 2 手 = 炸弹 + 单手）
                # → 圈 2 yf2 领出 6J + 圈 3 接力闭合
                logger.info(
                    "GUA-135 %s: @1 必头游，yf2 自闭合拿第二（冲刺能力成立）",
                    trigger,
                )
                # 找 min 整牌型领出（保持当前圈 1 出 PASS 等待，让 @1 圈 2 出一手清）
                # 实际：圈 1 yf2 应该 PASS（@1 必头游），让 @1 圈 2 出一手清
                # 若 @1 圈 1 出的就是 finish，则 yf2 圈 1 也可跟 PASS
                pass_act = self._find_pass_action(action_list)
                if pass_act is not None:
                    return pass_act
            else:
                # yf2 无冲刺能力 → yf2 圈 1 PASS 等 @1 头游，圈 2/3 闭合 @3
                logger.info(
                    "GUA-135 %s: @1 必头游，yf2 PASS 等闭合 @3",
                    trigger,
                )
                pass_act = self._find_pass_action(action_list)
                if pass_act is not None:
                    return pass_act

        # 情形 2：yf2_self_sprint（yf2 已闭合头游）→ yf1 必抢第二
        if trigger == "yf2_self_sprint":
            # yf2 圈 1 必跟 min TWT 夺权（GUA-134 已落）
            # GUA-135 这里只判定 yf1 能否抢第二
            if yf1_sprint:
                # yf1 也有冲刺能力 → 让 yf1 拿第二（yf2 不抢）
                logger.info(
                    "GUA-135 yf2_self_sprint: yf1 也有冲刺能力，yf2 PASS 让 yf1 拿第二",
                )
                pass_act = self._find_pass_action(action_list)
                if pass_act is not None:
                    return pass_act
            else:
                # yf1 无冲刺能力 → yf2 必跟 min TWT 夺权（GUA-134 路径）
                twt = self._find_twt_min_point(action_list, cur_rank)
                if twt is not None:
                    logger.info(
                        "GUA-135 yf2_self_sprint: 跟 min TWT 夺权",
                    )
                    return twt

        # 情形 3：yf1_sprint（yf1 已头游）→ yf2 必第三
        if trigger == "yf1_sprint":
            # yf2 必第三（无冲刺能力）→ PASS 等 @3 抢第二 / yf2 抢第三
            logger.info(
                "GUA-135 yf1_sprint: yf1 已头游，yf2 必第三，PASS",
            )
            pass_act = self._find_pass_action(action_list)
            if pass_act is not None:
                return pass_act

        # 情形 4：sprint_race（双方都 ≤ 6 张）→ 判定谁拿第二
        if trigger == "sprint_race":
            if yf2_sprint and not yf1_sprint:
                # yf2 有冲刺能力，yf1 无 → yf2 拿第二
                logger.info(
                    "GUA-135 sprint_race: yf2 有冲刺能力，yf2 拿第二",
                )
                twt = self._find_twt_min_point(action_list, cur_rank)
                if twt is not None:
                    return twt
            elif yf1_sprint and not yf2_sprint:
                # yf1 有冲刺能力，yf2 无 → yf1 拿第二，yf2 PASS 让道
                logger.info(
                    "GUA-135 sprint_race: yf1 有冲刺能力，yf2 PASS 让 yf1 拿第二",
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

