# -*- coding: utf-8 -*-
"""
V7-native P0 Guard 壳 — V7-R01~R06（GUA-045）

使用方式（在 separate_engine 的 decide() 内）：
    from src.v.nn.guards import filter_action_list, validate_decision
    # 过滤：去掉明显不当的动作
    filtered_actions, action_map = filter_action_list(game_state)
    # ... 模型在 filtered_actions 上决策 ...
    # 校验：模型选出的 index 若有问题，覆盖为更优选择
    safe_idx = validate_decision(best_idx, filtered_actions, game_state)

所有函数 V7-native，不依赖 src.m.m3.*。
"""

from typing import List, Dict, Any, Tuple, Optional

import logging

logger = logging.getLogger("v7_guards")

# ── 常量 ──────────────────────────────────────────────
SUITS = ("S", "H", "D", "C")
RANK_STR = ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")
# 牌面数值（越大越强）
CARD_RANK_ORDER: Dict[str, int] = {r: i for i, r in enumerate(RANK_STR)}  # 2=0 … A=12
JOKER_VALUE_BJ = 13
JOKER_VALUE_RJ = 14

# ── 牌型枚举 ──────────────────────────────────────────
ACTION_TYPE_PASS = "PASS"
ACTION_TYPE_SINGLE = "Single"
ACTION_TYPE_PAIR = "Pair"
ACTION_TYPE_TRIPS = "Trips"
ACTION_TYPE_BOMB = "Bomb"
ACTION_TYPE_STRAIGHT_FLUSH = "StraightFlush"
ACTION_TYPE_THREE_PAIR = "ThreePair"       # 三连对
ACTION_TYPE_TWO_TRIPS = "TwoTrips"         # 钢板（两连三张）
ACTION_TYPE_THREE_WITH_TWO = "ThreeWithTwo"  # 三带二
ACTION_TYPE_STRAIGHT = "Straight"           # 顺子（5+ 不同花连号）
ACTION_TYPE_FREE = "Free"                  # 其他/未知


# ═══════════════════════════════════════════════════════
#  公用工具
# ═══════════════════════════════════════════════════════

def get_card_rank(card: str) -> str:
    """从 'S2' / 'BJ' / 'RJ' 提取等级字符。"""
    if card in ("RJ", "BJ"):
        return card
    if len(card) >= 2:
        return card[1]
    return card


def get_card_value(card: str, cur_rank: str = None) -> int:
    """
    牌面数值（越大越强）。
    BJ=13, RJ=14, curRank=15（级牌提升一级）。
    """
    if card == "BJ":
        return JOKER_VALUE_BJ
    if card == "RJ":
        return JOKER_VALUE_RJ
    rank = get_card_rank(card)
    base = CARD_RANK_ORDER.get(rank, 0)
    if cur_rank and rank == cur_rank:
        base += 15  # 级牌压一切普通牌（但比王低）
    return base


def get_action_type(action: List[str]) -> str:
    """
    判断一手牌的类型。
    输入示例：["S2"], ["S2","H2"], ["PASS"] ...
    """
    if not action:
        return ACTION_TYPE_PASS
    if action[0] == "PASS":
        return ACTION_TYPE_PASS
    n = len(action)
    if n == 1:
        return ACTION_TYPE_SINGLE
    # 取每张牌的 rank
    ranks = [get_card_rank(c) for c in action]
    first = ranks[0]
    all_same_rank = all(r == first for r in ranks)
    # 花色序列
    suits = [c[0] for c in action if len(c) >= 2]

    if n == 2 and all_same_rank:
        return ACTION_TYPE_PAIR
    if n == 3 and all_same_rank:
        return ACTION_TYPE_TRIPS
    if all_same_rank:
        if n >= 4:
            return ACTION_TYPE_BOMB
    # 同花顺
    if n >= 5 and _is_consecutive_ranks(ranks) and _is_same_suit(suits):
        return ACTION_TYPE_STRAIGHT_FLUSH
    # 顺子（不同花）
    if n >= 5 and _is_consecutive_ranks(ranks):
        return ACTION_TYPE_STRAIGHT
    # 三连对（如 33 44 55）
    if n == 6 and _is_consecutive_pairs(ranks):
        return ACTION_TYPE_THREE_PAIR
    # 钢板（如 333 444）
    if n == 6 and _is_consecutive_trips(ranks):
        return ACTION_TYPE_TWO_TRIPS
    # 三带二
    if n == 5:
        rank_counts = {}
        for r in ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1
        if 3 in rank_counts.values() and 2 in rank_counts.values():
            return ACTION_TYPE_THREE_WITH_TWO
    return ACTION_TYPE_FREE


def get_action_rank(action: List[str]) -> Optional[str]:
    """获取一手牌的比较等级（如 Pair 'S2','H2' → '2'；Bomb 取牌面）。"""
    if not action or action[0] == "PASS":
        return None
    ranks = [get_card_rank(c) for c in action]
    # 取出现最多的 rank（炸弹/三带二等取主牌）
    from collections import Counter
    cnt = Counter(ranks)
    return cnt.most_common(1)[0][0]


def is_bomb(action: List[str]) -> bool:
    return get_action_type(action) in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH)


def is_straight_flush(action: List[str]) -> bool:
    return get_action_type(action) == ACTION_TYPE_STRAIGHT_FLUSH


def is_pure_bomb(action: List[str], cur_rank: str = None) -> bool:
    """
    判断是否为纯炸（不含逢人配/级牌）。
    若 cur_rank 提供，含 H+curRank 的视为非纯炸。
    """
    if not is_bomb(action):
        return False
    wild = f"H{cur_rank}" if cur_rank else None
    for card in action:
        if wild and card == wild:
            return False
    return True


def has_teammate_passed(action_list: List[List[str]], greater_pos: int,
                        my_pos: int) -> bool:
    """
    判断队友是否在本圈已 PASS。
    简化实现：若 greaterPos 不是队友，假定队友未全 PASS；
    若 greaterPos 是队友，说明队友是本圈最大，不需要炸。
    """
    teammate = (my_pos + 2) % 4
    # greater_pos 不是队友 → 队友可能还能压
    if greater_pos != teammate:
        return False
    # greater_pos 是队友 → 队友是圈内最大 → 不需要炸
    return False  # 返回 False 意味着「队友未全部 PASS」，触发 R05 过滤


# ── 内部辅助 ──────────────────────────────────────────

def _is_consecutive_ranks(ranks: List[str]) -> bool:
    """检查 rank 序列是否连续（A 可作为 1 或 14）。"""
    if not ranks:
        return False
    unique = list(dict.fromkeys(ranks))  # 去重保序
    if len(unique) < 5:
        return False
    # 检查是否连续
    indices = sorted({CARD_RANK_ORDER.get(r, 99) for r in unique})
    if len(indices) < 5:
        return False
    for i in range(len(indices) - 1):
        if indices[i + 1] - indices[i] != 1:
            # 特殊：A→2 不连续
            return False
    return True


def _is_same_suit(suits: List[str]) -> bool:
    """检查花色是否全相同（王不计花色）。"""
    real = [s for s in suits if s in SUITS]
    if len(real) < 1:
        return False
    first = real[0]
    return all(s == first for s in real)


def _is_consecutive_pairs(ranks: List[str]) -> bool:
    """检查是否为连续对子（33 44 55 → 6 张，3 种 rank）。"""
    if len(ranks) != 6:
        return False
    pairs = [ranks[i:i+2] for i in range(0, 6, 2)]
    if not all(len(set(p)) == 1 for p in pairs):
        return False  # 每组两张必须相同
    unique_ranks = [p[0] for p in pairs]
    return _is_consecutive_ranks(unique_ranks)


def _is_consecutive_trips(ranks: List[str]) -> bool:
    """检查是否为连续三张（333 444 → 6 张，2 种 rank）。"""
    if len(ranks) != 6:
        return False
    trips = [ranks[i:i+3] for i in range(0, 6, 3)]
    if not all(len(set(t)) == 1 for t in trips):
        return False
    unique_ranks = [t[0] for t in trips]
    return _is_consecutive_ranks(unique_ranks)


# ═══════════════════════════════════════════════════════
#  Guard 规则
# ═══════════════════════════════════════════════════════

def _rule_r05_teammate_no_bomb(
    action_list: List[List[str]],
    greater_action: List[str],
    greater_pos: int,
    my_pos: int,
) -> List[int]:
    """
    V7-R05：greaterPos == (myPos+2)%4 且队友非 PASS → 剔除 Bomb/StraightFlush。
    过滤后至少保留一个合法动作。
    """
    teammate = (my_pos + 2) % 4
    if greater_pos != teammate:
        return list(range(len(action_list)))

    # 检查队友是否已 PASS（通过 greaterAction 判断）
    if greater_action and greater_action[0] == "PASS":
        return list(range(len(action_list)))

    # 队友领出 → 过滤炸弹
    banned = {ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH}
    kept = [i for i, act in enumerate(action_list)
            if get_action_type(act) not in banned]
    if not kept:
        # 全是炸弹 → 保留最小的一个（不能无动作）
        bombs = [(i, len(act)) for i, act in enumerate(action_list)
                 if get_action_type(act) in banned]
        if bombs:
            bombs.sort(key=lambda x: x[1])  # 最少张
            kept = [bombs[0][0]]
        else:
            kept = list(range(len(action_list)))
    return kept


def _rule_r01_no_bomb_for_single(
    action_list: List[List[str]],
    greater_action: List[str],
    cur_rank: str,
) -> List[int]:
    """
    V7-R01：压 Single 且 curRank 在场 → 优先 Single B/Single 最小点；
    禁为压单选 Bomb 若存在更小单牌选项。
    """
    if not greater_action or greater_action[0] == "PASS":
        return list(range(len(action_list)))
    if get_action_type(greater_action) != ACTION_TYPE_SINGLE:
        return list(range(len(action_list)))

    # 找所有非 bomb 的 single 选项
    singles = []
    bomb_indices = []
    for i, act in enumerate(action_list):
        t = get_action_type(act)
        if t == ACTION_TYPE_SINGLE:
            val = get_card_value(act[0], cur_rank)
            singles.append((i, val, act))
        elif t in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            bomb_indices.append(i)

    if not bomb_indices:
        return list(range(len(action_list)))

    if singles:
        # 有 single 选项 → 剔除 bomb（让模型在 singles 中选）
        kept = [i for i in range(len(action_list)) if i not in bomb_indices]
        return kept if kept else list(range(len(action_list)))

    # 没有单牌选项，但可能有其他非 bomb（pair/trips 等）→ 保留
    return list(range(len(action_list)))


def _rule_r02_minimal_bomb(
    action_list: List[List[str]],
    cur_rank: str,
) -> List[int]:
    """
    V7-R02：同牌型能压时选 len(cards) 最小合法炸；
    禁逢人配凑炸若纯炸可压。
    """
    bombs = []
    for i, act in enumerate(action_list):
        if is_bomb(act):
            bombs.append((i, len(act), act, is_pure_bomb(act, cur_rank)))

    if len(bombs) <= 1:
        return list(range(len(action_list)))

    # 按长度排序，选最短的
    bombs.sort(key=lambda x: (x[1], not x[3]))  # 优先短+纯炸
    best_idx = bombs[0][0]

    # 保留最佳炸弹和其他非炸弹
    kept = [i for i in range(len(action_list)) if i == best_idx or
            not is_bomb(action_list[i])]
    return kept if kept else list(range(len(action_list)))


def _rule_r03_passive_no_pass(
    action_list: List[List[str]],
    greater_action: List[str],
    greater_pos: int,
    my_pos: int,
) -> List[int]:
    """
    V7-R03：被动且 greaterPos 为对手；
    actionList 有同型非 PASS → 禁默认 PASS（取最小够用）。
    不直接剔除 PASS，而是返回优先同型非 PASS 的排序建议。
    返回 kept indices（PASS 在队手时后置）。
    """
    # 检查是否被动（对手出了牌）
    if not greater_action or greater_action[0] == "PASS":
        return list(range(len(action_list)))
    opponent_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]
    if greater_pos not in opponent_positions:
        return list(range(len(action_list)))

    greater_type = get_action_type(greater_action)
    # 找同型非 PASS 选项
    same_type = []
    pass_indices = []
    for i, act in enumerate(action_list):
        t = get_action_type(act)
        if t == ACTION_TYPE_PASS:
            pass_indices.append(i)
        elif t == greater_type:
            same_type.append(i)

    if not same_type:
        # 无同型 → 保留全部（后续规则可能处理）
        return list(range(len(action_list)))

    # 有同型选项 → 将 PASS 置于列表末尾（非删除，让模型先选同型）
    non_pass = [i for i in range(len(action_list)) if i not in pass_indices]
    # 重新排列：非 PASS 在前，PASS 在后
    ordering = non_pass + pass_indices
    return ordering  # 注意：返回的是重排后的顺序，不是过滤


def _rule_r04_single_b_non_pass(
    action_list: List[List[str]],
    greater_action: List[str],
    greater_pos: int,
    my_pos: int,
    cur_rank: str,
) -> List[int]:
    """
    V7-R04：对手 Single 且己方可 Single B → 优先非 PASS。
    若有可压单牌，将 PASS 置后。
    """
    if not greater_action or greater_action[0] == "PASS":
        return list(range(len(action_list)))
    opponent_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]
    if greater_pos not in opponent_positions:
        return list(range(len(action_list)))
    if get_action_type(greater_action) != ACTION_TYPE_SINGLE:
        return list(range(len(action_list)))

    # 检查自己是否有可压单牌
    greater_val = get_card_value(greater_action[0], cur_rank)
    has_beating_single = False
    pass_indices = []
    for i, act in enumerate(action_list):
        if get_action_type(act) == ACTION_TYPE_SINGLE:
            if get_card_value(act[0], cur_rank) > greater_val:
                has_beating_single = True
                break
    if not has_beating_single:
        # 加个例外：有级牌单张也能压
        for i, act in enumerate(action_list):
            if get_action_type(act) == ACTION_TYPE_SINGLE:
                r = get_card_rank(act[0])
                if r == "BJ" or r == "RJ":
                    has_beating_single = True
                    break

    # 找出 PASS
    pass_indices = [i for i, act in enumerate(action_list)
                    if get_action_type(act) == ACTION_TYPE_PASS]

    if has_beating_single and pass_indices:
        non_pass = [i for i in range(len(action_list)) if i not in pass_indices]
        ordering = non_pass + pass_indices
        return ordering

    return list(range(len(action_list)))


def _rule_r06_no_break_structure_pair(
    action_list: List[List[str]],
    hand_cards: List[str],
) -> List[int]:
    """
    V7-R06（轻量）：存在不拆结构的更大 Pair 可压时，
    剔除拆 ThreePair/钢板的 Pair。
    """
    # 获取手牌中所有完整的结构
    # 简化：统计手牌中每种 rank 的牌数
    from collections import Counter
    hand_ranks = Counter(get_card_rank(c) for c in hand_cards)

    pair_indices = []
    for i, act in enumerate(action_list):
        if get_action_type(act) == ACTION_TYPE_PAIR:
            rank = get_action_rank(act)
            if rank is None:
                continue
            cnt = hand_ranks.get(rank, 0)
            # 若手牌中该 rank 正好 2 张 → 天然对子
            if cnt == 2:
                pair_indices.append(i)

    if not pair_indices:
        return list(range(len(action_list)))

    # 如果存在天然对子，将「非天然对子」置后
    break_pair_indices = []
    for i, act in enumerate(action_list):
        if get_action_type(act) == ACTION_TYPE_PAIR:
            rank = get_action_rank(act)
            cnt = hand_ranks.get(rank, 0)
            if cnt != 2:  # 拆结构得到的对
                break_pair_indices.append(i)

    if not break_pair_indices:
        return list(range(len(action_list)))

    # 保留天然对子在前
    kept = [i for i in range(len(action_list)) if i not in break_pair_indices]
    return kept if kept else list(range(len(action_list)))


# ═══════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════

def filter_action_list(
    game_state: Dict[str, Any],
) -> Tuple[List[List[str]], List[int]]:
    """
    GUA-045 主过滤入口：对 model 前的 actionList 应用全部 V7-R 规则。

    Returns:
        (filtered_actions, action_map)
        - filtered_actions: 过滤/重排后的 action 列表
        - action_map: 映射 [新下标] → [原下标]
    """
    action_list = game_state.get("actionList", [])
    if not action_list:
        return [], []

    try:
        return _filter_action_list_impl(game_state, action_list)
    except Exception as e:
        logger.error(f"filter_action_list 异常，回退原始 actionList: {e}", exc_info=True)
        return action_list, list(range(len(action_list)))


def _filter_action_list_impl(
    game_state: Dict[str, Any],
    action_list: List[List[str]],
) -> Tuple[List[List[str]], List[int]]:
    """filter_action_list 实际逻辑（被外层 try/except 包裹）。"""
    my_pos = game_state.get("myPos", game_state.get("player_id", 0))
    greater_pos = game_state.get("greaterPos", -1)
    greater_action = game_state.get("greaterAction", [])
    if isinstance(greater_action, str):
        import ast
        try:
            greater_action = ast.literal_eval(greater_action)
        except (ValueError, SyntaxError):
            greater_action = []
    cur_rank = game_state.get("curRank", "2")
    hand_cards = game_state.get("handCards", [])

    # 收集各规则产生的 index 约束
    # 用 set 累积被排除的索引
    excluded = set()

    # 1) R05: 队友领出不炸
    r05_kept = _rule_r05_teammate_no_bomb(
        action_list, greater_action, greater_pos, my_pos)
    excluded |= {i for i in range(len(action_list)) if i not in set(r05_kept)}

    # 2) R01: 压单不用炸
    r01_kept = _rule_r01_no_bomb_for_single(
        action_list, greater_action, cur_rank)
    excluded |= {i for i in range(len(action_list)) if i not in set(r01_kept)}

    # 3) R02: 最小炸弹
    r02_kept = _rule_r02_minimal_bomb(action_list, cur_rank)
    excluded |= {i for i in range(len(action_list)) if i not in set(r02_kept)}

    # 4) R06: 不拆结构对子
    r06_kept = _rule_r06_no_break_structure_pair(action_list, hand_cards)
    excluded |= {i for i in range(len(action_list)) if i not in set(r06_kept)}

    # R03/R04 重排（不真正剔除，影响后续模型选择顺序）
    # 这些规则不剔除元素，只返回排序
    r03_order = _rule_r03_passive_no_pass(
        action_list, greater_action, greater_pos, my_pos)
    r04_order = _rule_r04_single_b_non_pass(
        action_list, greater_action, greater_pos, my_pos, cur_rank)

    # 构建最终过滤列表
    kept = [i for i in range(len(action_list)) if i not in excluded]
    if not kept:
        # 全被过滤了 → 保留全部
        kept = list(range(len(action_list)))

    # 应用重排（R03 和 R04 同时适用时，取交集顺序）
    # 先取 r03_order 在 kept 中的顺序，再取 r04_order 在 kept 中的顺序
    # 简单做法：取最后一个重排规则
    final_order = kept[:]
    for ordering in (r03_order, r04_order):
        filtered_order = [i for i in ordering if i in set(kept)]
        if filtered_order and filtered_order != final_order:
            final_order = filtered_order

    filtered = [action_list[i] for i in final_order]

    logger.debug(
        "filter_action_list: %d→%d actions (excluded %d rules: R05=%s R01=%s R02=%s R06=%s)",
        len(action_list), len(filtered), len(excluded),
        len(action_list) - len(r05_kept) if r05_kept != list(range(len(action_list))) else 0,
        len(action_list) - len(r01_kept) if r01_kept != list(range(len(action_list))) else 0,
        len(action_list) - len(r02_kept) if r02_kept != list(range(len(action_list))) else 0,
        len(action_list) - len(r06_kept) if r06_kept != list(range(len(action_list))) else 0,
    )

    return filtered, final_order


def validate_decision(
    model_idx: int,
    filtered_actions: List[List[str]],
    game_state: Dict[str, Any],
    original_action_list: List[List[str]] = None,
) -> int:
    """
    模型决策后校验。若模型选了 PASS 但 guard 认为应出牌 → 覆盖。
    若选了炸弹炸队友 → 覆盖为非炸最小动作。

    Returns:
        安全的 filtered_actions 下标。
    """
    if not filtered_actions:
        return 0

    try:
        return _validate_decision_impl(model_idx, filtered_actions, game_state, original_action_list)
    except Exception as e:
        logger.error(f"validate_decision 异常，返回 0: {e}", exc_info=True)
        return 0


def _validate_decision_impl(
    model_idx: int,
    filtered_actions: List[List[str]],
    game_state: Dict[str, Any],
    original_action_list: List[List[str]] = None,
) -> int:
    """validate_decision 实际逻辑（被外层 try/except 包裹）。"""
    if model_idx < 0 or model_idx >= len(filtered_actions):
        model_idx = 0

    chosen = filtered_actions[model_idx]
    chosen_type = get_action_type(chosen)
    my_pos = game_state.get("myPos", game_state.get("player_id", 0))
    greater_pos = game_state.get("greaterPos", -1)
    greater_action = game_state.get("greaterAction", [])
    if isinstance(greater_action, str):
        import ast
        try:
            greater_action = ast.literal_eval(greater_action)
        except (ValueError, SyntaxError):
            greater_action = []
    opponent_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]

    # 1) 检查是否在炸队友
    if is_bomb(chosen) and greater_pos in opponent_positions:
        # 对手出牌，我方炸 → 合理
        pass
    elif is_bomb(chosen) and greater_pos == (my_pos + 2) % 4:
        # 队友领出我方出炸 → 不合理，找非炸动作
        non_bomb = [i for i, act in enumerate(filtered_actions)
                    if not is_bomb(act)]
        if non_bomb:
            logger.info("validate_decision: 覆盖炸队友 (idx %d → %d)", model_idx, non_bomb[0])
            return non_bomb[0]

    # 2) 被动且对手出牌，模型选了 PASS，但有同型非 PASS
    if chosen_type == ACTION_TYPE_PASS and greater_action and greater_action[0] != "PASS":
        if greater_pos in opponent_positions:
            greater_type = get_action_type(greater_action)
            same_type = [i for i, act in enumerate(filtered_actions)
                         if get_action_type(act) == greater_type]
            if same_type:
                # 选最小够用的
                logger.info("validate_decision: 覆盖被动 PASS (idx %d → %d)", model_idx, same_type[0])
                return same_type[0]

    return model_idx


def get_hand_card_counts(game_state: Dict[str, Any]) -> Dict[str, int]:
    """辅助：统计手牌各 rank 出现次数。"""
    from collections import Counter
    hand = game_state.get("handCards", [])
    return Counter(get_card_rank(c) for c in hand)