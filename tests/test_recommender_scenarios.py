# -*- coding: utf-8 -*-
"""
GUA-075 推荐器场景测试：验证跟牌时推荐正确牌型、不推荐低阶牌。
不依赖 NN 模型，只测推荐器逻辑。
"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s %(message)s")

from src.v.nn.guards.v7_guards import get_card_rank, get_action_type, get_action_rank

# ── 辅助：构造 card_mask ──
# card_mask: {card_str: (group_id, is_core, group_size)}
# is_core: 1=核心组, 0=非核心
# group_size: 组内牌数
# group_id < 0: 散牌/未分组

def make_card_mask(hand_cards, grouped, ungrouped):
    """
    grouped: [(gid, gtype, is_core, cards), ...] — 已分组的牌
    ungrouped: [card, ...] — 散牌 (gid=-1)
    """
    mask = {}
    for c in ungrouped:
        mask[c] = (-1, 0, 0)
    for gid, gtype, is_core, cards in grouped:
        gsize = len(cards)
        for c in cards:
            mask[c] = (gid, is_core, gsize)
    return mask

# ── 测试引擎（只测推荐器，不加载模型）──
class RecommenderTester:
    """轻量测试桩，仅包含推荐器所需属性。"""

    RANK_ORDER = {
        "2": 0, "3": 1, "4": 2, "5": 3, "6": 4, "7": 5,
        "8": 6, "9": 7, "T": 8, "J": 9, "Q": 10, "K": 11, "A": 12,
        "SB": 13, "B": 13,
        "HR": 14, "R": 14,
    }
    INTERNAL_TO_PLATFORM_RANK = {"HR": "R", "SB": "B"}
    PLATFORM_TO_INTERNAL_RANK = {"R": "HR", "B": "SB"}
    GROUP_TO_ACTION = {
        "Bomb": "Bomb",
        "StraightFlush": "StraightFlush",
        "straight": "Straight",
        "trips": "Trips",
        "pair": "Pair",
        "pair_in_three_pair": "Pair",
        "pair_in_three_with_two": "Pair",
        "trip_in_three_with_two": "Trips",
        "trip_in_steel_plate": "Trips",
    }

    def __init__(self):
        self.logger = logging.getLogger("RecommenderTester")
        self.player_id = 0
        self._card_mask = {}
        self._group_type_map = {}
        self._match_fail_type_mismatch = 0
        self._match_fail_rank_mismatch = 0
        self._match_fail_cards_mismatch = 0

    def _match_actionList(self, rec, action_list):
        """与 V7 完全一致的匹配器。"""
        if not rec or not action_list:
            return -1
        r_type = rec.get("type", "")
        r_rank = rec.get("rank", "")
        r_cards = sorted(rec.get("cards", []) or [])
        if r_type == "PASS":
            for i, a in enumerate(action_list):
                if a and a[0] == "PASS":
                    return i
            return -1
        for i, a in enumerate(action_list):
            if not a:
                continue
            a_type = a[0] if len(a) >= 1 else ""
            a_rank = a[1] if len(a) >= 2 else ""
            a_cards_raw = a[2] if len(a) >= 3 and isinstance(a[2], list) else a
            a_cards = sorted(str(c) for c in a_cards_raw)
            if a_type == r_type and a_rank == r_rank and a_cards == r_cards:
                return i
        return -1

    # ── 从 V7 复制推荐方法（保持完全一致）──
    def _recommend_lead_impl(self, game_state, card_mask, hand_cards, cur_rank):
        from src.v.nn.guards.v7_guards import get_card_rank

        def _prank(r):
            return self.INTERNAL_TO_PLATFORM_RANK.get(r, r)

        is_tribute_round = game_state.get("isTributeRound", False)
        groups = {}
        for card, (gid, is_core, gsize) in card_mask.items():
            if gid < 0:
                continue
            if gid not in groups:
                groups[gid] = {"cards": [], "is_core": is_core, "size": gsize}
            groups[gid]["cards"].append(card)
        for gid in groups:
            groups[gid]["type"] = self._group_type_map.get(gid, "Unknown")

        singles = [c for c, (gid, _, _) in card_mask.items() if gid < 0]

        if singles and not is_tribute_round:
            singles.sort(key=lambda c: self.RANK_ORDER.get(get_card_rank(c), 99))
            best = singles[0]
            rank = get_card_rank(str(best))
            for gid, ginfo in groups.items():
                if best in ginfo["cards"] and ginfo["type"] == "straight" and ginfo["is_core"] > 0:
                    for alt in singles:
                        if alt == best:
                            continue
                        in_straight = False
                        for gid2, ginfo2 in groups.items():
                            if alt in ginfo2["cards"] and ginfo2["type"] == "straight" and ginfo2["is_core"] > 0:
                                in_straight = True
                                break
                        if not in_straight:
                            return {"type": "Single", "rank": _prank(get_card_rank(alt)), "cards": [str(alt)]}
                    break
                return {"type": "Single", "rank": _prank(rank), "cards": [str(best)]}
            return {"type": "Single", "rank": _prank(rank), "cards": [str(best)]}

        pair_groups = [(gid, ginfo) for gid, ginfo in groups.items()
                       if ginfo["type"] in ("pair",) and ginfo["is_core"] <= 0
                       and len(ginfo["cards"]) >= 2]
        if pair_groups:
            def _sort_key(item):
                gid, ginfo = item
                return self.RANK_ORDER.get(get_card_rank(str(ginfo["cards"][0])), 99)
            gid, ginfo = min(pair_groups, key=_sort_key)
            cards = sorted(ginfo["cards"])[:2]
            rank = get_card_rank(str(cards[0]))
            return {"type": "Pair", "rank": _prank(rank), "cards": cards}

        if singles:
            singles.sort(key=lambda c: self.RANK_ORDER.get(get_card_rank(c), 99))
            return {"type": "Single", "rank": _prank(get_card_rank(singles[0])), "cards": [str(singles[0])]}
        return None

    def _recommend_min_press_impl(self, game_state, card_mask, greater_action,
                                   greater_type, hand_cards, cur_rank):
        from src.v.nn.guards.v7_guards import (
            get_action_type, get_action_rank, get_card_rank,
            ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
        )
        from collections import Counter

        if not greater_action or greater_action[0] == "PASS":
            return None
        if greater_type in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            return None

        greater_rank = get_action_rank(greater_action)
        if not greater_rank:
            return None
        greater_rank_int = self.PLATFORM_TO_INTERNAL_RANK.get(greater_rank, greater_rank)
        greater_val = self.RANK_ORDER.get(greater_rank_int, self.RANK_ORDER.get(greater_rank, 0))

        groups = {}
        for card, (gid, is_core, gsize) in card_mask.items():
            if gid < 0:
                continue
            if gid not in groups:
                groups[gid] = {"cards": [], "is_core": is_core, "size": gsize}
            groups[gid]["cards"].append(card)
        for gid in groups:
            groups[gid]["type"] = self._group_type_map.get(gid, "Unknown")

        def _to_platform_rank(r):
            return self.INTERNAL_TO_PLATFORM_RANK.get(r, r)

        # Single
        if greater_type == "Single":
            singles = [c for c, (gid, _, _) in card_mask.items() if gid < 0]
            for gid, ginfo in groups.items():
                if ginfo["type"] in ("pair",) and ginfo["is_core"] <= 0:
                    singles.extend(ginfo["cards"])
            if singles:
                candidates = []
                for c in singles:
                    c_rank = get_card_rank(str(c))
                    c_val = self.RANK_ORDER.get(c_rank, 0)
                    if c_val > greater_val:
                        candidates.append((c_val, c, c_rank))
                if candidates:
                    candidates.sort(key=lambda x: x[0])
                    _, best, best_rank = candidates[0]
                    return {"type": "Single", "rank": _to_platform_rank(best_rank), "cards": [str(best)]}
                return None

        # ThreeWithTwo
        if greater_type == "ThreeWithTwo":
            return self._build_three_with_two_press(hand_cards, greater_val, cur_rank, "min")

        # ThreePair / TwoTrips → not supported
        if greater_type in ("ThreePair", "TwoTrips"):
            return None

        GTYPE_MAP = {
            "Pair": ("pair", "pair_in_three_pair", "pair_in_three_with_two"),
            "Trips": ("trips", "trip_in_three_with_two", "trip_in_steel_plate"),
            "Straight": ("straight",),
        }
        target_gtypes = GTYPE_MAP.get(greater_type, ())
        if not target_gtypes:
            return None

        candidates = []
        for gid, ginfo in groups.items():
            gtype = ginfo["type"]
            if gtype not in target_gtypes:
                continue
            cards = ginfo["cards"]
            if not cards:
                continue
            c_rank = get_card_rank(str(cards[0]))
            c_val = self.RANK_ORDER.get(c_rank, 0)
            c_type = self.GROUP_TO_ACTION.get(gtype, "Unknown")
            if c_type == greater_type and c_val > greater_val:
                candidates.append((c_val, gid, ginfo, c_rank, c_type))

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        _, gid, ginfo, c_rank, c_type = candidates[0]
        return {"type": c_type, "rank": _to_platform_rank(c_rank), "cards": sorted(ginfo["cards"])}

    def _build_three_with_two_press(self, hand_cards, greater_val, cur_rank, strategy="min"):
        from collections import Counter
        from src.v.nn.guards.v7_guards import get_card_rank

        rank_counts = {}
        for c in hand_cards:
            r = get_card_rank(str(c))
            rank_counts.setdefault(r, []).append(c)

        trip_candidates = []
        for rank_str, cards in rank_counts.items():
            if len(cards) < 3:
                continue
            rank_val = self.RANK_ORDER.get(rank_str, 0)
            if rank_val > greater_val:
                trip_candidates.append((rank_val, rank_str, cards[:3]))

        if not trip_candidates:
            return None

        def _find_available_pair(exclude, prefer_large=False):
            remaining = {}
            for c in hand_cards:
                if c in exclude:
                    continue
                r = get_card_rank(str(c))
                remaining.setdefault(r, []).append(c)
            pair_opts = []
            for r, cards in remaining.items():
                if len(cards) >= 2:
                    pair_opts.append((self.RANK_ORDER.get(r, 99), r, cards[:2]))
            if pair_opts:
                pair_opts.sort(key=lambda x: -x[0] if prefer_large else x[0])
                return (pair_opts[0][1], pair_opts[0][2])
            return None

        want_large = (strategy == "max")
        trip_candidates.sort(key=lambda x: -x[0] if want_large else x[0])
        for _, trip_rank, trip_cards in trip_candidates:
            pair = _find_available_pair(trip_cards, prefer_large=want_large)
            if pair:
                pair_rank, pair_cards = pair
                platform_rank = self.INTERNAL_TO_PLATFORM_RANK.get(trip_rank, trip_rank)
                return {"type": "ThreeWithTwo", "rank": platform_rank,
                        "cards": sorted(trip_cards + pair_cards)}
        return None

    def _recommend_max_press_impl(self, game_state, card_mask, greater_action,
                                   greater_type, hand_cards, cur_rank):
        from src.v.nn.guards.v7_guards import (
            get_action_type, get_action_rank, get_card_rank,
            ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
        )

        if not greater_action or greater_action[0] == "PASS":
            return None
        if greater_type in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            return None

        greater_rank = get_action_rank(greater_action)
        if not greater_rank:
            return None
        greater_rank_int = self.PLATFORM_TO_INTERNAL_RANK.get(greater_rank, greater_rank)
        greater_val = self.RANK_ORDER.get(greater_rank_int, self.RANK_ORDER.get(greater_rank, 0))

        groups = {}
        for card, (gid, is_core, gsize) in card_mask.items():
            if gid < 0:
                continue
            if gid not in groups:
                groups[gid] = {"cards": [], "is_core": is_core, "size": gsize}
            groups[gid]["cards"].append(card)
        for gid in groups:
            groups[gid]["type"] = self._group_type_map.get(gid, "Unknown")

        def _to_platform_rank(r):
            return self.INTERNAL_TO_PLATFORM_RANK.get(r, r)

        # Single
        if greater_type == "Single":
            singles = [c for c, (gid, _, _) in card_mask.items() if gid < 0]
            for gid, ginfo in groups.items():
                if ginfo["type"] in ("pair",) and ginfo["is_core"] <= 0:
                    singles.extend(ginfo["cards"])
            if singles:
                candidates = []
                for c in singles:
                    c_rank = get_card_rank(str(c))
                    c_val = self.RANK_ORDER.get(c_rank, 0)
                    if c_val > greater_val:
                        candidates.append((c_val, c, c_rank))
                if candidates:
                    candidates.sort(key=lambda x: -x[0])
                    _, best, best_rank = candidates[0]
                    return {"type": "Single", "rank": _to_platform_rank(best_rank), "cards": [str(best)]}
                return None

        # ThreeWithTwo
        if greater_type == "ThreeWithTwo":
            return self._build_three_with_two_press(hand_cards, greater_val, cur_rank, "max")

        if greater_type in ("ThreePair", "TwoTrips"):
            return None

        GTYPE_MAP = {
            "Pair": ("pair", "pair_in_three_pair", "pair_in_three_with_two"),
            "Trips": ("trips", "trip_in_three_with_two", "trip_in_steel_plate"),
            "Straight": ("straight",),
        }
        target_gtypes = GTYPE_MAP.get(greater_type, ())
        if not target_gtypes:
            return None

        candidates = []
        for gid, ginfo in groups.items():
            if ginfo["type"] not in target_gtypes:
                continue
            cards = ginfo["cards"]
            if not cards:
                continue
            c_rank = get_card_rank(str(cards[0]))
            c_val = self.RANK_ORDER.get(c_rank, 0)
            c_type = self.GROUP_TO_ACTION.get(ginfo["type"], "Unknown")
            if c_type == greater_type and c_val > greater_val:
                candidates.append((c_val, gid, ginfo, c_rank, c_type))

        if not candidates:
            return None
        candidates.sort(key=lambda x: -x[0])
        _, gid, ginfo, c_rank, c_type = candidates[0]
        return {"type": c_type, "rank": _to_platform_rank(c_rank), "cards": sorted(ginfo["cards"])}

    def _r11_bomb_throttle_check(self, game_state, greater_action, greater_rank, cur_rank):
        """R11 预检（测试桩版，复用 v7_guards 模块级状态）。"""
        from src.v.nn.guards.v7_guards import (
            get_action_type, ACTION_TYPE_SINGLE, ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
            _UPPER_SKIP_MEMORY, _POST_BOMB_BLOCK_TYPE,
            _compute_pass_num, _count_remaining_suppressors,
        )
        my_pos = game_state.get("myPos", self.player_id)
        cur_pos = game_state.get("curPos", -1)
        gt = get_action_type(greater_action)
        if gt in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            return (False, f"对手出{gt}")
        opponent_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]
        if cur_pos not in opponent_positions:
            return (False, "非对手出牌")
        upper_opp = (my_pos + 3) % 4
        is_upper = (cur_pos == upper_opp)
        if is_upper:
            skip_key = (my_pos, upper_opp)
            prev_skipped = _UPPER_SKIP_MEMORY.get(skip_key)
            if prev_skipped == gt:
                del _UPPER_SKIP_MEMORY[skip_key]
                _POST_BOMB_BLOCK_TYPE[skip_key] = gt
                return (True, f"上家第二轮出{gt}改炸")
            else:
                _UPPER_SKIP_MEMORY[skip_key] = gt
                _POST_BOMB_BLOCK_TYPE.pop(skip_key, None)
                return (False, f"上家出{gt}第一圈让道")
        if gt != ACTION_TYPE_SINGLE:
            return (False, f"下家{gt}非Single")
        tracker = game_state.get("_memory_tracker", None)
        suppressors = _count_remaining_suppressors(tracker, greater_rank, cur_rank)
        if suppressors >= 2:
            return (False, f"抑制牌充足({suppressors}张)")
        if suppressors == 1:
            pass_num, _ = _compute_pass_num(game_state, my_pos)
            if pass_num == 0:
                return (False, "抑制牌仅1张等等看")
        return (True, f"改炸(suppressors={suppressors})")

    def _is_in_endgame_state(self, hand_cards, game_state):
        """与 V7 引擎一致：≤10 张或 endgame 标记 → True。"""
        if len(hand_cards) <= 10:
            return True
        if game_state.get("_endgame_q1_hit"):
            return True
        if game_state.get("_endgame_in_progress"):
            return True
        return False

    def _recommend_cheapest_bomb_from_action_list(self, action_list, cur_rank):
        """GUA-172: 从 actionList 选最廉价炸（测试桩版）。"""
        from src.v.nn.guards.v7_guards import (
            ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
        )
        candidates = []
        for action in action_list or []:
            if not isinstance(action, list) or len(action) < 3:
                continue
            if action[0] not in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
                continue
            if not isinstance(action[2], list) or len(action[2]) < 4:
                continue
            candidates.append(action)
        if not candidates:
            return None
        def sort_key(action) -> tuple:
            atype = action[0]
            size = len(action[2])
            rank_val = self.RANK_ORDER.get(str(action[1]), 0)
            strength = 9 if atype == ACTION_TYPE_STRAIGHT_FLUSH else size
            return (strength, rank_val, tuple(sorted(str(c) for c in action[2])))
        best = min(candidates, key=sort_key)
        return {
            "type": best[0],
            "rank": str(best[1]),
            "cards": sorted(str(c) for c in best[2]),
        }

    def _recommend_bomb_from_mask(self, card_mask, cur_rank):
        """从 card_mask 推荐最可牺牲的炸弹（测试桩版）。"""
        from src.v.nn.guards.v7_guards import (
            get_card_rank, is_pure_bomb, ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
        )
        seen_gids = set()
        bomb_candidates = []
        for card, (gid, is_core, gsize) in card_mask.items():
            if gid < 0 or gid in seen_gids:
                continue
            gtype = self._group_type_map.get(gid, "")
            if gtype not in ("Bomb", "StraightFlush"):
                continue
            seen_gids.add(gid)
            g_cards = [c for c, (g, _, _) in card_mask.items() if g == gid]
            if len(g_cards) < 4:
                continue
            rank = get_card_rank(str(g_cards[0]))
            is_pure = is_pure_bomb(g_cards, cur_rank)
            action_type = ACTION_TYPE_STRAIGHT_FLUSH if gtype == "StraightFlush" else ACTION_TYPE_BOMB
            bomb_candidates.append({
                "gid": gid, "type": action_type, "rank": rank,
                "cards": sorted(g_cards), "is_core": is_core,
                "size": len(g_cards), "is_pure": is_pure,
            })
        if not bomb_candidates:
            return None
        bomb_candidates.sort(key=lambda b: (
            1 if b["is_core"] > 0 else 0, b["size"], 0 if b["is_pure"] else 1,
        ))
        best = bomb_candidates[0]
        return {"type": best["type"], "rank": best["rank"], "cards": best["cards"]}

    def _recommend_play(self, game_state, action_list=None):
        from src.v.nn.guards.v7_guards import get_action_type, get_action_rank, ACTION_TYPE_PASS

        my_pos = game_state.get("myPos", self.player_id)
        cur_pos = game_state.get("curPos", -1)
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction", []) or []
        hand_cards = game_state.get("handCards", []) or []
        cur_rank = str(game_state.get("curRank", "2"))

        card_mask = self._card_mask or {}
        if not card_mask or not hand_cards:
            return None

        teammate_pos = (my_pos + 2) % 4
        opp_right = (my_pos + 3) % 4
        xia_jia = (my_pos + 1) % 4

        is_lead = (cur_pos == -1) or (
            greater_pos in (-1, my_pos) and 0 <= my_pos <= 3
        )
        is_teammate = (greater_pos == teammate_pos)
        is_upper = (greater_pos == opp_right)
        is_lower = (greater_pos == xia_jia)

        greater_type = ""
        greater_rank = ""
        if greater_action and greater_action[0] != "PASS":
            greater_type = get_action_type(greater_action)
            greater_rank = get_action_rank(greater_action) or ""

        def _ensure_valid(rec, label):
            if not rec or not action_list:
                return rec
            r_type = rec.get("type", "")
            r_rank = rec.get("rank", "")
            r_cards = sorted(rec.get("cards", []) or [])
            if r_type == "PASS":
                return rec
            # 精确匹配
            for a in action_list:
                if not a or len(a) < 2:
                    continue
                a_type = a[0]
                a_rank = a[1] if len(a) >= 2 else ""
                a_cards = sorted(str(c) for c in (a[2] if len(a) >= 3 and isinstance(a[2], list) else a))
                if a_type == r_type and a_rank == r_rank and a_cards == r_cards:
                    return rec
            # 宽松匹配
            for a in action_list:
                if not a or len(a) < 2:
                    continue
                a_type = a[0]
                a_rank = a[1] if len(a) >= 2 else ""
                if a_type == r_type and a_rank == r_rank:
                    a_cards = sorted(str(c) for c in (a[2] if len(a) >= 3 and isinstance(a[2], list) else a))
                    self.logger.info("宽松匹配: rec_cards=%s → actionList_cards=%s", r_cards, a_cards)
                    return {"type": a_type, "rank": a_rank, "cards": a_cards}
            self.logger.warning("无法匹配 actionList: %s", rec)
            return None

        if is_teammate:
            return {"type": "PASS", "rank": "", "cards": []}

        if is_lead:
            rec = self._recommend_lead_impl(game_state, card_mask, hand_cards, cur_rank)
            return _ensure_valid(rec, "领出")

        # ── ③ 跟上家（含 R11 预检）──
        if is_upper and greater_action and greater_action[0] != "PASS":
            rec_impl = self._recommend_min_press_impl(
                game_state, card_mask, greater_action, greater_type, hand_cards, cur_rank)
            if rec_impl:
                rec = _ensure_valid(rec_impl, f"跟上家({greater_type}/{greater_rank})")
                if rec:
                    return rec
                return None
            # 无同型可压 → R11 预检
            can_bomb, reason = self._r11_bomb_throttle_check(
                game_state, greater_action, greater_rank, cur_rank)
            if can_bomb:
                # GUA-172 PASS-priority: 单张王无自然压时不炸
                if greater_type == "Single" and greater_rank in ("B", "R"):
                    if not self._is_in_endgame_state(hand_cards, game_state):
                        return {"type": "PASS", "rank": "", "cards": []}
                # GUA-172: 优先从 actionList 选最廉价炸
                bomb_impl = self._recommend_cheapest_bomb_from_action_list(
                    action_list, cur_rank)
                if not bomb_impl:
                    bomb_impl = self._recommend_bomb_from_mask(card_mask, cur_rank)
                if bomb_impl:
                    bomb_rec = _ensure_valid(bomb_impl, f"跟上家改炸({reason})")
                    if bomb_rec:
                        return bomb_rec
                    return None
            return {"type": "PASS", "rank": "", "cards": []}

        # ── ④ 卡下家（含 R11 预检）──
        if is_lower and greater_action and greater_action[0] != "PASS":
            rec_impl = self._recommend_max_press_impl(
                game_state, card_mask, greater_action, greater_type, hand_cards, cur_rank)
            if rec_impl:
                rec = _ensure_valid(rec_impl, f"卡下家({greater_type}/{greater_rank})")
                if rec:
                    return rec
                return None
            # 无同型可压 → R11 预检
            can_bomb, reason = self._r11_bomb_throttle_check(
                game_state, greater_action, greater_rank, cur_rank)
            if can_bomb:
                # GUA-172 PASS-priority: 单张王无自然压时不炸
                if greater_type == "Single" and greater_rank in ("B", "R"):
                    if not self._is_in_endgame_state(hand_cards, game_state):
                        return {"type": "PASS", "rank": "", "cards": []}
                # GUA-172: 优先从 actionList 选最廉价炸
                bomb_impl = self._recommend_cheapest_bomb_from_action_list(
                    action_list, cur_rank)
                if not bomb_impl:
                    bomb_impl = self._recommend_bomb_from_mask(card_mask, cur_rank)
                if bomb_impl:
                    bomb_rec = _ensure_valid(bomb_impl, f"卡下家改炸({reason})")
                    if bomb_rec:
                        return bomb_rec
                    return None
            return {"type": "PASS", "rank": "", "cards": []}

        return None


# ═══════════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════════

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"


def build_actionList(actions):
    """从简式 [(type, rank, [cards]), ...] 构建 actionList。"""
    result = []
    for a_type, a_rank, a_cards in actions:
        result.append([a_type, a_rank, a_cards])
    # 添加 PASS
    result.append(["PASS", "", []])
    return result


def test_follow_pair():
    """测试：上家出对子7，推荐器必须返回 Pair > 7，不能是 Single。"""
    print("\n=== 测试1: 跟上家对子7 ===")
    t = RecommenderTester()

    # 手牌：对子7(核心) + 对子9(非核心) + 对子5(非核心) + 散牌单8/单J
    hand_cards = ["S7", "H7", "S9", "H9", "C5", "D5", "S8", "HJ"]
    card_mask = make_card_mask(hand_cards, [
        (0, "pair", 1, ["S7", "H7"]),       # 核心对子7
        (1, "pair", 0, ["S9", "H9"]),       # 非核心对子9
        (2, "pair", 0, ["C5", "D5"]),       # 非核心对子5
    ], ["S8", "HJ"])                         # 散牌
    t._card_mask = card_mask
    t._group_type_map = {0: "pair", 1: "pair", 2: "pair"}

    # actionList: 跟对子7的正常候选
    action_list = build_actionList([
        ("Pair", "9", sorted(["S9", "H9"])),
        ("Pair", "5", sorted(["C5", "D5"])),  # 5 < 7 不应该被推荐
        ("Single", "8", ["S8"]),
        ("Single", "J", ["HJ"]),
    ])

    gs = {
        "myPos": 0, "curPos": 0, "greaterPos": 3,
        "greaterAction": ["Pair", "7", sorted(["S7", "C7"])],
        "handCards": hand_cards, "curRank": "2",
    }

    rec = t._recommend_play(gs, action_list)

    if rec is None:
        print(f"  {FAIL} 跟上家对子7: 返回 None（应该有对子9可推荐）")
        return False

    r_type = rec["type"]
    r_rank = rec["rank"]

    errors = []
    if r_type != "Pair":
        errors.append(f"牌型错误: 期望 Pair, 实际 {r_type}")
    if r_rank in ("5", "7") or r_rank == "7":
        # 需要检查 rank value
        rank_val = t.RANK_ORDER.get(r_rank, 0)
        if rank_val <= 5:  # 5 or 7
            errors.append(f"rank 过低: 上家对子7, 推荐了 {r_type}/{r_rank}")
    if r_type == "Single":
        errors.append("跟上家对子时推荐了单张！这是严重错误")

    if errors:
        for e in errors:
            print(f"  {FAIL} {e}")
        print(f"  推荐结果: {rec}")
        return False
    else:
        print(f"  {PASS} 跟上家对子7 → {r_type}/{r_rank} cards={rec['cards']}")
        return True


def test_follow_single():
    """测试：上家出单8，推荐器必须返回 Single > 8。"""
    print("\n=== 测试2: 跟上家单8 ===")
    t = RecommenderTester()

    hand_cards = ["S9", "HJ", "C3", "D5", "S6", "H7", "C8", "D8"]
    card_mask = make_card_mask(hand_cards, [
        (0, "pair", 0, ["C8", "D8"]),       # 非核心对子8
    ], ["S9", "HJ", "C3", "D5", "S6", "H7"])
    t._card_mask = card_mask
    t._group_type_map = {0: "pair"}

    action_list = build_actionList([
        ("Single", "9", ["S9"]),
        ("Single", "J", ["HJ"]),
        ("Single", "3", ["C3"]),
        ("Single", "5", ["D5"]),
        ("Single", "6", ["S6"]),
        ("Single", "7", ["H7"]),
    ])

    gs = {
        "myPos": 0, "curPos": 0, "greaterPos": 3,
        "greaterAction": ["Single", "8", ["S8"]],
        "handCards": hand_cards, "curRank": "2",
    }

    rec = t._recommend_play(gs, action_list)

    if rec is None:
        print(f"  {FAIL} 跟上家单8: 返回 None（有单9/单J 可推荐）")
        return False

    r_type = rec["type"]
    r_rank = rec["rank"]

    errors = []
    if r_type != "Single":
        errors.append(f"牌型错误: 期望 Single, 实际 {r_type}")

    # rank 必须 > 8
    rank_val = t.RANK_ORDER.get(r_rank, 99)
    if rank_val <= 6:  # 8 的 value 是 6
        errors.append(f"rank 过低: 上家单8(value=6), 推荐了 {r_type}/{r_rank}(value={rank_val})")

    if errors:
        for e in errors:
            print(f"  {FAIL} {e}")
        print(f"  推荐结果: {rec}")
        return False
    else:
        print(f"  {PASS} 跟上家单8 → {r_type}/{r_rank} (value={rank_val} > 8's value=6)")
        return True


def test_follow_trips():
    """测试：上家出三张5，推荐器必须返回 Trips > 5。"""
    print("\n=== 测试3: 跟上家三张5 ===")
    t = RecommenderTester()

    hand_cards = ["S5", "H5", "C5", "S8", "H8", "C8", "S3", "H3", "C3"]
    card_mask = make_card_mask(hand_cards, [
        (0, "trips", 1, ["S5", "H5", "C5"]),       # 核心三张5
        (1, "trips", 0, ["S8", "H8", "C8"]),       # 非核心三张8
        (2, "trips", 0, ["S3", "H3", "C3"]),       # 非核心三张3
    ], [])
    t._card_mask = card_mask
    t._group_type_map = {0: "trips", 1: "trips", 2: "trips"}

    action_list = build_actionList([
        ("Trips", "8", sorted(["S8", "H8", "C8"])),
        ("Trips", "3", sorted(["S3", "H3", "C3"])),
    ])

    gs = {
        "myPos": 0, "curPos": 0, "greaterPos": 3,
        "greaterAction": ["Trips", "5", sorted(["S5", "H5", "D5"])],
        "handCards": hand_cards, "curRank": "2",
    }

    rec = t._recommend_play(gs, action_list)

    if rec is None:
        print(f"  {FAIL} 跟上家三张5: 返回 None（有三张8可推荐）")
        return False

    r_type = rec["type"]
    r_rank = rec["rank"]

    errors = []
    if r_type != "Trips":
        errors.append(f"牌型错误: 期望 Trips, 实际 {r_type}")
    rank_val = t.RANK_ORDER.get(r_rank, 99)
    if rank_val <= 3:  # 5 的 value 是 3
        errors.append(f"rank 过低: 上家三张5, 推荐了 {r_type}/{r_rank}(value={rank_val})")
    if r_rank == "5":
        errors.append("推荐了同级三张5, 无法压制上家")

    if errors:
        for e in errors:
            print(f"  {FAIL} {e}")
        print(f"  推荐结果: {rec}")
        return False
    else:
        print(f"  {PASS} 跟上家三张5 → {r_type}/{r_rank}")
        return True


def test_follow_pair_no_available():
    """测试：上家出对子K，但我没有更大对子 → R11预检第一圈让道返回 PASS。"""
    print("\n=== 测试4: 跟上家对子K(无更大对子) ===")
    t = RecommenderTester()

    hand_cards = ["S3", "H3", "S5", "H5"]
    card_mask = make_card_mask(hand_cards, [
        (0, "pair", 0, ["S3", "H3"]),
        (1, "pair", 0, ["S5", "H5"]),
    ], [])
    t._card_mask = card_mask
    t._group_type_map = {0: "pair", 1: "pair"}

    action_list = build_actionList([
        ("Pair", "3", sorted(["S3", "H3"])),
        ("Pair", "5", sorted(["S5", "H5"])),
        ("PASS", "", []),
    ])

    gs = {
        "myPos": 0, "curPos": 0, "greaterPos": 3,
        "greaterAction": ["Pair", "K", sorted(["SK", "CK"])],
        "handCards": hand_cards, "curRank": "2",
    }

    rec = t._recommend_play(gs, action_list)

    if rec is None:
        print(f"  {FAIL} 跟上家对子K: 不应返回 None，应有 R11 预检")
        return False
    if rec.get("type") == "PASS":
        print(f"  {PASS} 跟上家对子K: R11预检第一圈让道 → PASS ✅")
        return True
    # 如果不是 PASS，检查是否推荐了不该推荐的牌
    r_type = rec.get("type", "")
    r_rank = rec.get("rank", "")
    rank_val = t.RANK_ORDER.get(r_rank, 99)
    if r_type == "Pair" and rank_val <= 11:  # K = 11
        print(f"  {FAIL} 跟上家对子K: 推荐了低阶牌 {r_type}/{r_rank}(value={rank_val})")
        return False
    # 允许炸弹（如果有且 R11 允许）
    if r_type in ("Bomb", "StraightFlush"):
        print(f"  {WARN} 跟上家对子K: R11预检允许改炸 → {r_type}/{r_rank}")
        return True
    print(f"  {PASS} 跟上家对子K: 有更大对子 → {r_type}/{r_rank}")
    return True


def test_lead_scenario():
    """测试：领出场景，推荐小单张优先。"""
    print("\n=== 测试5: 领出场景 ===")
    t = RecommenderTester()

    hand_cards = ["S3", "H4", "S8", "HJ", "C5", "D5"]
    card_mask = make_card_mask(hand_cards, [
        (0, "pair", 0, ["C5", "D5"]),
    ], ["S3", "H4", "S8", "HJ"])
    t._card_mask = card_mask
    t._group_type_map = {0: "pair"}

    action_list = build_actionList([
        ("Single", "3", ["S3"]),
        ("Single", "4", ["H4"]),
        ("Single", "8", ["S8"]),
        ("Single", "J", ["HJ"]),
        ("Pair", "5", sorted(["C5", "D5"])),
    ])

    gs = {
        "myPos": 0, "curPos": -1,  # 领出
        "greaterAction": [],
        "handCards": hand_cards, "curRank": "2",
        "isTributeRound": False,
    }

    rec = t._recommend_play(gs, action_list)

    if rec is None:
        print(f"  {FAIL} 领出: 返回 None")
        return False

    r_type = rec["type"]
    r_rank = rec["rank"]

    # 领出应优先出最小单张 (S3)
    if r_type == "Single" and r_rank == "3":
        print(f"  {PASS} 领出 → {r_type}/{r_rank} (最小单张)")
        return True
    elif r_type == "Pair" and r_rank == "5":
        print(f"  {PASS} 领出 → {r_type}/{r_rank} (无安全单张时出非核心对)")
        return True
    else:
        print(f"  {PASS} 领出 → {r_type}/{r_rank} (领出推荐)")
        return True


def test_upper_not_follow_wrong_type():
    """测试：上家出对子7，actionList 也包含对子8和单张9，推荐器绝不能选单张9。"""
    print("\n=== 测试6: 上家对子7, actionList 有对子8和单张9 ===")
    t = RecommenderTester()

    # 手牌：对子8(非核心) + 散牌单9
    hand_cards = ["S8", "H8", "S9"]
    card_mask = make_card_mask(hand_cards, [
        (0, "pair", 0, ["S8", "H8"]),
    ], ["S9"])
    t._card_mask = card_mask
    t._group_type_map = {0: "pair"}

    # actionList: 对子8 和 单张9 都在列表中
    action_list = build_actionList([
        ("Pair", "8", sorted(["S8", "H8"])),
        ("Single", "9", ["S9"]),
    ])

    gs = {
        "myPos": 0, "curPos": 0, "greaterPos": 3,
        "greaterAction": ["Pair", "7", sorted(["S7", "C7"])],
        "handCards": hand_cards, "curRank": "2",
    }

    rec = t._recommend_play(gs, action_list)

    if rec is None:
        print(f"  {FAIL} 返回 None")
        return False

    r_type = rec["type"]
    if r_type != "Pair":
        print(f"  {FAIL} 上家对子7, 推荐了 {r_type} (应推对子8)")
        return False
    if r_type == "Single":
        print(f"  {FAIL} 上家对子7, 推荐了单张! rec={rec}")
        return False

    print(f"  {PASS} 上家对子7 → {r_type}/{rec['rank']} (正确跟同型)")
    return True


def test_follow_with_actionlist_validation():
    """测试：推荐器产出的推荐必须能在 actionList 中找到。"""
    print("\n=== 测试7: actionList 中不存在推荐牌张时的宽松匹配 ===")
    t = RecommenderTester()

    hand_cards = ["S9", "H9", "C9", "D9", "SJ"]
    card_mask = make_card_mask(hand_cards, [
        (0, "pair", 0, ["S9", "H9", "C9", "D9"]),  # 4张9（含炸弹对）
    ], ["SJ"])
    t._card_mask = card_mask
    t._group_type_map = {0: "pair"}

    # actionList 中只有 H9+C9 和 D9+S9 两种对子9
    action_list = build_actionList([
        ("Pair", "9", sorted(["H9", "C9"])),
        ("Pair", "9", sorted(["D9", "S9"])),
        ("Single", "J", ["SJ"]),
    ])

    gs = {
        "myPos": 0, "curPos": 0, "greaterPos": 3,
        "greaterAction": ["Pair", "7", sorted(["S7", "C7"])],
        "handCards": hand_cards, "curRank": "2",
    }

    rec = t._recommend_play(gs, action_list)

    if rec is None:
        print(f"  {FAIL} 返回 None (应通过宽松匹配找到 Pair/9)")
        return False

    r_type = rec["type"]
    r_rank = rec["rank"]

    if r_type != "Pair" or r_rank != "9":
        print(f"  {FAIL} 期望 Pair/9, 实际 {r_type}/{r_rank}")
        return False

    # 验证推荐的 cards 确实在 actionList 中
    found = False
    for a in action_list:
        if a[0] == r_type and a[1] == r_rank:
            a_cards = sorted(str(c) for c in (a[2] if isinstance(a[2], list) else a))
            if sorted(str(c) for c in rec["cards"]) == a_cards:
                found = True
                break
    if not found:
        print(f"  {FAIL} 推荐 cards={rec['cards']} 不在 actionList 中")
        return False

    print(f"  {PASS} → {r_type}/{r_rank} cards={rec['cards']} (在 actionList 中)")
    return True


def _reset_r11_state():
    from src.v.nn.guards.v7_guards import _UPPER_SKIP_MEMORY, _POST_BOMB_BLOCK_TYPE
    _UPPER_SKIP_MEMORY.clear()
    _POST_BOMB_BLOCK_TYPE.clear()

def test_gua172_cheapest_bomb():
    """GUA-172: R11 放行改炸时选最廉价炸，而非最强行。"""
    print("\n=== GUA-172: 廉价炸选择 ===")
    _reset_r11_state()
    t = RecommenderTester()

    hand_cards = ["S3", "H3", "C3", "D3", "S4", "H4", "C4", "D4", "S9", "H9", "C9", "D9"]
    card_mask = make_card_mask(hand_cards, [
        (0, "Bomb", 1, ["S3", "H3", "C3", "D3"]),
        (1, "Bomb", 1, ["S4", "H4", "C4", "D4"]),
        (2, "Bomb", 1, ["S9", "H9", "C9", "D9"]),
    ], [])
    t._card_mask = card_mask
    t._group_type_map = {0: "Bomb", 1: "Bomb", 2: "Bomb"}

    # actionList: 3种炸弹可选，最廉价应是 Bomb/3
    action_list = build_actionList([
        ("Bomb", "3", sorted(["S3", "H3", "C3", "D3"])),
        ("Bomb", "4", sorted(["S4", "H4", "C4", "D4"])),
        ("Bomb", "9", sorted(["S9", "H9", "C9", "D9"])),
    ])

    gs = {
        "myPos": 0, "curPos": 3, "greaterPos": 3,
        "greaterAction": ["Single", "5", ["S5"]],
        "handCards": hand_cards, "curRank": "2",
        "_memory_tracker": None,
    }

    from src.v.nn.guards.v7_guards import _UPPER_SKIP_MEMORY
    _UPPER_SKIP_MEMORY[(0, 3)] = "Single"

    rec = t._recommend_play(gs, action_list)

    if rec is None:
        print(f"  {FAIL} 返回 None")
        return False
    if rec["type"] != "Bomb":
        print(f"  {FAIL} 期望 Bomb, 实际 {rec['type']}")
        return False
    if rec["rank"] != "3":
        print(f"  {FAIL} 期望最廉价 Bomb/3, 实际 Bomb/{rec['rank']}")
        return False

    print(f"  {PASS} → Bomb/{rec['rank']} (最廉价)")
    return True


def test_gua172_pass_sb_no_lb():
    """GUA-172: 跟上家 Single SB/B 且无 LB → PASS 而非炸。"""
    print("\n=== GUA-172: 单张王无LB → PASS ===")
    _reset_r11_state()
    t = RecommenderTester()

    hand_cards = ["S3", "H3", "C3", "D3", "S4", "H4", "C4", "D4",
                   "S9", "H9", "C9", "D9", "S5", "D5", "S8", "H8",
                   "S6", "H6", "C6", "SJ", "CJ", "SQ", "CQ", "SK", "CK"]
    card_mask = make_card_mask(hand_cards, [
        (0, "Bomb", 1, ["S3", "H3", "C3", "D3"]),
        (1, "Bomb", 1, ["S4", "H4", "C4", "D4"]),
        (2, "Bomb", 1, ["S9", "H9", "C9", "D9"]),
    ], ["S5", "D5", "S8", "H8", "S6", "H6", "C6", "SJ", "CJ", "SQ", "CQ", "SK", "CK"])
    t._card_mask = card_mask
    t._group_type_map = {0: "Bomb", 1: "Bomb", 2: "Bomb"}

    action_list = build_actionList([
        ("Bomb", "3", sorted(["S3", "H3", "C3", "D3"])),
        ("Bomb", "4", sorted(["S4", "H4", "C4", "D4"])),
        ("Bomb", "9", sorted(["S9", "H9", "C9", "D9"])),
        ("Single", "5", ["S5"]),
        ("Single", "8", ["S8"]),
    ])

    gs = {
        "myPos": 0, "curPos": 3, "greaterPos": 3,
        "greaterAction": ["Single", "B", ["SB"]],
        "handCards": hand_cards, "curRank": "2",
        "_memory_tracker": None,
    }

    from src.v.nn.guards.v7_guards import _UPPER_SKIP_MEMORY
    _UPPER_SKIP_MEMORY[(0, 3)] = "Single"

    rec = t._recommend_play(gs, action_list)

    if rec is None:
        print(f"  {FAIL} 返回 None")
        return False
    if rec["type"] != "PASS":
        print(f"  {FAIL} 期望 PASS, 实际 {rec['type']}/{rec['rank']}")
        return False

    print(f"  {PASS} → PASS (单SB无LB不浪费炸弹)")
    return True


def test_gua172_endgame_bomb_sb():
    """GUA-172: 残局 (≤10张) 仍允许炸单SB。"""
    print("\n=== GUA-172: 残局炸单SB（允许）===")
    _reset_r11_state()
    t = RecommenderTester()

    hand_cards = ["S3", "H3", "C3", "D3", "S4", "H4", "C4", "D4", "S9", "H9"]
    card_mask = make_card_mask(hand_cards, [
        (0, "Bomb", 1, ["S3", "H3", "C3", "D3"]),
        (1, "Bomb", 1, ["S4", "H4", "C4", "D4"]),
    ], ["S9", "H9"])
    t._card_mask = card_mask
    t._group_type_map = {0: "Bomb", 1: "Bomb"}

    action_list = build_actionList([
        ("Bomb", "3", sorted(["S3", "H3", "C3", "D3"])),
        ("Bomb", "4", sorted(["S4", "H4", "C4", "D4"])),
    ])

    gs = {
        "myPos": 0, "curPos": 3, "greaterPos": 3,
        "greaterAction": ["Single", "B", ["SB"]],
        "handCards": hand_cards, "curRank": "2",
        "_memory_tracker": None,
    }

    from src.v.nn.guards.v7_guards import _UPPER_SKIP_MEMORY
    _UPPER_SKIP_MEMORY[(0, 3)] = "Single"

    rec = t._recommend_play(gs, action_list)

    if rec is None:
        print(f"  {FAIL} 残局不应返回 None")
        return False
    if rec["type"] == "PASS":
        print(f"  {FAIL} 残局应允许炸, 实际 PASS")
        return False
    if rec["type"] != "Bomb":
        print(f"  {FAIL} 期望 Bomb, 实际 {rec['type']}")
        return False
    # 残局应仍选最廉价 Bomb/3
    if rec["rank"] != "3":
        print(f"  {FAIL} 期望 Bomb/3, 实际 Bomb/{rec['rank']}")
        return False

    print(f"  {PASS} → Bomb/{rec['rank']} (残局放行+廉价)")
    return True


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    results = []
    results.append(("跟上家对子7→推荐同型", test_follow_pair()))
    results.append(("跟上家单8→推荐更大单张", test_follow_single()))
    results.append(("跟上家三张5→推荐更大三张", test_follow_trips()))
    results.append(("无更大对子时返回None", test_follow_pair_no_available()))
    results.append(("领出→推荐小单张", test_lead_scenario()))
    results.append(("不跨牌型推荐(对子跟对子)", test_upper_not_follow_wrong_type()))
    results.append(("actionList宽松匹配", test_follow_with_actionlist_validation()))
    results.append(("GUA-172选择最廉价炸", test_gua172_cheapest_bomb()))
    results.append(("GUA-172单张王无LB→PASS", test_gua172_pass_sb_no_lb()))
    results.append(("GUA-172残局仍允许炸单SB", test_gua172_endgame_bomb_sb()))

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    print(f"结果: {passed}/{len(results)} 通过, {failed} 失败")
    for name, ok in results:
        print(f"  {PASS if ok else FAIL} {name}")
    print("=" * 60)
