# -*- coding: utf-8 -*-
"""
EndgameSolver — 完美信息残局求解器（离线败招归因用）
======================================================
路径 1 核心模块：从历史牌谱的残局决策点重建完美信息局面，
用 alpha-beta 搜索求「理论上最优动作」，与 V8 实际动作对比，
产出决策一致率 + 偏差清单（自动败招归因）。

设计约束：
  - 只读不写真实流水（回放不篡改牌谱）
  - 动作生成覆盖自然牌型 + 逢人配基础补位（Pair/Trips/Bomb 升配）
  - 顺子/三带二/钢板/同花顺内的逢人配补位暂不枚举（MVP，动作集为
    平台 actionList 的子集；V8 实际动作不在候选集时单独标记，不误判）
  - 搜索为完美信息 alpha-beta，队伍价值：我方先出完为胜，双上加权
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Tuple

try:
    from ..guards.v7_guards import (
        get_card_rank, get_card_value, get_action_type, get_action_rank,
        CARD_RANK_ORDER, JOKER_VALUE_SB, JOKER_VALUE_HR,
        ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR, ACTION_TYPE_TRIPS,
        ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH, ACTION_TYPE_THREE_PAIR,
        ACTION_TYPE_TWO_TRIPS, ACTION_TYPE_THREE_WITH_TWO, ACTION_TYPE_STRAIGHT,
        ACTION_TYPE_PASS, ACTION_TYPE_FREE,
    )
    GUARD_TOOLS_OK = True
except ImportError:  # pragma: no cover
    from src.v.nn.guards.v7_guards import (
        get_card_rank, get_card_value, get_action_type, get_action_rank,
        CARD_RANK_ORDER, JOKER_VALUE_SB, JOKER_VALUE_HR,
        ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR, ACTION_TYPE_TRIPS,
        ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH, ACTION_TYPE_THREE_PAIR,
        ACTION_TYPE_TWO_TRIPS, ACTION_TYPE_THREE_WITH_TWO, ACTION_TYPE_STRAIGHT,
        ACTION_TYPE_PASS, ACTION_TYPE_FREE,
    )
    GUARD_TOOLS_OK = True

try:
    from src.game_logic.trick_state import action_beats, rank_value
except Exception:  # pragma: no cover
    action_beats = None
    rank_value = None

RANKS_SEQ = ["3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
RANK_INDEX = {r: i for i, r in enumerate(RANKS_SEQ)}
SUITS = set("SHDC")


# ═══════════════════════════════════════════════════════
#  动作生成：从手牌枚举合法动作
# ═══════════════════════════════════════════════════════

def _rank_of(card: str) -> str:
    if card in ("SB", "HR", "BJ", "RJ"):
        return card
    return card[1] if len(card) >= 2 else card


def _suit_of(card: str) -> str:
    if len(card) < 1 or card[0] not in SUITS:
        return ""
    return card[0]


def _cards_key(cards: List[str]) -> Tuple[str, ...]:
    return tuple(sorted(str(c) for c in cards))


def _platform_action(atype: str, cards: List[str]) -> List:
    rank = ""
    if cards:
        r = _rank_of(cards[0])
        rank = r if r in ("SB", "HR") else r
    return [atype, rank, [str(c) for c in cards]]


def _enumerate_natural_actions(hand: List[str], cur_rank: str) -> List[List]:
    """枚举自然牌型动作（不把逢人配当万能，仅作级牌单张）。"""
    plays: List[List] = []
    cnt: Counter = Counter(_rank_of(c) for c in hand)
    cards_by_rank: Dict[str, List[str]] = {}
    for c in hand:
        cards_by_rank.setdefault(_rank_of(c), []).append(c)

    # Single：每张牌
    for c in hand:
        plays.append(_platform_action(ACTION_TYPE_SINGLE, [c]))

    # Pair / Trips / Bomb：按 rank 计数
    for r, lst in cards_by_rank.items():
        if r in ("SB", "HR"):
            continue
        n = len(lst)
        if n >= 2:
            plays.append(_platform_action(ACTION_TYPE_PAIR, lst[:2]))
        if n >= 3:
            plays.append(_platform_action(ACTION_TYPE_TRIPS, lst[:3]))
        if n >= 4:
            plays.append(_platform_action(ACTION_TYPE_BOMB, lst[:4]))

    # Straight：5 连（含 A2345 用 A 作 1；3-A 常规）
    for start in range(len(RANKS_SEQ) - 4):
        window = RANKS_SEQ[start:start + 5]
        if all(cnt.get(r, 0) >= 1 for r in window):
            cards = [cards_by_rank[r][0] for r in window]
            plays.append(_platform_action(ACTION_TYPE_STRAIGHT, cards))
    # A2345：A 作 1
    if all(cnt.get(r, 0) >= 1 for r in ["A", "2", "3", "4", "5"]):
        cards = [cards_by_rank[r][0] for r in ["A", "2", "3", "4", "5"]]
        plays.append(_platform_action(ACTION_TYPE_STRAIGHT, cards))

    # ThreeWithTwo：Trips + 任意 Pair
    for r3, lst3 in cards_by_rank.items():
        if r3 in ("SB", "HR") or len(lst3) < 3:
            continue
        for r2, lst2 in cards_by_rank.items():
            if r2 in ("SB", "HR") or len(lst2) < 2:
                continue
            if r2 == r3:
                continue
            plays.append(_platform_action(
                ACTION_TYPE_THREE_WITH_TWO, lst3[:3] + lst2[:2]))

    # ThreePair：3 连对
    for start in range(len(RANKS_SEQ) - 2):
        window = RANKS_SEQ[start:start + 3]
        if all(cnt.get(r, 0) >= 2 for r in window):
            cards = [cards_by_rank[r][0] for r in window for _ in range(2)]
            plays.append(_platform_action(ACTION_TYPE_THREE_PAIR, cards))

    # TwoTrips：2 连三张（钢板）
    for start in range(len(RANKS_SEQ) - 1):
        window = RANKS_SEQ[start:start + 2]
        if all(cnt.get(r, 0) >= 3 for r in window):
            cards = [cards_by_rank[r][0] for r in window for _ in range(3)]
            plays.append(_platform_action(ACTION_TYPE_TWO_TRIPS, cards))

    # StraightFlush：5 连同花
    by_suit_rank: Dict[str, List[str]] = {}
    for c in hand:
        by_suit_rank.setdefault(_suit_of(c), []).append(c)
    for suit, lst in by_suit_rank.items():
        if suit == "":
            continue
        scnt = Counter(_rank_of(c) for c in lst)
        for start in range(len(RANKS_SEQ) - 4):
            window = RANKS_SEQ[start:start + 5]
            if all(scnt.get(r, 0) >= 1 for r in window):
                pool = [c for c in lst if _rank_of(c) in window]
                pick = []
                for r in window:
                    pick.append(next(c for c in pool if _rank_of(c) == r))
                plays.append(_platform_action(ACTION_TYPE_STRAIGHT_FLUSH, pick))
        # A2345 同花
        if all(scnt.get(r, 0) >= 1 for r in ["A", "2", "3", "4", "5"]):
            pool = [c for c in lst if _rank_of(c) in ["A", "2", "3", "4", "5"]]
            pick = []
            for r in ["A", "2", "3", "4", "5"]:
                pick.append(next(c for c in pool if _rank_of(c) == r))
            plays.append(_platform_action(ACTION_TYPE_STRAIGHT_FLUSH, pick))

    return plays


def _enumerate_with_wild(hand: List[str], cur_rank: str) -> List[List]:
    """逢人配 H{cur_rank} 基础补位：升对/升三/升四头炸。"""
    wild = "H" + str(cur_rank)
    if wild not in hand:
        return []
    plays: List[List] = []
    cnt: Counter = Counter(_rank_of(c) for c in hand)
    cards_by_rank: Dict[str, List[str]] = {}
    for c in hand:
        cards_by_rank.setdefault(_rank_of(c), []).append(c)

    for r, lst in cards_by_rank.items():
        if r in ("SB", "HR") or r == str(cur_rank):
            continue
        n = len(lst)
        if n == 1:
            # Pair: [r] + wild
            plays.append(_platform_action(
                ACTION_TYPE_PAIR, lst[:1] + [wild]))
        if n == 2:
            # Trips: [r,r] + wild
            plays.append(_platform_action(
                ACTION_TYPE_TRIPS, lst[:2] + [wild]))
        if n == 3:
            # Bomb: [r,r,r] + wild（四头炸）
            plays.append(_platform_action(
                ACTION_TYPE_BOMB, lst[:3] + [wild]))
    return plays


def enumerate_legal_plays(hand: List[str], cur_rank: str) -> List[List]:
    """从手牌枚举全部可出动作（自然牌型 + 逢人配基础补位）。"""
    plays = _enumerate_natural_actions(hand, cur_rank)
    plays += _enumerate_with_wild(hand, cur_rank)
    # 去重：键 = (牌型, 牌集合)。Straight 与 StraightFlush 可用同组牌，
    # 若只按牌集合去重会把后枚举的 StraightFlush 丢掉。
    seen = set()
    uniq = []
    for p in plays:
        atype = p[0] if p else ""
        key = (atype, _cards_key(p[2]))
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


def beats(play: List, greater: List, cur_rank: str) -> bool:
    """play 能否压过 greater。greater 为空/PASS 视为可自由出。"""
    if not greater or not greater[0]:
        return True
    if greater[0] == ACTION_TYPE_PASS:
        return True
    if play[0] == ACTION_TYPE_PASS:
        return False
    if action_beats is None:  # pragma: no cover
        return True
    return action_beats(play, greater, cur_rank) is True


# ═══════════════════════════════════════════════════════
#  完美信息 alpha-beta 搜索
# ═══════════════════════════════════════════════════════

class EndgameSolver:
    """
    完美信息残局求解器。

    搜索目标（队伍视角）：我方两席先出完为胜；双上（我方头游+二游）加分。
    价值为正 → 我方有利；为负 → 敌方有利。
    """

    def __init__(self, max_depth: int = 6, max_nodes: int = 200000):
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self._nodes = 0

    # ── 状态模型 ──
    # hands: List[List[str]]  四席当前手牌（按席 0-3）
    # my_team: frozenset      我方两席
    # finish_order: List[int] 已出完顺序

    def _team_value(self, finish_order: List[int], my_team) -> float:
        """按出完顺序估值：我方可出完席数加权。"""
        value = 0.0
        for i, seat in enumerate(finish_order):
            if seat in my_team:
                # 越早出完权重越高：头游+4.0，二游+2.0
                value += (4.0 if i == 0 else 2.0)
            else:
                value -= (4.0 if i == 0 else 2.0)
        # 双上奖励：我方头游+二游
        if len(finish_order) >= 2 and finish_order[0] in my_team and finish_order[1] in my_team:
            value += 1.0
        return value

    def _heuristic(self, hands: List[List[str]], my_team) -> float:
        """未终局启发式：我方剩余手牌越少越优。"""
        my_rem = sum(len(h) for s, h in enumerate(hands) if s in my_team)
        opp_rem = sum(len(h) for s, h in enumerate(hands) if s not in my_team)
        return (opp_rem - my_rem) / 108.0

    def _actions_for(
        self,
        seat: int,
        hands: List[List[str]],
        cur_rank: str,
        greater: Optional[List],
    ) -> List[List]:
        """某席可出动作：自由领出时全枚举；跟压时仅可压过 greater 的 + PASS。"""
        if len(hands[seat]) == 0:
            return []
        plays = enumerate_legal_plays(hands[seat], cur_rank)
        if greater and greater[0] != ACTION_TYPE_PASS:
            legal = [p for p in plays if beats(p, greater, cur_rank)]
            # 压不过时只能 PASS；压得过时也可选择 PASS（弃牌）
            if not legal:
                return [[ACTION_TYPE_PASS, "", []]]
            return legal + [[ACTION_TYPE_PASS, "", []]]
        return plays

    def _search(
        self,
        hands: List[List[str]],
        turn: int,
        cur_rank: str,
        greater: Optional[List],
        greater_pos: int,
        pass_count: int,
        finish_order: List[int],
        my_team,
        depth: int,
        alpha: float,
        beta: float,
    ) -> Tuple[float, Optional[List]]:
        """negamax 队伍视角：当前 turn 若属我方取 max，属敌方取 min。"""
        self._nodes += 1
        if self._nodes > self.max_nodes:
            return self._heuristic(hands, my_team), None

        # 终局：两家出完（此时必有结果）；或单家出完时补充估值
        done = [s for s in range(4) if len(hands[s]) == 0]
        for s in done:
            if s not in finish_order:
                finish_order = finish_order + [s]
        if len(finish_order) >= 2:
            return self._team_value(finish_order, my_team), None

        if depth <= 0:
            return self._heuristic(hands, my_team), None

        # 当前席手牌为空 → 自动跳过
        while len(hands[turn]) == 0:
            turn = (turn + 1) % 4

        actions = self._actions_for(turn, hands, cur_rank, greater)
        if not actions:
            actions = [[ACTION_TYPE_PASS, "", []]]

        is_my = turn in my_team
        best_val = -1e9 if is_my else 1e9
        best_act = None

        for act in actions:
            new_hands = [list(h) for h in hands]
            if act[0] != ACTION_TYPE_PASS:
                cards = act[2] if len(act) > 2 and isinstance(act[2], list) else []
                cnt = Counter(str(c) for c in cards)
                hand_ct = Counter(str(c) for c in new_hands[turn])
                remain = hand_ct - cnt
                if sum(remain.values()) < 0:
                    continue  # 非法动作（防御）
                new_hands[turn] = list(remain.elements())

                if not new_hands[turn]:
                    finish_order = finish_order + [turn]

                new_greater = act
                new_greater_pos = turn
                new_pass = 0
            else:
                new_greater = greater
                new_greater_pos = greater_pos
                new_pass = pass_count + 1
                # 三家 PASS → 圈结束，领出者重新自由出
                if new_pass >= 3:
                    new_greater = None
                    new_greater_pos = -1
                    new_pass = 0

            nxt = (turn + 1) % 4
            val, _ = self._search(
                new_hands, nxt, cur_rank, new_greater, new_greater_pos,
                new_pass, finish_order, my_team, depth - 1, alpha, beta,
            )

            if is_my:
                if val > best_val:
                    best_val, best_act = val, act
                alpha = max(alpha, val)
            else:
                if val < best_val:
                    best_val, best_act = val, act
                beta = min(beta, val)
            if beta <= alpha:
                break  # 剪枝

        return best_val, best_act

    def _pick_heuristic_best(
        self,
        actions: List[List],
        hands: List[List[str]],
        my_team,
        cur_rank: str,
        turn: int = 0,
    ) -> Optional[List]:
        """启发式选最优动作：一手清最高；其次非炸小结构先出；炸弹尽量省。"""
        best_act = None
        best_score = -1e9
        hand_n = len(hands[turn]) if 0 <= turn < len(hands) else 0
        for act in actions:
            if act[0] == ACTION_TYPE_PASS:
                continue
            cards = act[2] if len(act) > 2 and isinstance(act[2], list) else []
            n = len(cards)
            is_bomb = act[0] in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH)
            # 一手清 → 最高分
            if hand_n and n == hand_n:
                val = 100.0
            else:
                val = n * 1.0 - (1.0 if is_bomb else 0.0)
                if is_bomb:
                    val -= 5.0  # 非清场炸弹额外降权
            if val > best_score:
                best_score = val
                best_act = act
        return best_act

    def evaluate_action(
        self,
        act: List,
        hands: List[List[str]],
        turn: int,
        cur_rank: str,
        greater: Optional[List],
        greater_pos: int,
        my_seat: int,
        depth: Optional[int] = None,
    ) -> float:
        """评估给定动作的价值（应用该动作后继续搜索 depth-1 层）。"""
        my_team = frozenset({my_seat, (my_seat + 2) % 4})
        new_hands = [list(h) for h in hands]
        pass_count = 0
        finish_order: List[int] = []
        new_greater = greater
        new_greater_pos = greater_pos
        if act and act[0] != ACTION_TYPE_PASS:
            cards = act[2] if len(act) > 2 and isinstance(act[2], list) else []
            cnt = Counter(str(c) for c in cards)
            hand_ct = Counter(str(c) for c in new_hands[turn])
            remain = hand_ct - cnt
            if sum(remain.values()) < 0:
                return -1e9
            new_hands[turn] = list(remain.elements())
            if not new_hands[turn]:
                finish_order = finish_order + [turn]
            new_greater = act
            new_greater_pos = turn
        else:
            pass_count = 1

        d = depth if depth is not None else self.max_depth - 1
        self._nodes = 0
        value, _ = self._search(
            new_hands, (turn + 1) % 4, str(cur_rank), new_greater,
            new_greater_pos, pass_count, finish_order, my_team, d, -1e9, 1e9,
        )
        return value

    def solve_all(
        self,
        hands: List[List[str]],
        turn: int,
        cur_rank: str,
        greater: Optional[List] = None,
        greater_pos: int = -1,
        my_seat: int = 0,
    ) -> List[Tuple[List, float]]:
        """枚举当前席全部合法动作并逐一评估价值，按价值降序。"""
        my_actions = self._actions_for(turn, hands, str(cur_rank), greater)
        scored = []
        for act in my_actions:
            v = self.evaluate_action(
                act, hands, turn, str(cur_rank), greater, greater_pos, my_seat)
            scored.append((act, v))
        scored.sort(key=lambda x: -x[1])
        return scored

    def solve(
        self,
        hands: List[List[str]],
        turn: int,
        cur_rank: str,
        greater: Optional[List] = None,
        greater_pos: int = -1,
        my_seat: int = 0,
    ) -> Tuple[Optional[List], float, int]:
        """
        求解当前局面最优动作。

        Args:
            hands: 四席当前手牌（完美信息）
            turn: 当前行动席
            cur_rank: 级牌
            greater / greater_pos: 本圈最大动作
            my_seat: 我方席（队伍 = {my_seat, (my_seat+2)%4}）

        Returns:
            (best_action, value, nodes)
        """
        my_team = frozenset({my_seat, (my_seat + 2) % 4})
        self._nodes = 0
        value, act = self._search(
            hands, turn, str(cur_rank), greater, greater_pos, 0, [],
            my_team, self.max_depth, -1e9, 1e9,
        )
        # 深度耗尽/终局路径可能未绑定具体动作 → 回退到当前席启发式最优动作
        if act is None:
            my_actions = self._actions_for(turn, hands, str(cur_rank), greater)
            if my_actions:
                act = self._pick_heuristic_best(
                    my_actions, hands, my_team, cur_rank, turn=turn)
        return act, value, self._nodes
