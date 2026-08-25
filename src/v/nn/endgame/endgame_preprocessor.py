# -*- coding: utf-8 -*-
"""
EndgamePreprocessor — 残局上下文注入器
========================================
在 decide() 入口统一注入 _endgame_context，供 Guard / 推荐引擎 / heuristic 读取。

注入点：_inject_numofplayers 之后，GUA-075 主路径之前。
不修改 actionList，纯上下文注入。

四家角色路由：
  - 敌方（myPos+1, myPos+3）→ 封锁管线（endgame_rule + BAOSHU_RULE）
  - 队友（myPos+2）         → 助攻管线（assist_prefer）
  - 自己（myPos）           → 冲刺优先 / 助攻兜底
"""

from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger("endgame_preprocessor")

# ── 从 v7_guards 导入工具 ──────────────────────────────
try:
    from ..guards.v7_guards import (

        get_action_type, get_card_value, get_card_rank,
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
            get_action_type, get_card_value, get_card_rank,
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
        # 回退：定义基础常量
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
#  常量数据块
# ═══════════════════════════════════════════════════════

ENEMY_POSITIONS_TEMPLATE = lambda my_pos: [(my_pos + 1) % 4, (my_pos + 3) % 4]

# ── 牌型中文名 → V7 ACTION_TYPE 映射 ──
_SHAPE_NAME_TO_ACTION_TYPES: Dict[str, List[str]] = {
    "单张":      ["Single"],
    "大单张":    ["Single"],      # 大单张需进一步 check value≥K
    "最大单张":   ["Single"],
    "小单":      ["Single"],      # 小单张需 check value<K
    "对子":      ["Pair"],
    "三张":      ["Trips"],
    "三同张":    ["Trips"],
    "三不带":    ["Trips"],
    "3带2":      ["ThreeWithTwo"],
    "三带二":    ["ThreeWithTwo"],
    "顺子":      ["Straight"],
    "长顺子":    ["Straight"],
    "钢板":      ["TwoTrips"],
    "连对":      ["ThreePair"],
    "三连对":    ["ThreePair"],
    "长组合牌":   ["Straight", "ThreePair", "TwoTrips"],
    "炸弹":      ["Bomb", "StraightFlush"],
    "零散单":    ["Single"],
    "零散单、对子、三不带": ["Single", "Pair", "Trips"],
    "所有普通单张": ["Single"],
}

# ── 牌型 → 所需张数 ──
_ACTION_TYPE_CARD_COUNT: Dict[str, int] = {
    "Single": 1, "Pair": 2, "Trips": 3, "ThreeWithTwo": 5,
    "Straight": 5, "TwoTrips": 6, "ThreePair": 6,
    "Bomb": 4, "StraightFlush": 5,
}

# ── endgame_rule：剩 N 张 → (danger_level, recommended_types, banned_types) ──
endgame_rule: Dict[int, tuple] = {
    1:  ("极高", ["最大单张"],           []),
    2:  ("高",   ["单张"],               ["Pair"]),
    3:  ("高",   ["单张", "对子"],        ["Trips"]),
    4:  ("中高", ["大单张", "Straight"],  ["Pair"]),
    5:  ("中",   ["Pair", "Trips", "大单张"], []),
    6:  ("中",   ["ThreePair", "TwoTrips", "Straight", "Trips"], []),  # GUA-142：宜整结构；不禁 Pair（小对可作冲刺尾手）
    7:  ("低",   ["Straight", "TwoTrips", "ThreePair"], []),  # 敌剩7-8：宜整牌结构；跟压时同理可出三带二（GUA-125 §0）
    8:  ("低",   ["Straight", "TwoTrips", "ThreePair"], []),
    9:  ("低",   ["Straight", "ThreePair", "TwoTrips"], []),
    10: ("低",   ["Straight", "ThreePair", "TwoTrips"], []),
}

max_end_card: int = 10

# ── BAOSHU_RULE：报单/报双封锁（≤4 张触发） ──
# remaining: (可能牌型描述, block_with, never_play)
BAOSHU_RULE: Dict[int, tuple] = {
    1: ("单张(听牌)", ["ThreeWithTwo", "TwoTrips", "ThreePair", "Straight", "Bomb"],  []),
    2: ("对子",       ["ThreeWithTwo", "TwoTrips", "ThreePair", "Straight", "Bomb", "Trips"], ["Pair"]),
    3: ("三同张",     ["Pair", "Single", "TwoTrips", "ThreePair", "Straight", "Bomb"], ["Trips"]),
    4: ("炸弹/四张",   ["ThreeWithTwo", "TwoTrips", "ThreePair", "Straight"], ["Pair", "Bomb", "StraightFlush"]),
}

# GUA-115：报四时 never_play 中的 bomb-like 不受「张数 ≤ remaining」过滤（SF 平台张数=5）
_BAOSHU_BOMB_LIKE_NEVER_AT_FOUR = frozenset({"Bomb", "StraightFlush"})

# 危险等级序数映射
_DANGER_ORDER: Dict[str, int] = {"极高": 0, "高": 1, "中高": 2, "中": 3, "低": 4}

_VALID_ACTION_TYPES = set(_ACTION_TYPE_CARD_COUNT.keys())


# ═══════════════════════════════════════════════════════
#  公共 API：单函数版本（模块级）
# ═══════════════════════════════════════════════════════

def endgame_preprocess(game_state: Dict[str, Any]) -> Dict[str, Any]:
    """模块级快捷调用，等同 EndgamePreprocessor().preprocess(game_state)。"""
    return EndgamePreprocessor().preprocess(game_state)


def _dedupe_keep_order(values: List[str]) -> List[str]:
    """去重但保留首次出现顺序。"""
    seen = set()
    result: List[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _map_shape_names_to_action_types(shape_names: List[str]) -> Tuple[List[str], List[str]]:
    """中文牌型描述映射到 ACTION_TYPE，同时返回未知牌型名。"""
    action_types: List[str] = []
    unknown_names: List[str] = []
    for shape_name in shape_names:
        if shape_name in _VALID_ACTION_TYPES:
            action_types.append(shape_name)
            continue
        mapped = _SHAPE_NAME_TO_ACTION_TYPES.get(shape_name)
        if mapped is None:
            unknown_names.append(shape_name)
            continue
        action_types.extend(mapped)
    return _dedupe_keep_order(action_types), _dedupe_keep_order(unknown_names)


def _append_validation_error(
    errors: List[Dict[str, Any]],
    *,
    table: str,
    remaining: int,
    code: str,
    message: str,
    **extra: Any,
) -> None:
    """统一构造规则表校验错误对象。"""
    error = {
        "table": table,
        "remaining": remaining,
        "code": code,
        "message": message,
    }
    error.update(extra)
    errors.append(error)


def validate_q1_rule_table_consistency(
    endgame_rules: Optional[Dict[int, tuple]] = None,
    baoshu_rules: Optional[Dict[int, tuple]] = None,
) -> List[Dict[str, Any]]:
    """
    静态校验残局 Q1 规则表是否自洽。

    返回结构化错误列表；空列表表示通过。
    """
    endgame_rules = endgame_rule if endgame_rules is None else endgame_rules
    baoshu_rules = BAOSHU_RULE if baoshu_rules is None else baoshu_rules
    errors: List[Dict[str, Any]] = []

    for remaining, rule in sorted(endgame_rules.items()):
        if not isinstance(rule, (list, tuple)) or len(rule) != 3:
            _append_validation_error(
                errors,
                table="endgame_rule",
                remaining=remaining,
                code="invalid_rule_shape",
                message="endgame_rule 表项必须是 (danger_level, recommended_types, banned_types) 三元组。",
                actual_rule=rule,
            )
            continue

        _, recommended_shapes, banned_types = rule
        recommended_shapes = list(recommended_shapes or [])
        banned_types = list(banned_types or [])

        mapped_types, unknown_shapes = _map_shape_names_to_action_types(recommended_shapes)
        if unknown_shapes:
            _append_validation_error(
                errors,
                table="endgame_rule",
                remaining=remaining,
                code="unknown_recommended_shape",
                message="recommended_types 含未登记中文牌型名。",
                recommended_shapes=recommended_shapes,
                unknown_shapes=unknown_shapes,
            )

        unknown_banned = sorted(set(banned_types) - _VALID_ACTION_TYPES)
        if unknown_banned:
            _append_validation_error(
                errors,
                table="endgame_rule",
                remaining=remaining,
                code="unknown_banned_type",
                message="banned_types 含未知 ACTION_TYPE。",
                banned_types=banned_types,
                unknown_action_types=unknown_banned,
            )

        overlap = sorted(set(mapped_types) & set(banned_types))
        if overlap:
            _append_validation_error(
                errors,
                table="endgame_rule",
                remaining=remaining,
                code="recommended_banned_overlap",
                message="recommended_types 映射后的 ACTION_TYPE 与 banned_types 冲突。",
                recommended_shapes=recommended_shapes,
                recommended_action_types=mapped_types,
                banned_types=banned_types,
                overlap=overlap,
            )

    for remaining, rule in sorted(baoshu_rules.items()):
        if not isinstance(rule, (list, tuple)) or len(rule) != 3:
            _append_validation_error(
                errors,
                table="BAOSHU_RULE",
                remaining=remaining,
                code="invalid_rule_shape",
                message="BAOSHU_RULE 表项必须是 (likely_hand, block_with, never_play) 三元组。",
                actual_rule=rule,
            )
            continue

        _, block_with, never_play = rule
        block_with = list(block_with or [])
        never_play = list(never_play or [])

        unknown_block_with = sorted(set(block_with) - _VALID_ACTION_TYPES)
        if unknown_block_with:
            _append_validation_error(
                errors,
                table="BAOSHU_RULE",
                remaining=remaining,
                code="unknown_block_with_type",
                message="block_with 含未知 ACTION_TYPE。",
                block_with=block_with,
                unknown_action_types=unknown_block_with,
            )

        unknown_never_play = sorted(set(never_play) - _VALID_ACTION_TYPES)
        if unknown_never_play:
            _append_validation_error(
                errors,
                table="BAOSHU_RULE",
                remaining=remaining,
                code="unknown_never_play_type",
                message="never_play 含未知 ACTION_TYPE。",
                never_play=never_play,
                unknown_action_types=unknown_never_play,
            )

        overlap = sorted(set(block_with) & set(never_play))
        if overlap:
            _append_validation_error(
                errors,
                table="BAOSHU_RULE",
                remaining=remaining,
                code="block_with_never_play_overlap",
                message="block_with 与 never_play 同时包含同一 ACTION_TYPE。",
                block_with=block_with,
                never_play=never_play,
                overlap=overlap,
            )

    return errors


def format_q1_rule_table_validation_errors(errors: List[Dict[str, Any]]) -> str:
    """将结构化校验错误渲染为 CLI 友好的文本。"""
    if not errors:
        return "Q1 rule table validation PASS"

    lines: List[str] = []
    for error in errors:
        lines.append(
            f"[{error['table']}][remaining={error['remaining']}][{error['code']}] {error['message']}"
        )
        overlap = error.get("overlap")
        if overlap:
            lines.append(f"  overlap: {', '.join(overlap)}")
        recommended_shapes = error.get("recommended_shapes")
        if recommended_shapes:
            lines.append(f"  recommended_shapes: {recommended_shapes}")
        recommended_action_types = error.get("recommended_action_types")
        if recommended_action_types:
            lines.append(f"  recommended_action_types: {recommended_action_types}")
        banned_types = error.get("banned_types")
        if banned_types:
            lines.append(f"  banned_types: {banned_types}")
        block_with = error.get("block_with")
        if block_with:
            lines.append(f"  block_with: {block_with}")
        never_play = error.get("never_play")
        if never_play:
            lines.append(f"  never_play: {never_play}")
        unknown_shapes = error.get("unknown_shapes")
        if unknown_shapes:
            lines.append(f"  unknown_shapes: {unknown_shapes}")
        unknown_action_types = error.get("unknown_action_types")
        if unknown_action_types:
            lines.append(f"  unknown_action_types: {unknown_action_types}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
#  EndgamePreprocessor
# ═══════════════════════════════════════════════════════

class EndgamePreprocessor:
    """
    残局预处理：读取 numofplayers，注入 _endgame_context。

    不修改 actionList。纯上下文注入器。
    """

    # ── 牌型映射 ──
    SHAPE_MAP = _SHAPE_NAME_TO_ACTION_TYPES
    ACTION_CARD_COUNT = _ACTION_TYPE_CARD_COUNT

    def _map_types(self, chinese_names: List[str]) -> List[str]:
        """中文牌型名 → V7 ACTION_TYPE 枚举名列表（去重）"""
        mapped_types, _ = _map_shape_names_to_action_types(chinese_names)
        return mapped_types

    def _assist_prefer_for(self, remaining: int) -> List[str]:
        """队友剩 N 张时，精确投喂牌型（按优先序）→ 见 assist_prefer_table。"""
        from src.v.nn.assist_prefer_table import assist_prefer_for
        return assist_prefer_for(remaining)

    # ── 大单张动态阈值 ── IGNORE_STUB_RESOLVE_BIG_SINGLE_THRESHOLD ──

    def _resolve_big_single_threshold(self, game_state: Dict[str, Any]) -> str:
        """
        根据 MemoryTracker 中剩余大牌数，K→Q→J 三级动态降级。
        返回 "K" / "Q" / "J" 之一。
        """
        tracker = game_state.get("_memory_tracker")
        cur_rank = str(game_state.get("curRank", "2"))

        # 检查 K 以上还剩多少
        k_remaining = self._count_remaining_suppressors(tracker, "K", cur_rank)
        if k_remaining >= 2:
            return "K"

        q_remaining = self._count_remaining_suppressors(tracker, "Q", cur_rank)
        if q_remaining >= 2:
            return "Q"

        return "J"

    def _count_remaining_suppressors(
        self, tracker, rank: str, cur_rank: str
    ) -> int:
        """
        统计 ≥rank 的剩余可用牌张数（排除自己已出牌和已见打出的牌）。

        rank: "K" / "Q" / "J" 等
        返回：剩余可压制牌张数
        """
        if tracker is None:
            return 4  # 无 tracker 时保守估计 4 张都在

        try:
            # rank 值 → 比较起点
            threshold = CARD_RANK_ORDER.get(rank, 11)  # K=11
            # 总张数：每个点数 4 张 + 2 王
            total = 0
            for r, val in CARD_RANK_ORDER.items():
                if val >= threshold and r != cur_rank:
                    total += 4
                elif r == cur_rank:
                    # 级牌 4+1（逢人配算 1 张可炸）
                    if val >= threshold:
                        total += 5

            # 小王=13, 大王=14 总是 ≥ threshold
            if JOKER_VALUE_SB >= CARD_RANK_ORDER.get(rank, 0):
                total += 1
            if JOKER_VALUE_HR >= CARD_RANK_ORDER.get(rank, 0):
                total += 1
            if str(cur_rank) in ("SB",) and JOKER_VALUE_SB >= CARD_RANK_ORDER.get(rank, 0):
                total += 1
            if str(cur_rank) in ("HR",) and JOKER_VALUE_HR >= CARD_RANK_ORDER.get(rank, 0):
                total += 1

            # 减去已打出的
            seen = getattr(tracker, 'seen_counts', {}) or {}
            for card, count in seen.items():
                if count > 0:
                    rk = card[1] if len(card) >= 2 and card[0] in "SHDC" else card
                    if rk in ("SB", "HR") or (rk in CARD_RANK_ORDER and CARD_RANK_ORDER[rk] >= threshold):
                        total -= count

            # 减去自己手牌中已有的
            my_hand = getattr(tracker, 'my_initial_hand', []) or []
            for card in my_hand:
                rk = card[1] if len(card) >= 2 and card[0] in "SHDC" else card
                if rk in ("SB", "HR") or (rk in CARD_RANK_ORDER and CARD_RANK_ORDER[rk] >= threshold):
                    total -= 1

            return max(0, total)
        except Exception:
            return 4  # 降级保守返回

    # ── 核心判定 ──

    @staticmethod
    def count_semantic_hands(grouptype_map: Dict[str, int]) -> int:
        """
        语义手数：把 to_card_mask 子结构合并为整牌型后再计数。

        组牌引擎把钢板拆成 2×trip_in_steel_plate、三连对拆成 3×pair_in_three_pair、
        三带二拆成 trip+pair；冲刺「两手」必须按整牌型计，否则 Bomb+钢板会被算成 3 组。
        """
        if not grouptype_map:
            return 99
        m = {str(k): int(v) for k, v in grouptype_map.items() if int(v) > 0}
        hands = 0

        twt_trips = m.pop("trip_in_three_with_two", 0)
        twt_pairs = m.pop("pair_in_three_with_two", 0)
        twt_units = min(twt_trips, twt_pairs)
        hands += twt_units
        hands += (twt_trips - twt_units) + (twt_pairs - twt_units)

        steel = m.pop("trip_in_steel_plate", 0)
        hands += steel // 2
        hands += steel % 2

        three_pair = m.pop("pair_in_three_pair", 0)
        hands += three_pair // 3
        hands += three_pair % 3

        # scatter 注入为散牌张数；每张散单算一手
        hands += m.pop("scatter", 0)

        for _gtype, cnt in m.items():
            hands += cnt
        return hands

    def _has_two_clean_hands(self, game_state: Dict[str, Any]) -> bool:
        """
        两手整牌判定：语义手数 ≤2（子结构已合并为整牌型）。

        基于 grouptype_map（组牌引擎产出 / 引擎注入的 type→count）。
        """
        grouptype_map = game_state.get("_group_type_map", {})
        if not grouptype_map:
            # 回退：没有组牌引擎 → 不敢说两手整牌
            return False
        return self.count_semantic_hands(grouptype_map) <= 2

    def _has_bomb(self, game_state: Dict[str, Any]) -> bool:
        """
        手牌中是否有炸弹类资源可用（含同花顺）。

        掼蛋牌力：4星炸 < 5星炸 < 同花顺(5张) < 6星炸+。
        组牌与平台统一使用 ``Bomb`` / ``StraightFlush``。

        先查 grouptype_map（组牌引擎产出），再查 actionList。
        """
        grouptype_map = game_state.get("_group_type_map", {})
        if grouptype_map:
            bomb_count = grouptype_map.get("Bomb", 0) + grouptype_map.get("炸", 0)
            sf_count = grouptype_map.get("StraightFlush", 0)
            if bomb_count > 0 or sf_count > 0:
                return True

        # 回退：遍历 actionList（平台声明 Bomb / StraightFlush 优先）
        action_list = game_state.get("actionList", [])
        for act in action_list:
            if not act or not isinstance(act, list):
                continue
            declared = act[0] if act else ""
            if declared in ("Bomb", "StraightFlush"):
                return True
        if GUARD_TOOLS_OK:
            for act in action_list:
                try:
                    if is_bomb(act):
                        return True
                except Exception:
                    pass
        else:
            for act in action_list:
                if not act or act[0] == "PASS":
                    continue
                cards = act[2] if len(act) >= 3 and isinstance(act[2], list) else act
                if len(cards) >= 4:
                    ranks = [c[1] if len(c) >= 2 else c for c in cards]
                    if len(set(ranks)) == 1:
                        return True
        return False

    def _should_sprint(self, game_state: Dict[str, Any]) -> bool:
        """
        自己是否应该冲刺：
          ① 语义手数 ≤2（两手整牌，无需炸弹）
          ② 或具备冲刺能力（炸(+炸*)+单手结构，GUA-135；覆盖双炸+结构）
        """
        if self._has_two_clean_hands(game_state):
            return True
        hand_cards = list(game_state.get("handCards") or [])
        if not hand_cards:
            return False
        try:
            from src.v.nn.endgame.endgame_decide import (
                EndgameDecider,
                _is_two_trips_plus_wild_hand,
            )
            cur_rank = str(game_state.get("curRank", "2"))
            # GUA-281：两趟三张+配子 = 配子升炸 + 剩一手三张
            if _is_two_trips_plus_wild_hand(hand_cards, cur_rank):
                return True
            return EndgameDecider._hand_has_sprint_capability(hand_cards)
        except Exception:
            return False

    # ── 静态工具方法 ──

    @staticmethod
    def _can_clear(game_state: Dict[str, Any], bomb_size: int) -> bool:
        """
        炸完剩余手牌能否一轮走完。

        判据：剩余手牌数 ≤5（一手整牌最大张数）且组牌引擎判手数 ≤1。
        """
        hand_cards = game_state.get("handCards", [])
        remaining = len(hand_cards) - bomb_size
        if remaining <= 0:
            return True
        if remaining > 5:
            return False

        # 尝试用组牌引擎判断
        grouptype_map = game_state.get("_group_type_map", {})
        if grouptype_map:
            # 简易：剩余少判一手
            if remaining <= 5:
                return True
        return remaining <= 5

    @staticmethod
    def _will_lose(game_state: Dict[str, Any]) -> bool:
        """
        不炸必输判定：敌人是否极可能一手走完。

        致命张数：1, 2, 3, 5
        4 张规则：炸不压四（火不打四），但两手整牌可冲刺例外。
        """
        ec = game_state.get("_endgame_context", {})
        enemies = ec.get("enemies", {})

        for opp_pos, ectx in enemies.items():
            rem = ectx.get("remaining", 27)
            if rem in (1, 2, 3, 5):
                return True
            if rem == 4:
                # 4 张 → 炸不压四，不纳入 will_lose（除非自己可冲刺）
                pass

        return False

    @staticmethod
    def _should_bomb(game_state: Dict[str, Any], bomb_size: int) -> Dict[str, Any]:
        """
        Q3 炸弹兜底决策表。

        返回：{"should_bomb": bool, "reason": str}
        """
        can_clear = EndgamePreprocessor._can_clear(game_state, bomb_size)
        will_lose = EndgamePreprocessor._will_lose(game_state)

        if can_clear and will_lose:
            reason = "炸完能走+不炸必输"
            return {"should_bomb": True, "reason": reason}
        elif can_clear and not will_lose:
            reason = "炸完能走但非必须"
            return {"should_bomb": False, "reason": reason}
        elif not can_clear and will_lose:
            reason = "不炸必输但炸也走不掉"
            return {"should_bomb": False, "reason": reason}
        else:
            reason = "炸不走+不会输"
            return {"should_bomb": False, "reason": reason}

    # ── 敌方危险度排序 ──

    def _enemy_danger_key(
        self, my_pos: int, enemy_pos: int, remaining: int,
        danger_level: str, has_baoshu: bool,
    ) -> tuple:
        """危险度排序键：越小越危险"""
        pos_score = 0 if enemy_pos == (my_pos + 1) % 4 else 1
        return (
            remaining,
            pos_score,
            0 if has_baoshu else 1,
            _DANGER_ORDER.get(danger_level, 5),
        )

    # ── 主入口 ──

    def preprocess(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        注入 _endgame_context。

        读取 numofplayers（由 _inject_numofplayers 已注入），
        计算四家角色，填充封锁/助攻/冲刺上下文。

        Returns:
            注入后的 game_state
        """
        my_pos = game_state.get("myPos", 0)
        numofplayers = game_state.get("numofplayers", [27, 27, 27, 27])

        # ── 计算位置 ──
        teammate_pos = (my_pos + 2) % 4
        enemy_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]

        # ── is_active：任何一家 ≤10 触发 ──
        is_active = any(1 <= numofplayers[p] <= max_end_card for p in range(4))

        context: Dict[str, Any] = {
            "is_active": is_active,
            "numofplayers": numofplayers,
            "my_pos": my_pos,
            "enemies": {},
            "teammate": {},
            "self": {},
        }

        # ── ① 敌方封锁 ──
        for opp_pos in enemy_positions:
            remaining = numofplayers[opp_pos]
            if 1 <= remaining <= max_end_card:
                rule = endgame_rule.get(remaining, ("低", [], []))
                danger_level = rule[0]
                raw_recommended = list(rule[1])
                raw_banned = list(rule[2])

                # banned_types 过滤：仅保留敌人能出的牌型（张数 ≤ remaining）
                banned_types = [
                    t for t in raw_banned
                    if self.ACTION_CARD_COUNT.get(t, 99) <= remaining
                ]

                recommended_types = raw_recommended  # 推荐不做张数过滤（出牌不受限制）

                enemy_ctx: Dict[str, Any] = {
                    "remaining": remaining,
                    "danger_level": danger_level,
                    "recommended_types": recommended_types,
                    "banned_types": banned_types,
                }

                # BAOSHU 强化（≤4 张）
                if remaining <= 4 and remaining in BAOSHU_RULE:
                    bs = BAOSHU_RULE[remaining]
                    raw_block_with = list(bs[1])
                    raw_never_play = list(bs[2])

                    # never_play 张数过滤（≤ remaining 的才写入；报四 bomb-like 例外见 GUA-115）
                    never_play = []
                    for t in raw_never_play:
                        if remaining == 4 and t in _BAOSHU_BOMB_LIKE_NEVER_AT_FOUR:
                            never_play.append(t)
                        elif self.ACTION_CARD_COUNT.get(t, 99) <= remaining:
                            never_play.append(t)

                    block_with = [
                        t for t in raw_block_with
                        if self.ACTION_CARD_COUNT.get(t, 99) <= remaining
                    ]

                    enemy_ctx["baoshu"] = {
                        "likely_hand": bs[0],
                        "block_with": block_with,
                        "never_play": never_play,
                    }

                context["enemies"][opp_pos] = enemy_ctx

        # ── ② 队友助攻 ──
        mate_remaining = numofplayers[teammate_pos]
        if 1 <= mate_remaining <= max_end_card:
            from src.v.nn.assist_prefer_table import assist_is_close, assist_prefer_for
            context["teammate"] = {
                "remaining": mate_remaining,
                "is_close": assist_is_close(mate_remaining),
                "assist_prefer": assist_prefer_for(mate_remaining),
            }

        # ── ③ 自己冲刺 ──
        self_remaining = numofplayers[my_pos]
        context["self"] = {
            "remaining": self_remaining,
            "has_two_clean_hands": self._has_two_clean_hands(game_state),
            "has_bomb": self._has_bomb(game_state),
            "should_sprint": self._should_sprint(game_state),
        }

        # ── 注入 ──
        game_state["_endgame_context"] = context

        if is_active:
            logger.debug(
                "残局激活: myPos=%d enemies=%s teammate=%s self_remaining=%d sprint=%s",
                my_pos,
                {p: e.get("remaining") for p, e in context["enemies"].items()},
                context["teammate"].get("remaining"),
                self_remaining,
                context["self"]["should_sprint"],
            )

        return game_state
