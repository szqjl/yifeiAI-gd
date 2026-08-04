# -*- coding: utf-8 -*-
"""
GUA-116：主攻 stage_1 / stage_2 自由领出整牌型链。

P1 散单 → P2 TWT → P3 顺 → P3b 钢板 → P3c 三连对 → P3d 天然三张 → P4 小对。
GUA-174：2-hand sprint 时 P3b/P3c 优先于 P2（三连对/钢板硬先出）。
GUA-189：队友 1-5 张时按 assist_prefer 表优先喂牌（覆盖 P1-P4 管线）。

真源：docs/guandan-brain/V7-主攻领出-阶段划分设计口径.md
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.v.nn.assist_prefer_table import assist_prefer_for

if TYPE_CHECKING:
    from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _effective_stage(current_stage: str) -> str:
    if current_stage == "stage_0":
        return "stage_1"
    return current_stage


def _pip_order(card: str, cur_rank: str) -> int:
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank

    rank = get_card_rank(str(card))
    if rank == cur_rank:
        return 99
    if rank in ("HR", "SB", "BJ", "RJ"):
        return 100
    return CARD_RANK_ORDER.get(rank, 99)


def _has_joker(hand_cards: List[str]) -> bool:
    for c in hand_cards:
        r = str(c)
        if r in ("HR", "SB", "BJ", "RJ"):
            return True
        if len(r) >= 2 and r[1] in ("R", "B") and r[0] in "SHDC":
            return True
    return False


def _eligible_p1_singles(
    engine: "UltimateWinRateEngineV7",
    card_mask: Dict[str, tuple],
    hand_cards: List[str],
    cur_rank: str,
    group_type_map: Dict[int, str],
    group_members: Optional[Dict[int, List[str]]],
) -> List[str]:
    """O10：<10 散单（3–9，不含级牌）。"""
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank

    protected = frozenset(("Bomb", "StraightFlush", "straight"))

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    def _breaks_core(card: str) -> bool:
        broken = engine._get_broken_core_type(
            ["Single", _prank(get_card_rank(str(card))), [str(card)]],
            card_mask,
            group_type_map,
            group_members,
        )
        return broken in protected

    out: List[str] = []
    for card in engine._scatter_singles(card_mask):
        card = str(card)
        if get_card_rank(card) == cur_rank:
            continue
        pip = _pip_order(card, cur_rank)
        if CARD_RANK_ORDER["3"] <= pip <= CARD_RANK_ORDER["9"]:
            if not _breaks_core(card):
                out.append(card)
    out.sort(key=lambda c: (_pip_order(c, cur_rank), c))
    return out


def _pick_p1_second_smallest(
    eligible: List[str], *, enemy_one_left: bool = False,
) -> Optional[str]:
    """P1 出单：默认第二小；若第二小 > Q 则出第一小（守大不破）。

    对方剩一张时保持原逻辑（始终第二小），不触发 >Q 改写。
    """
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank

    if len(eligible) >= 2:
        second = eligible[1]
        if not enemy_one_left and CARD_RANK_ORDER.get(get_card_rank(second), 99) > CARD_RANK_ORDER["Q"]:
            return eligible[0]
        return eligible[1]
    if len(eligible) == 1:
        return eligible[0]
    return None


def _any_enemy_one_left(game_state: Dict[str, Any], my_pos: int) -> bool:
    """任一敌方剩 1 张 → True（P1 保持原逻辑出第二小）。"""
    numofplayers = game_state.get("numofplayers") or []
    if not numofplayers or len(numofplayers) != 4:
        return False
    teammate_pos = (my_pos + 2) % 4
    for seat in ((my_pos + 1) % 4, (my_pos + 3) % 4):
        rem = numofplayers[seat]
        if isinstance(rem, (int, float)) and int(rem) == 1:
            return True
    return False


def _has_k_principle_pair_recapture(
    engine: "UltimateWinRateEngineV7",
    groups: Dict[int, dict],
    cur_rank: str,
) -> bool:
    """§2.4：存在 K 及以上（含级牌）对子作回手。"""
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank

    pair_types = ("pair", "pair_in_three_with_two", "pair_in_three_pair")
    for ginfo in groups.values():
        if ginfo["type"] not in pair_types:
            continue
        if len(ginfo["cards"]) < 2:
            continue
        rank = get_card_rank(str(ginfo["cards"][0]))
        if rank == cur_rank:
            return True
        if CARD_RANK_ORDER.get(rank, -1) >= CARD_RANK_ORDER["K"]:
            return True
    return False


def _enumerate_twt_units(groups: Dict[int, dict]) -> List[Dict[str, Any]]:
    """三带二 = trip_in_three_with_two + 紧邻 pair_in_three_with_two（to_card_mask 顺序）。"""
    units: List[Dict[str, Any]] = []
    for gid in sorted(groups.keys()):
        trip = groups.get(gid)
        if not trip or trip["type"] != "trip_in_three_with_two":
            continue
        pair = groups.get(gid + 1)
        if not pair or pair["type"] != "pair_in_three_with_two":
            continue
        cards = sorted(str(c) for c in trip["cards"]) + sorted(
            str(c) for c in pair["cards"]
        )
        if len(cards) != 5:
            continue
        units.append(
            {
                "trip_gid": gid,
                "pair_gid": gid + 1,
                "cards": cards,
                "is_core": max(trip["is_core"], pair["is_core"]),
            }
        )
    return units


def _enumerate_two_trips_units(groups: Dict[int, dict]) -> List[Dict[str, Any]]:
    """钢板 = 相邻两个 trip_in_steel_plate（to_card_mask 顺序）。"""
    units: List[Dict[str, Any]] = []
    for gid in sorted(groups.keys()):
        t0 = groups.get(gid)
        if not t0 or t0["type"] != "trip_in_steel_plate":
            continue
        t1 = groups.get(gid + 1)
        if not t1 or t1["type"] != "trip_in_steel_plate":
            continue
        cards = sorted(str(c) for c in t0["cards"]) + sorted(str(c) for c in t1["cards"])
        if len(cards) != 6:
            continue
        units.append(
            {
                "gids": (gid, gid + 1),
                "cards": cards,
                "is_core": max(t0["is_core"], t1["is_core"]),
            }
        )
    return units


def _enumerate_three_pair_units(groups: Dict[int, dict]) -> List[Dict[str, Any]]:
    """三连对 = 连续三个 pair_in_three_pair。"""
    units: List[Dict[str, Any]] = []
    for gid in sorted(groups.keys()):
        p0 = groups.get(gid)
        if not p0 or p0["type"] != "pair_in_three_pair":
            continue
        p1 = groups.get(gid + 1)
        p2 = groups.get(gid + 2)
        if not p1 or p1["type"] != "pair_in_three_pair":
            continue
        if not p2 or p2["type"] != "pair_in_three_pair":
            continue
        cards = (
            sorted(str(c) for c in p0["cards"])
            + sorted(str(c) for c in p1["cards"])
            + sorted(str(c) for c in p2["cards"])
        )
        if len(cards) != 6:
            continue
        units.append(
            {
                "gids": (gid, gid + 1, gid + 2),
                "cards": cards,
                "is_core": max(p0["is_core"], p1["is_core"], p2["is_core"]),
            }
        )
    return units


def _has_twt_recapture(
    groups: Dict[int, dict],
    lead_trip_gid: Optional[int],
) -> bool:
    """P2：除拟出 TWT 外仍有另一手三带二。"""
    others = [
        u for u in _enumerate_twt_units(groups) if u["trip_gid"] != lead_trip_gid
    ]
    return len(others) >= 1


def _has_straight_recapture(
    groups: Dict[int, dict],
    lead_gid: Optional[int],
) -> bool:
    straights = [gid for gid, g in groups.items() if g["type"] == "straight" and gid != lead_gid]
    return len(straights) >= 1


def _has_bomb_recapture(groups: Dict[int, dict]) -> bool:
    """回手泛化：组牌内仍有 Bomb / StraightFlush 可接回牌权（整组出，非拆核）。"""
    return any(g.get("type") in ("Bomb", "StraightFlush") for g in groups.values())


def _has_structure_recapture(
    groups: Dict[int, dict],
    *,
    lead_gid: Optional[int] = None,
    kind: str,
    engine: Optional["UltimateWinRateEngineV7"] = None,
    cur_rank: str = "2",
) -> bool:
    """
    自由领出「有回手」统一判定（§2.4 + L11/L14 炸夺权语义）：
    - 同型更大/另一手（TWT / 顺 / 钢板 / 三连对 / 三张）
    - K 原则对子（顺领出时可作回手）
    - 组内炸弹/同花顺（接回，不限牌型）
    """
    if kind == "twt":
        if _has_twt_recapture(groups, lead_gid):
            return True
    elif kind == "straight":
        if _has_straight_recapture(groups, lead_gid):
            return True
        if engine is not None and _has_k_principle_pair_recapture(engine, groups, cur_rank):
            return True
    elif kind == "two_trips":
        others = [
            u for u in _enumerate_two_trips_units(groups)
            if lead_gid is None or lead_gid not in u["gids"]
        ]
        if others:
            return True
    elif kind == "three_pair":
        others = [
            u for u in _enumerate_three_pair_units(groups)
            if lead_gid is None or lead_gid not in u["gids"]
        ]
        if others:
            return True
    elif kind == "trips":
        trips = [
            gid for gid, g in groups.items()
            if g["type"] == "trips" and gid != lead_gid
        ]
        if trips:
            return True
    if _has_bomb_recapture(groups):
        return True
    return False


def _count_groups(groups: Dict[int, dict], gtypes: frozenset) -> int:
    return sum(1 for g in groups.values() if g["type"] in gtypes)


def _pick_smallest_twt(
    engine: "UltimateWinRateEngineV7",
    groups: Dict[int, dict],
    cur_rank: str,
) -> Optional[tuple]:
    from src.v.nn.guards.v7_guards import get_card_rank

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    best = None
    for unit in _enumerate_twt_units(groups):
        cards = unit["cards"]
        trip_rank = get_card_rank(cards[0])
        key = (_pip_order(cards[0], cur_rank), cards)
        if best is None or key < best[0]:
            pr = _prank(trip_rank)
            best = (key, unit["trip_gid"], "ThreeWithTwo", pr, cards)
    if not best:
        return None
    _, trip_gid, typ, pr, cards = best
    return trip_gid, typ, pr, cards


def _pick_smallest_straight(
    engine: "UltimateWinRateEngineV7",
    groups: Dict[int, dict],
    cur_rank: str,
) -> Optional[tuple]:
    from src.v.nn.guards.v7_guards import get_card_rank

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    # is_core 只禁「拆」不禁「整组出」：顺子在 to_card_mask 中均为 is_core=1.0，
    # 不得因 is_core 跳过；整组 cards 打出由 filter 判定 used==total 放行。
    best = None
    for gid, ginfo in groups.items():
        if ginfo["type"] != "straight":
            continue
        sequence_cards = [str(c) for c in ginfo["cards"]]
        cards = sorted(sequence_cards)
        if len(cards) < 5:
            continue
        pr = _prank(get_card_rank(sequence_cards[0]))
        key = (_pip_order(cards[0], cur_rank), cards)
        if best is None or key < best[0]:
            best = (key, gid, "Straight", pr, cards[:5])
    if not best:
        return None
    _, gid, typ, pr, cards = best
    return gid, typ, pr, cards


def _pick_smallest_two_trips(
    engine: "UltimateWinRateEngineV7",
    groups: Dict[int, dict],
    cur_rank: str,
) -> Optional[tuple]:
    from src.v.nn.guards.v7_guards import get_card_rank

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    best = None
    for unit in _enumerate_two_trips_units(groups):
        cards = unit["cards"]
        # 小点三张在前：取两组三张中较小 rank
        ranks = sorted(
            {get_card_rank(c) for c in cards},
            key=lambda r: engine.RANK_ORDER.get(r, 99),
        )
        low_rank = ranks[0]
        low_card = next(c for c in cards if get_card_rank(c) == low_rank)
        key = (_pip_order(low_card, cur_rank), cards)
        if best is None or key < best[0]:
            pr = _prank(low_rank)
            best = (key, unit["gids"][0], "TwoTrips", pr, cards)
    if not best:
        return None
    _, gid, typ, pr, cards = best
    return gid, typ, pr, cards


def _pick_smallest_three_pair(
    engine: "UltimateWinRateEngineV7",
    groups: Dict[int, dict],
    cur_rank: str,
) -> Optional[tuple]:
    from src.v.nn.guards.v7_guards import get_card_rank

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    best = None
    for unit in _enumerate_three_pair_units(groups):
        cards = unit["cards"]
        ranks = sorted(
            {get_card_rank(c) for c in cards},
            key=lambda r: engine.RANK_ORDER.get(r, 99),
        )
        low_rank = ranks[0]
        low_card = next(c for c in cards if get_card_rank(c) == low_rank)
        key = (_pip_order(low_card, cur_rank), cards)
        if best is None or key < best[0]:
            pr = _prank(low_rank)
            best = (key, unit["gids"][0], "ThreePair", pr, cards)
    if not best:
        return None
    _, gid, typ, pr, cards = best
    return gid, typ, pr, cards


def _pick_smallest_natural_trips(
    engine: "UltimateWinRateEngineV7",
    groups: Dict[int, dict],
    cur_rank: str,
) -> Optional[tuple]:
    """仅天然 trips；禁止 trip_in_steel_plate / trip_in_three_with_two（那是拆核）。"""
    from src.v.nn.guards.v7_guards import get_card_rank

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    best = None
    for gid, ginfo in groups.items():
        if ginfo["type"] != "trips":
            continue
        cards = sorted(str(c) for c in ginfo["cards"])[:3]
        if len(cards) < 3:
            continue
        pr = _prank(get_card_rank(cards[0]))
        key = (_pip_order(cards[0], cur_rank), cards)
        if best is None or key < best[0]:
            best = (key, gid, "Trips", pr, cards)
    if not best:
        return None
    _, gid, typ, pr, cards = best
    return gid, typ, pr, cards


def _pick_p4_small_pair(
    engine: "UltimateWinRateEngineV7",
    groups: Dict[int, dict],
    cur_rank: str,
) -> Optional[Dict[str, Any]]:
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    # 仅天然 pair（整组）；禁止抠 pair_in_three_with_two / pair_in_three_pair（那是拆核）
    candidates = []
    for ginfo in groups.values():
        if ginfo["type"] != "pair":
            continue
        cards = sorted(str(c) for c in ginfo["cards"])[:2]
        if len(cards) < 2:
            continue
        rank = get_card_rank(cards[0])
        if rank == cur_rank:
            continue
        pip = CARD_RANK_ORDER.get(rank, 99)
        if pip >= CARD_RANK_ORDER["T"]:
            continue
        candidates.append((pip, cards, rank))
    if not candidates:
        return None
    _, cards, rank = min(candidates, key=lambda x: (x[0], x[1]))
    return {
        "type": "Pair",
        "rank": _prank(rank),
        "cards": cards,
        "intent": "main_p4_small_pair",
    }


def _try_feed_from_groups(
    engine: "UltimateWinRateEngineV7",
    groups: Dict[int, dict],
    card_mask: Dict[str, tuple],
    hand_cards: List[str],
    cur_rank: str,
    feed_prefer: List[str],
    group_type_map: Dict[int, str],
    group_members: Optional[Dict[int, List[str]]],
) -> Optional[Dict[str, Any]]:
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    for atype in feed_prefer:
        if atype == "Straight":
            result = _pick_smallest_straight(engine, groups, cur_rank)
            if result:
                gid, typ, pr, cards = result
                if _has_structure_recapture(groups, lead_gid=gid, kind="straight", engine=engine, cur_rank=cur_rank):
                    return {"type": typ, "rank": pr, "cards": cards, "intent": "main_feed_teammate_Straight"}

        elif atype == "ThreeWithTwo":
            result = _pick_smallest_twt(engine, groups, cur_rank)
            if result:
                gid, typ, pr, cards = result
                if _has_structure_recapture(groups, lead_gid=gid, kind="twt", engine=engine, cur_rank=cur_rank):
                    return {"type": typ, "rank": pr, "cards": cards, "intent": "main_feed_teammate_ThreeWithTwo"}

        elif atype == "Trips":
            result = _pick_smallest_natural_trips(engine, groups, cur_rank)
            if result:
                gid, typ, pr, cards = result
                if _has_structure_recapture(groups, lead_gid=gid, kind="trips", engine=engine, cur_rank=cur_rank):
                    return {"type": typ, "rank": pr, "cards": cards, "intent": "main_feed_teammate_Trips"}

        elif atype == "Pair":
            from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank
            _candidates = []
            for _ginfo in groups.values():
                if _ginfo["type"] != "pair":
                    continue
                _crds = sorted(str(c) for c in _ginfo["cards"])[:2]
                if len(_crds) < 2:
                    continue
                _rk = get_card_rank(_crds[0])
                if _rk == cur_rank:
                    continue
                _candidates.append((CARD_RANK_ORDER.get(_rk, 99), _crds, _rk))
            if _candidates:
                _, _crds, _rk = min(_candidates, key=lambda x: (x[0], x[1]))
                return {
                    "type": "Pair",
                    "rank": _prank(_rk),
                    "cards": _crds,
                    "intent": "main_feed_teammate_Pair",
                }

        elif atype == "Single":
            eligible = _eligible_p1_singles(
                engine, card_mask, hand_cards, cur_rank, group_type_map, group_members,
            )
            if eligible:
                card = eligible[0]
                return {
                    "type": "Single",
                    "rank": _prank(get_card_rank(card)),
                    "cards": [card],
                    "intent": "main_feed_teammate_Single",
                }

    return None


def recommend_main_attack_lead(
    engine: "UltimateWinRateEngineV7",
    game_state: Dict[str, Any],
    card_mask: Dict[str, tuple],
    hand_cards: List[str],
    cur_rank: str,
    current_stage: str,
) -> Optional[Dict[str, Any]]:
    """
    主攻 is_lead：P1 → P2 → P3 → P4（命中即返回）。
    GUA-189：队友 1-5 张时按 assist_prefer 表优先喂牌（覆盖 P1-P4 管线）。
    stage_0 overlay 按 stage_1 规则；L11/L14 defer 在 stage_1 跳过唯一小 TWT/顺。
    """
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    stage = _effective_stage(current_stage)
    group_type_map = engine._group_type_map or {}
    group_members = engine._group_members or None
    groups = engine._build_group_index(card_mask)

    # ── 送队友覆盖（before P1）：队友 1-5 张时按 assist_prefer 表喂牌 ──
    numofplayers = game_state.get("numofplayers") or []
    my_pos = int(game_state.get("myPos", 0))
    if numofplayers and len(numofplayers) == 4:
        teammate_pos = (my_pos + 2) % 4
        teammate_rem = numofplayers[teammate_pos]
        if isinstance(teammate_rem, (int, float)) and 1 <= int(teammate_rem) <= 5:
            feed_prefer = assist_prefer_for(int(teammate_rem))
            feed_action = _try_feed_from_groups(
                engine, groups, card_mask, hand_cards, cur_rank,
                feed_prefer, group_type_map, group_members,
            )
            if feed_action:
                return feed_action

    # ── P1（O10）──
    p1_singles = _eligible_p1_singles(
        engine, card_mask, hand_cards, cur_rank, group_type_map, group_members,
    )
    if _has_joker(hand_cards) or len(p1_singles) >= 2:
        enemy_one_left = _any_enemy_one_left(game_state, my_pos)
        card = _pick_p1_second_smallest(p1_singles, enemy_one_left=enemy_one_left)
        if card:
            return {
                "type": "Single",
                "rank": _prank(get_card_rank(card)),
                "cards": [card],
                "intent": "main_p1_second_single",
            }

    straight_types = frozenset(("straight",))
    twt_count = len(_enumerate_twt_units(groups))
    straight_count = _count_groups(groups, straight_types)

    # ── GUA-174: 2-hand sprint detection ──
    _tp_units = _enumerate_three_pair_units(groups)
    _tt_units = _enumerate_two_trips_units(groups)
    _non_bomb_structures = twt_count + len(_tt_units) + len(_tp_units) + straight_count
    _scatter_singles = len(engine._scatter_singles(card_mask))
    _sprint_two_hands = (
        _non_bomb_structures == 2 and _scatter_singles == 0
        and (len(_tp_units) > 0 or len(_tt_units) > 0)
    )

    # ── GUA-179：对手牌型弱点感知 → 优先出对手 PASS/被迫开炸过的牌型 ──
    # 预计算 st_pick（原在 P3 中，为弱点检测提前）
    st_pick = _pick_smallest_straight(engine, groups, cur_rank)
    _weakness_promoted = None
    tracker = game_state.get("_memory_tracker")
    if tracker is not None and hasattr(tracker, "get_type_weakness"):
        _my_pos = game_state.get("myPos", game_state.get("player_id", 0))
        opps = {(_my_pos + 1) % 4, (_my_pos + 3) % 4}
        _opp_weakness = {}
        for opp in opps:
            for k, v in tracker.get_type_weakness(opp).items():
                _opp_weakness[k] = _opp_weakness.get(k, 0) + v
        # 若顺子是对方弱点且有可用顺子 → 提前走 P3
        if _opp_weakness.get("Straight", 0) >= 1 and st_pick:
            gid, typ, pr, cards = st_pick
            scatter_n = len(engine._scatter_singles(card_mask))
            lonely_ok = scatter_n <= 2
            if lonely_ok and _has_structure_recapture(
                groups, lead_gid=gid, kind="straight", engine=engine, cur_rank=cur_rank,
            ):
                _weakness_promoted = {
                    "type": typ,
                    "rank": pr,
                    "cards": cards,
                    "intent": "main_p3_straight_via_weakness",
                }

    # GUA-179：弱点牌型优先于 P2（原"先 TWT 再顺"固序）
    if _weakness_promoted is not None and not _sprint_two_hands:
        return _weakness_promoted

    # ── GUA-XXX: 光三检测 — 全小Trips无回收时跳过P2 ──
    # 场景：多组小 Trips（222/333/666/888），无 QQQ+ 回收，无 <10 对子
    # 人类俗称光三：出纯 Trips 让对手带对子更难、留下我方对子回收
    _skip_p2_for_trips = False
    if twt_count >= 1 and not _sprint_two_hands:
        _twt_units = _enumerate_twt_units(groups)
        if _twt_units:
            _all_small_trip = all(
                CARD_RANK_ORDER.get(get_card_rank(u["cards"][0]), 99) <= CARD_RANK_ORDER.get("J", 9)
                for u in _twt_units
            )
            _all_big_pair = all(
                CARD_RANK_ORDER.get(get_card_rank(u["cards"][3]), 0) >= CARD_RANK_ORDER.get("T", 8)
                for u in _twt_units
            )
            _has_big_trip = any(
                CARD_RANK_ORDER.get(get_card_rank(g["cards"][0]), 0) >= CARD_RANK_ORDER.get("Q", 10)
                for g in groups.values()
                if g["type"] in ("trips", "trip_in_three_with_two", "trip_in_steel_plate")
            )
            if _all_small_trip and _all_big_pair and not _has_big_trip:
                _skip_p2_for_trips = True

    # ── P2：整组三带二（is_core 整组出 ≠ 拆核）──
    #    GUA-174: skip TWT in 2-hand sprint when ThreePair/TwoTrips available
    twt_pick = _pick_smallest_twt(engine, groups, cur_rank)
    if _skip_p2_for_trips:
        pass
    elif twt_pick and not _sprint_two_hands:
        gid, typ, pr, cards = twt_pick
        defer = twt_count == 1 and stage == "stage_1"
        if not defer and _has_structure_recapture(
            groups, lead_gid=gid, kind="twt", engine=engine, cur_rank=cur_rank,
        ):
            return {
                "type": typ,
                "rank": pr,
                "cards": cards,
                "intent": "main_p2_three_with_two",
            }

    # ── P3：整组短小顺（含 is_core=1.0 的组牌顺）──
    st_pick = _pick_smallest_straight(engine, groups, cur_rank)
    if st_pick:
        gid, typ, pr, cards = st_pick
        scatter_n = len(engine._scatter_singles(card_mask))
        defer = straight_count == 1 and stage == "stage_1"
        lonely_ok = scatter_n <= 2
        if not defer and lonely_ok and _has_structure_recapture(
            groups, lead_gid=gid, kind="straight", engine=engine, cur_rank=cur_rank,
        ):
            return {
                "type": typ,
                "rank": pr,
                "cards": cards,
                "intent": "main_p3_short_straight",
            }

    # ── P3b：整组钢板 TwoTrips（禁半组 Trips）──
    tt_pick = _pick_smallest_two_trips(engine, groups, cur_rank)
    if tt_pick:
        gid, typ, pr, cards = tt_pick
        tt_count = len(_enumerate_two_trips_units(groups))
        # GUA-XXX: 大点钢板 defer — rank > T(J/Q/K/A) 时让 P3c 先出
        # AAA-KKK 等既可钢板又可 TWT 还可拆防，前期出太浪费
        _low_rank_val = CARD_RANK_ORDER.get(get_card_rank(cards[0]), 0)
        _high_tt_defer = _low_rank_val > CARD_RANK_ORDER.get("T", 8)

        # 有炸回手时不 defer（炸+钢板 = 冲刺态，应整组领出）
        # 但大点钢板有炸也 defer（灵活牌型前期不浪费）
        defer = (
            tt_count == 1 and stage == "stage_1"
            and (not _has_bomb_recapture(groups) or _high_tt_defer)
        )
        if not defer and _has_structure_recapture(
            groups, lead_gid=gid, kind="two_trips", engine=engine, cur_rank=cur_rank,
        ):
            return {
                "type": typ,
                "rank": pr,
                "cards": cards,
                "intent": "main_p3b_two_trips",
            }

    # ── P3c：整组三连对 ThreePair ──
    tp_pick = _pick_smallest_three_pair(engine, groups, cur_rank)
    if tp_pick:
        gid, typ, pr, cards = tp_pick
        tp_count = len(_enumerate_three_pair_units(groups))
        defer = (
            tp_count == 1 and stage == "stage_1"
            and not _has_bomb_recapture(groups)
        )
        if not defer and _has_structure_recapture(
            groups, lead_gid=gid, kind="three_pair", engine=engine, cur_rank=cur_rank,
        ):
            return {
                "type": typ,
                "rank": pr,
                "cards": cards,
                "intent": "main_p3c_three_pair",
            }

    # ── P3d：天然三张 Trips（不含钢板/TWT 子结构）──
    trips_pick = _pick_smallest_natural_trips(engine, groups, cur_rank)
    if trips_pick:
        gid, typ, pr, cards = trips_pick
        if _has_structure_recapture(
            groups, lead_gid=gid, kind="trips", engine=engine, cur_rank=cur_rank,
        ):
            return {
                "type": typ,
                "rank": pr,
                "cards": cards,
                "intent": "main_p3d_trips",
            }

    # GUA-174: 2-hand sprint fallback — ThreePair/TwoTrips unmatched, use TWT
    if _sprint_two_hands and twt_pick:
        _, typ, pr, cards = twt_pick
        return {
            "type": typ,
            "rank": pr,
            "cards": cards,
            "intent": "main_p2_three_with_two",
        }

    # 无回手 TWT 仍可能 P2 若多手
    if twt_pick and twt_count >= 2:
        _, typ, pr, cards = twt_pick
        return {
            "type": typ,
            "rank": pr,
            "cards": cards,
            "intent": "main_p2_three_with_two",
        }

    # 无回手钢板：多手钢板仍可领；仅剩「炸+钢板」时炸已在 recapture 命中
    if tt_pick and len(_enumerate_two_trips_units(groups)) >= 2:
        _, typ, pr, cards = tt_pick
        return {
            "type": typ,
            "rank": pr,
            "cards": cards,
            "intent": "main_p3b_two_trips",
        }

    # ── P4 ──
    p4 = _pick_p4_small_pair(engine, groups, cur_rank)
    if p4:
        return p4

    # 兜底：最小非 core 单（仍优于 orphan 高单）
    singles = _eligible_p1_singles(
        engine, card_mask, hand_cards, cur_rank, group_type_map, group_members,
    )
    if singles:
        card = singles[0]
        return {
            "type": "Single",
            "rank": _prank(get_card_rank(card)),
            "cards": [card],
            "intent": "main_p4_fallback_single",
        }

    return None
