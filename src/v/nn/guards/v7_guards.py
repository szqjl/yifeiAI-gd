# -*- coding: utf-8 -*-
"""
V7-native P0 Guard 壳 — V7-R01~R14（GUA-045 + 064 + 065 + 068）

规则列表：
  R01: 压单不用炸
  R02: 最小炸弹
  R03: 被动对手出牌 → 优先非 PASS 同型
  R04: 对手 Single 且己方可压 → 优先非 PASS
  R05: 队友领出或队友为圈最大 → 不炸
  R06: 不拆结构对子
  R07: 队友控牌 → 按牌型阈值让道（决议 9 细化）
  R08: 队友剩 1 张 → 主动出最小 Single 送队友
  R09: 队友剩 5 张 → assist_prefer_for(5) 过滤（Straight/ThreeWithTwo/Single）
  R10: 自己领出不炸
  R11: 对手出不可压牌 → 全局抑制牌检查 + 节流
  R12: 三带二最小带对（同一三张 rank 多个变体 → 保留最小对子）
  R13: 平台炸弹合法性校验
  R14: 领出不拆天然牌型（有天然对子/三张 → 过滤拆散 Single/Pair）

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
JOKER_VALUE_SB = 16  # 小王（单张：大王>小王>级牌>A…）
JOKER_VALUE_HR = 17  # 大王
JOKER_VALUE_CUR_RANK = 15  # 级牌（任一花色同点）

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
    """从 'S2' / 'SB' / 'HR' 提取等级字符。"""
    if card is None:
        return ""
    if card in ("HR", "SB"):
        return card
    if len(card) >= 2:
        return card[1]
    return card


def get_card_value(card: str, cur_rank: str = None) -> int:
    """
    牌面数值（越大越强，用于 Single 比大小）。

    固定顺序（见 docs/knowledge/rules/01_basic_rules/04_card_types_guide.md §4.0）：
      大王(17) > 小王(16) > 级牌(15) > A(12) > … > 2(0)
    """
    if card in ("BJ", "RJ"):
        card = {"BJ": "SB", "RJ": "HR"}.get(card, card)
    if card == "SB":
        return JOKER_VALUE_SB
    if card == "HR":
        return JOKER_VALUE_HR
    rank = get_card_rank(card)
    if cur_rank and rank == cur_rank:
        return JOKER_VALUE_CUR_RANK
    return CARD_RANK_ORDER.get(rank, 0)


def _extract_action_cards(action: List) -> List[str]:
    """
    GUA-071：从 action 中提取实际牌列表，兼容两种格式：
      - 平台格式: [type, rank, [cards...]] → 返回 [cards...]
      - 扁平格式: [card1, card2, ...] → 直接返回

    平台 v1006 对复杂牌型（Bomb/Pair/ThreeWithTwo 等）使用
    [type, rank, [cards]] 格式，但简单牌型（Single）使用扁平 [card]。
    这导致 get_action_type 把 "Bomb"/"Pair" 当牌名解析，全部误判为 Free。
    """
    if isinstance(action, list) and len(action) >= 3 and isinstance(action[2], list):
        return action[2]
    return action


def get_action_type(action: List[str]) -> str:
    """
    判断一手牌的类型。
    输入示例：["S2"], ["S2","H2"], ["PASS"] ...
    也支持平台格式：["Bomb","A",["HA","CA","CA","H9"]]
    """
    if not action:
        return ACTION_TYPE_PASS
    # 防御：过滤列表中可能的 None 元素
    action = [c for c in action if c is not None]
    if not action:
        return ACTION_TYPE_PASS
    if action[0] == "PASS":
        return ACTION_TYPE_PASS

    # 平台格式 [type, rank, [cards]] 保留了逢人配后的语义牌型。
    # 例如 ["Pair","J",["CJ","H2"]] 是合法对子，若只按实牌 ranks 会被误判成 Free。
    # 但 Bomb/StraightFlush 仍需按实牌校验，供 R13 剔除平台假炸弹。
    if isinstance(action, list) and len(action) >= 3 and isinstance(action[2], list):
        declared = action[0]
        if declared in (
            ACTION_TYPE_SINGLE,
            ACTION_TYPE_PAIR,
            ACTION_TYPE_TRIPS,
            ACTION_TYPE_THREE_WITH_TWO,
            ACTION_TYPE_STRAIGHT,
            ACTION_TYPE_THREE_PAIR,
            ACTION_TYPE_TWO_TRIPS,
        ):
            return declared
        return get_action_type(action[2])

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
    # GUA-071：检测平台格式 [type, rank, [cards]]，提取实际牌列表后递归
    if isinstance(action, list) and len(action) >= 3 and isinstance(action[2], list):
        return get_action_rank(action[2])
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
    # GUA-071：从 action 提取实际牌列表迭代
    cards = _extract_action_cards(action)
    for card in cards:
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
        # GUA-071: 用实际牌张数（兼容平台格式 [type, rank, [cards]]）
        bombs = [(i, len(_extract_action_cards(act)))
                 for i, act in enumerate(action_list)
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
            # GUA-071: 从 action 提取实际牌（兼容平台格式 [type, rank, [cards]]）
            cards = _extract_action_cards(act)
            val = get_card_value(cards[0] if cards else act[0], cur_rank)
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
            # GUA-071: 用实际牌张数（兼容平台格式 [type, rank, [cards]]）
            cards = _extract_action_cards(act)
            bombs.append((i, len(cards), act, is_pure_bomb(act, cur_rank)))

    if len(bombs) <= 1:
        return list(range(len(action_list)))

    # 按长度排序，选最短的
    bombs.sort(key=lambda x: (x[1], not x[3]))  # 优先短+纯炸
    best_idx = bombs[0][0]

    # 保留最佳炸弹和其他非炸弹
    kept = [i for i in range(len(action_list)) if i == best_idx or
            not is_bomb(action_list[i])]
    return kept if kept else list(range(len(action_list)))


def _rule_r10_no_lead_bomb(
    action_list: List[List[str]],
    greater_pos: int,
    my_pos: int = -1,
) -> List[int]:
    """
    V7-R10：自己领出时禁用炸弹。
    领出判定：greaterPos == myPos（v1006 平台语义）或 greaterPos == -1（旧平台）。
    当手牌有非炸弹选项时，剔除 Bomb/StraightFlush 动作，
    避免浪费炸弹领出（自己炸自己）。

    设计要点：
    - 领出判定：greaterPos in (-1, my_pos)（新轮领出 / 自己是greater）
    - 如果全被过滤（只剩炸弹）→ 保留最小的一张炸弹（不能无动作）
    - 不依赖 greater_action（领出时无 greater_action）
    """
    is_lead = (greater_pos == -1) or (0 <= my_pos <= 3 and greater_pos == my_pos)
    if not is_lead:
        return list(range(len(action_list)))

    banned = {ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH}
    kept = [i for i, act in enumerate(action_list)
            if get_action_type(act) not in banned]
    if not kept:
        # 全是炸弹 → 保留最小的一个
        # GUA-071: 用实际牌张数（兼容平台格式 [type, rank, [cards]]）
        bombs = [(i, len(_extract_action_cards(act)))
                 for i, act in enumerate(action_list)
                 if get_action_type(act) in banned]
        if bombs:
            bombs.sort(key=lambda x: x[1])  # 最少张
            kept = [bombs[0][0]]
        else:
            kept = list(range(len(action_list)))
    return kept


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
    # GUA-071: greaterAction 可能是平台格式 [type, rank, [cards]]，提取实际牌
    greater_cards = _extract_action_cards(greater_action)
    greater_val = get_card_value(greater_cards[0] if greater_cards else (greater_action[0] if len(greater_action) >= 1 else ""), cur_rank)
    has_beating_single = False
    pass_indices = []
    for i, act in enumerate(action_list):
        if get_action_type(act) == ACTION_TYPE_SINGLE:
            # GUA-071: 从 action 提取实际牌
            cards = _extract_action_cards(act)
            val = get_card_value(cards[0] if cards else (act[0] if len(act) >= 1 else ""), cur_rank)
            if val > greater_val:
                has_beating_single = True
                break
    if not has_beating_single:
        # 加个例外：有级牌单张也能压
        for i, act in enumerate(action_list):
            if get_action_type(act) == ACTION_TYPE_SINGLE:
                cards = _extract_action_cards(act)
                r = get_card_rank(cards[0] if cards else (act[0] if len(act) >= 1 else ""))
                if r == "SB" or r == "HR":
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


# ── R11 上家让道 + 炸后相克 模块级追踪（GUA-071）──
# key: (my_pos, upper_opp_pos) → 上家出的、V7跳过的牌型
_UPPER_SKIP_MEMORY: Dict[Tuple[int, int], str] = {}
# key: (my_pos, upper_opp_pos) → 炸后不可再出的牌型（相克）
_POST_BOMB_BLOCK_TYPE: Dict[Tuple[int, int], str] = {}


def _clear_r11_memory_for_game(my_pos: int = None):
    """游戏开始时清理 R11 记忆。"""
    if my_pos is not None:
        keys_to_del = [k for k in _UPPER_SKIP_MEMORY if k[0] == my_pos]
        for k in keys_to_del:
            _UPPER_SKIP_MEMORY.pop(k, None)
            _POST_BOMB_BLOCK_TYPE.pop(k, None)
    else:
        _UPPER_SKIP_MEMORY.clear()
        _POST_BOMB_BLOCK_TYPE.clear()


# ── V7-R11: 全局抑制牌检查 + 节流（GUA-068）────────────

def _compute_pass_num(
    game_state: Dict[str, Any],
    my_pos: int,
) -> Tuple[int, int]:
    """
    从 recentPlays 计算当前轮的连续 PASS 数。

    Returns:
        (pass_num, my_pass_num)
        - pass_num: 本圈已有多少人 PASS
        - my_pass_num: 自己在本圈 PASS 了多少次
    """
    recent = game_state.get("recentPlays", [])
    if not recent:
        return (0, 0)

    pass_num = 0
    my_pass_num = 0
    for rp in reversed(recent):
        cards = rp.get("cards", [])
        if not cards:
            pass_num += 1
            if rp.get("pos", -1) == my_pos:
                my_pass_num += 1
        else:
            break  # 遇到非 PASS → 轮次边界
    return (pass_num, my_pass_num)


def _is_single_beater(played_rank: str, suppressor_rank: str, cur_rank: str) -> bool:
    """
    判断 suppressor_rank 能否在 Single 中压制 played_rank。

    掼蛋单张真实排序：大王 > 小王 > 级牌 > A > K > ... > 2
    """
    # 大王压制一切
    if suppressor_rank == "HR":
        return played_rank != "HR"  # 大王互压需要炸弹
    # 小王压制除大王外一切
    if suppressor_rank == "SB":
        return played_rank not in ("HR", "SB")
    # 级牌压制除王外的所有牌（但同级牌不互压）
    if suppressor_rank == cur_rank:
        return played_rank not in ("HR", "SB", cur_rank)
    # 对方是级牌 → 普通牌无法压制
    if played_rank == cur_rank:
        return False
    # 对方是王 → 普通牌无法压制
    if played_rank in ("HR", "SB"):
        return False
    # 普通牌 → 更大的普通牌可压（但级牌不算普通牌）
    suppressor_base = CARD_RANK_ORDER.get(suppressor_rank, 0)
    played_base = CARD_RANK_ORDER.get(played_rank, 0)
    return suppressor_base > played_base


def _count_remaining_suppressors(
    tracker,  # MemoryTracker 实例
    greater_rank: str,
    cur_rank: str,
) -> int:
    """
    统计全局未打出的「能压制 greater_rank」的牌张数。

    仅统计 Single 维度（对子炸弹暂不涉及）。
    通过 MemoryTracker.get_played_cards() 查询已出数，
    总张数 - 已出 = 剩余可压制数。
    """
    if tracker is None:
        return -1  # 无 tracker 时用节流模式

    try:
        played = tracker.get_played_cards()
    except Exception:
        return -1

    remaining = 0

    # 大王（HR）：共 2 张
    if _is_single_beater(greater_rank, "HR", cur_rank):
        remaining += max(0, 2 - played.get("HR", 0))

    # 小王（SB）：共 2 张
    if _is_single_beater(greater_rank, "SB", cur_rank):
        remaining += max(0, 2 - played.get("SB", 0))

    # 级牌：共 8 张（4 花色 × 2 副本）
    if _is_single_beater(greater_rank, cur_rank, cur_rank):
        for suit in SUITS:
            ct = f"{suit}{cur_rank}"
            remaining += max(0, 2 - played.get(ct, 0))

    # 更高普通牌（A/K/Q...）：每种 8 张
    for r in RANK_STR:
        if r == cur_rank:
            continue  # 级牌已统计
        if _is_single_beater(greater_rank, r, cur_rank):
            for suit in SUITS:
                ct = f"{suit}{r}"
                remaining += max(0, 2 - played.get(ct, 0))

    return remaining


def _rule_r11_unbeatable_card_throttle(
    action_list: List[List[str]],
    greater_action: List[str],
    greater_pos: int,
    my_pos: int,
    cur_rank: str,
    game_state: Dict[str, Any] = None,
) -> List[int]:
    """
    V7-R11（GUA-068）：对手出不可压牌时的全局抑制牌检查 + 节流。

    两阶段决策：
      Phase A（全局检查）：MemoryTracker 查询「还有几张能压住对手的牌」。
        - 剩余 ≥ 2 张 → 断定有他人能压 → 过滤炸弹（保留 PASS/普通牌）
        - 剩余 = 1 张 → 模糊地带（可能队友/对手持有）→ 低 pass_num 时过滤炸弹
        - 剩余 = 0 张 → 真正无人能压 → 进入 Phase B
      Phase B（节流）：无可压制牌时，按紧迫度决定是否炸弹。
        - pass_num < 3 且 my_pass_num < 2 → 过早，过滤炸弹
        - 否则 → 允许炸弹（再不炸可能失控）

    与 M3 _Single() 的关键区别：
      - M3 仅看 pass_num / 对手剩牌，不知道外面还有没有王
      - V7-R11 先查全局牌记忆，有王剩余就放心 PASS，无王才考虑节流
    """
    # ── 前置条件：对手出牌 + 非 PASS ──
    if not greater_action or greater_action[0] == "PASS":
        return list(range(len(action_list)))

    opponent_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]
    if greater_pos not in opponent_positions:
        return list(range(len(action_list)))

    # ── 上家/下家区分 ──
    upper_opp = (my_pos + 3) % 4
    is_upper = (greater_pos == upper_opp)
    gt = get_action_type(greater_action)

    # 非上家的非Single：暂不覆盖（保持原行为）
    if not is_upper and gt != ACTION_TYPE_SINGLE:
        return list(range(len(action_list)))

    # ── 检查自己是否有同型非炸弹可压 ──
    bomb_indices: List[int] = []
    has_same_type_normal = False

    for i, act in enumerate(action_list):
        t = get_action_type(act)
        if t in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            bomb_indices.append(i)
        elif t == gt:
            has_same_type_normal = True

    if has_same_type_normal:
        # 有同型非炸弹可压 → R01/R04 已处理，R11 不干预
        return list(range(len(action_list)))

    if not bomb_indices:
        # 无炸弹可选 → 放行
        return list(range(len(action_list)))

    # ── 上家出不可压牌 → GUA-071 让道（所有牌型，含第二圈检测）──
    if is_upper:
        skip_key = (my_pos, upper_opp)
        prev_skipped = _UPPER_SKIP_MEMORY.get(skip_key)

        if prev_skipped == gt:
            # 第二圈：同样牌型，队友未接 → 允许炸
            del _UPPER_SKIP_MEMORY[skip_key]
            # 记录炸后相克类型：炸了上家的 gt，炸后不可再出 gt
            _POST_BOMB_BLOCK_TYPE[skip_key] = gt
            logger.debug(
                "R11 上家第二轮出%s → 队友未接，允许炸弹（炸后禁出%s），%d炸弹可选",
                gt, gt, len(bomb_indices),
            )
            return list(range(len(action_list)))
        else:
            # 第一圈（或换牌型）：PASS让道
            _UPPER_SKIP_MEMORY[skip_key] = gt
            # 清除旧相克记录（牌型变了）
            _POST_BOMB_BLOCK_TYPE.pop(skip_key, None)
            kept = [i for i in range(len(action_list)) if i not in bomb_indices]
            if kept:
                logger.debug(
                    "R11 上家出%s无同型可压 → 让道PASS，过滤 %d 个炸弹",
                    gt, len(bomb_indices),
                )
                return kept
            # 只剩炸弹可选 → 没得选，放行（含 PASS）
            return list(range(len(action_list)))

    # ── 下家出牌：Single 走原逻辑，非 Single 放行 ──
    if gt != ACTION_TYPE_SINGLE:
        return list(range(len(action_list)))

    # ── Phase A: 全局抑制牌检查（下家出 Single）──
    tracker = game_state.get("_memory_tracker", None) if game_state else None
    greater_rank = get_action_rank(greater_action)
    suppressors_remaining = _count_remaining_suppressors(tracker, greater_rank, cur_rank)

    # Phase A-1: 抑制牌充足（≥2）→ 坚决 PASS，让队友/对手自然压
    if suppressors_remaining >= 2:
        kept = [i for i in range(len(action_list)) if i not in bomb_indices]
        if kept:
            logger.debug(
                "R11 抑制牌充足(剩余%d张可压%s) → 过滤 %d 个炸弹",
                suppressors_remaining, greater_rank, len(bomb_indices),
            )
            return kept

    # Phase A-2: 仅剩 1 张抑制牌 → 队友还没回应时可以等（pass_num==0）
    if suppressors_remaining == 1:
        pass_num, _ = _compute_pass_num(game_state or {}, my_pos)
        if pass_num == 0:
            kept = [i for i in range(len(action_list)) if i not in bomb_indices]
            if kept:
                logger.debug(
                    "R11 抑制牌仅剩1张 pass_num=0 → 等等看，过滤 %d 个炸弹",
                    len(bomb_indices),
                )
                return kept
        # pass_num >= 1 → 有人已 PASS，那1张可能不在他们手里，允许炸弹

    # Phase A-3: 抑制牌为 0 → 真正无人能压，允许炸弹
    # （再等也没用，不如抢牌权）

    # 其余情况：允许炸弹
    return list(range(len(action_list)))


# ── V7-R12: 三带二最小带对（GUA-064 发现）──────────────

def _rule_r12_min_pair_in_three_with_two(
    action_list: List[List[str]],
) -> List[int]:
    """
    V7-R12（GUA-064 副场发现）：三带二最小带对。

    当同一三张 rank 存在多个 ThreeWithTwo 变体（带不同对子）时：
      保留带最小对子的那个，剔除带更大对子的变体。
    节约大对子作为后续独立出牌资源。

    例如：手牌 777, 44, 66, AA → ThreeWithTwo 候选可能有 777-44, 777-66, 777-AA
    → 保留 777-44（最小对子），剔除 777-66 和 777-AA。
    → 若选 777-AA，浪费 AA 对子，后续出 44/66 容易被压导致烂牌。

    不干预不同三张 rank 的 ThreeWithTwo（如 777-44 vs 888-66 各自保留）。
    """
    twt_indices = []
    for i, act in enumerate(action_list):
        if get_action_type(act) == ACTION_TYPE_THREE_WITH_TWO:
            twt_indices.append((i, act))

    if len(twt_indices) <= 1:
        return list(range(len(action_list)))

    # 按三张 rank 分组，计算每组的 pair rank
    from collections import defaultdict
    groups: Dict[str, List[Tuple[int, Optional[str], int]]] = defaultdict(list)

    for idx, act in twt_indices:
        cards = _extract_action_cards(act)
        ranks = [get_card_rank(c) for c in cards]
        rank_counts: Dict[str, int] = {}
        for r in ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1

        triplet_rank = None
        pair_rank = None
        for r, cnt in rank_counts.items():
            if cnt == 3:
                triplet_rank = r
            elif cnt == 2:
                pair_rank = r

        if triplet_rank:
            pair_val = CARD_RANK_ORDER.get(pair_rank, -1)
            groups[triplet_rank].append((idx, pair_rank, pair_val))

    # 同一 triplet rank 组内，保留最小对子，剔除更大对子
    excluded = set()
    for triplet_rank, entries in groups.items():
        if len(entries) <= 1:
            continue
        # 按 pair_val 升序（最小对子在前）
        entries.sort(key=lambda x: x[2])
        kept_entry = entries[0]
        for entry in entries[1:]:
            excluded.add(entry[0])
            logger.debug(
                "R12: 三张%s 剔除 带对%s (保留最小对子%s)",
                triplet_rank, entry[1], kept_entry[1],
            )

    if not excluded:
        return list(range(len(action_list)))

    kept = [i for i in range(len(action_list)) if i not in excluded]
    if kept:
        return kept
    return list(range(len(action_list)))


# ── V7-R14: 领出不拆天然牌型（GUA-064 副场延伸）────────

def _rule_r14_no_break_pattern_when_lead(
    action_list: List[List[str]],
    hand_cards: List[str],
    greater_pos: int,
    my_pos: int,
    numofplayers: List[int] = None,
) -> List[int]:
    """
    V7-R14：领出时不拆天然牌型。

    当自己领出时（新轮），手牌中存在天然对子/三张等完整牌型时，
    应出完整牌型而非拆散。过滤掉从天然牌型中拆出子集的拆牌动作。

    天然牌型定义：
      - 天然对子：手牌中恰好出现 2 次的 rank → 该 rank 的 Single 是拆牌
      - 天然三张：手牌中恰好出现 3 次的 rank → 该 rank 的 Single/Pair 是拆牌

    例如：手牌 S4,D4,S6,D6,SB
      → 天然对子 4-4（rank 4 出现2次）和 6-6（rank 6 出现2次）
      → 过滤 Single S4/D4/S6/D6（拆对子），保留 Pair 44/66 + Single SB

    例外：R08 队友剩 1 张需要送单时，送单优先于保对子（不触发）。
    """
    # ── 领出判定 ──
    is_lead = (greater_pos == -1) or (0 <= my_pos <= 3 and greater_pos == my_pos)
    if not is_lead:
        return list(range(len(action_list)))

    # ── R08 例外：队友剩 1 张且自己领出 → 送单优先，不保对子 ──
    if numofplayers and len(numofplayers) >= 4:
        teammate = (my_pos + 2) % 4
        if numofplayers[teammate] == 1:
            return list(range(len(action_list)))

    # ── 统计手牌中的天然牌型 ──
    from collections import Counter
    hand_ranks = Counter(get_card_rank(c) for c in hand_cards)

    # 天然对子：恰好 2 张
    natural_pairs: Dict[str, bool] = {
        r: True for r, cnt in hand_ranks.items() if cnt == 2
    }
    # 天然三张：恰好 3 张
    natural_trips: Dict[str, bool] = {
        r: True for r, cnt in hand_ranks.items() if cnt == 3
    }

    if not natural_pairs and not natural_trips:
        return list(range(len(action_list)))

    # ── 检查每个 action 是否拆了天然牌型 ──
    excluded: set = set()
    for i, act in enumerate(action_list):
        act_type = get_action_type(act)
        if act_type == ACTION_TYPE_PASS:
            continue

        cards = _extract_action_cards(act)
        act_ranks = Counter(get_card_rank(c) for c in cards)

        for rank, used_count in act_ranks.items():
            if rank in natural_pairs:
                # 天然对子 → 用了其中 1 张就是拆对子
                if used_count == 1:
                    excluded.add(i)
                    logger.debug(
                        "R14: 领出拆对子 rank=%s (天然2张→用了%d张) 剔除 idx=%d",
                        rank, used_count, i,
                    )
            elif rank in natural_trips:
                # 天然三张 → 用了其中 1~2 张就是拆三张
                if used_count in (1, 2):
                    excluded.add(i)
                    logger.debug(
                        "R14: 领出拆三张 rank=%s (天然3张→用了%d张) 剔除 idx=%d",
                        rank, used_count, i,
                    )

    if not excluded:
        return list(range(len(action_list)))

    kept = [i for i in range(len(action_list)) if i not in excluded]
    if kept:
        return kept
    return list(range(len(action_list)))


# ── GUA-065 队友保护规则 ──────────────────────────────

def _rule_r07_teammate_yield(
    action_list: List[List[str]],
    greater_pos: int,
    my_pos: int,
    numofplayers: List[int],
    greater_action: List[str] = None,
    cur_rank: str = "2",
) -> List[int]:
    """
    V7-R07（GUA-065 + 决议 9 细化）：队友控牌时按牌型阈值让道。

    决议 9 升级（2026-06-19）：从一刀切改为按 6 种牌型的 curVal 阈值分别判断。
    等价 M3 的 _Single/_Pair/_Three/... 各自 curVal 判断逻辑。

    阈值表：
      - Single:         curVal >= 15 → 让道
      - Pair:           curVal >= 12 → 让道
      - Trips:          curVal >= 11 → 让道
      - ThreeWithTwo:   curVal >= 12 → 让道
      - Straight:       curVal >= 10 → 让道
      - StraightFlush:  curVal >= 10 → 让道
      - Bomb/Unknown:   保持原行为（只留 PASS）

    队友近尾例外：numoffri <= 4 → 不让道，返回全部（帮队友冲线）。
    """
    teammate = (my_pos + 2) % 4
    if greater_pos != teammate:
        return list(range(len(action_list)))

    if not numofplayers or len(numofplayers) < 4:
        return list(range(len(action_list)))

    numofmy = numofplayers[my_pos]
    if numofmy <= 10:
        # 自己已进入残局冲刺 → 不放行，需积极出牌
        return list(range(len(action_list)))

    # ── 决议 9: 队友近尾例外 ──
    numoffri = numofplayers[teammate]
    if numoffri <= 4:
        # 队友快走完了，不让道，帮队友冲线
        return list(range(len(action_list)))

    # ── 读取 greaterAction ──
    if greater_action is None or not greater_action or greater_action[0] == "PASS":
        # 队友 PASS 了 → 实际上队友没控牌，不触发让道
        return list(range(len(action_list)))

    ga_type = get_action_type(greater_action)
    # greater_action 可能是 ["Single", "S2", ["S2"]] 格式，get_action_type 对前2元素不识别
    # 从 card list (元素[2]) 重新判定牌型
    if ga_type == ACTION_TYPE_FREE and len(greater_action) >= 3:
        ga_type = get_action_type(greater_action[2])

    if ga_type == ACTION_TYPE_PASS or ga_type == ACTION_TYPE_FREE:
        return list(range(len(action_list)))

    # ── 决议 9: 按牌型 curVal 阈值 ──
    # Bomb/StraightFlush: 保持原行为（curVal 无关，只留 PASS）
    if ga_type in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
        pass_indices = [i for i, act in enumerate(action_list)
                        if get_action_type(act) == ACTION_TYPE_PASS]
        if pass_indices:
            logger.debug("R07 细化: 队友出炸/同花顺 → 只留 PASS")
            return pass_indices
        return list(range(len(action_list)))

    # 计算 curVal
    cur_val = 0
    if ga_type == ACTION_TYPE_SINGLE:
        cur_val = get_card_value(greater_action[1], cur_rank) if len(greater_action) >= 2 else 99
    elif ga_type == ACTION_TYPE_PAIR:
        rank = get_action_rank(greater_action)
        cur_val = CARD_RANK_ORDER.get(rank, 99)
    elif ga_type in (ACTION_TYPE_TRIPS, ACTION_TYPE_THREE_WITH_TWO, ACTION_TYPE_STRAIGHT):
        rank = get_action_rank(greater_action)
        cur_val = CARD_RANK_ORDER.get(rank, 99)
    else:
        # 未知牌型 → 保守，不让道
        return list(range(len(action_list)))

    # 按牌型阈值判断
    thresholds = {
        ACTION_TYPE_SINGLE: 15,
        ACTION_TYPE_PAIR: 12,
        ACTION_TYPE_TRIPS: 11,
        ACTION_TYPE_THREE_WITH_TWO: 12,
        ACTION_TYPE_STRAIGHT: 10,
        ACTION_TYPE_STRAIGHT_FLUSH: 10,
    }
    threshold = thresholds.get(ga_type, 99)

    if cur_val >= threshold:
        # 队友出高牌 → 安全让道，只留 PASS
        pass_indices = [i for i, act in enumerate(action_list)
                        if get_action_type(act) == ACTION_TYPE_PASS]
        if pass_indices:
            logger.debug("R07 细化: 队友%s curVal=%d>=%d → 让道 PASS",
                         ga_type, cur_val, threshold)
            return pass_indices
        return list(range(len(action_list)))

    # curVal 低于阈值 → 不让道（对手可能压队友，自己应参与）
    return list(range(len(action_list)))


def _rule_r08_feed_teammate_single(
    action_list: List[List[str]],
    cur_pos: int,
    my_pos: int,
    numofplayers: List[int],
    cur_rank: str,
) -> List[int]:
    """
    V7-R08（GUA-065）：主动 + 队友剩 1 张 → 出最小 Single 送队友。
    等价 M3 `_gua031_active_min_single`。
    """
    if cur_pos != my_pos and cur_pos != -1:
        return list(range(len(action_list)))

    if not numofplayers or len(numofplayers) < 4:
        return list(range(len(action_list)))

    teammate = (my_pos + 2) % 4
    numoffri = numofplayers[teammate]

    # 仅当队友确实只剩 1 张时才触发
    if numoffri != 1:
        return list(range(len(action_list)))

    # 找所有 Single 选项
    singles = []
    for i, act in enumerate(action_list):
        if get_action_type(act) == ACTION_TYPE_SINGLE:
            # GUA-071: 从 action 提取实际牌（兼容平台格式 [type, rank, [cards]]）
            cards = _extract_action_cards(act)
            val = get_card_value(cards[0] if cards else act[0], cur_rank)
            singles.append((i, val))

    if not singles:
        return list(range(len(action_list)))

    # 队友剩 1 张 → 出最小单（最容易接）
    singles.sort(key=lambda x: x[1])
    best_idx = singles[0][0]

    # 保留最优单牌 + PASS
    kept = [i for i in range(len(action_list))
            if i == best_idx or get_action_type(action_list[i]) == ACTION_TYPE_PASS]
    return kept if kept else list(range(len(action_list)))


def _rule_r09_feed_teammate_5(
    action_list: List[List[str]],
    cur_pos: int,
    my_pos: int,
    numofplayers: List[int],
) -> List[int]:
    """
    V7-R09（GUA-065 / Q1）：主动 + 队友剩 5 张 → 按 assist_prefer_for(5) 过滤。

    与 EndgameDecider Q2 / stage_assist_feed 共用 assist_prefer_table 单一真源。
    """
    if cur_pos != my_pos and cur_pos != -1:
        return list(range(len(action_list)))

    if not numofplayers or len(numofplayers) < 4:
        return list(range(len(action_list)))

    teammate = (my_pos + 2) % 4
    numoffri = numofplayers[teammate]

    if numoffri != 5:
        return list(range(len(action_list)))

    from src.v.nn.assist_prefer_table import assist_prefer_for

    prefer = assist_prefer_for(5)
    feed_indices: List[int] = []
    seen = set()
    for pref_type in prefer:
        for i, act in enumerate(action_list):
            if i in seen:
                continue
            if get_action_type(act) == pref_type:
                feed_indices.append(i)
                seen.add(i)

    if not feed_indices:
        return list(range(len(action_list)))

    pass_indices = [i for i, act in enumerate(action_list)
                    if get_action_type(act) == ACTION_TYPE_PASS]
    kept = feed_indices + pass_indices
    ordered: List[int] = []
    seen.clear()
    for i in kept:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    return ordered if ordered else list(range(len(action_list)))


# ═══════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════

# ── Guard 管道职责边界（GUA-073 整理，2026-06-19）────
#
# 决策管线三层：
#   Layer 1: Guard 过滤（本文件）→ 硬排除错误动作
#     - 只用"移除"语义：返回保持的子集，多条规则 UNION 叠加
#     - 不参与排序/打分/选择，不负责"哪个更好"
#   Layer 2: Heuristic 选择（engine._heuristic_select）→ 软排序合理动作
#     - 在 Guard 保留的动作中按优先级打分
#     - 规则：组局一致性 > 场景感知 > 牌力节约
#   Layer 3: validate_decision（本文件底部）→ 安全网兜底
#     - 覆盖 NN/heuristic 选择的错误决策（PASS 强制/炸队友覆盖）
#
# 新增规则 checklist：
#   - Guard 规则：问"这个动作应该被排除吗？"→ 是 → 加进本文件
#   - Heuristic 规则：问"这两个合法动作哪个更好？"→ 是 → 加进 engine._heuristic_select
#   - 不要同时在两层写相同逻辑（如 Guard 删炸弹 + Heuristic 也扣炸弹分）


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
    cur_pos = game_state.get("curPos", -1)
    # 防御：greaterAction 可能为 None（首出牌或无压牌场景）
    if greater_action is None:
        greater_action = []
    if isinstance(greater_action, str):
        import ast
        try:
            greater_action = ast.literal_eval(greater_action)
        except (ValueError, SyntaxError):
            greater_action = []
    # 防御：过滤列表中可能的 None 元素（脏数据）
    if isinstance(greater_action, list):
        greater_action = [a for a in greater_action if a is not None]
    cur_rank = game_state.get("curRank", "2")
    hand_cards = game_state.get("handCards", [])
    numofplayers = game_state.get("numofplayers", [])

    # 收集各规则产生的 index 约束
    # 用 set 累积被排除的索引
    excluded = set()

    # 0) R10: 自己领出不炸（greaterPos == myPos 或 -1 → 新轮领出 → 炸自己）
    r10_kept = _rule_r10_no_lead_bomb(action_list, greater_pos, my_pos)
    excluded |= {i for i in range(len(action_list)) if i not in set(r10_kept)}

    # 0.5) R15: 炸后相克 — 炸了上家的牌型后，自己领出时禁出该牌型（GUA-071）
    if greater_pos in (my_pos, -1) and (not greater_action or greater_action[0] == "PASS"):
        block_key = (my_pos, (my_pos + 3) % 4)
        block_type = _POST_BOMB_BLOCK_TYPE.get(block_key)
        if block_type:
            blocked = {i for i, act in enumerate(action_list)
                       if get_action_type(act) == block_type}
            if blocked:
                _POST_BOMB_BLOCK_TYPE.pop(block_key, None)  # 消费一次
                excluded |= blocked
                logger.debug(
                    "R15 炸后相克：禁出%s（炸了上家该牌型，%d个动作被过滤）",
                    block_type, len(blocked),
                )

    # 1) R05: 队友领出不炸
    r05_kept = _rule_r05_teammate_no_bomb(
        action_list, greater_action, greater_pos, my_pos)
    excluded |= {i for i in range(len(action_list)) if i not in set(r05_kept)}

    # 1.5) R11: 对手出不可压牌 → 全局抑制牌检查 + 节流（GUA-068）
    r11_kept = _rule_r11_unbeatable_card_throttle(
        action_list, greater_action, greater_pos, my_pos, cur_rank, game_state)
    excluded |= {i for i in range(len(action_list)) if i not in set(r11_kept)}

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

    # 4.5) R12: 三带二最小带对（同一三张 rank 多个变体 → 保留最小对子）
    r12_kept = _rule_r12_min_pair_in_three_with_two(action_list)
    excluded |= {i for i in range(len(action_list)) if i not in set(r12_kept)}

    # 4.6) R14: 领出不拆天然牌型（有天然对子/三张时 → 剔除拆散动作）
    r14_kept = _rule_r14_no_break_pattern_when_lead(
        action_list, hand_cards, greater_pos, my_pos, numofplayers)
    excluded |= {i for i in range(len(action_list)) if i not in set(r14_kept)}

    # 5) GUA-065 R07: 队友控牌且非残局 → 按牌型阈值让道（决议 9 细化）
    if numofplayers:
        r07_kept = _rule_r07_teammate_yield(
            action_list, greater_pos, my_pos, numofplayers, greater_action, cur_rank)
        excluded |= {i for i in range(len(action_list)) if i not in set(r07_kept)}

    # 6) GUA-117 Layer0：助攻/超弱 B1–B6 + 让权（117-2a … 117-2g）
    try:
        from src.v.nn.guards.assist_layer0_guard import apply_assist_layer0_exclusions
        apply_assist_layer0_exclusions(action_list, game_state, excluded)
    except Exception as e:
        logger.warning("GUA-117 assist Layer0 异常: %s", e)

    # 5.5) GUA-071 R13: 平台炸弹合法性校验
    # 平台可能将非炸弹（如 3 Aces+单张）标为 Bomb，但 V7 get_action_type 正确识别为非炸弹。
    # R01~R02 只用 get_action_type 判断炸弹类型 → 假炸弹以 Free 形态溜过 Guard。
    # 此规则检查：平台标 Bomb/StraightFlush 但实际牌型不符 → 直接剔除。
    forbidden = set()
    for i, act in enumerate(action_list):
        if isinstance(act, list) and len(act) >= 1 and act[0] in ("Bomb", "StraightFlush"):
            real_type = get_action_type(act)
            if real_type not in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
                forbidden.add(i)
    if forbidden:
        excluded |= forbidden
        logger.warning(
            "R13 平台炸弹校验: 剔除 %d 个假炸弹/同花顺 (平台标记为 Bomb 但实际牌型不符)",
            len(forbidden),
        )

    # R03/R04 重排（不真正剔除，影响后续模型选择顺序）
    # 这些规则不剔除元素，只返回排序
    r03_order = _rule_r03_passive_no_pass(
        action_list, greater_action, greater_pos, my_pos)
    r04_order = _rule_r04_single_b_non_pass(
        action_list, greater_action, greater_pos, my_pos, cur_rank)

    # GUA-065 R08/R09 重排（队友送牌优先）
    r08_order = list(range(len(action_list)))
    r09_order = list(range(len(action_list)))
    if numofplayers:
        r08_order = _rule_r08_feed_teammate_single(
            action_list, cur_pos, my_pos, numofplayers, cur_rank)
        r09_order = _rule_r09_feed_teammate_5(
            action_list, cur_pos, my_pos, numofplayers)

    # 构建最终过滤列表
    kept = [i for i in range(len(action_list)) if i not in excluded]
    if not kept:
        # 全被过滤了 → 保留全部
        kept = list(range(len(action_list)))

    # 应用重排（R03/R04/R08/R09 同时适用时，取交集顺序）
    final_order = kept[:]
    for ordering in (r03_order, r04_order, r08_order, r09_order):
        filtered_order = [i for i in ordering if i in set(kept)]
        if filtered_order and filtered_order != final_order:
            final_order = filtered_order

    filtered = [action_list[i] for i in final_order]

    logger.debug(
        "filter_action_list: %d→%d actions (excluded %d rules: R10=%s R05=%s R11=%s R01=%s R02=%s R06=%s R12=%s R14=%s R07=%s)",
        len(action_list), len(filtered), len(excluded),
        len(action_list) - len(r10_kept) if r10_kept != list(range(len(action_list))) else 0,
        len(action_list) - len(r05_kept) if r05_kept != list(range(len(action_list))) else 0,
        len(action_list) - len(r11_kept) if r11_kept != list(range(len(action_list))) else 0,
        len(action_list) - len(r01_kept) if r01_kept != list(range(len(action_list))) else 0,
        len(action_list) - len(r02_kept) if r02_kept != list(range(len(action_list))) else 0,
        len(action_list) - len(r06_kept) if r06_kept != list(range(len(action_list))) else 0,
        len(action_list) - len(r12_kept) if r12_kept != list(range(len(action_list))) else 0,
        len(action_list) - len(r14_kept) if r14_kept != list(range(len(action_list))) else 0,
        len(action_list) - len(r07_kept) if numofplayers and r07_kept != list(range(len(action_list))) else 0,
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
    if greater_action is None:
        greater_action = []
    if isinstance(greater_action, str):
        import ast
        try:
            greater_action = ast.literal_eval(greater_action)
        except (ValueError, SyntaxError):
            greater_action = []
    if isinstance(greater_action, list):
        greater_action = [a for a in greater_action if a is not None]
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
    elif is_bomb(chosen) and (greater_pos == -1 or greater_pos == my_pos):
        # R10: 自己领出用炸弹 → 不合理，找非炸动作
        non_bomb = [i for i, act in enumerate(filtered_actions)
                    if not is_bomb(act)]
        if non_bomb:
            logger.info("validate_decision: 覆盖领出炸弹 (idx %d → %d)", model_idx, non_bomb[0])
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

    # 3) Q12: Solo 模式强化 — 队友已走完 + 对手出牌 + 模型选 PASS → 强制用同型压制
    numofplayers = game_state.get("numofplayers", [])
    if (chosen_type == ACTION_TYPE_PASS and numofplayers and
            len(numofplayers) >= 4):
        teammate = (my_pos + 2) % 4
        if numofplayers[teammate] == 0:
            # Solo: 队友已走完，只剩自己对抗两个对手
            if greater_action and greater_action[0] != "PASS":
                if greater_pos in opponent_positions:
                    greater_type = get_action_type(greater_action)
                    # 优先同型，其次任意非 PASS 非炸弹
                    same_type = [i for i, act in enumerate(filtered_actions)
                                 if get_action_type(act) == greater_type]
                    if same_type:
                        logger.info("validate_decision: Solo 覆盖 PASS → 同型压制 (idx %d → %d)",
                                    model_idx, same_type[0])
                        return same_type[0]
                    # 无同型 → 找任意非炸弹非PASS动作
                    any_counter = [i for i, act in enumerate(filtered_actions)
                                   if get_action_type(act) not in
                                   (ACTION_TYPE_PASS, ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH)]
                    if any_counter:
                        logger.info("validate_decision: Solo 覆盖 PASS → 非炸压制 (idx %d → %d)",
                                    model_idx, any_counter[0])
                        return any_counter[0]

    return model_idx


def get_hand_card_counts(game_state: Dict[str, Any]) -> Dict[str, int]:
    """辅助：统计手牌各 rank 出现次数。"""
    from collections import Counter
    hand = game_state.get("handCards", [])
    return Counter(get_card_rank(c) for c in hand)
