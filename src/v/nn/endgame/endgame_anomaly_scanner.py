# -*- coding: utf-8 -*-
"""残局异常扫描器。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .endgame_decide import EndgameDecider, _rank_beats_same_type
from .endgame_preprocessor import EndgamePreprocessor

try:
    from ..guards.v7_guards import (
        ACTION_TYPE_BOMB,
        ACTION_TYPE_PAIR,
        ACTION_TYPE_PASS,
        ACTION_TYPE_SINGLE,
        ACTION_TYPE_STRAIGHT_FLUSH,
        ACTION_TYPE_THREE_PAIR,
        ACTION_TYPE_THREE_WITH_TWO,
        ACTION_TYPE_TRIPS,
        ACTION_TYPE_TWO_TRIPS,
        get_action_rank,
        get_action_type,
        get_card_value,
        is_bomb,
    )
    GUARD_TOOLS_OK = True
except ImportError:
    ACTION_TYPE_SINGLE = "Single"
    ACTION_TYPE_PAIR = "Pair"
    ACTION_TYPE_TRIPS = "Trips"
    ACTION_TYPE_THREE_WITH_TWO = "ThreeWithTwo"
    ACTION_TYPE_THREE_PAIR = "ThreePair"
    ACTION_TYPE_TWO_TRIPS = "TwoTrips"
    ACTION_TYPE_BOMB = "Bomb"
    ACTION_TYPE_STRAIGHT_FLUSH = "StraightFlush"
    ACTION_TYPE_PASS = "PASS"
    GUARD_TOOLS_OK = False


_COMPLEX_SAME_TYPE_ACTIONS = {
    ACTION_TYPE_THREE_WITH_TWO,
    ACTION_TYPE_THREE_PAIR,
    ACTION_TYPE_TWO_TRIPS,
}


def _action_cards(action: Sequence[Any]) -> List[str]:
    if isinstance(action, list) and len(action) >= 3 and isinstance(action[2], list):
        return [str(card) for card in action[2]]
    return []


def _action_signature(action: Sequence[Any]) -> Tuple[str, str, Tuple[str, ...]]:
    if not isinstance(action, list) or len(action) < 2:
        return ("", "", tuple())
    return (
        str(action[0]),
        str(action[1]),
        tuple(sorted(_action_cards(action))),
    )


def _sample_to_action_list(sample: Sequence[Dict[str, Any]]) -> List[List[Any]]:
    action_list: List[List[Any]] = []
    for item in sample or []:
        action_list.append([
            str(item.get("type", "")),
            str(item.get("rank", "")),
            [str(card) for card in item.get("cards", [])],
        ])
    return action_list


def _is_pass(action: Sequence[Any]) -> bool:
    return get_action_type(action) == ACTION_TYPE_PASS if GUARD_TOOLS_OK else bool(action and action[0] == "PASS")


def _is_same_type_beater(action: Sequence[Any], greater_action: Sequence[Any], cur_rank: str) -> bool:
    if not GUARD_TOOLS_OK or not action or not greater_action:
        return False
    action_type = get_action_type(action)
    greater_type = get_action_type(greater_action)
    if action_type != greater_type:
        return False

    if action_type == ACTION_TYPE_SINGLE:
        cards = _action_cards(action)
        greater_cards = _action_cards(greater_action)
        if not cards or not greater_cards:
            return False
        return get_card_value(cards[0], cur_rank) > get_card_value(greater_cards[0], cur_rank)

    if action_type in (ACTION_TYPE_PAIR, ACTION_TYPE_TRIPS):
        action_rank = get_action_rank(action)
        greater_rank = get_action_rank(greater_action)
        return _rank_beats_same_type(greater_rank, action_rank, cur_rank)

    if action_type in _COMPLEX_SAME_TYPE_ACTIONS:
        action_rank = get_action_rank(action)
        greater_rank = get_action_rank(greater_action)
        return _rank_beats_same_type(greater_rank, action_rank, cur_rank)

    if action_type == ACTION_TYPE_STRAIGHT_FLUSH:
        action_rank = get_action_rank(action)
        greater_rank = get_action_rank(greater_action)
        return _rank_beats_same_type(greater_rank, action_rank, cur_rank)

    if action_type == ACTION_TYPE_BOMB:
        action_cards = _action_cards(action)
        greater_cards = _action_cards(greater_action)
        if len(action_cards) != len(greater_cards):
            return len(action_cards) > len(greater_cards)
        action_rank = get_action_rank(action)
        greater_rank = get_action_rank(greater_action)
        return _rank_beats_same_type(greater_rank, action_rank, cur_rank)

    return False


def _is_legal_beater(action: Sequence[Any], greater_action: Sequence[Any], cur_rank: str) -> bool:
    if not GUARD_TOOLS_OK or not action or not greater_action or _is_pass(action):
        return False
    if _is_same_type_beater(action, greater_action, cur_rank):
        return True

    action_type = get_action_type(action)
    greater_type = get_action_type(greater_action)
    if action_type in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
        if greater_type not in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            return True
        if action_type == ACTION_TYPE_STRAIGHT_FLUSH and greater_type == ACTION_TYPE_BOMB:
            return True
        if action_type == ACTION_TYPE_BOMB and greater_type == ACTION_TYPE_STRAIGHT_FLUSH:
            return False
        return _is_same_type_beater(action, greater_action, cur_rank)
    return False


def _find_record_my_pos(record: Dict[str, Any]) -> int:
    player_id = record.get("player_id", -1)
    if isinstance(player_id, int) and 0 <= player_id <= 3:
        return player_id
    player_name = str(record.get("player_name", ""))
    return 2 if ("yf2" in player_name.lower()) else 0


def _advance_trick_state(
    remaining: List[int],
    greater_pos: int,
    greater_action: Optional[List[Any]],
    pass_count: int,
    action_entry: Dict[str, Any],
) -> Tuple[List[int], int, Optional[List[Any]], int]:
    cur_pos = int(action_entry.get("cur_pos", -1))
    cur_action = action_entry.get("cur_action", []) or []
    cards = _action_cards(cur_action)

    if 0 <= cur_pos < 4:
        remaining[cur_pos] = max(0, remaining[cur_pos] - len(cards))

    if _is_pass(cur_action):
        if greater_action:
            pass_count += 1
            if pass_count >= 3:
                greater_action = None
                pass_count = 0
        return remaining, greater_pos, greater_action, pass_count

    greater_pos = cur_pos
    greater_action = list(cur_action)
    pass_count = 0
    return remaining, greater_pos, greater_action, pass_count


def _iter_play_decision_snapshots(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    snapshots: List[Dict[str, Any]] = []
    actions = record.get("actions", []) or []
    my_decisions = record.get("my_decisions", []) or []
    my_pos = _find_record_my_pos(record)
    cur_rank_default = str((record.get("game_info") or {}).get("curRank", "2"))

    remaining = [27, 27, 27, 27]
    greater_pos = -1
    greater_action: Optional[List[Any]] = None
    pass_count = 0
    action_cursor = 0

    for decision_index, decision in enumerate(my_decisions):
        ctx = decision.get("context", {}) or {}
        if ctx.get("stage") != "play":
            continue

        target_signature = _action_signature(decision.get("action", []))
        matched = False
        while action_cursor < len(actions):
            action_entry = actions[action_cursor]
            cur_action = action_entry.get("cur_action", []) or []
            cur_pos = int(action_entry.get("cur_pos", -1))
            signature = _action_signature(cur_action)
            if cur_pos == my_pos and signature == target_signature:
                hand_cards = [str(card) for card in ctx.get("handCards", [])]
                snapshot_remaining = list(remaining)
                snapshot_remaining[my_pos] = len(hand_cards) if hand_cards else snapshot_remaining[my_pos]
                snapshots.append({
                    "decision_index": decision_index,
                    "my_pos": my_pos,
                    "chosen_action": list(decision.get("action", [])),
                    "layer": decision.get("layer"),
                    "candidates_count": decision.get("candidates_count"),
                    "action_list_size": ctx.get("actionList_size", 0),
                    "action_list_sample": _sample_to_action_list(ctx.get("actionList_sample", [])),
                    "action_list_is_complete": bool(
                        ctx.get("actionList_sample")
                        and ctx.get("actionList_size") == len(ctx.get("actionList_sample", []))
                    ),
                    "hand_cards": hand_cards,
                    "cur_rank": str(ctx.get("curRank") or cur_rank_default or "2"),
                    "cur_pos": ctx.get("curPos", cur_pos),
                    "greater_pos": ctx.get("greaterPos", greater_pos),
                    "greater_action": list(ctx.get("greaterAction") or greater_action or []),
                    "numofplayers": snapshot_remaining,
                })
                remaining, greater_pos, greater_action, pass_count = _advance_trick_state(
                    remaining, greater_pos, greater_action, pass_count, action_entry,
                )
                action_cursor += 1
                matched = True
                break

            remaining, greater_pos, greater_action, pass_count = _advance_trick_state(
                remaining, greater_pos, greater_action, pass_count, action_entry,
            )
            action_cursor += 1

        if not matched:
            hand_cards = [str(card) for card in ctx.get("handCards", [])]
            snapshots.append({
                "decision_index": decision_index,
                "my_pos": my_pos,
                "chosen_action": list(decision.get("action", [])),
                "layer": decision.get("layer"),
                "candidates_count": decision.get("candidates_count"),
                "action_list_size": ctx.get("actionList_size", 0),
                "action_list_sample": _sample_to_action_list(ctx.get("actionList_sample", [])),
                "action_list_is_complete": bool(
                    ctx.get("actionList_sample")
                    and ctx.get("actionList_size") == len(ctx.get("actionList_sample", []))
                ),
                "hand_cards": hand_cards,
                "cur_rank": str(ctx.get("curRank") or cur_rank_default or "2"),
                "cur_pos": ctx.get("curPos", my_pos),
                "greater_pos": ctx.get("greaterPos", greater_pos),
                "greater_action": list(ctx.get("greaterAction") or greater_action or []),
                "numofplayers": list(remaining),
                "unmatched_action": True,
            })

    return snapshots


def scan_endgame_snapshot(
    snapshot: Dict[str, Any],
    *,
    critical_remaining: Sequence[int] = (1, 3),
) -> List[Dict[str, Any]]:
    anomalies: List[Dict[str, Any]] = []
    action_list = snapshot.get("action_list_sample", []) or []
    if not action_list:
        return anomalies

    game_state = {
        "myPos": snapshot["my_pos"],
        "curPos": snapshot.get("cur_pos", snapshot["my_pos"]),
        "greaterPos": snapshot.get("greater_pos", -1),
        "greaterAction": snapshot.get("greater_action", []),
        "handCards": list(snapshot.get("hand_cards", [])),
        "actionList": list(action_list),
        "curRank": snapshot.get("cur_rank", "2"),
        "numofplayers": list(snapshot.get("numofplayers", [27, 27, 27, 27])),
    }
    EndgamePreprocessor().preprocess(game_state)
    ec = game_state.get("_endgame_context", {})
    if not ec.get("is_active"):
        return anomalies

    chosen_action = snapshot.get("chosen_action", [])
    my_pos = snapshot["my_pos"]
    enemy_positions = {(my_pos + 1) % 4, (my_pos + 3) % 4}
    greater_pos = int(game_state.get("greaterPos", -1))
    greater_action = game_state.get("greaterAction", []) or []
    cur_rank = str(game_state.get("curRank", "2"))
    non_pass_candidates = [act for act in action_list if not _is_pass(act)]
    decider = EndgameDecider()
    filtered, banned_empty = decider.apply_banned_filter(action_list, game_state)
    current_idx, current_action = decider.decide(
        game_state,
        action_list if banned_empty else filtered,
    )
    current_action = current_action or ["PASS", "PASS", "PASS"]
    current_is_pass = _is_pass(current_action)

    if _is_pass(chosen_action):
        legal_same_type = [
            act for act in action_list
            if _is_same_type_beater(act, greater_action, cur_rank)
        ]
        legal_beaters = [
            act for act in action_list
            if _is_legal_beater(act, greater_action, cur_rank)
        ]
        enemy_remaining = None
        if greater_pos in enemy_positions and 0 <= greater_pos < len(game_state["numofplayers"]):
            enemy_remaining = game_state["numofplayers"][greater_pos]

        if enemy_remaining in critical_remaining and legal_beaters and current_is_pass:
            anomalies.append({
                "code": "enemy_critical_pass_with_legal_beater",
                "severity": "high",
                "message": "敌方临门张数时，当前代码重放后仍存在合法可压却 PASS。",
                "enemy_pos": greater_pos,
                "enemy_remaining": enemy_remaining,
                "legal_candidates": legal_beaters,
                "same_type_candidates": legal_same_type,
                "current_action": current_action,
                "current_decision_index": current_idx,
            })

    if snapshot.get("action_list_is_complete") and greater_pos in enemy_positions:
        filtered_non_pass = [act for act in filtered if not _is_pass(act)]
        any_recommended = any(
            ectx.get("recommended_types")
            for ectx in ec.get("enemies", {}).values()
        )
        if (
            any_recommended
            and not banned_empty
            and not filtered_non_pass
            and non_pass_candidates
            and current_is_pass
        ):
            anomalies.append({
                "code": "recommended_filtered_to_pass_only",
                "severity": "high",
                "message": "recommended_types 非空，且当前代码重放后 banned 过滤仍只剩 PASS。",
                "enemy_pos": greater_pos,
                "enemy_remaining": game_state["numofplayers"][greater_pos] if 0 <= greater_pos < 4 else None,
                "legal_candidates": non_pass_candidates,
                "filtered_candidates": filtered,
                "current_action": current_action,
                "current_decision_index": current_idx,
            })

    return anomalies


def scan_game_record(
    record: Dict[str, Any],
    *,
    file_name: str = "",
    critical_remaining: Sequence[int] = (1, 3),
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for snapshot in _iter_play_decision_snapshots(record):
        anomalies = scan_endgame_snapshot(snapshot, critical_remaining=critical_remaining)
        for anomaly in anomalies:
            enriched = dict(anomaly)
            enriched.update({
                "file": file_name,
                "decision_index": snapshot["decision_index"],
                "layer": snapshot.get("layer"),
                "chosen_action": snapshot.get("chosen_action"),
                "greater_action": snapshot.get("greater_action"),
                "cur_rank": snapshot.get("cur_rank"),
                "numofplayers": snapshot.get("numofplayers"),
                "action_list_size": snapshot.get("action_list_size"),
                "action_list_sample": snapshot.get("action_list_sample"),
            })
            findings.append(enriched)
    return findings


def scan_record_file(
    path: Path,
    *,
    critical_remaining: Sequence[int] = (1, 3),
) -> List[Dict[str, Any]]:
    record = json.loads(path.read_text(encoding="utf-8"))
    return scan_game_record(record, file_name=path.name, critical_remaining=critical_remaining)


def format_anomaly(anomaly: Dict[str, Any]) -> str:
    enemy_remaining = anomaly.get("enemy_remaining")
    players = anomaly.get("numofplayers")
    players_text = "/".join(str(v) for v in players) if isinstance(players, list) else "-"
    return (
        f"[{anomaly.get('severity','?')}] {anomaly.get('code')} "
        f"{anomaly.get('file','')}#d{anomaly.get('decision_index','?')} "
        f"layer={anomaly.get('layer')} enemy_rem={enemy_remaining} "
        f"players={players_text} chosen={anomaly.get('chosen_action')} "
        f"current={anomaly.get('current_action')} "
        f"greater={anomaly.get('greater_action')}"
    )
