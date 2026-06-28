# -*- coding: utf-8 -*-
"""
EndgameDecider — 残局 Q0→Q3 决策引擎
======================================
读取 _endgame_context，按优先序执行四级决策：

  Q0: 自己冲刺（self.should_sprint）→ 出最大整炸抢头游
  Q1: 封锁敌方（有敌人 ≤10）→ banned 硬排 + recommended 优先
  Q2: 助攻队友（teammate.is_close）→ assist_prefer 喂牌
  Q3: 炸弹兜底（非冲刺/封锁/助攻）→ should_bomb 判决

任一 Q 命中 → 返回 action；全未命中 → 返回 None，交由上游管线处理。
"""

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

        # 收集所有敌人的 banned_types + baoshu.never_play
        banned_set: set = set()
        enemies = ec.get("enemies", {})
        for opp_pos, ectx in enemies.items():
            remaining = ectx.get("remaining", 27)
            banned_set.update(ectx.get("banned_types", []))
            baoshu = ectx.get("baoshu", {})
            if baoshu:
                # never_play 需验证 ≤ remaining（预处理器已过滤但再做一次防御）
                for t in baoshu.get("never_play", []):
                    try:
                        from .endgame_preprocessor import _ACTION_TYPE_CARD_COUNT as _card_count
                    except ImportError:
                        from src.v.nn.endgame.endgame_preprocessor import _ACTION_TYPE_CARD_COUNT as _card_count
                    if _card_count.get(t, 99) <= remaining:
                        banned_set.add(t)

        if not banned_set:
            return action_list, False

        if not GUARD_TOOLS_OK:
            return action_list, False

        # 硬排除
        filtered = []
        for a in action_list:
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
        两手整牌 + 有炸 → 出最大整炸抢头游。

        按出牌权 + 对手残局状态动态选「先炸后整」还是「先整后炸」。
        """
        my_pos = ec.get("my_pos", 0)
        cur_pos = game_state.get("curPos", my_pos)
        is_my_turn = (cur_pos == my_pos)
        enemies = ec.get("enemies", {})

        # 分离炸弹和非炸弹
        bombs = []
        non_bombs = []
        if GUARD_TOOLS_OK:
            for i, a in enumerate(action_list):
                try:
                    if is_bomb(a):
                        bombs.append((i, a))
                    else:
                        non_bombs.append((i, a))
                except Exception:
                    non_bombs.append((i, a))
        else:
            for i, a in enumerate(action_list):
                cards = _get_cards(a)
                if len(cards) >= 4:
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
                # 敌方已进残局 → 必须炸，夺回出牌权
                return self._select_best_bomb(bombs, action_list)
            else:
                # 不急于炸，让对手出
                if non_bombs:
                    return self._select_best_index(non_bombs, action_list, game_state)
                return None  # 只有炸，但没有合适时机

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

        # ① 找最危险敌人（主目标）
        sorted_enemies = sorted(
            enemies.items(),
            key=lambda kv: self._enemy_danger_score(kv[0], kv[1], my_pos),
        )
        main_pos, main_enemy = sorted_enemies[0]

        # ② 收集 banned_set（所有敌人 banned + baoshu.never_play 并集）
        banned_set: set = set()
        for opp_pos, ectx in enemies.items():
            banned_set.update(ectx.get("banned_types", []))
            baoshu = ectx.get("baoshu", {})
            if baoshu:
                banned_set.update(baoshu.get("never_play", []))

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

        # ④ 走 recommended 优先（主目标）
        rec_types = main_enemy.get("recommended_types", [])
        if rec_types:
            recom_actions = self._filter_by_recommended_types(
                non_banned_candidates, rec_types, game_state,
            )
            if recom_actions:
                # recommended 排序（回收优先）
                recom_actions = _sort_by_recapture_first(recom_actions, hand_cards)
                return self._select_best_index(recom_actions, action_list, game_state)

        # ⑤ recommended 走不通 → 看 baoshu.block_with
        baoshu = main_enemy.get("baoshu", {})
        block_with = baoshu.get("block_with", []) if baoshu else []
        if block_with:
            block_actions = self._filter_by_recommended_types(
                non_banned_candidates, block_with, game_state,
            )
            if block_actions:
                block_actions = _sort_by_recapture_first(block_actions, hand_cards)
                return self._select_best_index(block_actions, action_list, game_state)

        # ⑥ 仍无 → 任意 non_banned
        if non_banned_candidates:
            non_banned_candidates = _sort_by_recapture_first(non_banned_candidates, hand_cards)
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
        队友 ≤4 张 → 按 assist_prefer 喂牌送队友走。
        """
        teammate = ec.get("teammate", {})
        if not teammate or not teammate.get("is_close"):
            return None

        assist_prefer = teammate.get("assist_prefer", [])
        if not assist_prefer:
            return None

        hand_cards = game_state.get("handCards", [])

        # 过滤出助攻牌型
        if not GUARD_TOOLS_OK:
            return None

        assist_actions = []
        for i, a in enumerate(action_list):
            try:
                atype = get_action_type(a)
                if atype in assist_prefer:
                    assist_actions.append((i, a))
            except Exception:
                pass

        if not assist_actions:
            return None

        # 排序：回收优先
        assist_actions = _sort_by_recapture_first(assist_actions, hand_cards)
        return self._select_best_index(assist_actions, action_list, game_state)

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
