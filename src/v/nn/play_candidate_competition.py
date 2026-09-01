# -*- coding: utf-8 -*-
"""GUA-283 / GUA-285 / GUA-234 §3.4：GUA-075 主路径候选竞争 + 出牌前残手前瞻。

GUA-285：跟压候选池扩至 actionList 同型可压全集 + GUA-075 多候选；
拆核惩罚对齐 ``EndgameDecider._action_breaks_core_structure``（group_members 真源）。

设计真源：docs/guandan-brain/V8-中期压顺灵活性-组牌-动态重组方案.md §3.3–3.4
基础策略：docs/knowledge/skills/01_foundation/03_basic_strategy.md §灵活应对

决策优先级（高 → 低，**残局规则全部保留**）：
  1. 残局管线 ``EndgameDecider``（Q0–Q3、GUA-257/260/261/238…）— 命中则不经本模块
  2. 本模块候选竞争（仅中期跟压、非残局态）
  3. GUA-075 原推荐

豁免 E1–E4（与 ``dynamic_regroup.check_regroup_exemption`` 同口径）：
  - E1 队友冲刺 ≤5：teammate_win_gain +0.38，残手罚 ×0.25
  - E2 敌冲刺阻断 ≤5 + 无反压：control_gain +0.22
  - E3 无反压窗口：残手罚 ×0.6
  - E4 自己残局自救 ≤5：残手罚 ×0.6，两手内可走完时 control_gain +0.18

每候选在「打出前」对 residual_hand 跑 enumerate_groupings，避免出牌后才重算。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.v.nn.dynamic_regroup import check_regroup_exemption
from src.v.nn.features.grouping_engine import NORM_MAX_POWER
from src.v.nn.residual_hand_quality import (
    ResidualQualityResult,
    evaluate_after_counter_action,
    evaluate_residual_hand,
    residual_structure_penalty,
    residual_waste_penalty,
)


@dataclass
class CandidateScore:
    """单候选 exec_weight 分解（trace 用）。"""

    source: str
    rec: Dict[str, Any]
    exec_weight: float
    control_gain: float = 0.0
    teammate_gain: float = 0.0
    plan_loss: float = 0.0
    core_break_penalty: float = 0.0
    waste_penalty: float = 0.0
    structure_penalty: float = 0.0
    belief_penalty: float = 0.0
    residual_power: float = 0.0
    baseline_power: float = 0.0
    power_drop: float = 0.0
    has_anchor: bool = False
    vetoed: bool = False
    veto_reason: str = ""
    exemption: str = ""
    joker_penalty: float = 0.0


PRESERVE_JOKER_CONTROL_PENALTY = 0.6


@dataclass
class CompetitionResult:
    """候选竞争结果。"""

    rec: Optional[Dict[str, Any]]
    act_index: int
    scores: List[CandidateScore] = field(default_factory=list)
    picked_source: str = ""


def _seat_rest(game_state: Dict[str, Any], seat: int) -> int:
    """剩张数：优先 numofplayers（平台 publicInfo），再 belief。"""
    nop = game_state.get("numofplayers") or []
    if isinstance(nop, (list, tuple)) and len(nop) > seat:
        try:
            return int(nop[seat])
        except (TypeError, ValueError):
            pass
    if isinstance(nop, dict):
        try:
            return int(nop.get(seat, 27) or 27)
        except (TypeError, ValueError):
            pass
    belief = game_state.get("_belief") or {}
    hand_counts = belief.get("hand_counts") or {}
    if isinstance(hand_counts, dict):
        try:
            return int(hand_counts.get(seat, 27) or 27)
        except (TypeError, ValueError):
            return 27
    if isinstance(hand_counts, list) and seat < len(hand_counts):
        try:
            return int(hand_counts[seat] or 27)
        except (TypeError, ValueError):
            return 27
    return 27


def _is_follow_press_scenario(game_state: Dict[str, Any]) -> bool:
    """跟压场景（非自由领出、非纯让队友）才跑候选竞争。"""
    my_pos = int(game_state.get("myPos", 0) or 0)
    greater_pos = int(game_state.get("greaterPos", -1) or -1)
    teammate_pos = (my_pos + 2) % 4
    greater_action = game_state.get("greaterAction") or []
    if not greater_action or greater_action[0] in ("PASS", ""):
        return False
    if greater_pos in (-1, my_pos):
        return False
    if greater_pos == teammate_pos:
        return False
    gt = str(greater_action[0] or "")
    if gt in ("Bomb", "StraightFlush"):
        return False
    return True


def _pass_candidate(game_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return {
        "type": "PASS",
        "rank": "",
        "cards": [],
        "intent": "gua283_compete_pass",
    }


_CORE_TYPES_GROUP_MEMBERS = frozenset({
    "StraightFlush", "Bomb", "straight", "trips",
    "trip_in_three_with_two", "pair_in_three_with_two",
    "pair_in_three_pair", "trip_in_steel_plate",
})


def _action_to_rec(action: List) -> Dict[str, Any]:
    """actionList 条目 → GUA-075 推荐 dict。"""
    cards = list(action[2]) if len(action) >= 3 and isinstance(action[2], list) else []
    return {
        "type": str(action[0] or ""),
        "rank": str(action[1] or "") if len(action) > 1 else "",
        "cards": [str(c) for c in cards],
    }


def _broken_core_from_group_members(
    engine: Any,
    game_state: Dict[str, Any],
    rec: Dict[str, Any],
) -> Optional[str]:
    """GUA-285：group_members 真源拆核判定（与残局 Q3 一致）。"""
    from src.v.nn.endgame.endgame_decide import EndgameDecider

    group_members = (
        game_state.get("_group_members")
        or getattr(engine, "_group_members", None)
    )
    if not group_members:
        return None

    gid_type_map = (
        game_state.get("_group_gid_type_map")
        or game_state.get("_group_type_map")
        or getattr(engine, "_group_type_map", {})
        or {}
    )
    gs = dict(game_state)
    gs["_group_members"] = group_members
    gs["_group_gid_type_map"] = gid_type_map

    action = [
        str(rec.get("type") or ""),
        str(rec.get("rank") or ""),
        list(rec.get("cards") or []),
    ]
    if not EndgameDecider._action_breaks_core_structure(action, gs):
        return None

    action_counts = Counter(str(c) for c in (rec.get("cards") or []))
    best_type: Optional[str] = None
    best_cost = -1
    for gid, members in group_members.items():
        gtype = gid_type_map.get(gid) or gid_type_map.get(str(gid), "")
        if gtype not in _CORE_TYPES_GROUP_MEMBERS:
            continue
        members_counts = Counter(str(c) for c in members)
        overlap = action_counts & members_counts
        if not overlap or overlap == members_counts:
            continue
        cost = _core_type_break_cost(str(gtype))
        if cost > best_cost:
            best_cost = cost
            best_type = str(gtype)
    return best_type or "core"


def _core_type_break_cost(gtype: str) -> int:
    if gtype in ("Bomb", "StraightFlush"):
        return 100
    if gtype == "straight":
        return 12
    if gtype in ("trips", "pair", "trip_in_three_with_two", "pair_in_three_with_two"):
        return 6
    return 1


def _merge_core_break_types(
    broken_mask: Optional[str],
    broken_members: Optional[str],
) -> Optional[str]:
    """合并 mask 与 group_members 拆核结论；任一命中 Bomb/SF 即硬否决。"""
    for b in (broken_mask, broken_members):
        if b in ("Bomb", "StraightFlush"):
            return b
    return broken_members or broken_mask


def collect_actionlist_press_candidates(
    action_list: List,
    greater_action: List,
    cur_rank: str,
) -> List[Dict[str, Any]]:
    """GUA-285：从 actionList 枚举同型合法压牌（平台真源全集）。"""
    from src.v.nn.endgame.endgame_decide import (
        _action_beats_greater,
        _get_declared_action_type,
        _is_bomb_like_action,
        _min_card_value,
    )
    from src.v.nn.guards.v7_guards import get_action_type

    if not action_list or not greater_action or greater_action[0] in ("PASS", ""):
        return []

    greater_type = get_action_type(greater_action)
    if greater_type in ("Bomb", "StraightFlush"):
        return []

    matched: List[Tuple[int, List]] = []
    for i, action in enumerate(action_list):
        try:
            if _get_declared_action_type(action) in ("PASS",):
                continue
            if _is_bomb_like_action(action):
                continue
            if get_action_type(action) != greater_type:
                continue
            if not _action_beats_greater(action, greater_action, cur_rank):
                continue
            matched.append((i, action))
        except Exception:
            continue

    if not matched:
        return []

    matched.sort(key=lambda x: _min_card_value(x[1], cur_rank))
    return [_action_to_rec(a) for _, a in matched]


def collect_competition_candidates(
    engine: Any,
    game_state: Dict[str, Any],
    primary_rec: Optional[Dict[str, Any]],
    action_list: Optional[List] = None,
    *,
    include_regroup: bool = True,
) -> List[Tuple[str, Dict[str, Any]]]:
    """收集 GUA-075 主路径竞争候选（含 PASS、actionList 全集、GUA-075 多候选）。"""
    out: List[Tuple[str, Dict[str, Any]]] = []
    seen: set = set()

    def _add(source: str, rec: Optional[Dict[str, Any]]) -> None:
        if not rec:
            return
        key = (
            rec.get("type"),
            rec.get("rank"),
            tuple(sorted(str(c) for c in (rec.get("cards") or []))),
        )
        if key in seen:
            return
        seen.add(key)
        out.append((source, dict(rec)))

    pass_rec = _pass_candidate(game_state)
    _add("pass", pass_rec)
    _add("gua075_primary", primary_rec)

    cur_rank = str(game_state.get("curRank", "2"))
    greater_action = game_state.get("greaterAction") or []

    # GUA-285：actionList 同型可压全集
    if action_list and _is_follow_press_scenario(game_state):
        for rec in collect_actionlist_press_candidates(
            action_list, greater_action, cur_rank,
        ):
            _add("actionlist", rec)

    # GUA-285：GUA-075 跟压多候选（不单 early-return 的第一个）
    if hasattr(engine, "recommend_min_press_all_candidates"):
        try:
            for rec in engine.recommend_min_press_all_candidates(game_state) or []:
                _add("gua075_alt", rec)
        except Exception:
            pass

    if not include_regroup or not getattr(engine, "_dynamic_regroup_enabled", True):
        return out

    hand_cards = list(game_state.get("handCards") or [])
    if not hand_cards or not greater_action:
        return out

    from src.v.nn.guards.v7_guards import get_action_type

    greater_type = get_action_type(greater_action)
    card_mask = getattr(engine, "_card_mask", None) or {}
    if not card_mask:
        return out

    try:
        raw = engine._collect_regroup_press_candidates(
            game_state,
            card_mask,
            greater_action,
            greater_type,
            hand_cards,
            cur_rank,
        )
    except Exception:
        raw = []

    for rec in raw or []:
        _add("regroup", rec)

    return out


def _core_break_penalty(
    engine: Any,
    game_state: Dict[str, Any],
    rec: Dict[str, Any],
) -> Tuple[float, Optional[str]]:
    """拆核软/硬惩罚；Bomb/SF 部分拆 → 硬否决。

    GUA-285：mask ``_get_broken_core_type`` 与 group_members
    ``_action_breaks_core_structure`` 取并集，避免 mask 已散但结构仍整。
    """
    action_type = str(rec.get("type") or "")
    if action_type == "PASS":
        return 0.0, None

    cards = list(rec.get("cards") or [])
    press_rank = str(rec.get("rank") or "")
    broken_mask = engine._get_broken_core_type(
        [action_type, press_rank, cards],
        engine._card_mask or {},
        engine._group_type_map or {},
        engine._group_members,
    )
    broken_members = _broken_core_from_group_members(engine, game_state, rec)
    broken = _merge_core_break_types(broken_mask, broken_members)

    if broken in ("Bomb", "StraightFlush"):
        return 999.0, broken
    if broken == "straight":
        return 0.12, broken
    if broken in ("trips", "pair", "trip_in_three_with_two", "pair_in_three_with_two"):
        return 0.06, broken
    return 0.0, broken


def _belief_counter_risk_penalty(
    engine: Any,
    game_state: Dict[str, Any],
    rec: Dict[str, Any],
) -> float:
    action_type = str(rec.get("type") or "")
    if action_type == "PASS":
        return 0.0
    if engine._belief_gate_counter_press(game_state, rec):
        return 0.35
    # soft risk only: can_opponent_form_type without hard block
    counter = engine._rule_card_counter_from_state(game_state)
    if counter is None:
        return 0.0
    greater_pos = int(game_state.get("greaterPos", -1) or -1)
    press_rank = str(rec.get("rank") or "")
    if greater_pos < 0 or not press_rank:
        return 0.0
    if counter.can_opponent_form_type(
        greater_pos, action_type, press_rank, game_state
    ):
        belief = game_state.get("_belief") or {}
        opp_risks = belief.get("opp_bomb_risks") or {}
        risk = float(opp_risks.get(greater_pos, 0) or 0)
        return 0.12 + (0.08 if risk >= 0.6 else 0.0)
    return 0.0


# §3.4 / §3.3.3 豁免与增益系数
E2_CONTROL_GAIN_BOOST = 0.22
E1_TEAMMATE_WIN_GAIN_BOOST = 0.38
E1_RESIDUAL_PENALTY_SCALE = 0.25
E4_SELF_RESCUE_CONTROL_BOOST = 0.18
E4_MAX_RESIDUAL_ROUNDS = 2
# GUA-294：队友已 PASS + 对手控牌 → 弱牌也须压制（防对手白跑牌）。
E5_TEAMMATE_PASSED_BLOCK_BOOST = 0.5
E5_TEAMMATE_PASSED_BLOCK_BOOST_STRONG = 0.3


def _my_pos(game_state: Dict[str, Any]) -> int:
    return int(game_state.get("myPos", 0) or 0)


def _is_endgame_reserved(
    game_state: Dict[str, Any],
    engine: Any,
) -> bool:
    """残局管线已激活或手牌进残局：候选竞争让位，保留 Q0–Q3 等硬规则。"""
    ec = game_state.get("_endgame_context") or {}
    if ec.get("is_active"):
        return True
    if game_state.get("_endgame_in_progress"):
        return True
    if game_state.get("_endgame_q1_hit"):
        return True
    hand_cards = game_state.get("handCards") or []
    if len(hand_cards) <= 10:
        return True
    if hasattr(engine, "_is_in_endgame_state"):
        try:
            if engine._is_in_endgame_state(hand_cards, game_state):
                return True
        except Exception:
            pass
    return False


def is_competition_enabled(
    game_state: Dict[str, Any],
    engine: Any,
) -> bool:
    """是否应跑 GUA-283 候选竞争（中期跟压且非残局）。"""
    if _is_endgame_reserved(game_state, engine):
        return False
    return _is_follow_press_scenario(game_state)


def _teammate_pos(game_state: Dict[str, Any]) -> int:
    return (_my_pos(game_state) + 2) % 4


def _resolve_proactive_exemption(
    game_state: Dict[str, Any],
    residual_rounds: int = 99,
) -> Optional[str]:
    """地板未触发时的主动豁免（顺序与 check_regroup_exemption 一致）。"""
    my_rest = _seat_rest(game_state, _my_pos(game_state))
    if my_rest <= 5:
        return "E4"
    mate_rest = _seat_rest(game_state, _teammate_pos(game_state))
    if mate_rest <= 5:
        return "E1"
    return None


def _self_rescue_control_boost(
    game_state: Dict[str, Any],
    rec: Dict[str, Any],
    residual_rounds: int,
) -> float:
    """E4：自己 ≤5 张且出完可两手内收尾 → 抬高夺权收益。"""
    if str(rec.get("type") or "") == "PASS":
        return 0.0
    if _seat_rest(game_state, _my_pos(game_state)) > 5:
        return 0.0
    if residual_rounds > E4_MAX_RESIDUAL_ROUNDS:
        return 0.0
    return E4_SELF_RESCUE_CONTROL_BOOST


def _teammate_sprint_win_gain(
    game_state: Dict[str, Any],
    rec: Dict[str, Any],
) -> float:
    """E1：队友 ≤5 张冲刺 → teammate_win_gain 可盖过残手罚。"""
    if str(rec.get("type") or "") == "PASS":
        return 0.0
    mate_rest = _seat_rest(game_state, _teammate_pos(game_state))
    if mate_rest > 5:
        return 0.0
    return E1_TEAMMATE_WIN_GAIN_BOOST


def _enemy_block_control_boost(
    engine: Any,
    game_state: Dict[str, Any],
    rec: Dict[str, Any],
) -> float:
    """E2：敌 ≤5 张且压住可阻断头游 → current_control_gain +0.22。"""
    if str(rec.get("type") or "") == "PASS":
        return 0.0
    my_pos = int(game_state.get("myPos", 0) or 0)
    teammate = _teammate_pos(game_state)
    greater_pos = int(game_state.get("greaterPos", -1) or -1)
    if greater_pos in (-1, my_pos, teammate):
        return 0.0
    opp_rest = _seat_rest(game_state, greater_pos)
    if opp_rest > 5:
        return 0.0
    press_rank = str(rec.get("rank") or "")
    action_type = str(rec.get("type") or "")
    if not press_rank or not action_type:
        return 0.0
    counter = engine._rule_card_counter_from_state(game_state)
    if counter is None:
        return 0.0
    if counter.can_opponent_form_type(
        greater_pos, action_type, press_rank, game_state
    ):
        return 0.0
    return E2_CONTROL_GAIN_BOOST


def _teammate_passed_block_gain(
    engine: Any,
    game_state: Dict[str, Any],
    rec: Dict[str, Any],
) -> float:
    """GUA-294：队友已 PASS + 对手控牌 → 抬高「压制」收益，弱牌也须收回牌权。

    场景：当前 greater 是**对手**（非自己、非队友）打出，且**队友在本圈已 PASS**
    ——若我方也 PASS，则对手白跑一手继续控牌，队友此前 PASS 等于浪费。
    此时即便牌力超弱也应出一手合法压制（最省的那手），避免对手跑牌。
    仅对「压制」候选（非 PASS）加成；PASS 候选不享受。

    牌力越弱加成越大：超弱/助攻 用 E5_TEAMMATE_PASSED_BLOCK_BOOST，
    其余角色用 E5_TEAMMATE_PASSED_BLOCK_BOOST_STRONG。
    """
    if str(rec.get("type") or "") == "PASS":
        return 0.0
    if not game_state.get("_teammate_passed_current_trick"):
        return 0.0
    my_pos = int(game_state.get("myPos", 0) or 0)
    great = int(game_state.get("greaterPos", -1) or -1)
    if great in (-1, my_pos, _teammate_pos(game_state)):
        return 0.0
    role = getattr(engine, "_current_role", None) or "主攻"
    if role in ("助攻", "超弱"):
        return E5_TEAMMATE_PASSED_BLOCK_BOOST
    return E5_TEAMMATE_PASSED_BLOCK_BOOST_STRONG


def _apply_exemption_to_penalties(
    exemption: Optional[str],
    *,
    plan_loss: float,
    waste_penalty: float,
    structure_penalty: float,
) -> Tuple[float, float, float]:
    """E1：残手软罚大幅减免，teammate_win_gain 另行加成。"""
    if exemption == "E1":
        scale = E1_RESIDUAL_PENALTY_SCALE
        return plan_loss * scale, waste_penalty * scale, structure_penalty * scale
    if exemption in ("E2", "E3", "E4"):
        return plan_loss * 0.6, waste_penalty * 0.6, structure_penalty * 0.6
    return plan_loss, waste_penalty, structure_penalty


def _teammate_yield_gain(
    engine: Any,
    game_state: Dict[str, Any],
    rec: Dict[str, Any],
) -> float:
    """队友领出圈：PASS 增益 / 自私跟压减益。"""
    if not getattr(engine, "_gua282_teammate_led_current_trick", lambda: False)():
        return 0.0
    greater_action = game_state.get("greaterAction") or []
    greater_type = str(greater_action[0] or "") if greater_action else ""
    if getattr(engine, "_gua282_takeover_ok", lambda *_a, **_k: False)(
        game_state, greater_type
    ):
        return 0.0

    role = getattr(engine, "_current_role", None) or "主攻"
    if str(rec.get("type") or "") == "PASS":
        if role in ("助攻", "超弱"):
            return 0.28
        if role in ("主攻", "超强主攻"):
            return 0.12
        return 0.08

    if role in ("助攻", "超弱"):
        return -0.18
    if role in ("主攻", "超强主攻"):
        return -0.08
    return 0.0


def _control_gain(
    game_state: Dict[str, Any],
    rec: Dict[str, Any],
) -> float:
    if str(rec.get("type") or "") == "PASS":
        return 0.0
    gain = 0.32
    my_pos = int(game_state.get("myPos", 0) or 0)
    enemies = ((my_pos + 1) % 4, (my_pos + 3) % 4)
    if any(_seat_rest(game_state, s) <= 2 for s in enemies):
        gain += 0.15
    return gain


def _is_joker_single(
    rec: Dict[str, Any],
    cur_rank: str,
) -> bool:
    """GUA-298：候选是否为「大王/小王」单张跟压（HR=大王, SB=小王）。"""
    if str(rec.get("type") or "") != "Single":
        return False
    rank = str(rec.get("rank") or "")
    if rank in ("R", "B"):
        return True
    for c in (rec.get("cards") or []):
        if str(c) in ("HR", "SB"):
            return True
    return False


def _has_non_joker_single_press(
    game_state: Dict[str, Any],
    cur_rank: str,
) -> bool:
    """GUA-298：actionList 是否存在「非王」单张能压过 greaterAction。"""
    from src.v.nn.endgame.endgame_decide import (
        _action_beats_greater,
        _get_declared_action_type,
        _is_bomb_like_action,
    )
    from src.v.nn.guards.v7_guards import get_action_type

    greater_action = game_state.get("greaterAction") or []
    action_list = game_state.get("actionList") or []
    if not greater_action or greater_action[0] in ("PASS", ""):
        return False
    if get_action_type(greater_action) != "Single":
        return False
    for action in action_list:
        try:
            if _get_declared_action_type(action) in ("PASS",):
                continue
            if _is_bomb_like_action(action):
                continue
            if get_action_type(action) != "Single":
                continue
            if not _action_beats_greater(action, greater_action, cur_rank):
                continue
            cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
            if any(str(cac) in ("HR", "SB") for cac in cards):
                continue
            return True
        except Exception:
            continue
    return False


def _preserve_joker_control_penalty(
    engine: Any,
    game_state: Dict[str, Any],
    rec: Dict[str, Any],
    cur_rank: str,
) -> float:
    """GUA-298：跟在廉可压单后烧王作普通单 → 罚分，防凭 E3 豁免超车。

    主攻应顺势跟小单、保留王作控制。当候选为单张王且存在非王普通单也能
    压过 greaterAction 时，出王属浪费最高控制牌 → 罚 PRESERVE_JOKER_CONTROL_PENALTY。
    仅当没有廉可压单（只有靠王才能拿圈）时为 0，不误伤合法用王。
    """
    if not _is_joker_single(rec, cur_rank):
        return 0.0
    if not _is_follow_press_scenario(game_state):
        return 0.0
    if not _has_non_joker_single_press(game_state, cur_rank):
        return 0.0
    return PRESERVE_JOKER_CONTROL_PENALTY


def score_play_candidate(
    engine: Any,
    game_state: Dict[str, Any],
    source: str,
    rec: Dict[str, Any],
    *,
    baseline_power: float,
    baseline_rounds: int,
) -> CandidateScore:
    """出牌前残手前瞻 + exec_weight（§3.4）。"""
    hand_cards = list(game_state.get("handCards") or [])
    cur_rank = str(game_state.get("curRank", "2"))
    action_type = str(rec.get("type") or "")

    teammate_gain = (
        _teammate_yield_gain(engine, game_state, rec)
        + _teammate_sprint_win_gain(game_state, rec)
    )
    control_gain = (
        _control_gain(game_state, rec)
        + _enemy_block_control_boost(engine, game_state, rec)
    )
    belief_penalty = _belief_counter_risk_penalty(engine, game_state, rec)
    core_penalty, broken = _core_break_penalty(engine, game_state, rec)

    if core_penalty >= 100:
        return CandidateScore(
            source=source,
            rec=rec,
            exec_weight=-999.0,
            control_gain=control_gain,
            teammate_gain=teammate_gain,
            core_break_penalty=core_penalty,
            belief_penalty=belief_penalty,
            baseline_power=baseline_power,
            vetoed=True,
            veto_reason=f"core_{broken}",
        )

    if action_type == "PASS":
        residual = evaluate_residual_hand(
            hand_cards,
            cur_rank,
            baseline_rounds=baseline_rounds,
            baseline_power=baseline_power,
        )
        exec_weight = teammate_gain - belief_penalty * 0.25
        return CandidateScore(
            source=source,
            rec=rec,
            exec_weight=exec_weight,
            teammate_gain=teammate_gain,
            belief_penalty=belief_penalty * 0.25,
            residual_power=residual.metrics.residual_power,
            baseline_power=baseline_power,
            has_anchor=residual.metrics.has_anchor,
        )

    cards = list(rec.get("cards") or [])
    try:
        residual = evaluate_after_counter_action(
            hand_cards,
            cards,
            cur_rank,
            baseline_rounds=baseline_rounds,
            baseline_power=baseline_power,
        )
    except ValueError:
        return CandidateScore(
            source=source,
            rec=rec,
            exec_weight=-999.0,
            vetoed=True,
            veto_reason="invalid_cards",
        )

    power_drop = max(0.0, baseline_power - float(residual.metrics.residual_power))
    rounds_increase = max(
        0, residual.metrics.residual_rounds - baseline_rounds
    )
    plan_loss = (
        0.45 * (power_drop / max(NORM_MAX_POWER, 1.0))
        + 0.06 * rounds_increase
    )
    waste_penalty = residual_waste_penalty(residual.metrics)
    structure_penalty = residual_structure_penalty(residual.metrics)

    exemption: Optional[str] = None
    if residual.residual_floor_veto:
        exemption = check_regroup_exemption(game_state, rec, engine, residual)
        if not exemption:
            return CandidateScore(
                source=source,
                rec=rec,
                exec_weight=-999.0,
                control_gain=control_gain,
                teammate_gain=teammate_gain,
                plan_loss=plan_loss,
                core_break_penalty=core_penalty,
                waste_penalty=waste_penalty,
                structure_penalty=structure_penalty,
                belief_penalty=belief_penalty,
                residual_power=residual.metrics.residual_power,
                baseline_power=baseline_power,
                power_drop=power_drop,
                has_anchor=residual.metrics.has_anchor,
                vetoed=True,
                veto_reason="residual_" + ",".join(residual.floor_reasons),
            )

    # E1/E4 主动豁免（地板未触发时，顺序同 check_regroup_exemption）
    if exemption is None:
        exemption = _resolve_proactive_exemption(
            game_state, residual.metrics.residual_rounds,
        )

    # E3：无反压窗口（信念已确认）→ 标记 E3 以减免残手罚
    if exemption is None and _enemy_block_control_boost(engine, game_state, rec) > 0:
        exemption = "E2"
    elif exemption is None:
        belief = game_state.get("_belief") or {}
        greater_pos = int(game_state.get("greaterPos", -1) or -1)
        opp_risks = belief.get("opp_bomb_risks") or {}
        risk = float(opp_risks.get(greater_pos, 0) or 0)
        counter = engine._rule_card_counter_from_state(game_state)
        press_rank = str(rec.get("rank") or "")
        if (
            counter is not None
            and greater_pos >= 0
            and press_rank
            and not counter.can_opponent_form_type(
                greater_pos, action_type, press_rank, game_state,
            )
            and risk < 0.6
        ):
            exemption = "E3"

    # GUA-298：跟在廉可压单后烧王作普通单 → 罚分 + 不给 E3 豁免兜底（保留王作控制）
    joker_penalty = _preserve_joker_control_penalty(
        engine, game_state, rec, cur_rank,
    )
    if joker_penalty and exemption == "E3":
        exemption = None

    control_gain += _self_rescue_control_boost(
        game_state, rec, residual.metrics.residual_rounds,
    )
    # GUA-294：队友已 PASS + 对手控牌 → 弱牌也须收回牌权（防对手白跑）。
    control_gain += _teammate_passed_block_gain(engine, game_state, rec)

    plan_loss, waste_penalty, structure_penalty = _apply_exemption_to_penalties(
        exemption,
        plan_loss=plan_loss,
        waste_penalty=waste_penalty,
        structure_penalty=structure_penalty,
    )

    exec_weight = (
        control_gain
        + teammate_gain
        - plan_loss
        - core_penalty
        - waste_penalty
        - structure_penalty
        - belief_penalty
        - joker_penalty
    )

    # §3.4：can_opponent_form_type 软风险 → 折半夺权；E2/E3 豁免不减 E2 加成
    if belief_penalty >= 0.12 and control_gain > 0 and exemption not in ("E2", "E3"):
        e2_part = _enemy_block_control_boost(engine, game_state, rec)
        exec_weight -= max(0.0, control_gain - e2_part) * 0.45

    return CandidateScore(
        source=source,
        rec=rec,
        exec_weight=exec_weight,
        control_gain=control_gain,
        teammate_gain=teammate_gain,
        plan_loss=plan_loss,
        core_break_penalty=core_penalty,
        waste_penalty=waste_penalty,
        structure_penalty=structure_penalty,
        belief_penalty=belief_penalty,
        residual_power=residual.metrics.residual_power,
        baseline_power=baseline_power,
        power_drop=power_drop,
        has_anchor=residual.metrics.has_anchor,
        exemption=exemption or "",
        joker_penalty=joker_penalty,
    )


def run_candidate_competition(
    engine: Any,
    game_state: Dict[str, Any],
    action_list: List,
    primary_rec: Optional[Dict[str, Any]],
    primary_act_index: int,
) -> CompetitionResult:
    """GUA-075 主路径：候选竞争，返回最优 (rec, act_index)。"""
    if not is_competition_enabled(game_state, engine):
        reason = (
            "endgame_reserved"
            if _is_endgame_reserved(game_state, engine)
            else "gua075_primary_skip"
        )
        return CompetitionResult(
            rec=primary_rec,
            act_index=primary_act_index,
            picked_source=reason,
        )

    plan = getattr(engine, "_active_plan", None) or getattr(engine, "_best_plan", None)
    baseline_power = float(getattr(plan, "power_score", 0.0) or 0.0)
    baseline_rounds = int(plan.num_rounds()) if plan is not None else 99

    candidates = collect_competition_candidates(
        engine, game_state, primary_rec, action_list, include_regroup=True,
    )

    scored: List[CandidateScore] = []
    for source, rec in candidates:
        scored.append(
            score_play_candidate(
                engine,
                game_state,
                source,
                rec,
                baseline_power=baseline_power,
                baseline_rounds=baseline_rounds,
            )
        )

    valid: List[Tuple[CandidateScore, int]] = []
    for item in scored:
        idx = engine._match_actionList(item.rec, action_list)
        if idx < 0 and str(item.rec.get("type")) != "PASS":
            continue
        if item.vetoed and item.exec_weight <= -900:
            continue
        if idx < 0 and str(item.rec.get("type")) == "PASS":
            for i, a in enumerate(action_list):
                if a and a[0] == "PASS":
                    idx = i
                    break
        if idx < 0:
            continue
        valid.append((item, idx))

    if not valid:
        return CompetitionResult(
            rec=primary_rec,
            act_index=primary_act_index,
            scores=scored,
            picked_source="gua075_primary_fallback",
        )

    best_score, best_idx = max(valid, key=lambda x: x[0].exec_weight)

    game_state["_gua283_competition"] = {
        "picked": best_score.source,
        "exec_weight": round(best_score.exec_weight, 4),
        "power_drop": round(best_score.power_drop, 3),
        "baseline_power": round(best_score.baseline_power, 3),
        "residual_power": round(best_score.residual_power, 3),
        "pool_size": len(candidates),
        "trace": [
            {
                "source": s.source,
                "type": s.rec.get("type"),
                "rank": s.rec.get("rank"),
                "weight": round(s.exec_weight, 4),
                "power_drop": round(s.power_drop, 3),
                "vetoed": s.vetoed,
                "exemption": s.exemption,
                "control_gain": round(s.control_gain, 3),
                "teammate_gain": round(s.teammate_gain, 3),
            }
            for s in scored
        ],
    }

    return CompetitionResult(
        rec=best_score.rec,
        act_index=best_idx,
        scores=scored,
        picked_source=best_score.source,
    )
