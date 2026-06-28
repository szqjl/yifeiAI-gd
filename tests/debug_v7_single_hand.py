# -*- coding: utf-8 -*-
"""
V7 单手牌调试脚本 — 喂手牌 + 模拟对手出牌 → 观察 V7 决策

用法：
  python tests/debug_v7_single_hand.py              # 跑预设场景
  python tests/debug_v7_single_hand.py --interactive # 交互模式（TODO）

参照组牌引擎的 pytest 秒级反馈模式，对 V7 行牌决策做单步调试。
"""

import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from itertools import combinations
from collections import Counter

# 项目根
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
from src.v.nn.guards.v7_guards import (
    get_action_type, get_action_rank, get_card_rank, get_card_value,
    ACTION_TYPE_PASS, ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR,
    ACTION_TYPE_TRIPS, ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
    ACTION_TYPE_THREE_PAIR, ACTION_TYPE_TWO_TRIPS, ACTION_TYPE_THREE_WITH_TWO,
    ACTION_TYPE_STRAIGHT, ACTION_TYPE_FREE,
    CARD_RANK_ORDER, SUITS,
    _is_consecutive_ranks, _is_same_suit,
)

# ── 日志 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("debug_v7")

# ── 常量 ──────────────────────────────────────────────
RANK_STR = ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")
RANK_ORDER = {r: i for i, r in enumerate(RANK_STR)}  # 2=0 … A=12

# ── 辅助：构造手牌 ────────────────────────────────────

def make_hand(*ranks: str) -> List[str]:
    """从 rank 列表构造手牌（自动分配花色）。"""
    cards = []
    suit_cycle = ["S", "H", "C", "D"]
    for i, r in enumerate(ranks):
        if r in ("SB", "HR"):
            cards.append(r)  # 王不加花色
        else:
            suit = suit_cycle[i % 4]
            cards.append(f"{suit}{r}")
    return cards


def make_action(type_str: str, rank_str: str, cards: List[str]) -> List:
    """构造平台格式 action：[type, rank, [cards...]]。"""
    return [type_str, rank_str, cards]


PASS_ACTION = ["PASS", "", []]

# ═══════════════════════════════════════════════════════
#  ActionList 生成器（轻量，覆盖常见牌型）
# ═══════════════════════════════════════════════════════

def _rank_cards_by_rank(hand: List[str], cur_rank: str = "2") -> Dict[str, List[str]]:
    """按 rank 分组手牌。"""
    groups: Dict[str, List[str]] = {}
    for c in hand:
        r = get_card_rank(c)
        groups.setdefault(r, []).append(c)
    return groups


def _rank_sort_key(rank: str) -> int:
    """排序键：王 > A > K > ... > 2。"""
    if rank == "HR":
        return 100
    if rank == "SB":
        return 99
    return RANK_ORDER.get(rank, -1)


def _gen_singles(rank_groups: Dict[str, List[str]],
                 greater_action: List) -> List[List]:
    """生成所有合法 Single 出牌。"""
    actions = []
    need_beat = greater_action and greater_action[0] != "PASS"
    gt_type = get_action_type(greater_action) if need_beat else None
    gt_rank = get_action_rank(greater_action) if need_beat else None

    if need_beat and gt_type != ACTION_TYPE_SINGLE:
        return actions  # 不是单张→不能出单张

    for r, cards in sorted(rank_groups.items(), key=lambda x: _rank_sort_key(x[0])):
        if gt_rank and _rank_sort_key(r) <= _rank_sort_key(gt_rank):
            continue
        for c in cards:
            actions.append(make_action(ACTION_TYPE_SINGLE, r, [c]))
    return actions


def _gen_pairs(rank_groups: Dict[str, List[str]],
               greater_action: List) -> List[List]:
    """生成所有合法 Pair 出牌。"""
    actions = []
    need_beat = greater_action and greater_action[0] != "PASS"
    gt_type = get_action_type(greater_action) if need_beat else None
    gt_rank = get_action_rank(greater_action) if need_beat else None

    if need_beat and gt_type != ACTION_TYPE_PAIR:
        return actions

    for r, cards in sorted(rank_groups.items(), key=lambda x: _rank_sort_key(x[0])):
        if len(cards) < 2:
            continue
        if gt_rank and _rank_sort_key(r) <= _rank_sort_key(gt_rank):
            continue
        for combo in combinations(cards, 2):
            actions.append(make_action(ACTION_TYPE_PAIR, r, list(combo)))
    return actions


def _gen_trips(rank_groups: Dict[str, List[str]],
               greater_action: List) -> List[List]:
    """生成所有合法 Trips 出牌。"""
    actions = []
    need_beat = greater_action and greater_action[0] != "PASS"
    gt_type = get_action_type(greater_action) if need_beat else None
    gt_rank = get_action_rank(greater_action) if need_beat else None

    if need_beat and gt_type != ACTION_TYPE_TRIPS:
        return actions

    for r, cards in sorted(rank_groups.items(), key=lambda x: _rank_sort_key(x[0])):
        if len(cards) < 3:
            continue
        if gt_rank and _rank_sort_key(r) <= _rank_sort_key(gt_rank):
            continue
        for combo in combinations(cards, 3):
            actions.append(make_action(ACTION_TYPE_TRIPS, r, list(combo)))
    return actions


def _gen_bombs(rank_groups: Dict[str, List[str]],
               cur_rank: str = "2") -> List[List]:
    """生成所有炸弹（4同点 / 王炸 / 含逢人配的炸弹）。"""
    actions = []

    # 1. 普通炸弹（4张同点）
    for r, cards in sorted(rank_groups.items(), key=lambda x: _rank_sort_key(x[0])):
        if len(cards) >= 4:
            for combo in combinations(cards, 4):
                actions.append(make_action(ACTION_TYPE_BOMB, r, list(combo)))
        # 含逢人配的炸弹（3张同点 + H+curRank）
        if len(cards) >= 3 and cur_rank:
            wild = f"H{cur_rank}"
            for combo3 in combinations(cards, 3):
                actions.append(make_action(
                    ACTION_TYPE_BOMB, r, list(combo3) + [wild]))

    # 2. 王炸（SB + HR）
    sb_list = rank_groups.get("SB", [])
    hr_list = rank_groups.get("HR", [])
    if sb_list and hr_list:
        actions.append(make_action(ACTION_TYPE_BOMB, "HR",
                                   [hr_list[0], sb_list[0]] +
                                   (hr_list[1:] if len(hr_list) > 1 else []) +
                                   (sb_list[1:] if len(sb_list) > 1 else [])))

    return actions


def _gen_straights(rank_groups: Dict[str, List[str]],
                   cur_rank: str = "2",
                   greater_action: List = None) -> List[List]:
    """生成所有顺子（5+ 连号，不同花）。

    Args:
        greater_action: 如果需要跟牌，传入对手顺子，只生成起始 rank 更高的同长度顺子
    """
    # 收集每个 rank 可用的花色
    rank_suits: Dict[str, List[str]] = {}
    for r, cards in rank_groups.items():
        if r in ("SB", "HR"):
            continue
        rank_suits[r] = cards

    available_ranks = sorted([r for r in rank_suits.keys()],
                             key=_rank_sort_key)
    actions = []

    # 跟牌约束：必须同长度且起始 rank 更高
    min_start_rank = None
    required_length = None
    if greater_action and greater_action[0] != "PASS":
        gt_type = get_action_type(greater_action)
        if gt_type == ACTION_TYPE_STRAIGHT:
            gt_cards = greater_action[2] if len(greater_action) >= 3 else []
            required_length = len(gt_cards)
            gt_start = greater_action[1]  # 对手顺子的起始 rank
            min_start_rank = _rank_sort_key(gt_start) + 1  # 必须严格更大

    for start_idx in range(len(available_ranks)):
        # 跟牌：起始 rank 必须大于对手
        if min_start_rank is not None:
            start_rk = available_ranks[start_idx]
            if _rank_sort_key(start_rk) < min_start_rank:
                continue

        for length in range(5, len(available_ranks) - start_idx + 1):
            seq = available_ranks[start_idx:start_idx + length]
            # 跟牌：长度必须相同
            if required_length is not None and len(seq) != required_length:
                continue
            indices = [RANK_ORDER.get(r, 99) for r in seq]
            if not all(indices[i+1] - indices[i] == 1 for i in range(len(indices)-1)):
                continue  # 不连续
            # 从每个 rank 各取一张，组合所有花色
            from itertools import product as cartesian_product
            card_lists = [rank_suits[r] for r in seq]
            for combo in cartesian_product(*card_lists):
                suits_in = [c[0] for c in combo if len(c) >= 2]
                if _is_same_suit(suits_in):
                    continue  # 同花 → 这是同花顺，不走 Straight
                actions.append(make_action(
                    ACTION_TYPE_STRAIGHT, seq[0], list(combo)))
    return actions


def _gen_straight_flushes(rank_groups: Dict[str, List[str]],
                          cur_rank: str = "2",
                          greater_action: List = None) -> List[List]:
    """生成所有同花顺。跟牌时只生成起始 rank 更高的同长度同花顺。"""
    actions = []
    # 跟牌约束
    min_start_rank = None
    required_length = None
    if greater_action and greater_action[0] != "PASS":
        gt_type = get_action_type(greater_action)
        if gt_type == ACTION_TYPE_STRAIGHT_FLUSH:
            gt_cards = greater_action[2] if len(greater_action) >= 3 else []
            required_length = len(gt_cards)
            gt_start = greater_action[1]
            min_start_rank = _rank_sort_key(gt_start) + 1
    # 按花色分组
    suit_ranks: Dict[str, Dict[str, List[str]]] = {}
    for r, cards in rank_groups.items():
        if r in ("SB", "HR"):
            continue
        for c in cards:
            s = c[0] if len(c) >= 2 else ""
            if s not in SUITS:
                continue
            suit_ranks.setdefault(s, {}).setdefault(r, []).append(c)

    for suit, r_grp in suit_ranks.items():
        avail = sorted([r for r in r_grp.keys()], key=_rank_sort_key)
        for start_idx in range(len(avail)):
            # 跟牌：起始 rank 必须大于对手
            if min_start_rank is not None:
                start_rk = avail[start_idx]
                if _rank_sort_key(start_rk) < min_start_rank:
                    continue
            for length in range(5, len(avail) - start_idx + 1):
                seq = avail[start_idx:start_idx + length]
                # 跟牌：长度必须相同
                if required_length is not None and len(seq) != required_length:
                    continue
                indices = [RANK_ORDER.get(r, 99) for r in seq]
                if not all(indices[i+1] - indices[i] == 1
                           for i in range(len(indices)-1)):
                    continue
                from itertools import product as cartesian_product
                card_lists = [r_grp[r] for r in seq]
                for combo in cartesian_product(*card_lists):
                    actions.append(make_action(
                        ACTION_TYPE_STRAIGHT_FLUSH, seq[0], list(combo)))
    return actions


def _gen_three_pair(rank_groups: Dict[str, List[str]],
                    greater_action: List = None) -> List[List]:
    """生成三连对 (如 33 44 55)。跟牌时只生成起始 rank 更高的三连对。"""
    actions = []
    pair_ranks = sorted(
        [r for r, cards in rank_groups.items()
         if len(cards) >= 2 and r not in ("SB", "HR")],
        key=_rank_sort_key)

    # 跟牌约束
    min_start_rank = None
    if greater_action and greater_action[0] != "PASS":
        gt_type = get_action_type(greater_action)
        if gt_type == ACTION_TYPE_THREE_PAIR:
            gt_start = greater_action[1]
            min_start_rank = _rank_sort_key(gt_start) + 1

    for start_idx in range(len(pair_ranks) - 2):
        seq = pair_ranks[start_idx:start_idx + 3]
        # 跟牌：起始 rank 必须大于对手
        if min_start_rank is not None:
            start_rk = seq[0]
            if _rank_sort_key(start_rk) < min_start_rank:
                continue
        indices = [RANK_ORDER.get(r, 99) for r in seq]
        if not all(indices[i+1] - indices[i] == 1 for i in range(2)):
            continue
        from itertools import product as cartesian_product
        card_lists = [
            list(combinations(rank_groups[r], 2)) for r in seq
        ]
        for combo in cartesian_product(*card_lists):
            all_cards = []
            for pair in combo:
                all_cards.extend(pair)
            actions.append(make_action(
                ACTION_TYPE_THREE_PAIR, seq[0], all_cards))
    return actions


def _gen_two_trips(rank_groups: Dict[str, List[str]],
                   greater_action: List = None) -> List[List]:
    """生成钢板 (如 333 444)。跟牌时只生成起始 rank 更高的钢板。"""
    actions = []
    trip_ranks = sorted(
        [r for r, cards in rank_groups.items()
         if len(cards) >= 3 and r not in ("SB", "HR")],
        key=_rank_sort_key)

    # 跟牌约束
    min_start_rank = None
    if greater_action and greater_action[0] != "PASS":
        gt_type = get_action_type(greater_action)
        if gt_type == ACTION_TYPE_TWO_TRIPS:
            gt_start = greater_action[1]
            min_start_rank = _rank_sort_key(gt_start) + 1

    for start_idx in range(len(trip_ranks) - 1):
        seq = trip_ranks[start_idx:start_idx + 2]
        # 跟牌：起始 rank 必须大于对手
        if min_start_rank is not None:
            start_rk = seq[0]
            if _rank_sort_key(start_rk) < min_start_rank:
                continue
        indices = [RANK_ORDER.get(r, 99) for r in seq]
        if indices[1] - indices[0] != 1:
            continue
        from itertools import product as cartesian_product
        card_lists = [
            list(combinations(rank_groups[r], 3)) for r in seq
        ]
        for combo in cartesian_product(*card_lists):
            all_cards = []
            for trip in combo:
                all_cards.extend(trip)
            actions.append(make_action(
                ACTION_TYPE_TWO_TRIPS, seq[0], all_cards))
    return actions


def _gen_three_with_two(rank_groups: Dict[str, List[str]],
                        greater_action: List = None) -> List[List]:
    """生成三带二。跟牌时只生成主三张 rank 更高的三带二。"""
    actions = []
    # 跟牌约束
    min_trip_rank = None
    if greater_action and greater_action[0] != "PASS":
        gt_type = get_action_type(greater_action)
        if gt_type == ACTION_TYPE_THREE_WITH_TWO:
            gt_trip_rank = greater_action[1]
            min_trip_rank = _rank_sort_key(gt_trip_rank) + 1

    trip_ranks = [r for r, cards in rank_groups.items()
                  if len(cards) >= 3 and r not in ("SB", "HR")]
    pair_ranks = [r for r, cards in rank_groups.items()
                  if len(cards) >= 2 and r not in ("SB", "HR")]

    for tr in trip_ranks:
        # 跟牌：主三张 rank 必须大于对手
        if min_trip_rank is not None and _rank_sort_key(tr) < min_trip_rank:
            continue
        trip_cards = list(combinations(rank_groups[tr], 3))
        for pr in pair_ranks:
            if pr == tr:
                # 同 rank 需要至少 5 张才能三带二
                if len(rank_groups[tr]) < 5:
                    continue
                pair_cards = list(combinations(
                    [c for c in rank_groups[tr]
                     if c not in trip_cards[0]], 2))
            else:
                pair_cards = list(combinations(rank_groups[pr], 2))
            for tc in trip_cards:
                for pc in pair_cards:
                    actions.append(make_action(
                        ACTION_TYPE_THREE_WITH_TWO, tr,
                        list(tc) + list(pc)))
    return actions


def generate_action_list(hand: List[str],
                         greater_action: Optional[List] = None,
                         cur_rank: str = "2") -> List[List]:
    """
    根据手牌和当前圈最大出牌，生成合法出牌列表。

    Args:
        hand: 手牌列表，如 ["S3","H3","D4","C5",...]
        greater_action: 当前圈最大出牌，None 或 PASS 表示轮到自己领出
        cur_rank: 当前级牌

    Returns:
        actionList（平台格式），包含 PASS
    """
    rank_groups = _rank_cards_by_rank(hand, cur_rank)
    ga = greater_action if greater_action and greater_action[0] != "PASS" else None

    actions: List[List] = [PASS_ACTION]

    # 没有需要压的牌 → 自由出牌（领出）
    if ga is None:
        # 所有牌型均可出
        actions.extend(_gen_singles(rank_groups, PASS_ACTION))
        actions.extend(_gen_pairs(rank_groups, PASS_ACTION))
        actions.extend(_gen_trips(rank_groups, PASS_ACTION))
        actions.extend(_gen_bombs(rank_groups, cur_rank))
        actions.extend(_gen_straights(rank_groups, cur_rank))
        actions.extend(_gen_straight_flushes(rank_groups, cur_rank))
        actions.extend(_gen_three_pair(rank_groups))
        actions.extend(_gen_two_trips(rank_groups))
        actions.extend(_gen_three_with_two(rank_groups))
    else:
        gt_type = get_action_type(ga)
        gt_rank_str = get_action_rank(ga)

        # 同型压牌
        if gt_type == ACTION_TYPE_SINGLE:
            actions.extend(_gen_singles(rank_groups, ga))
        elif gt_type == ACTION_TYPE_PAIR:
            actions.extend(_gen_pairs(rank_groups, ga))
        elif gt_type == ACTION_TYPE_TRIPS:
            actions.extend(_gen_trips(rank_groups, ga))
        elif gt_type == ACTION_TYPE_STRAIGHT:
            actions.extend(_gen_straights(rank_groups, cur_rank, greater_action=ga))
        elif gt_type == ACTION_TYPE_STRAIGHT_FLUSH:
            actions.extend(_gen_straight_flushes(rank_groups, cur_rank, greater_action=ga))
        elif gt_type == ACTION_TYPE_THREE_PAIR:
            actions.extend(_gen_three_pair(rank_groups, greater_action=ga))
        elif gt_type == ACTION_TYPE_TWO_TRIPS:
            actions.extend(_gen_two_trips(rank_groups, greater_action=ga))
        elif gt_type == ACTION_TYPE_THREE_WITH_TWO:
            actions.extend(_gen_three_with_two(rank_groups, greater_action=ga))

        # 炸弹可以压任何非炸弹
        if gt_type not in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            actions.extend(_gen_bombs(rank_groups, cur_rank))
            actions.extend(_gen_straight_flushes(rank_groups, cur_rank))

    return actions

# ═══════════════════════════════════════════════════════
#  场景构造
# ═══════════════════════════════════════════════════════

def build_game_state(
    hand: List[str],
    greater_action: List,
    my_pos: int = 0,
    cur_pos: int = 1,
    greater_pos: int = 1,
    cur_rank: str = "2",
    self_rank: str = "2",
    oppo_rank: str = "2",
    stage: str = "play",
    public_rest: Tuple[int, int, int, int] = (27, 27, 27, 27),
    history: List[Dict] = None,
) -> Dict[str, Any]:
    """
    构造 V7 decide() 所需的最小 game_state。

    Args:
        hand: 手牌列表
        greater_action: 当前圈最大出牌（对手出的牌），PASS 表示领出
        my_pos: 我方位置 (0-3)
        cur_pos: 当前出牌人位置
        greater_pos: 圈最大牌出牌人位置
        cur_rank: 级牌点数
        stage: "play" / "tribute" / "back"
        public_rest: 四家剩余牌数
        history: 出牌历史
    """
    action_list = generate_action_list(
        hand, greater_action
        if greater_action and greater_action[0] != "PASS" else None,
        cur_rank)

    # curAction 同 greaterAction（简化：认为对手出的就是当前圈最大）
    cur_action = greater_action

    return {
        "actionList": action_list,
        "handCards": list(hand),
        "myPos": my_pos,
        "curPos": cur_pos,
        "greaterPos": greater_pos,
        "greaterAction": greater_action,
        "curAction": cur_action,
        "curRank": cur_rank,
        "selfRank": self_rank,
        "oppoRank": oppo_rank,
        "curBombNum": 0,
        "stage": stage,
        "publicInfo": [
            {"rest": public_rest[i]} for i in range(4)
        ],
        "history": history or [],
        "recentPlays": [],
    }


def run_scenario(
    name: str,
    hand: List[str],
    opponent_play: List,
    my_pos: int = 0,
    cur_rank: str = "2",
    public_rest: Tuple[int, int, int, int] = (27, 27, 27, 27),
):
    """执行单个调试场景。"""
    print(f"\n{'='*60}")
    print(f"  场景: {name}")
    print(f"{'='*60}")
    print(f"  手牌 ({len(hand)}张): {hand}")
    print(f"  对手出牌: {opponent_play}")
    print(f"  级牌: {cur_rank}  我方位置: {my_pos}")

    engine = UltimateWinRateEngineV7(player_id=my_pos)
    if engine.model is None:
        print("  ⚠ 模型未加载（将走 heuristic 纯规则路径）")

    gs = build_game_state(
        hand=hand,
        greater_action=opponent_play,
        my_pos=my_pos,
        cur_pos=(my_pos + 1) % 4,
        greater_pos=(my_pos + 1) % 4,
        cur_rank=cur_rank,
        public_rest=public_rest,
    )

    act_list = gs["actionList"]
    print(f"  候选动作数: {len(act_list)}")
    # 显示前 10 个候选
    for i, a in enumerate(act_list[:10]):
        a_type = a[0] if isinstance(a, list) and len(a) > 0 else str(a)
        a_rank = a[1] if isinstance(a, list) and len(a) >= 2 else ""
        a_show = f"{a_type} {a_rank}" if a_type != "PASS" else "PASS"
        print(f"    [{i:3d}] {a_show}")

    if len(act_list) > 10:
        print(f"    ... 省略 {len(act_list) - 10} 个候选")

    # 决策
    result_idx = engine.decide(gs)
    result_action = act_list[result_idx] if result_idx < len(act_list) else None

    # 显示结果
    if result_action:
        r_type = result_action[0] if isinstance(result_action, list) and len(result_action) > 0 else str(result_action)
        r_rank = result_action[1] if isinstance(result_action, list) and len(result_action) >= 2 else ""
        r_cards = result_action[2] if isinstance(result_action, list) and len(result_action) >= 3 else []
        print(f"\n  >>> V7 决策: idx={result_idx} → {r_type} {r_rank} {r_cards}")
    else:
        print(f"\n  >>> V7 决策: idx={result_idx} (无效)")

    # 显示组牌引擎结果
    print(f"  角色: {engine._current_role}")
    if engine._card_mask:
        core_groups = set()
        for card, (gid, is_core, gsize) in engine._card_mask.items():
            if is_core >= 1.0:
                core_groups.add(gid)
        print(f"  核心牌组数: {len(core_groups)}")

    # 显示 Guard 统计
    print(f"  Guard 过滤次数: {engine.guard_filtered_count}")
    print(f"  Guard 覆盖次数: {engine.guard_override_count}")
    print(f"  组牌过滤次数: {engine.group_filtered_count}")

    return result_idx, result_action


# ═══════════════════════════════════════════════════════
#  预设场景
# ═══════════════════════════════════════════════════════

def scenario_simple_pair_pressure():
    """场景1: 我被对手用大对子压住，看看 V7 是否合理应对。"""
    hand = make_hand(
        # 炸弹
        "5", "5", "5", "5",
        # 大对子
        "A", "A",
        # 中牌
        "K", "K", "Q", "Q",
        # 散牌
        "7", "3", "9", "J", "T",
        # 一张王
        "SB",
    )
    opp_play = make_action("Pair", "Q", make_hand("Q", "Q"))
    run_scenario("对手出对Q → V7如何应对？", hand, opp_play)


def scenario_bomb_vs_single():
    """场景2: 对手出单张，我有炸弹，看看 V7 会不会浪费炸弹。"""
    hand = make_hand(
        "3", "3", "3", "3",           # 小炸弹
        "K", "K", "K", "K",           # 大炸弹
        "A", "A",                      # 大对子
        "Q", "J", "T", "9", "8",      # 散牌
        "SB",                          # 小王
    )
    opp_play = make_action("Single", "T", make_hand("T"))
    run_scenario("对手出单张T → V7会不会炸？", hand, opp_play)


def scenario_teammate_leading():
    """场景3: 队友控牌时，V7 应该让道（PASS）。"""
    hand = make_hand(
        "3", "3", "3", "3",
        "K", "K", "A", "A", "2",
        "Q", "J", "T", "9",
    )
    # 队友是 greaterPos
    opp_play = make_action("Single", "5", make_hand("5"))
    # 设置 greaterPos = 2 (队友), myPos = 0
    print(f"\n{'='*60}")
    print(f"  场景: 队友控牌 → V7应PASS让道")
    print(f"{'='*60}")
    print(f"  手牌 ({len(hand)}张): {hand}")
    print(f"  对手(队友)出牌: {opp_play}")

    engine = UltimateWinRateEngineV7(player_id=0)
    gs = build_game_state(
        hand=hand,
        greater_action=opp_play,
        my_pos=0,
        cur_pos=2,
        greater_pos=2,  # 队友
    )
    result_idx = engine.decide(gs)
    act_list = gs["actionList"]
    result_action = act_list[result_idx] if result_idx < len(act_list) else None
    r_type = result_action[0] if result_action and len(result_action) > 0 else "?"
    print(f"  >>> V7 决策: idx={result_idx} → {r_type}")
    print(f"  期望: PASS")
    print(f"  {'✓ 正确让道' if r_type == 'PASS' else '✗ 未让道！'}")
    print(f"  角色: {engine._current_role}")


def scenario_opponent_low_cards():
    """场景4: 对手只剩2张，V7 应优先用炸。"""
    hand = make_hand(
        "3", "3", "3", "3",           # 炸弹
        "K", "K", "K", "K",           # 炸弹
        "A", "A", "Q", "Q",
        "J", "T", "9", "8", "SB",
    )
    opp_play = make_action("Single", "A", make_hand("A"))
    run_scenario(
        "对手剩2张出单A → V7应炸",
        hand, opp_play,
        public_rest=(10, 2, 10, 27),  # 对手(pos1)剩2张
    )


def scenario_lead_hand():
    """场景5: 我领出，看 V7 选什么牌型起手。"""
    hand = make_hand(
        "3", "3", "3", "3",
        "K", "K", "A", "A",
        "Q", "Q", "J", "J",
        "T", "9", "8", "7",
        "SB", "HR",
    )
    opp_play = PASS_ACTION  # 领出
    run_scenario("我领出（无压牌）→ V7选什么起手？", hand, opp_play)


# ═══════════════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════╗")
    print("║     V7 单手牌调试 — 喂牌 → 看决策               ║")
    print("╚══════════════════════════════════════════════════╝")

    scenario_simple_pair_pressure()
    scenario_bomb_vs_single()
    scenario_teammate_leading()
    scenario_opponent_low_cards()
    scenario_lead_hand()

    print(f"\n{'='*60}")
    print("  全部场景执行完毕。")
    print(f"{'='*60}")
